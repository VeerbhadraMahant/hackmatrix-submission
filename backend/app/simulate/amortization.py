"""Standalone loan amortization math used by the simulation engine.

NOTE: analytics-agent's `app.analytics.debt` module is expected to expose a
richer `compare_payoff_strategies(debts, extra_payment)` (avalanche vs
snowball across *multiple* debts). Until that's merged, we implement a small
single-debt amortization routine here so `prepay_debt` / `refinance_debt`
work standalone. This is an intentional, temporary duplication -- de-dupe at
integration time by delegating to the analytics module instead.
"""
from __future__ import annotations

from dataclasses import dataclass

_MAX_MONTHS = 720  # 60 years -- safety cap against pathological inputs


@dataclass
class AmortizationResult:
    months_to_payoff: int
    total_interest: float
    total_paid: float


def amortize(
    principal: float,
    annual_rate_pct: float,
    monthly_payment: float,
    extra_monthly_payment: float = 0.0,
) -> AmortizationResult:
    """Simulate a standard amortizing loan paid down by a fixed monthly
    payment (+ optional extra principal payment each month).

    If the payment is too small to ever cover the accruing interest, we cap
    at `_MAX_MONTHS` and return whatever accumulated (this signals "does not
    amortize" rather than looping forever / raising).
    """
    balance = principal
    monthly_rate = annual_rate_pct / 100.0 / 12.0
    payment = monthly_payment + extra_monthly_payment
    total_interest = 0.0
    months = 0

    if principal <= 0:
        return AmortizationResult(months_to_payoff=0, total_interest=0.0, total_paid=0.0)

    while balance > 0 and months < _MAX_MONTHS:
        interest = balance * monthly_rate
        total_interest += interest
        principal_component = payment - interest
        if principal_component <= 0:
            # payment doesn't even cover interest -- loan never amortizes
            months = _MAX_MONTHS
            break
        balance -= principal_component
        months += 1
        if balance < 0:
            # last payment was larger than needed; correct the overshoot
            total_interest += balance  # balance is negative here, reduces interest slightly
            balance = 0

    total_paid = principal + total_interest
    return AmortizationResult(months_to_payoff=months, total_interest=round(total_interest, 2), total_paid=round(total_paid, 2))
