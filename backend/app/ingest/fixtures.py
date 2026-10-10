"""Static fixture DashboardSnapshot for the demo persona "Priya" -- used by
stub API endpoints in Phase 0 so the frontend agent can build the full UI
before analytics/forecast/simulate are wired up for real. The real data
generator (personas.py, built by data-agent) supersedes this at integration
time; keep this fixture in sync at a high level so the UI doesn't need
reshaping later.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.schemas import (
    ActionType,
    AnswerContract,
    CashFlowForecast,
    DashboardSnapshot,
    Debt,
    Fact,
    ForecastPoint,
    HealthScore,
    ImpactEstimate,
    Prediction,
    Recommendation,
    RecurrenceFrequency,
    RecurringObligation,
    SubScore,
    TxnCategory,
)

TODAY = date.today()


def _forecast() -> CashFlowForecast:
    points: list[ForecastPoint] = []
    balance = 42_000.0
    gap_date = None
    for i in range(90):
        d = TODAY + timedelta(days=i)
        # simple synthetic wave: salary on the 1st, EMI/rent drain mid-month
        daily_drift = -650
        if d.day == 1:
            daily_drift += 95_000
        if d.day == 5:
            daily_drift -= 28_000  # rent
        if d.day == 10:
            daily_drift -= 14_500  # car EMI
        balance += daily_drift
        p50 = balance
        p10 = balance - 6000
        p90 = balance + 6000
        is_gap = p10 < 0
        if is_gap and gap_date is None:
            gap_date = d
        points.append(ForecastPoint(date=d, p10=p10, p50=p50, p90=p90, is_gap_risk=is_gap))
    return CashFlowForecast(
        generated_at=datetime.now(timezone.utc),
        horizon_days=90,
        points=points,
        first_gap_date=gap_date,
        confidence=0.72,
        basis="Projected from 3 recurring obligations, 1 income source, and 90 days of category-level spend history.",
    )


def demo_dashboard_snapshot(user_id: str = "demo-priya") -> DashboardSnapshot:
    health = HealthScore(
        overall=64,
        sub_scores=[
            SubScore(name="Cash-flow stability", score=58, weight=0.3, detail="2 low-balance risk days in the next 90"),
            SubScore(name="Debt pressure", score=52, weight=0.25, detail="EMI + credit card = 34% of income"),
            SubScore(name="Savings behaviour", score=71, weight=0.2, detail="12% average monthly savings rate"),
            SubScore(name="Emergency fund", score=45, weight=0.15, detail="0.8 months of expenses covered"),
            SubScore(name="Spending consistency", score=88, weight=0.1, detail="Low variance across categories"),
        ],
        computed_at=datetime.now(timezone.utc),
        trend_30d=3.5,
    )

    recurring = [
        RecurringObligation(group_id="rg-rent", merchant="Prestige Lakeview Apts", category=TxnCategory.rent_housing, amount=-28000, frequency=RecurrenceFrequency.monthly, next_expected_date=TODAY.replace(day=5) if TODAY.day < 5 else TODAY + timedelta(days=30), confidence=0.98),
        RecurringObligation(group_id="rg-car-emi", merchant="HDFC Auto Loan", category=TxnCategory.emi_loan, amount=-14500, frequency=RecurrenceFrequency.monthly, next_expected_date=TODAY + timedelta(days=10), confidence=0.99),
        RecurringObligation(group_id="rg-netflix", merchant="Netflix", category=TxnCategory.subscriptions, amount=-649, frequency=RecurrenceFrequency.monthly, next_expected_date=TODAY + timedelta(days=14), confidence=0.95),
        RecurringObligation(group_id="rg-sip", merchant="Zerodha Coin SIP", category=TxnCategory.investment_sip, amount=-5000, frequency=RecurrenceFrequency.monthly, next_expected_date=TODAY + timedelta(days=3), confidence=0.97),
    ]

    debts = [
        Debt(id="debt-car", user_id=user_id, account_id="acc-car-loan", principal=380000, interest_rate_apr=9.5, minimum_payment=14500, due_day_of_month=10),
        Debt(id="debt-cc", user_id=user_id, account_id="acc-credit-card", principal=62000, interest_rate_apr=42.0, minimum_payment=3100, due_day_of_month=18),
    ]

    insights = AnswerContract(
        narrative="Your cash flow is generally healthy, but a credit-card balance carried at 42% APR and a thin emergency fund are creating avoidable risk.",
        facts=[
            Fact(text="You spent ₹6,490 on subscriptions across 6 services in the last 30 days.", value=6490, source_txn_ids=[]),
            Fact(text="Your average monthly savings rate over the last 3 months is 12%.", value=0.12),
        ],
        predictions=[
            Prediction(text="Your checking balance is projected to dip below ₹0 around day 23 if spending continues at the current rate.", value=-3200, range_low=-9200, range_high=2800, confidence=0.68, basis="90-day forecast from recurring obligations + spend variance"),
        ],
        recommendations=[
            Recommendation(
                action=ActionType.prepay_debt,
                text="Redirect ₹5,000/month from savings to pay down the credit card balance instead of carrying it at 42% APR.",
                rationale="Your credit card APR (42%) is far higher than any realistic investment return; paying it down first is mathematically optimal.",
                impact=ImpactEstimate(metric="Interest paid (12mo)", before=18200, after=9100, delta=-9100, horizon="12 months"),
                confidence=0.83,
                action_params={"debt_id": "debt-cc", "extra_payment": 5000},
            ),
            Recommendation(
                action=ActionType.cancel_subscription,
                text="Cancel or pause 2 unused subscriptions (₹1,298/month) to strengthen your emergency fund faster.",
                rationale="Usage pattern suggests these 2 of 6 subscriptions have not been used in 60+ days.",
                impact=ImpactEstimate(metric="Emergency fund months", before=0.8, after=1.1, delta=0.3, horizon="6 months"),
                confidence=0.61,
                action_params={"group_ids": ["rg-sub-unused-1", "rg-sub-unused-2"]},
            ),
        ],
        data_gaps=[],
    )

    return DashboardSnapshot(
        user_id=user_id,
        health_score=health,
        net_worth=612_000,
        monthly_income=95_000,
        monthly_expenses=78_400,
        savings_rate=0.12,
        recurring_obligations=recurring,
        debts=debts,
        forecast=_forecast(),
        insights=insights,
        generated_at=datetime.now(timezone.utc),
    )
