"""Debt pressure analysis: DTI, interest cost, credit utilization, and
avalanche-vs-snowball payoff simulation.

Pure functions over `list[Debt]` (schemas.py) so this integrates cleanly with
forecast-sim-agent's simulate/recommend engines without depending on the DB.
"""
from __future__ import annotations

from typing import Optional

from app.schemas import Debt

_MAX_SIMULATION_MONTHS = 600  # safety cap (50 years) against non-convergent inputs


def compute_dti(debts: list[Debt], monthly_income: float) -> float:
    """Debt-to-income ratio = sum of minimum payments / monthly income."""
    if monthly_income <= 0:
        return 0.0
    total_min_payments = sum(d.minimum_payment for d in debts)
    return total_min_payments / monthly_income


def monthly_interest_cost(debt: Debt) -> float:
    """Effective interest accrued in one month at the debt's current
    principal, i.e. principal * (APR / 12)."""
    return debt.principal * (debt.interest_rate_apr / 100.0) / 12.0


def credit_utilization(balance: float, credit_limit: Optional[float]) -> Optional[float]:
    """balance / credit_limit, or None if no limit is known (e.g. not a
    revolving credit product)."""
    if not credit_limit or credit_limit <= 0:
        return None
    return balance / credit_limit


def _simulate_payoff(debts: list[Debt], order: list[str], extra_monthly_payment: float) -> dict:
    """Simulate month-by-month payoff given a priority `order` (list of debt
    ids, highest priority first for extra payments). Minimum payments freed
    up by a fully-paid debt roll into the extra-payment pool for the next
    debt in priority order (this is what makes avalanche/snowball compound
    faster than just paying minimums)."""
    balances = {d.id: d.principal for d in debts}
    apr = {d.id: d.interest_rate_apr for d in debts}
    min_pay = {d.id: d.minimum_payment for d in debts}

    total_interest = 0.0
    months = 0
    freed_permanently = 0.0  # minimum payments no longer owed (debts already paid off)

    while any(b > 0.01 for b in balances.values()) and months < _MAX_SIMULATION_MONTHS:
        months += 1

        # accrue interest for the month on remaining balances
        for debt_id in order:
            if balances[debt_id] <= 0:
                continue
            interest = balances[debt_id] * (apr[debt_id] / 100.0) / 12.0
            total_interest += interest
            balances[debt_id] += interest

        # pay minimums on everything still outstanding
        for debt_id in order:
            if balances[debt_id] <= 0:
                continue
            pay = min(min_pay[debt_id], balances[debt_id])
            balances[debt_id] -= pay

        # apply extra payment pool (user's stated extra + freed-up minimums
        # from already-paid-off debts) to the highest-priority debt with a
        # remaining balance
        pool = extra_monthly_payment + freed_permanently
        for debt_id in order:
            if pool <= 0:
                break
            if balances[debt_id] <= 0:
                continue
            pay = min(pool, balances[debt_id])
            balances[debt_id] -= pay
            pool -= pay

        # recompute which debts are newly fully paid this month, freeing
        # their minimum payment for future months
        freed_permanently = sum(
            min_pay[debt_id] for debt_id in order if balances[debt_id] <= 0.01
        )

    return {
        "months_to_debt_free": months,
        "total_interest_paid": round(total_interest, 2),
    }


def compare_payoff_strategies(debts: list[Debt], extra_monthly_payment: float) -> dict:
    """Compare avalanche (highest APR first) vs snowball (smallest balance
    first) payoff order given a hypothetical extra monthly payment.

    Returns {"avalanche": {...}, "snowball": {...}} each with
    `months_to_debt_free` and `total_interest_paid`.
    """
    if not debts:
        empty = {"months_to_debt_free": 0, "total_interest_paid": 0.0}
        return {"avalanche": empty, "snowball": empty}

    avalanche_order = [d.id for d in sorted(debts, key=lambda d: d.interest_rate_apr, reverse=True)]
    snowball_order = [d.id for d in sorted(debts, key=lambda d: d.principal)]

    return {
        "avalanche": _simulate_payoff(debts, avalanche_order, extra_monthly_payment),
        "snowball": _simulate_payoff(debts, snowball_order, extra_monthly_payment),
    }
