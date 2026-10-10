"""Tests for app.recommend.engine and app.recommend.categories.

Covers: protected-vs-flexible spending categories (upgrade 3) and the
deterministic multi-tier lexicographic recommendation ranking (upgrade 4).
See backend/tests/test_forecast_sim.py for the minimum-balance-guard and
affordability-strategy tests (upgrades 1 and 2).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.forecast.cashflow import build_forecast
from app.recommend.categories import PROTECTED_CATEGORIES, is_flexible
from app.recommend.engine import _biggest_flexible_category, _candidate_requests, _ranking_key, generate_recommendations
from app.schemas import (
    ActionType,
    CashFlowForecast,
    Debt,
    ForecastPoint,
    HealthScore,
    ImpactEstimate,
    RecurrenceFrequency,
    RecurringObligation,
    SimulationRequest,
    SimulationResult,
    SubScore,
    TxnCategory,
)

TODAY = date.today()


# ---------------------------------------------------------------------------
# Upgrade 3: protected vs. flexible categories
# ---------------------------------------------------------------------------


def _fragile_scenario_recurring() -> list[RecurringObligation]:
    """A synthetic scenario where rent (protected, huge) is by far the
    biggest recurring outflow -- bigger than any flexible category -- so a
    naive "cut whatever is biggest" heuristic would pick rent. Dining is the
    biggest FLEXIBLE outflow and should be the one proposed instead."""
    return [
        RecurringObligation(
            group_id="salary",
            merchant="Employer",
            category=TxnCategory.income,
            amount=25_000,
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=1),
            confidence=0.9,
        ),
        RecurringObligation(
            group_id="rg-rent",
            merchant="Landlord",
            category=TxnCategory.rent_housing,
            amount=-50_000,  # by far the largest outflow -- but PROTECTED
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=3),
            confidence=0.98,
        ),
        RecurringObligation(
            group_id="rg-dining",
            merchant="Restaurants",
            category=TxnCategory.dining,
            amount=-5_000,  # the biggest FLEXIBLE outflow
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=6),
            confidence=0.9,
        ),
        RecurringObligation(
            group_id="rg-transport",
            merchant="Fuel",
            category=TxnCategory.transport,
            amount=-1_500,
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=TODAY + timedelta(days=8),
            confidence=0.9,
        ),
    ]


def test_biggest_flexible_category_skips_protected_rent():
    recurring = _fragile_scenario_recurring()
    category = _biggest_flexible_category(recurring)
    assert category == TxnCategory.dining
    assert category not in PROTECTED_CATEGORIES


def test_protected_category_never_proposed_for_cutting_even_when_biggest_lever():
    recurring = _fragile_scenario_recurring()
    # Small starting balance + near-term rent due -> a projected gap within
    # 30 days, which is what triggers the reduce_category_spend candidate.
    forecast = build_forecast(starting_balance=2_000, recurring=recurring, horizon_days=60)
    assert forecast.first_gap_date is not None
    days_to_gap = (forecast.first_gap_date - TODAY).days
    assert 0 <= days_to_gap <= 30

    candidates = _candidate_requests(recurring, debts=[], forecast=forecast)
    reduce_candidates = [c for c in candidates if c[0] == ActionType.reduce_category_spend]
    assert reduce_candidates, "expected at least one reduce_category_spend candidate"

    for _, params, _ in reduce_candidates:
        cut_category = TxnCategory(params["category"])
        assert cut_category not in PROTECTED_CATEGORIES
        assert is_flexible(cut_category)
        assert cut_category != TxnCategory.rent_housing

    # The biggest flexible lever (dining) IS proposed.
    assert any(params["category"] == TxnCategory.dining.value for _, params, _ in reduce_candidates)


# ---------------------------------------------------------------------------
# Upgrade 4: deterministic multi-tier ranking
# ---------------------------------------------------------------------------


def test_ranking_key_prefers_gap_resolution_over_larger_raw_delta():
    """Direct unit check of the documented tier order: tier 1 (resolves a
    near-term gap) beats tier 3 (raw |delta| size) outright."""
    huge_delta_does_not_resolve_gap = _ranking_key(
        resolves_gap=False, interest_savings=0.0, impact_delta=100_000.0, confidence=0.9
    )
    small_delta_resolves_gap = _ranking_key(
        resolves_gap=True, interest_savings=0.0, impact_delta=500.0, confidence=0.5
    )
    # Smaller tuple sorts first (ascending sort) -- the gap-resolving,
    # smaller-delta, lower-confidence candidate must still rank first.
    assert small_delta_resolves_gap < huge_delta_does_not_resolve_gap


def _minimal_forecast(first_gap_date) -> CashFlowForecast:
    return CashFlowForecast(
        generated_at=datetime.now(timezone.utc),
        horizon_days=60,
        points=[ForecastPoint(date=TODAY, p10=0.0, p50=0.0, p90=0.0, is_gap_risk=False)],
        first_gap_date=first_gap_date,
        confidence=0.8,
        basis="test fixture",
    )


def test_generate_recommendations_ranks_gap_resolving_candidate_first(monkeypatch):
    """Integration-level proof: construct two candidates where a naive
    scalar score (|delta| * confidence) would rank the huge-delta candidate
    first, but the tiered ranking correctly puts the smaller-delta,
    gap-resolving candidate first instead."""
    recurring: list[RecurringObligation] = []
    debts: list[Debt] = []

    forecast_before = _minimal_forecast(TODAY + timedelta(days=10))  # gap within 30 days

    # Candidate A: cancel_subscription, HUGE delta, but does NOT resolve the
    # near-term gap (still within 30 days afterward).
    result_a = SimulationResult(
        request=SimulationRequest(action=ActionType.cancel_subscription, action_params={}),
        health_score_before=50.0,
        health_score_after=55.0,
        forecast_before=forecast_before,
        forecast_after=_minimal_forecast(TODAY + timedelta(days=12)),
        impact=ImpactEstimate(metric="monthly free cash flow", before=0, after=100_000, delta=100_000.0, horizon="next 30 days"),
        confidence=0.9,
        breaches_minimum_balance=False,
    )
    # Candidate B: shift_payment_date, SMALL delta, but DOES resolve the gap.
    result_b = SimulationResult(
        request=SimulationRequest(action=ActionType.shift_payment_date, action_params={}),
        health_score_before=50.0,
        health_score_after=50.0,
        forecast_before=forecast_before,
        forecast_after=_minimal_forecast(None),  # gap fully resolved
        impact=ImpactEstimate(metric="days until first projected cash-flow gap", before=10, after=45, delta=500.0, horizon="next 90 days"),
        confidence=0.5,
        breaches_minimum_balance=False,
    )

    candidates = [
        (ActionType.cancel_subscription, {"a": 1}, "cancel a subscription"),
        (ActionType.shift_payment_date, {"b": 1}, "shift a payment date"),
    ]
    results_by_action = {
        ActionType.cancel_subscription: result_a,
        ActionType.shift_payment_date: result_b,
    }

    monkeypatch.setattr("app.recommend.engine._candidate_requests", lambda *a, **k: candidates)
    monkeypatch.setattr(
        "app.recommend.engine.simulate",
        lambda action, params, **k: results_by_action[action],
    )

    # Sanity check: the naive OLD scalar score would rank A first.
    naive_score_a = abs(result_a.impact.delta) * result_a.confidence
    naive_score_b = abs(result_b.impact.delta) * result_b.confidence
    assert naive_score_a > naive_score_b

    from app.simulate.engine import ForecastInputs

    forecast_inputs = ForecastInputs(starting_balance=10_000.0, recurring=recurring, horizon_days=60)
    health_score = HealthScore(
        overall=50.0,
        sub_scores=[SubScore(name="test", score=50.0, weight=1.0, detail="test")],
        computed_at=datetime.now(timezone.utc),
    )

    recs = generate_recommendations(
        recurring=recurring,
        debts=debts,
        health_score=health_score,
        forecast=forecast_before,
        forecast_inputs=forecast_inputs,
    )

    assert len(recs) == 2
    # Despite the huge raw delta, the gap-resolving candidate (B) must rank
    # first under the tiered logic.
    assert recs[0].action == ActionType.shift_payment_date
    assert recs[1].action == ActionType.cancel_subscription
