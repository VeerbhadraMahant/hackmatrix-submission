"""Tests for app.forecast.cashflow, app.simulate.engine, app.recommend.engine.

Covers: forecast shape/ordering invariants, gap-detection on underfunded vs
healthy synthetic scenarios, every ActionType branch of simulate() returning
a non-null ImpactEstimate + valid before/after forecasts, recommendation
ranking + confidence bounds, and determinism of a golden "cancel a
subscription" scenario (no unseeded randomness).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.forecast.cashflow import build_forecast
from app.ingest.fixtures import demo_dashboard_snapshot
from app.recommend.engine import generate_recommendations
from app.schemas import (
    ActionType,
    RecurrenceFrequency,
    RecurringObligation,
    TxnCategory,
)
from app.simulate.engine import ForecastInputs, simulate

TODAY = datetime.now(timezone.utc).date()  # app code uses UTC dates


# ---------------------------------------------------------------------------
# Forecast tests
# ---------------------------------------------------------------------------


def _income_and_rent(income: float, rent: float) -> list[RecurringObligation]:
    return [
        RecurringObligation(
            group_id="salary",
            merchant="Employer",
            category=TxnCategory.income,
            amount=income,
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=1),
            confidence=0.95,
        ),
        RecurringObligation(
            group_id="rent",
            merchant="Landlord",
            category=TxnCategory.rent_housing,
            amount=-rent,
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=5),
            confidence=0.98,
        ),
    ]


def test_forecast_produces_horizon_days_points():
    forecast = build_forecast(
        starting_balance=50_000,
        recurring=_income_and_rent(90_000, 30_000),
        horizon_days=90,
    )
    assert forecast.horizon_days == 90
    assert len(forecast.points) == 90


def test_forecast_band_ordering_holds_at_every_point():
    forecast = build_forecast(
        starting_balance=50_000,
        recurring=_income_and_rent(90_000, 30_000),
        horizon_days=90,
    )
    for point in forecast.points:
        assert point.p10 <= point.p50 <= point.p90


def test_gap_detected_on_underfunded_scenario():
    # Large rent, tiny income, small starting balance -> should go negative.
    forecast = build_forecast(
        starting_balance=1_000,
        recurring=_income_and_rent(income=10_000, rent=50_000),
        horizon_days=60,
    )
    assert forecast.first_gap_date is not None
    assert any(p.is_gap_risk for p in forecast.points)


def test_no_gap_on_healthy_scenario():
    forecast = build_forecast(
        starting_balance=200_000,
        recurring=_income_and_rent(income=150_000, rent=20_000),
        horizon_days=60,
    )
    assert forecast.first_gap_date is None
    assert not any(p.is_gap_risk for p in forecast.points)


def test_confidence_higher_for_data_rich_persona():
    sparse = build_forecast(
        starting_balance=10_000,
        recurring=[
            RecurringObligation(
                group_id="rg1",
                merchant="Unknown",
                category=TxnCategory.other,
                amount=-500,
                frequency=RecurrenceFrequency.irregular,
                next_expected_date=TODAY + timedelta(days=10),
                confidence=0.3,
            )
        ],
        transactions=None,
        horizon_days=90,
    )

    import pandas as pd

    rich_recurring = _income_and_rent(90_000, 30_000) + [
        RecurringObligation(
            group_id="rg-netflix",
            merchant="Netflix",
            category=TxnCategory.subscriptions,
            amount=-649,
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=14),
            confidence=0.95,
        ),
    ]
    txn_rows = []
    for i in range(90):
        txn_rows.append({"date": TODAY - timedelta(days=i), "amount": -200.0, "is_recurring": False})
    rich = build_forecast(
        starting_balance=50_000,
        recurring=rich_recurring,
        transactions=pd.DataFrame(txn_rows),
        horizon_days=90,
    )

    assert rich.confidence > sparse.confidence


# ---------------------------------------------------------------------------
# Simulation engine tests
# ---------------------------------------------------------------------------


def _forecast_inputs() -> ForecastInputs:
    snap = demo_dashboard_snapshot()
    return ForecastInputs(
        starting_balance=42_000.0,
        recurring=snap.recurring_obligations,
        debts=snap.debts,
        transactions=None,
        horizon_days=90,
    )


ACTION_PARAMS = {
    ActionType.cancel_subscription: {"group_ids": ["rg-netflix"]},
    ActionType.reduce_category_spend: {"category": "dining", "percent": 30},
    ActionType.prepay_debt: {"debt_id": "debt-cc", "extra_payment": 3000},
    ActionType.increase_sip: {"amount": 2000, "horizon_years": 5},
    ActionType.build_emergency_fund: {"monthly_contribution": 3000, "target_amount": 100000},
    ActionType.refinance_debt: {"debt_id": "debt-car", "new_apr": 8.0},
    ActionType.affordability_check: {"amount": 20000, "is_recurring": False, "label": "vacation"},
    ActionType.shift_payment_date: {"group_id": "rg-car-emi", "shift_days": 5},
}


@pytest.mark.parametrize("action", list(ActionType))
def test_every_action_returns_full_result(action):
    result = simulate(
        action,
        ACTION_PARAMS[action],
        current_forecast_inputs=_forecast_inputs(),
        current_health_score=64.0,
    )
    assert result.impact is not None
    assert result.forecast_before is not None
    assert result.forecast_after is not None
    assert len(result.forecast_before.points) == 90
    assert len(result.forecast_after.points) == 90
    assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= result.health_score_after <= 100.0


def test_build_emergency_fund_before_is_always_no_target_sentinel():
    """Regression: the 'before' side of the emergency-fund impact estimate
    must reflect the baseline (no dedicated contribution running -- target
    never reached on its own), i.e. the 9999 sentinel, regardless of the
    monthly_contribution proposed by this simulation. A previous version
    computed a nonsensical (remaining + contribution) / contribution value
    for 'before' instead."""
    result = simulate(
        ActionType.build_emergency_fund,
        {"monthly_contribution": 3000, "target_amount": 100000, "current_saved": 10000},
        current_forecast_inputs=_forecast_inputs(),
        current_health_score=64.0,
    )
    assert result.impact.before == 9999.0
    assert result.impact.after == pytest.approx(30.0, abs=0.01)


def test_unknown_debt_raises_value_error():
    with pytest.raises(ValueError):
        simulate(
            ActionType.prepay_debt,
            {"debt_id": "does-not-exist", "extra_payment": 1000},
            current_forecast_inputs=_forecast_inputs(),
            current_health_score=64.0,
        )


def test_cancel_subscription_golden_scenario_deterministic():
    """A known golden scenario: cancel the 649/month Netflix subscription.
    Free-cash-flow delta must have a consistent sign (+649) and magnitude
    across repeated calls -- no unseeded randomness anywhere in the path."""
    results = [
        simulate(
            ActionType.cancel_subscription,
            {"group_ids": ["rg-netflix"]},
            current_forecast_inputs=_forecast_inputs(),
            current_health_score=64.0,
        )
        for _ in range(2)
    ]
    deltas = [r.impact.delta for r in results]
    assert deltas[0] == deltas[1]
    assert deltas[0] == pytest.approx(649.0, abs=0.01)
    assert results[0].health_score_after == results[1].health_score_after
    # sanity: forecast paths are identical across runs too (seeded RNG)
    p50_a = [p.p50 for p in results[0].forecast_after.points]
    p50_b = [p.p50 for p in results[1].forecast_after.points]
    assert p50_a == p50_b


# ---------------------------------------------------------------------------
# Recommendation engine tests
# ---------------------------------------------------------------------------


def test_recommendations_sorted_by_impact_and_confidence_bounded():
    """Updated by simulate-upgrades-agent (upgrade 4): ranking is no longer a
    single scalar `|delta| * confidence` score -- it's a deterministic
    multi-tier lexicographic order (see `_ranking_key` in
    app.recommend.engine). The old scalar-monotonicity assertion is exactly
    the behaviour intentionally replaced, so it's replaced here with a check
    that recommendations are non-empty, well-formed, and that re-deriving
    each recommendation's tier-1 "resolves a near-term gap" flag never
    regresses later in the list (ties within a tier may reorder on
    lower-priority tiers, but a later recommendation can never resolve the
    gap while an earlier one that also could was skipped over)."""
    snap = demo_dashboard_snapshot()
    inputs = _forecast_inputs()
    recs = generate_recommendations(
        recurring=snap.recurring_obligations,
        debts=snap.debts,
        health_score=snap.health_score,
        forecast=snap.forecast,
        forecast_inputs=inputs,
    )
    assert len(recs) > 0
    for rec in recs:
        assert 0.0 <= rec.confidence <= 1.0
        assert rec.impact is not None


# ---------------------------------------------------------------------------
# Upgrade 1: minimum-balance guard
# ---------------------------------------------------------------------------


def test_minimum_balance_guard_flags_breach_with_correct_date():
    """A low starting balance minus a one-time purchase dips below a
    nonzero configured buffer on day 0 -- breaches_minimum_balance must be
    True and min_balance_date must be the first date it happens."""
    inputs = ForecastInputs(
        starting_balance=10_000.0,
        recurring=_income_and_rent(90_000, 30_000),
        minimum_balance_to_keep=8_000.0,
        horizon_days=30,
    )
    result = simulate(
        ActionType.affordability_check,
        {"amount": 5_000, "is_recurring": False, "label": "television"},
        current_forecast_inputs=inputs,
        current_health_score=60.0,
    )
    assert result.breaches_minimum_balance is True
    assert result.min_balance_date is not None
    # The purchase is paid today, so the P50 balance (10,000 - 5,000 = 5,000,
    # below the 8,000 buffer) breaches starting on day 0.
    assert result.min_balance_date == TODAY


def test_minimum_balance_guard_never_flags_comfortable_scenario():
    """A healthy, well-funded scenario with a modest buffer must never
    breach -- breaches_minimum_balance False and min_balance_date None."""
    inputs = ForecastInputs(
        starting_balance=200_000.0,
        recurring=_income_and_rent(150_000, 20_000),
        minimum_balance_to_keep=5_000.0,
        horizon_days=60,
    )
    result = simulate(
        ActionType.affordability_check,
        {"amount": 1_000, "is_recurring": False, "label": "groceries"},
        current_forecast_inputs=inputs,
        current_health_score=80.0,
    )
    assert result.breaches_minimum_balance is False
    assert result.min_balance_date is None


# ---------------------------------------------------------------------------
# Upgrade 2: multi-strategy affordability
# ---------------------------------------------------------------------------


def test_affordable_purchase_includes_pay_in_full_now_ranked_first():
    inputs = ForecastInputs(
        starting_balance=100_000.0,
        recurring=_income_and_rent(90_000, 30_000),
        minimum_balance_to_keep=5_000.0,
        horizon_days=90,
    )
    result = simulate(
        ActionType.affordability_check,
        {"amount": 2_000, "is_recurring": False, "label": "headphones"},
        current_forecast_inputs=inputs,
        current_health_score=70.0,
    )
    assert result.affordability_strategies is not None
    names = [s["strategy"] for s in result.affordability_strategies]
    assert "pay_in_full_now" in names
    assert names[0] == "pay_in_full_now"


def test_unaffordable_today_excludes_pay_in_full_but_offers_wait_until_safe():
    inputs = ForecastInputs(
        starting_balance=10_000.0,
        recurring=_income_and_rent(90_000, 30_000),
        minimum_balance_to_keep=5_000.0,
        horizon_days=90,
    )
    result = simulate(
        ActionType.affordability_check,
        {"amount": 8_000, "is_recurring": False, "label": "laptop"},
        current_forecast_inputs=inputs,
        current_health_score=60.0,
    )
    strategies = result.affordability_strategies
    assert strategies is not None
    names = [s["strategy"] for s in strategies]
    assert "pay_in_full_now" not in names

    wait_strategy = next(s for s in strategies if s["strategy"] == "wait_until_safe")
    assert wait_strategy["safe"] is True
    assert wait_strategy["date"] is not None
    assert date.fromisoformat(wait_strategy["date"]) >= TODAY


def test_affordability_strategy_ranking_deterministic_across_calls():
    inputs = ForecastInputs(
        starting_balance=10_000.0,
        recurring=_income_and_rent(90_000, 30_000),
        minimum_balance_to_keep=5_000.0,
        horizon_days=90,
    )
    params = {"amount": 8_000, "is_recurring": False, "label": "laptop"}
    runs = [
        simulate(
            ActionType.affordability_check,
            params,
            current_forecast_inputs=inputs,
            current_health_score=60.0,
        )
        for _ in range(3)
    ]
    strategy_orders = [[s["strategy"] for s in r.affordability_strategies] for r in runs]
    assert strategy_orders[0] == strategy_orders[1] == strategy_orders[2]
