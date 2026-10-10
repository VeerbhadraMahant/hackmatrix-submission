"""Unit tests for app.analytics.* built against small hand-built synthetic
DataFrames/objects -- deliberately independent of data-agent's persona
generator so these keep working once that lands."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from app.analytics.anomalies import detect_anomalies
from app.analytics.debt import compare_payoff_strategies, compute_dti
from app.analytics.goals import project_goal
from app.analytics.health_score import compute_health_score
from app.analytics.recurring import detect_recurring, find_redundant_subscriptions
from app.schemas import CashFlowForecast, Debt, ForecastPoint, Goal, RecurrenceFrequency, TxnCategory


def _txn_df(rows: list[dict]) -> pd.DataFrame:
    defaults = {"account_id": "acc-1", "is_recurring": False}
    return pd.DataFrame([{**defaults, **r} for r in rows])


# ---------------------------------------------------------------------------
# Recurring detection
# ---------------------------------------------------------------------------


def test_clean_monthly_recurring_series_detected_with_high_confidence():
    base = date(2025, 1, 5)
    rows = [
        {"date": base + timedelta(days=30 * i), "amount": -649.0, "merchant": "Netflix", "category": TxnCategory.subscriptions.value}
        for i in range(6)
    ]
    df = _txn_df(rows)

    recurring = detect_recurring(df)

    assert len(recurring) == 1
    obligation = recurring[0]
    assert obligation.frequency == RecurrenceFrequency.monthly
    assert obligation.confidence >= 0.8
    assert obligation.category == TxnCategory.subscriptions


def test_irregular_series_marked_irregular_or_low_confidence():
    base = date(2025, 1, 1)
    # wildly inconsistent gaps: 5, 40, 12, 65 days
    offsets = [0, 5, 45, 57, 122]
    rows = [
        {"date": base + timedelta(days=o), "amount": -300.0 - i * 40, "merchant": "Random Store", "category": TxnCategory.shopping.value}
        for i, o in enumerate(offsets)
    ]
    df = _txn_df(rows)

    recurring = detect_recurring(df)

    assert len(recurring) == 1
    obligation = recurring[0]
    assert obligation.frequency == RecurrenceFrequency.irregular or obligation.confidence < 0.6


def test_find_redundant_subscriptions_flags_overlapping_ott():
    base = date(2025, 1, 1)
    rows = []
    for merchant in ["Netflix", "Hotstar"]:
        for i in range(4):
            rows.append({"date": base + timedelta(days=30 * i), "amount": -500.0, "merchant": merchant, "category": TxnCategory.subscriptions.value})
    df = _txn_df(rows)

    recurring = detect_recurring(df)
    redundant = find_redundant_subscriptions(recurring)

    assert len(redundant) == 2
    assert {r.merchant for r in redundant} == {"netflix", "hotstar"}


# ---------------------------------------------------------------------------
# Debt payoff strategies
# ---------------------------------------------------------------------------


def _sample_debts() -> list[Debt]:
    return [
        Debt(id="d-cc", user_id="u1", account_id="a-cc", principal=62000, interest_rate_apr=42.0, minimum_payment=3100, due_day_of_month=18),
        Debt(id="d-car", user_id="u1", account_id="a-car", principal=380000, interest_rate_apr=9.5, minimum_payment=14500, due_day_of_month=10),
        Debt(id="d-small", user_id="u1", account_id="a-small", principal=15000, interest_rate_apr=15.0, minimum_payment=1500, due_day_of_month=5),
    ]


def test_avalanche_and_snowball_differ_and_avalanche_interest_lower_or_equal():
    debts = _sample_debts()
    result = compare_payoff_strategies(debts, extra_monthly_payment=5000)

    assert "avalanche" in result and "snowball" in result
    assert result["avalanche"]["total_interest_paid"] <= result["snowball"]["total_interest_paid"]


def test_compute_dti():
    debts = _sample_debts()
    dti = compute_dti(debts, monthly_income=95000)
    expected = (3100 + 14500 + 1500) / 95000
    assert dti == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------


def _forecast_no_gap() -> CashFlowForecast:
    points = [
        ForecastPoint(date=date(2025, 1, 1) + timedelta(days=i), p10=1000, p50=2000, p90=3000, is_gap_risk=False)
        for i in range(30)
    ]
    return CashFlowForecast(generated_at=pd.Timestamp.now(tz="UTC").to_pydatetime(), horizon_days=30, points=points, first_gap_date=None, confidence=0.8, basis="test")


def test_health_score_within_bounds_and_dti_sensitivity():
    forecast = _forecast_no_gap()

    low_dti_score = compute_health_score(
        forecast=forecast, dti=0.10, credit_utilization=0.1,
        savings_rate_trailing=0.15, emergency_fund_months=4, spending_cov=0.2,
    )
    high_dti_score = compute_health_score(
        forecast=forecast, dti=0.45, credit_utilization=0.9,
        savings_rate_trailing=0.15, emergency_fund_months=4, spending_cov=0.2,
    )

    assert 0 <= low_dti_score.overall <= 100
    assert 0 <= high_dti_score.overall <= 100

    low_debt_sub = next(s for s in low_dti_score.sub_scores if s.name == "Debt pressure")
    high_debt_sub = next(s for s in high_dti_score.sub_scores if s.name == "Debt pressure")
    assert high_debt_sub.score < low_debt_sub.score
    assert high_dti_score.overall < low_dti_score.overall


def test_health_score_trend_30d():
    forecast = _forecast_no_gap()
    prior = compute_health_score(
        forecast=forecast, dti=0.30, credit_utilization=0.5,
        savings_rate_trailing=0.10, emergency_fund_months=2, spending_cov=0.3,
    )
    current = compute_health_score(
        forecast=forecast, dti=0.10, credit_utilization=0.1,
        savings_rate_trailing=0.20, emergency_fund_months=5, spending_cov=0.1,
        prior_health_score=prior,
    )
    assert current.trend_30d is not None
    assert current.trend_30d > 0


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


def test_anomaly_detector_flags_outlier_and_not_normal_spend():
    base = date(2025, 1, 1)
    rows = []
    # 10 normal grocery transactions around ₹1000
    for i in range(10):
        amt = -1000.0 + (i % 3) * 20  # small natural variance
        rows.append({"date": base + timedelta(days=i), "amount": amt, "merchant": "BigBasket", "category": TxnCategory.groceries.value, "id": f"t{i}"})
    # then an injected outlier ~5x the median
    rows.append({"date": base + timedelta(days=11), "amount": -5000.0, "merchant": "BigBasket", "category": TxnCategory.groceries.value, "id": "t-outlier"})
    df = _txn_df(rows)

    facts = detect_anomalies(df)

    assert any("t-outlier" in f.source_txn_ids for f in facts)
    # none of the first 10 normal transactions (before enough history exists,
    # and given their tight variance) should be flagged
    normal_ids = {f"t{i}" for i in range(5)}
    flagged_ids = {tid for f in facts for tid in f.source_txn_ids}
    assert not (normal_ids & flagged_ids)


def test_anomaly_detector_no_false_positives_on_uniform_spend():
    base = date(2025, 1, 1)
    rows = [
        {"date": base + timedelta(days=i), "amount": -500.0, "merchant": "Coffee Shop", "category": TxnCategory.dining.value, "id": f"c{i}"}
        for i in range(15)
    ]
    df = _txn_df(rows)
    facts = detect_anomalies(df)
    assert facts == []


# ---------------------------------------------------------------------------
# Goal projection
# ---------------------------------------------------------------------------


def test_goal_projection_simple_case():
    goal = Goal(id="g1", user_id="u1", name="Emergency fund", target_amount=100000, current_amount=40000, target_date=None)
    result = project_goal(goal, monthly_contribution=10000)

    # remaining = 60000, /10000 per month = 6 months exactly
    assert result["months_remaining"] == 6
    assert result["on_track"] is True
    assert result["projected_completion_date"] is not None


def test_goal_projection_behind_target_date():
    goal = Goal(id="g2", user_id="u1", name="Vacation", target_amount=60000, current_amount=0, target_date=date.today() + timedelta(days=30))
    result = project_goal(goal, monthly_contribution=5000)

    # 12 months needed but target date is 1 month away -> not on track
    assert result["months_remaining"] == 12
    assert result["on_track"] is False


def test_goal_already_met():
    goal = Goal(id="g3", user_id="u1", name="Done", target_amount=1000, current_amount=1500)
    result = project_goal(goal, monthly_contribution=0)
    assert result["months_remaining"] == 0
    assert result["on_track"] is True
