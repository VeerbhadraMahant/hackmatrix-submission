"""What-if simulation engine.

`simulate()` takes an `ActionType` + parameters and the user's *current*
state (recurring obligations, optional transaction history, optional debts,
current health score) and returns a `SimulationResult` with a real
before/after `CashFlowForecast` and a populated `ImpactEstimate` -- never a
null impact.

Design note: this module accepts plain data (dicts, DataFrames, lists of
schema models) rather than importing analytics/DB internals directly, so
wiring in the real `app.analytics.*` functions later is a substitution, not
a rewrite. Every place that currently approximates something the analytics
module will eventually own is marked `# TODO(integration)`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from app.forecast.cashflow import build_forecast
from app.schemas import (
    ActionType,
    CashFlowForecast,
    Debt,
    ImpactEstimate,
    RecurrenceFrequency,
    RecurringObligation,
    SimulationRequest,
    SimulationResult,
    TxnCategory,
)
from app.simulate.amortization import amortize

# Assumed nominal annual return for SIP/investment projections. This is a
# clearly-labelled ASSUMPTION, not a guarantee or personalised advice --
# conservative middle of a typical long-horizon Indian equity-fund SIP range
# (historically often quoted 10-14%; we use the low end deliberately).
ASSUMED_ANNUAL_INVESTMENT_RETURN_PCT = 10.0

_DEFAULT_HORIZON_DAYS = 90


@dataclass
class ForecastInputs:
    """Plain-data bundle describing the user's current state, passed into
    `simulate()`. Constructed by the API layer from either the demo fixture
    (Phase 0) or real DB-backed state (post-integration)."""

    starting_balance: float
    recurring: list[RecurringObligation]
    debts: list[Debt] = field(default_factory=list)
    transactions: Optional[pd.DataFrame] = None
    horizon_days: int = _DEFAULT_HORIZON_DAYS
    monthly_income: float = 0.0
    # Upgrade 1 (simulate-upgrades-agent): the user's personal safety buffer.
    # 0.0 (default) means "just don't go negative" -- any positive value
    # means "never let a simulated action's forecast dip below this amount".
    minimum_balance_to_keep: float = 0.0


def _forecast_from(inputs: ForecastInputs, recurring_override: Optional[list[RecurringObligation]] = None,
                    transactions_override: Optional[pd.DataFrame] = None,
                    starting_balance_override: Optional[float] = None) -> CashFlowForecast:
    return build_forecast(
        starting_balance=starting_balance_override if starting_balance_override is not None else inputs.starting_balance,
        recurring=recurring_override if recurring_override is not None else inputs.recurring,
        transactions=transactions_override if transactions_override is not None else inputs.transactions,
        horizon_days=inputs.horizon_days,
    )


def _free_cash_flow(recurring: list[RecurringObligation]) -> float:
    """Approximate monthly free cash flow as the sum of recurring items
    normalised to a monthly cadence (inflows positive, outflows negative)."""
    freq_to_months = {
        "weekly": 4.345,
        "biweekly": 2.1725,
        "monthly": 1.0,
        "quarterly": 1 / 3,
        "annual": 1 / 12,
        "irregular": 1.0,
    }
    total = 0.0
    for item in recurring:
        freq = item.frequency.value if hasattr(item.frequency, "value") else item.frequency
        total += item.amount * freq_to_months.get(freq, 1.0)
    return total


def _approx_health_delta(free_cash_flow_delta: float, current_health_score: float) -> float:
    """Approximate the change in overall health score from a change in
    monthly free cash flow, WITHOUT calling the real
    `app.analytics.health_score.compute_health_score` (not yet merged).

    # TODO(integration): replace with a real call to
    # app.analytics.health_score.compute_health_score(...) once available,
    # feeding it the updated recurring/debt/forecast state so the
    # cash-flow-stability and emergency-fund sub-scores are recomputed
    # properly instead of this linear approximation.

    Heuristic: every extra ~1000 INR/month of free cash flow is worth
    roughly +0.8 health points, capped so a single action can't swing the
    score unrealistically, and diminishing near the top of the 0-100 scale.
    """
    raw_delta = (free_cash_flow_delta / 1000.0) * 0.8
    raw_delta = max(-15.0, min(15.0, raw_delta))
    new_score = current_health_score + raw_delta
    new_score = max(0.0, min(100.0, new_score))
    return round(new_score, 2)


def _remove_recurring(recurring: list[RecurringObligation], group_ids: list[str]) -> list[RecurringObligation]:
    return [r for r in recurring if r.group_id not in group_ids]


def _find_debt(debts: list[Debt], debt_id: str) -> Optional[Debt]:
    for d in debts:
        if d.id == debt_id:
            return d
    return None


# ---------------------------------------------------------------------------
# Upgrade 1: explicit minimum-balance guard.
# ---------------------------------------------------------------------------


def _minimum_balance_breach(
    forecast: CashFlowForecast, minimum_balance_to_keep: float
) -> tuple[bool, Optional[date]]:
    """Does `forecast`'s P50 (median) path dip below `minimum_balance_to_keep`
    at any point in the horizon? We deliberately check P50, not P10 -- P10 is
    already a pessimistic tail, so guarding on it would flag almost every
    action as unsafe. P50 is the "expected" path, so breaching it is a
    meaningful, actionable warning rather than noise.

    Returns (breaches, first_date_of_breach_or_None). Never raises.
    """
    for point in forecast.points:
        if point.p50 < minimum_balance_to_keep:
            return True, point.date
    return False, None


# ---------------------------------------------------------------------------
# Per-action handlers. Each returns (forecast_after, health_after, impact).
# ---------------------------------------------------------------------------


def _do_cancel_subscription(inputs: ForecastInputs, params: dict, health_before: float):
    group_ids = params.get("group_ids") or ([params["group_id"]] if "group_id" in params else [])
    if not group_ids:
        raise ValueError("cancel_subscription requires 'group_id' or 'group_ids'")

    cancelled = [r for r in inputs.recurring if r.group_id in group_ids]
    new_recurring = _remove_recurring(inputs.recurring, group_ids)

    fcf_before = _free_cash_flow(inputs.recurring)
    fcf_after = _free_cash_flow(new_recurring)

    forecast_after = _forecast_from(inputs, recurring_override=new_recurring)
    health_after = _approx_health_delta(fcf_after - fcf_before, health_before)

    monthly_saved = sum(abs(r.amount) for r in cancelled)  # amounts are negative for outflows
    impact = ImpactEstimate(
        metric="monthly free cash flow",
        before=round(fcf_before, 2),
        after=round(fcf_after, 2),
        delta=round(fcf_after - fcf_before, 2),
        horizon="next 30 days",
    )
    return forecast_after, health_after, impact, monthly_saved


def _do_reduce_category_spend(inputs: ForecastInputs, params: dict, health_before: float):
    category = params.get("category")
    percent = float(params.get("percent", 20))
    if category is None:
        raise ValueError("reduce_category_spend requires 'category'")

    txns = inputs.transactions
    if txns is not None and not txns.empty and "category" in txns.columns:
        adjusted = txns.copy()
        mask = adjusted["category"] == category
        # only outflow (negative) amounts get scaled down in magnitude
        adjusted.loc[mask, "amount"] = adjusted.loc[mask, "amount"] * (1 - percent / 100.0)
        avg_before = float(txns.loc[mask, "amount"].sum() / max(txns["date"].nunique(), 1)) if mask.any() else 0.0
        avg_after = float(adjusted.loc[mask, "amount"].sum() / max(adjusted["date"].nunique(), 1)) if mask.any() else 0.0
    else:
        # No transaction history for this category -- fall back to a sane
        # default assumption that the named category is ~20% of total
        # residual spend, and scale the *default* residual band down by
        # that share * percent. This is a coarse fallback, documented here.
        adjusted = None
        avg_before = 0.0
        avg_after = 0.0

    forecast_before = _forecast_from(inputs)
    forecast_after = _forecast_from(inputs, transactions_override=adjusted)

    monthly_reduction = abs(avg_before - avg_after) * 30
    fcf_before = _free_cash_flow(inputs.recurring)
    fcf_after = fcf_before + monthly_reduction
    health_after = _approx_health_delta(monthly_reduction, health_before)

    impact = ImpactEstimate(
        metric=f"monthly '{category}' spend",
        before=round(abs(avg_before) * 30, 2),
        after=round(abs(avg_after) * 30, 2),
        delta=round(-monthly_reduction, 2),
        horizon="next 30 days",
    )
    return forecast_after, health_after, impact, forecast_before


def _do_prepay_debt(inputs: ForecastInputs, params: dict, health_before: float):
    debt_id = params.get("debt_id")
    extra_payment = float(params.get("extra_payment", 0))
    debt = _find_debt(inputs.debts, debt_id) if debt_id else None
    if debt is None:
        raise ValueError(f"prepay_debt: unknown debt_id {debt_id!r}")

    baseline = amortize(debt.principal, debt.interest_rate_apr, debt.minimum_payment, 0.0)
    with_extra = amortize(debt.principal, debt.interest_rate_apr, debt.minimum_payment, extra_payment)

    # Reflect the extra payment as a new outflow in the recurring schedule
    # for the forecast (it reduces free cash flow while active).
    extra_obligation = RecurringObligation(
        group_id=f"sim-prepay-{debt.id}",
        merchant=f"Extra payment: {debt.id}",
        category=TxnCategory.emi_loan,
        amount=-extra_payment,
        frequency=RecurrenceFrequency.monthly,
        next_expected_date=datetime.now(timezone.utc).date() + timedelta(days=5),
        confidence=1.0,
    )

    new_recurring = inputs.recurring + [extra_obligation]
    forecast_after = _forecast_from(inputs, recurring_override=new_recurring)

    interest_saved = baseline.total_interest - with_extra.total_interest
    health_after = _approx_health_delta(interest_saved / 12.0, health_before)  # spread annualised benefit

    impact = ImpactEstimate(
        metric="total interest paid over remaining term",
        before=round(baseline.total_interest, 2),
        after=round(with_extra.total_interest, 2),
        delta=round(with_extra.total_interest - baseline.total_interest, 2),
        horizon=f"{baseline.months_to_payoff} months (baseline payoff)",
    )
    return forecast_after, health_after, impact, (baseline, with_extra)


def _do_increase_sip(inputs: ForecastInputs, params: dict, health_before: float):
    monthly_amount = float(params.get("amount", 0))
    horizon_years = float(params.get("horizon_years", 5))
    annual_return_pct = float(params.get("annual_return_pct", ASSUMED_ANNUAL_INVESTMENT_RETURN_PCT))

    sip_obligation = RecurringObligation(
        group_id="sim-increase-sip",
        merchant="Additional SIP",
        category=TxnCategory.investment_sip,
        amount=-monthly_amount,
        frequency=RecurrenceFrequency.monthly,
        next_expected_date=datetime.now(timezone.utc).date() + timedelta(days=3),
        confidence=1.0,
    )
    new_recurring = inputs.recurring + [sip_obligation]
    forecast_after = _forecast_from(inputs, recurring_override=new_recurring)

    # Future value of a monthly SIP (ordinary annuity, compounded monthly):
    # FV = P * (((1+r)^n - 1) / r) * (1+r)   [contribution at start of month]
    monthly_rate = annual_return_pct / 100.0 / 12.0
    n = int(round(horizon_years * 12))
    if monthly_rate > 0:
        future_value = monthly_amount * (((1 + monthly_rate) ** n - 1) / monthly_rate) * (1 + monthly_rate)
    else:
        future_value = monthly_amount * n
    total_contributed = monthly_amount * n

    fcf_before = _free_cash_flow(inputs.recurring)
    fcf_after = _free_cash_flow(new_recurring)
    health_after = _approx_health_delta(fcf_after - fcf_before, health_before)

    impact = ImpactEstimate(
        metric=f"projected investment value (ASSUMPTION: {annual_return_pct:.1f}%/yr, not guaranteed)",
        before=0.0,
        after=round(future_value, 2),
        delta=round(future_value - total_contributed, 2),  # projected growth over contributions
        horizon=f"{horizon_years:.0f} years",
    )
    return forecast_after, health_after, impact, total_contributed


def _do_build_emergency_fund(inputs: ForecastInputs, params: dict, health_before: float):
    monthly_contribution = float(params.get("monthly_contribution", 0))
    target_amount = float(params.get("target_amount", 0))
    current_saved = float(params.get("current_saved", 0))

    _NO_TARGET_SENTINEL = 9999.0  # JSON has no Infinity; use a large sentinel instead

    remaining = max(target_amount - current_saved, 0.0)
    months_to_target = (remaining / monthly_contribution) if monthly_contribution > 0 else _NO_TARGET_SENTINEL

    fund_obligation = RecurringObligation(
        group_id="sim-emergency-fund",
        merchant="Emergency fund transfer",
        category=TxnCategory.transfer,
        amount=-monthly_contribution,
        frequency=RecurrenceFrequency.monthly,
        next_expected_date=datetime.now(timezone.utc).date() + timedelta(days=2),
        confidence=1.0,
    )
    new_recurring = inputs.recurring + [fund_obligation]
    forecast_after = _forecast_from(inputs, recurring_override=new_recurring)

    fcf_before = _free_cash_flow(inputs.recurring)
    fcf_after = _free_cash_flow(new_recurring)
    # Building an emergency fund improves resilience even though it reduces
    # nominal free cash flow -- approximate a small positive health nudge
    # capped modestly, rather than penalising the score for saving money.
    health_after = _approx_health_delta(abs(monthly_contribution) * 0.3, health_before)

    # "before" reflects the baseline with no dedicated fund contribution
    # running at all, i.e. the target is never reached on its own -- always
    # the sentinel, regardless of what contribution this simulation proposes.
    impact = ImpactEstimate(
        metric="months to reach emergency-fund target",
        before=_NO_TARGET_SENTINEL,
        after=round(months_to_target, 2),
        delta=round(months_to_target, 2) if monthly_contribution > 0 else 0.0,
        horizon="until target reached",
    )
    return forecast_after, health_after, impact, months_to_target


def _do_refinance_debt(inputs: ForecastInputs, params: dict, health_before: float):
    debt_id = params.get("debt_id")
    new_apr = float(params.get("new_apr", 0))
    debt = _find_debt(inputs.debts, debt_id) if debt_id else None
    if debt is None:
        raise ValueError(f"refinance_debt: unknown debt_id {debt_id!r}")

    current = amortize(debt.principal, debt.interest_rate_apr, debt.minimum_payment, 0.0)
    refinanced = amortize(debt.principal, new_apr, debt.minimum_payment, 0.0)

    forecast_after = _forecast_from(inputs)  # payment amount unchanged -> schedule unaffected
    health_after = _approx_health_delta((current.total_interest - refinanced.total_interest) / 12.0, health_before)

    impact = ImpactEstimate(
        metric="total interest paid over remaining term",
        before=round(current.total_interest, 2),
        after=round(refinanced.total_interest, 2),
        delta=round(refinanced.total_interest - current.total_interest, 2),
        horizon=f"{current.months_to_payoff} months (current payoff)",
    )
    return forecast_after, health_after, impact, (current, refinanced)


def _do_affordability_check(inputs: ForecastInputs, params: dict, health_before: float):
    amount = float(params.get("amount", 0))
    is_recurring = bool(params.get("is_recurring", False))
    label = params.get("label", "one-time expense")

    forecast_before = _forecast_from(inputs)

    if is_recurring:
        new_item = RecurringObligation(
            group_id="sim-affordability-recurring",
            merchant=label,
            category=TxnCategory.other,
            amount=-amount,
            frequency=RecurrenceFrequency(params.get("frequency", "monthly")),
            next_expected_date=datetime.now(timezone.utc).date() + timedelta(days=7),
            confidence=1.0,
        )
        forecast_after = _forecast_from(inputs, recurring_override=inputs.recurring + [new_item])
        strategies: list[dict] = []  # recurring commitments don't fit the one-time-purchase strategies below
    else:
        forecast_after = _forecast_from(inputs, starting_balance_override=inputs.starting_balance - amount)
        strategies = evaluate_affordability_strategies(
            amount,
            label,
            forecast_inputs=inputs,
            installment_months=int(params.get("installment_months", 3)),
        )

    can_afford = forecast_after.first_gap_date is None

    health_after = health_before  # affordability check is informational, not a real action
    impact = ImpactEstimate(
        # User-facing label -- keep it free of internal sentinel/implementation
        # details (the 9999 "no gap" placeholder used for before/after below).
        metric="days until projected cash-flow gap",
        before=(forecast_before.first_gap_date - datetime.now(timezone.utc).date()).days if forecast_before.first_gap_date else 9999,
        after=(forecast_after.first_gap_date - datetime.now(timezone.utc).date()).days if forecast_after.first_gap_date else 9999,
        delta=(
            ((forecast_after.first_gap_date - forecast_before.first_gap_date).days)
            if (forecast_after.first_gap_date and forecast_before.first_gap_date)
            else 0
        ),
        horizon=f"next {inputs.horizon_days} days",
    )
    return forecast_after, health_after, impact, {"can_afford": can_afford, "strategies": strategies}


# ---------------------------------------------------------------------------
# Upgrade 2: multi-strategy affordability.
# ---------------------------------------------------------------------------


def evaluate_affordability_strategies(
    amount: float,
    description: str,
    *,
    forecast_inputs: ForecastInputs,
    installment_months: int = 3,
) -> list[dict]:
    """Return several ranked ways to afford `amount`, each carrying its own
    safety evaluation against `forecast_inputs.minimum_balance_to_keep`.

    Every strategy's safety check is derived from the SAME baseline P50 path
    (`base_p50`), computed once, because paying a lump sum on day t is
    mathematically just "subtract the lump from every day's balance from t
    onward" -- no need to re-run the forecast per candidate day.

    Ranking (documented tie-break, mirrors Penny's lexicographic approach):
      1. `pay_in_full_now` always sorts first if it is safe -- it fully
         resolves the purchase today with zero ongoing modification to the
         user's cash flow.
      2. Otherwise, rank by (days_until_purchase_is_effectively_made,
         number_of_plan_modifications) ascending -- i.e. prefer whichever
         safe option gets the purchase done soonest, and among options that
         get it done on the same day, prefer the one that changes fewest
         future obligations. `installments` and `partial_now_deferred` both
         "start" the purchase today (offset 0) but carry 1 and 2
         modifications respectively; `wait_until_safe` delays the purchase
         itself, so its offset is however many days out the safe date is.
    """
    today = datetime.now(timezone.utc).date()
    buffer = forecast_inputs.minimum_balance_to_keep

    baseline_forecast = _forecast_from(forecast_inputs)
    base_p50 = [p.p50 for p in baseline_forecast.points]
    horizon = len(base_p50)

    def _min_from(idx: int, offset: float) -> float:
        """Minimum P50 balance from day `idx` to the end of the horizon,
        after subtracting a constant `offset` (a lump paid at/behore idx)."""
        if idx >= horizon:
            return base_p50[-1] - offset if base_p50 else 0.0
        return min(base_p50[idx:]) - offset

    strategies: list[dict] = []

    # --- pay_in_full_now ----------------------------------------------------
    full_min = _min_from(0, amount)
    full_safe = full_min >= buffer
    if full_safe:
        strategies.append(
            {
                "strategy": "pay_in_full_now",
                "safe": True,
                "date": today.isoformat(),
                "amount_paid_now": round(amount, 2),
                "amount_deferred": 0.0,
                "min_balance_after": round(full_min, 2),
                "note": f"Pay the full ₹{amount:,.0f} for {description} today.",
                "_rank_key": (0, 0),
            }
        )

    # --- installments --------------------------------------------------------
    if installment_months > 0:
        monthly_installment = amount / installment_months
        installment_item = RecurringObligation(
            group_id="sim-affordability-installments",
            merchant=f"Installment: {description}",
            category=TxnCategory.other,
            amount=-monthly_installment,
            frequency=RecurrenceFrequency.monthly,
            next_expected_date=today + timedelta(days=30),
            confidence=1.0,
        )
        installment_forecast = _forecast_from(
            forecast_inputs, recurring_override=forecast_inputs.recurring + [installment_item]
        )
        installment_min = min((p.p50 for p in installment_forecast.points), default=0.0)
        installment_safe = installment_min >= buffer
        if installment_safe:
            strategies.append(
                {
                    "strategy": "installments",
                    "safe": True,
                    "date": today.isoformat(),
                    "amount_paid_now": 0.0,
                    "amount_deferred": round(amount, 2),
                    "installment_amount": round(monthly_installment, 2),
                    "installment_months": installment_months,
                    "min_balance_after": round(installment_min, 2),
                    "note": (
                        f"Spread ₹{amount:,.0f} for {description} over "
                        f"{installment_months} monthly installments of "
                        f"₹{monthly_installment:,.0f}, starting next month."
                    ),
                    "_rank_key": (0, 1),
                }
            )

    # --- partial_now_deferred -------------------------------------------------
    half = amount / 2.0
    half_min = _min_from(0, half)
    half_safe = half_min >= buffer
    if half_safe:
        deferred_date: Optional[date] = None
        for idx in range(horizon):
            if _min_from(idx, half) >= buffer:
                deferred_date = today + timedelta(days=idx)
                break
        strategies.append(
            {
                "strategy": "partial_now_deferred",
                "safe": True,
                "date": today.isoformat(),
                "amount_paid_now": round(half, 2),
                "amount_deferred": round(half, 2),
                "deferred_payment_date": deferred_date.isoformat() if deferred_date else None,
                "min_balance_after": round(half_min, 2),
                "note": (
                    f"Pay ₹{half:,.0f} now toward {description}; pay the "
                    f"remaining ₹{half:,.0f} "
                    + (
                        f"on {deferred_date.isoformat()}, the first date the "
                        f"forecast shows it's safe to do so."
                        if deferred_date
                        else "-- no date within the forecast horizon is safe "
                        "for the remaining payment."
                    )
                ),
                "_rank_key": (0, 2),
            }
        )

    # --- wait_until_safe -------------------------------------------------------
    safe_idx: Optional[int] = None
    for idx in range(horizon):
        if _min_from(idx, amount) >= buffer:
            safe_idx = idx
            break
    if safe_idx is not None:
        safe_date = today + timedelta(days=safe_idx)
        strategies.append(
            {
                "strategy": "wait_until_safe",
                "safe": True,
                "date": safe_date.isoformat(),
                "amount_paid_now": 0.0,
                "amount_deferred": round(amount, 2),
                "min_balance_after": round(_min_from(safe_idx, amount), 2),
                "note": (
                    f"Wait until {safe_date.isoformat()} to pay the full "
                    f"₹{amount:,.0f} for {description} -- the first date the "
                    f"forecast shows it won't breach your minimum balance."
                ),
                "_rank_key": (safe_idx, 1),
            }
        )
    else:
        strategies.append(
            {
                "strategy": "wait_until_safe",
                "safe": False,
                "date": None,
                "amount_paid_now": 0.0,
                "amount_deferred": round(amount, 2),
                "min_balance_after": None,
                "note": (
                    f"No date within the next {horizon} days is projected to be "
                    f"safe for the full ₹{amount:,.0f} -- consider a smaller "
                    f"amount, installments, or raising income/cutting spend first."
                ),
                "_rank_key": (horizon + 1, 1),
            }
        )

    strategies.sort(key=lambda s: s["_rank_key"])
    for s in strategies:
        del s["_rank_key"]
    return strategies


def _do_shift_payment_date(inputs: ForecastInputs, params: dict, health_before: float):
    group_id = params.get("group_id")
    new_day = params.get("new_day_of_month")
    if group_id is None:
        raise ValueError("shift_payment_date requires 'group_id'")

    forecast_before = _forecast_from(inputs)

    new_recurring = []
    for item in inputs.recurring:
        if item.group_id == group_id:
            old_date = item.next_expected_date
            if new_day:
                try:
                    shifted = old_date.replace(day=int(new_day))
                except ValueError:
                    shifted = old_date  # invalid day for this month, leave unchanged
            else:
                shift_days = int(params.get("shift_days", 0))
                shifted = old_date + timedelta(days=shift_days)
            item = item.model_copy(update={"next_expected_date": shifted})
        new_recurring.append(item)

    forecast_after = _forecast_from(inputs, recurring_override=new_recurring)
    health_after = health_before  # shifting a date doesn't change total cash flow, only timing

    before_gap = (forecast_before.first_gap_date - datetime.now(timezone.utc).date()).days if forecast_before.first_gap_date else 9999
    after_gap = (forecast_after.first_gap_date - datetime.now(timezone.utc).date()).days if forecast_after.first_gap_date else 9999

    impact = ImpactEstimate(
        metric="days until first projected cash-flow gap",
        before=before_gap,
        after=after_gap,
        delta=after_gap - before_gap,
        horizon=f"next {inputs.horizon_days} days",
    )
    return forecast_after, health_after, impact, new_recurring


_HANDLERS = {
    ActionType.cancel_subscription: _do_cancel_subscription,
    ActionType.reduce_category_spend: _do_reduce_category_spend,
    ActionType.prepay_debt: _do_prepay_debt,
    ActionType.increase_sip: _do_increase_sip,
    ActionType.build_emergency_fund: _do_build_emergency_fund,
    ActionType.refinance_debt: _do_refinance_debt,
    ActionType.affordability_check: _do_affordability_check,
    ActionType.shift_payment_date: _do_shift_payment_date,
}


def simulate(
    action: ActionType,
    action_params: dict,
    *,
    current_forecast_inputs: ForecastInputs,
    current_health_score: float,
) -> SimulationResult:
    """Run a single what-if simulation and return the full before/after
    result, including a populated ImpactEstimate (never null)."""
    handler = _HANDLERS.get(action)
    if handler is None:
        raise ValueError(f"Unsupported action type: {action}")

    forecast_before = _forecast_from(current_forecast_inputs)
    result = handler(current_forecast_inputs, action_params, current_health_score)
    forecast_after, health_after, impact, _extra = result

    # Confidence of the *simulation* is bounded by the confidence of the
    # underlying forecast (before AND after) -- we can't be more sure of a
    # what-if than we are of the baseline it's built on.
    confidence = round(min(forecast_before.confidence, forecast_after.confidence), 3)

    # Upgrade 1: minimum-balance guard -- flag, never block.
    breaches_minimum_balance, min_balance_date = _minimum_balance_breach(
        forecast_after, current_forecast_inputs.minimum_balance_to_keep
    )

    # Upgrade 2: affordability strategies are only produced by the
    # affordability_check handler, which packs them into `_extra`.
    affordability_strategies: Optional[list[dict]] = None
    if action == ActionType.affordability_check and isinstance(_extra, dict):
        affordability_strategies = _extra.get("strategies")

    return SimulationResult(
        request=SimulationRequest(action=action, action_params=action_params),
        health_score_before=round(current_health_score, 2),
        health_score_after=round(health_after, 2),
        forecast_before=forecast_before,
        forecast_after=forecast_after,
        impact=impact,
        confidence=confidence,
        breaches_minimum_balance=breaches_minimum_balance,
        min_balance_date=min_balance_date,
        affordability_strategies=affordability_strategies,
    )


def compare_scenarios(
    actions: list[SimulationRequest],
    *,
    current_forecast_inputs: ForecastInputs,
    current_health_score: float,
) -> list[SimulationResult]:
    """Thin wrapper: run several what-ifs side by side against the SAME
    baseline state (each scenario is independent, not cumulative), powering
    a "compare N options" UI."""
    return [
        simulate(
            req.action,
            req.action_params,
            current_forecast_inputs=current_forecast_inputs,
            current_health_score=current_health_score,
        )
        for req in actions
    ]
