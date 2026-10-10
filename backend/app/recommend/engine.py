"""Recommendation engine.

Generates a ranked `list[Recommendation]` by actually calling
`app.simulate.engine.simulate()` for each plausible candidate action -- every
recommendation therefore carries a real, simulated `ImpactEstimate`, not a
hand-waved guess. This is the core "show the expected impact of any
recommended action" requirement.

Candidate generation heuristics (deliberately simple / explainable):
  * every debt -> try prepaying it with ~10% of estimated monthly free cash
    flow
  * every subscription-category recurring item -> try cancelling it
    (in the absence of real usage-detection from analytics-agent, we treat
    ALL subscriptions as candidates and let the impact/ranking speak for
    itself; a real "unused" signal from `app.analytics.recurring` would
    narrow this list -- see TODO below)
  * if the forecast's first_gap_date falls within 30 days -> try
    `shift_payment_date` (if a plausible near-collision exists) and
    `reduce_category_spend` as gap-mitigation candidates
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from app.recommend.categories import is_flexible
from app.schemas import (
    ActionType,
    CashFlowForecast,
    Debt,
    HealthScore,
    Recommendation,
    RecurringObligation,
    TxnCategory,
)
from app.simulate.engine import (
    ForecastInputs,
    _forecast_from,
    _free_cash_flow,
    _minimum_balance_breach,
    simulate,
)

_TOP_N_DEFAULT = 5


def _biggest_flexible_category(recurring: list[RecurringObligation]) -> Optional[TxnCategory]:
    """Return the flexible (non-protected) category with the largest total
    recurring outflow, or None if there are no flexible outflows at all.
    Structurally excludes PROTECTED_CATEGORIES -- see app.recommend.categories."""
    totals: dict[TxnCategory, float] = {}
    for item in recurring:
        if item.amount < 0 and is_flexible(item.category):
            totals[item.category] = totals.get(item.category, 0.0) + abs(item.amount)
    if not totals:
        return None
    return max(totals, key=totals.get)


def _candidate_requests(
    recurring: list[RecurringObligation],
    debts: list[Debt],
    forecast: CashFlowForecast,
    minimum_balance_to_keep: float = 0.0,
) -> list[tuple[ActionType, dict, str]]:
    """Return (action, action_params, rationale) tuples for plausible
    candidate actions given the current state.

    `minimum_balance_to_keep` (upgrade 1) is accepted here for API symmetry
    with `generate_recommendations` and so a future candidate-generation
    heuristic can size its ask around the buffer; actual safety filtering
    happens once, after simulation, in `generate_recommendations` (a
    candidate's real safety can only be known after running the forecast,
    not while guessing at parameters)."""
    candidates: list[tuple[ActionType, dict, str]] = []

    monthly_fcf = _free_cash_flow(recurring)
    ten_pct_fcf = max(abs(monthly_fcf) * 0.10, 500.0)

    # TODO(integration): once app.analytics.debt.compare_payoff_strategies
    # is available, use it to pick which debt(s) to prioritise (avalanche
    # order) instead of proposing all of them.
    for debt in debts:
        # Debt has no human-readable name in the contract (only ids) -- describe
        # it by its salient numbers so recommendation text never surfaces a raw
        # UUID to the user.
        debt_label = f"your {debt.interest_rate_apr:.1f}% APR debt (₹{debt.principal:,.0f})"
        candidates.append(
            (
                ActionType.prepay_debt,
                {
                    "debt_id": debt.id,
                    "debt_label": debt_label,
                    "extra_payment": round(ten_pct_fcf, 2),
                },
                f"{debt_label.capitalize()} carries a high rate; "
                f"extra principal payments compound in your favour fastest "
                f"on your highest-rate debt.",
            )
        )

    # TODO(integration): once app.analytics.recurring exposes a real
    # "last used" / "likely unused" signal, filter this to only genuinely
    # unused subscriptions instead of proposing every one.
    for item in recurring:
        if item.category == TxnCategory.subscriptions:
            candidates.append(
                (
                    ActionType.cancel_subscription,
                    {"group_ids": [item.group_id]},
                    f"{item.merchant} (~{abs(item.amount):.0f}/mo) is a recurring "
                    f"subscription; cancelling frees up cash flow immediately.",
                )
            )

    if forecast.first_gap_date is not None:
        days_to_gap = (forecast.first_gap_date - datetime.now(timezone.utc).date()).days
        if 0 <= days_to_gap <= 30:
            # gap-mitigation candidate 1: shift the first outflow-heavy
            # obligation a few days later, if any exist
            outflows = [r for r in recurring if r.amount < 0]
            if outflows:
                target = min(outflows, key=lambda r: r.next_expected_date)
                candidates.append(
                    (
                        ActionType.shift_payment_date,
                        {"group_id": target.group_id, "shift_days": 5},
                        f"A projected cash-flow gap on {forecast.first_gap_date.isoformat()} "
                        f"is within 30 days; shifting {target.merchant}'s payment date by a "
                        f"few days may avoid the collision with other due dates.",
                    )
                )
            # gap-mitigation candidate 2: reduce discretionary spend.
            # Upgrade 3: only ever target a FLEXIBLE category -- pick the
            # biggest recurring flexible outflow (falling back to dining,
            # itself flexible, if there is no recurring flexible spend at
            # all). The `assert` below makes it structurally impossible for
            # a protected category to slip through, not just a promise in a
            # comment.
            category = _biggest_flexible_category(recurring) or TxnCategory.dining
            assert is_flexible(category), (
                f"reduce_category_spend must never target a protected category, got {category!r}"
            )
            candidates.append(
                (
                    ActionType.reduce_category_spend,
                    {"category": category.value, "percent": 25},
                    f"A projected cash-flow gap on {forecast.first_gap_date.isoformat()} "
                    f"is within 30 days; trimming discretionary spend (e.g. {category.value}) "
                    f"by 25% builds a buffer before then.",
                )
            )

    return candidates


def _ranking_key(
    resolves_gap: bool, interest_savings: float, impact_delta: float, confidence: float
) -> tuple[int, float, float, float]:
    """Deterministic multi-tier lexicographic ranking (upgrade 4, Penny-style).

    Returns a tuple that sorts ASCENDING, so a SMALLER tuple ranks FIRST:
      Tier 1: 0 if the action resolves a projected cash-flow gap within 30
              days, else 1 -- a recommendation that fixes an imminent gap
              always outranks one that doesn't, no matter how much bigger
              the other's raw dollar impact is.
      Tier 2: -interest_savings -- for prepay_debt actions, more interest
              saved ranks first. 0.0 for every other action type, so this
              tier is a no-op tie-break outside debt-payoff candidates.
      Tier 3: -abs(impact_delta) -- larger absolute impact ranks first.
      Tier 4: -confidence -- final tie-break: more confident wins.
    Python tuple comparison gives lexicographic ordering for free: ties on
    tier 1 fall through to tier 2, ties there fall through to tier 3, etc.
    """
    return (0 if resolves_gap else 1, -interest_savings, -abs(impact_delta), -confidence)


def generate_recommendations(
    *,
    recurring: list[RecurringObligation],
    debts: list[Debt],
    health_score: HealthScore,
    forecast: CashFlowForecast,
    forecast_inputs: ForecastInputs,
    top_n: int = _TOP_N_DEFAULT,
    minimum_balance_to_keep: Optional[float] = None,
) -> list[Recommendation]:
    """Simulate every candidate action and return the top-N ranked by the
    deterministic multi-tier order in `_ranking_key` (upgrade 4) -- never a
    single scalar score.

    Upgrade 1 (minimum-balance guard): `minimum_balance_to_keep` (falling
    back to `forecast_inputs.minimum_balance_to_keep` when not given here)
    is applied to every candidate's simulation. A candidate is EXCLUDED
    outright (not merely ranked down) when it would INTRODUCE a NEW breach
    of that guard that wasn't already present in the user's baseline
    forecast -- recommendations should never make a safe user's forecast
    unsafe. If the baseline is *already* breaching the buffer (a fragile
    persona who needs help most), candidates are NOT blanket-excluded just
    for failing to fully close a pre-existing hole -- that would leave the
    user with zero recommendations exactly when they need them most. Tier 1
    of `_ranking_key` already rewards candidates that resolve a near-term
    gap, so a candidate that meaningfully improves (or fully fixes) an
    already-breaching baseline is naturally ranked above one that doesn't.
    """
    buffer = (
        minimum_balance_to_keep
        if minimum_balance_to_keep is not None
        else forecast_inputs.minimum_balance_to_keep
    )
    effective_inputs = (
        forecast_inputs
        if buffer == forecast_inputs.minimum_balance_to_keep
        else replace(forecast_inputs, minimum_balance_to_keep=buffer)
    )

    candidates = _candidate_requests(recurring, debts, forecast, minimum_balance_to_keep=buffer)

    today = datetime.now(timezone.utc).date()
    gap_within_30d_before = (
        forecast.first_gap_date is not None and 0 <= (forecast.first_gap_date - today).days <= 30
    )
    # Compare against a baseline built from the SAME `effective_inputs` every
    # candidate is simulated against (not the possibly-stale `forecast`
    # argument the caller passed in), so the "did this candidate introduce a
    # NEW breach" comparison is apples-to-apples with a consistent starting
    # balance.
    baseline_breaches, _ = _minimum_balance_breach(_forecast_from(effective_inputs), buffer)

    scored: list[tuple[tuple, Recommendation]] = []
    for action, params, rationale in candidates:
        try:
            result = simulate(
                action,
                params,
                current_forecast_inputs=effective_inputs,
                current_health_score=health_score.overall,
            )
        except Exception:
            # A candidate that fails to simulate (e.g. bad params for this
            # user's data) is simply skipped rather than surfaced as a
            # broken recommendation.
            continue

        if result.breaches_minimum_balance and not baseline_breaches:
            # Upgrade 1: exclude only candidates that INTRODUCE a new breach
            # (see docstring above for why an already-breaching baseline
            # doesn't blanket-exclude every candidate).
            continue

        recommendation = Recommendation(
            action=action,
            text=_describe(action, params, result),
            rationale=rationale,
            impact=result.impact,
            confidence=result.confidence,
            action_params=params,
        )
        resolves_gap = gap_within_30d_before and (
            result.forecast_after.first_gap_date is None
            or (result.forecast_after.first_gap_date - today).days > 30
        )
        interest_savings = -result.impact.delta if action == ActionType.prepay_debt else 0.0
        rank_key = _ranking_key(resolves_gap, interest_savings, result.impact.delta, result.confidence)
        scored.append((rank_key, recommendation))

    scored.sort(key=lambda pair: pair[0])
    return [rec for _, rec in scored[:top_n]]


def _describe(action: ActionType, params: dict, result) -> str:
    impact = result.impact
    if action == ActionType.prepay_debt:
        debt_label = params.get("debt_label") or f"debt {params.get('debt_id')}"
        return (
            f"Pay an extra ₹{params.get('extra_payment', 0):.0f}/month toward "
            f"{debt_label} -- saves ~₹{abs(impact.delta):.0f} in interest."
        )
    if action == ActionType.cancel_subscription:
        return (
            f"Cancel subscription(s) {params.get('group_ids')} -- "
            f"+{impact.delta:.0f}/month free cash flow."
        )
    if action == ActionType.shift_payment_date:
        return (
            f"Shift {params.get('group_id')}'s due date by {params.get('shift_days', 0)} day(s) "
            f"-- moves first projected gap by {impact.delta} day(s)."
        )
    if action == ActionType.reduce_category_spend:
        return (
            f"Reduce {params.get('category')} spend by {params.get('percent')}% -- "
            f"saves ~{abs(impact.delta):.0f}/month."
        )
    return f"{action.value}: {impact.metric} changes by {impact.delta}."
