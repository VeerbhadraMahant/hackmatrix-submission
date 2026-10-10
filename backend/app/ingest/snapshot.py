"""Real, DB-backed per-user `DashboardSnapshot` builder.

This module is the integration seam that replaces the Phase-0
`app.ingest.fixtures.demo_dashboard_snapshot()` stub everywhere it was used
(routes.py, copilot/tools.py). It wires together every other agent's module:

    DB rows (models.py)
        -> pandas DataFrames (shape expected by app.analytics.*)
        -> app.analytics.recurring.detect_recurring        -> RecurringObligation list
        -> app.analytics.debt.compute_dti / credit_utilization
        -> app.analytics.savings.trailing_savings_rate / emergency_fund_months
        -> app.analytics.health_score.compute_health_score  -> HealthScore
        -> app.forecast.cashflow.build_forecast              -> CashFlowForecast
        -> app.analytics.anomalies.detect_anomalies          -> Fact[]
        -> app.analytics.benchmarks.benchmark_context        -> Fact[]
        -> app.recommend.engine.generate_recommendations     -> Recommendation[]
        -> schemas.DashboardSnapshot

Design decisions (documented here since they aren't dictated anywhere else):

  * "Starting balance" for forecasting/emergency-fund purposes is the sum of
    the user's *liquid* account balances (checking + savings). Credit cards,
    loans and investment accounts are excluded -- a forecast of "will my
    spendable cash run out" should not be inflated by a mutual fund balance
    the user can't spend on rent tomorrow, nor deflated by counting a credit
    card's outstanding balance as negative cash (that's debt pressure, a
    separate sub-score). `net_worth`, by contrast, DOES sum every account
    (credit cards/loans are already stored as negative balances).
  * "Monthly income" / "monthly expenses" are trailing-3-month averages
    (category != transfer), matching the window `trailing_savings_rate`
    itself uses internally, so the two numbers stay consistent with the
    `savings_rate` field.
  * `recurring_all` (includes the detected income recurring item, if any) is
    what's fed to the forecast/simulate/recommend engines, since they need
    the inflow to project cash flow correctly. `recurring_obligations` on the
    public `DashboardSnapshot` excludes the income entry -- consistent with
    the Phase-0 fixture's semantics ("obligations" = things you owe/pay).
  * `prior_health_score` for `trend_30d` is whatever was last cached in
    `InsightsSnapshotRow` for this user (not literally 30 days ago -- we
    don't have a scheduled recompute job -- but it's the most meaningful
    "before" we have, and is exactly what /events uses for its diff).
  * Unknown user_id (no accounts in the DB at all) falls back to the Phase-0
    fixture so the app never 500s on a bad/demo-less user_id.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from app.core import store

from app.analytics.anomalies import detect_anomalies
from app.analytics.benchmarks import benchmark_context
from app.analytics.debt import compute_dti, credit_utilization as _credit_utilization
from app.analytics.health_score import compute_health_score
from app.analytics.recurring import detect_recurring
from app.analytics.savings import emergency_fund_months, trailing_savings_rate
from app.forecast.cashflow import build_forecast
from app.ingest.fixtures import demo_dashboard_snapshot
from app.models import AccountRow, DebtRow, IncomeRow, InsightsSnapshotRow, TransactionRow
from app.recommend.engine import generate_recommendations
from app.core.auth import DEMO_USER_IDS
from app.schemas import (
    AnswerContract,
    CashFlowForecast,
    DashboardSnapshot,
    Debt,
    Fact,
    HealthScore,
    Prediction,
    RecurringObligation,
    TxnCategory,
)
from app.simulate.engine import ForecastInputs

_LIQUID_ACCOUNT_TYPES = {"checking", "savings"}
_FORECAST_HORIZON_DAYS = 90
_TRAILING_MONTHS = 3


# ---------------------------------------------------------------------------
# DB -> DataFrame / schema conversions
# ---------------------------------------------------------------------------


def _transactions_df(rows: list[TransactionRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=["id", "user_id", "account_id", "date", "amount", "merchant", "category", "is_recurring", "recurring_group_id"]
        )
    df = pd.DataFrame([r.model_dump() for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _debts_schema(rows: list[DebtRow], user_id: str) -> list[Debt]:
    return [
        Debt(
            id=d.id,
            user_id=user_id,
            account_id=d.account_id,
            principal=d.principal,
            interest_rate_apr=d.interest_rate_apr,
            minimum_payment=d.minimum_payment,
            due_day_of_month=d.due_day_of_month,
        )
        for d in rows
    ]


def _starting_balance(accounts: list[AccountRow]) -> float:
    """Sum of checking + savings balances -- see module docstring."""
    return float(sum(a.balance for a in accounts if a.type in _LIQUID_ACCOUNT_TYPES))


def _net_worth(accounts: list[AccountRow]) -> float:
    return float(sum(a.balance for a in accounts))


def _aggregate_credit_utilization(accounts: list[AccountRow]) -> Optional[float]:
    cards = [a for a in accounts if a.type == "credit_card" and a.credit_limit]
    if not cards:
        return None
    total_balance = sum(abs(a.balance) for a in cards)
    total_limit = sum(a.credit_limit for a in cards)
    return _credit_utilization(total_balance, total_limit)


def _avg_income_expenses(df: pd.DataFrame, months: int = _TRAILING_MONTHS) -> tuple[float, float]:
    """Trailing-`months`-month average monthly income/expenses, same window
    convention as `app.analytics.savings.trailing_savings_rate`."""
    if df.empty:
        return 0.0, 0.0
    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    as_of = work["date"].max()
    window_start = as_of - pd.DateOffset(months=months)
    window = work[(work["date"] > window_start) & (work["date"] <= as_of)]
    # Same exclusion as app.analytics.savings.trailing_savings_rate (transfers
    # and credit-card bill payments are not new spend -- see that module for
    # why credit_card_payment is excluded here).
    # SIP contributions move money into the user's own investments: that is saving, not spend.
    _excluded = {TxnCategory.transfer.value, TxnCategory.credit_card_payment.value, TxnCategory.investment_sip.value}
    window = window[~window["category"].isin(_excluded)]
    income_total = float(window.loc[window["amount"] > 0, "amount"].sum())
    expense_total = float(-window.loc[window["amount"] < 0, "amount"].sum())
    return income_total / months, expense_total / months


def _spending_consistency_cov(df: pd.DataFrame) -> float:
    """Coefficient of variation of total monthly (essential+discretionary)
    outflow across whatever months of history are available (excludes
    transfers). 0 months or 1 month of data -> 0.0 (perfectly "consistent" by
    definition of having nothing to compare)."""
    if df.empty:
        return 0.0
    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    _excluded = {TxnCategory.transfer.value, TxnCategory.credit_card_payment.value}
    work = work[(work["amount"] < 0) & (~work["category"].isin(_excluded))]
    if work.empty:
        return 0.0
    work["month"] = work["date"].dt.to_period("M")
    monthly = work.groupby("month")["amount"].sum().abs()
    values = monthly.tolist()
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    return abs(statistics.pstdev(values) / mean)


# ---------------------------------------------------------------------------
# Snapshot caching (InsightsSnapshotRow) -- powers the /timeline before/after diff
# ---------------------------------------------------------------------------


def get_last_snapshot(user_id: str) -> Optional[DashboardSnapshot]:
    """Most recently cached DashboardSnapshot for `user_id`, or None if this
    user has never had one computed/cached before."""
    row = store.get(InsightsSnapshotRow, user_id)
    if row is None:
        return None
    return DashboardSnapshot.model_validate_json(row.snapshot_json)


def _cache_snapshot(snapshot: DashboardSnapshot) -> None:
    # One doc per user (id=user_id) so the cache overwrites instead of growing.
    store.put(
        InsightsSnapshotRow(
            id=snapshot.user_id,
            user_id=snapshot.user_id,
            snapshot_json=snapshot.model_dump_json(),
            health_score=snapshot.health_score.overall,
        )
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def empty_dashboard_snapshot(user_id: str) -> DashboardSnapshot:
    """All-zero placeholder for a real user who hasn't added any data yet."""
    now = datetime.now(timezone.utc)
    return DashboardSnapshot(
        user_id=user_id,
        health_score=HealthScore(overall=0, sub_scores=[], computed_at=now),
        net_worth=0,
        monthly_income=0,
        monthly_expenses=0,
        savings_rate=0,
        recurring_obligations=[],
        debts=[],
        forecast=CashFlowForecast(
            generated_at=now, horizon_days=_FORECAST_HORIZON_DAYS, points=[], confidence=0,
            basis="No data yet -- add an account and some transactions to see a forecast.",
        ),
        insights=AnswerContract(narrative="Add your first account and transactions to get personalised insights."),
        generated_at=now,
        has_data=False,
    )


def build_dashboard_snapshot(user_id: str) -> DashboardSnapshot:
    """Build (and cache) a real DashboardSnapshot for `user_id` from the DB.

    A demo persona id with no accounts falls back to the Phase-0 fixture
    (never persisted/cached). Any other user with no accounts is a real,
    new user: they get an all-zero placeholder (`has_data=False`), never
    someone else's demo data.
    """
    accounts = store.query(AccountRow, user_id=user_id)
    if not accounts:
        if user_id in DEMO_USER_IDS:
            return demo_dashboard_snapshot(user_id)
        return empty_dashboard_snapshot(user_id)

    txn_rows = store.query(TransactionRow, user_id=user_id)
    debt_rows = store.query(DebtRow, user_id=user_id)
    # IncomeRow is queried for completeness/future use (e.g. irregular income
    # sources not visible as transactions yet); the recurring-detection path
    # below already recovers salary cadence from transaction history, which
    # is the richer signal for forecasting.
    store.query(IncomeRow, user_id=user_id)

    df = _transactions_df(list(txn_rows))
    debts = _debts_schema(list(debt_rows), user_id)

    starting_balance = _starting_balance(list(accounts))
    net_worth = _net_worth(list(accounts))

    recurring_all: list[RecurringObligation] = detect_recurring(df)
    recurring_obligations = [r for r in recurring_all if r.category != TxnCategory.income]

    monthly_income, monthly_expenses = _avg_income_expenses(df)
    savings_rate = trailing_savings_rate(df, months=_TRAILING_MONTHS)
    ef_months = emergency_fund_months(starting_balance, df, months_window=_TRAILING_MONTHS)
    dti = compute_dti(debts, monthly_income)
    credit_util = _aggregate_credit_utilization(list(accounts))
    spending_cov = _spending_consistency_cov(df)

    forecast = build_forecast(
        starting_balance=starting_balance,
        recurring=recurring_all,
        transactions=df,
        horizon_days=_FORECAST_HORIZON_DAYS,
    )

    prior = get_last_snapshot(user_id)
    health_score = compute_health_score(
        forecast=forecast,
        dti=dti,
        credit_utilization=credit_util,
        savings_rate_trailing=savings_rate,
        emergency_fund_months=ef_months,
        spending_cov=spending_cov,
        prior_health_score=prior.health_score if prior is not None else None,
    )

    forecast_inputs = ForecastInputs(
        starting_balance=starting_balance,
        recurring=recurring_all,
        debts=debts,
        transactions=df,
        horizon_days=_FORECAST_HORIZON_DAYS,
        monthly_income=monthly_income,
    )
    recommendations = generate_recommendations(
        recurring=recurring_all,
        debts=debts,
        health_score=health_score,
        forecast=forecast,
        forecast_inputs=forecast_inputs,
    )

    facts: list[Fact] = list(detect_anomalies(df))
    facts.append(
        Fact(
            text=f"Your average monthly savings rate over the trailing {_TRAILING_MONTHS} months is {savings_rate * 100:.0f}%.",
            value=savings_rate,
        )
    )
    for msg in benchmark_context(monthly_income, savings_rate, dti):
        facts.append(Fact(text=msg))

    predictions: list[Prediction] = []
    if forecast.first_gap_date is not None:
        gap_point = next((p for p in forecast.points if p.date == forecast.first_gap_date), None)
        predictions.append(
            Prediction(
                text=(
                    f"Your liquid balance is projected to dip below ₹0 around "
                    f"{forecast.first_gap_date.isoformat()} if current patterns continue."
                ),
                value=gap_point.p50 if gap_point else None,
                range_low=gap_point.p10 if gap_point else None,
                range_high=gap_point.p90 if gap_point else None,
                confidence=forecast.confidence,
                basis=forecast.basis,
            )
        )

    narrative = (
        f"Your overall financial health score is {health_score.overall:.0f}/100. "
        + (
            f"A projected cash-flow gap around {forecast.first_gap_date.isoformat()} is the most urgent risk. "
            if forecast.first_gap_date is not None
            else "No cash-flow gap is projected in the next 90 days. "
        )
        + (
            f"Debt payments consume {dti * 100:.0f}% of monthly income, and you have "
            f"{ef_months:.1f} months of essential expenses in reserve."
        )
    )

    insights = AnswerContract(
        narrative=narrative,
        facts=facts,
        predictions=predictions,
        recommendations=recommendations,
        data_gaps=[],
    )

    snapshot = DashboardSnapshot(
        user_id=user_id,
        health_score=health_score,
        net_worth=net_worth,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        savings_rate=savings_rate,
        recurring_obligations=recurring_obligations,
        debts=debts,
        forecast=forecast,
        insights=insights,
        generated_at=datetime.now(timezone.utc),
    )

    _cache_snapshot(snapshot)
    return snapshot
