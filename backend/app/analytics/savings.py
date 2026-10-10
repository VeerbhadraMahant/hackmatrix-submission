"""Savings rate and emergency-fund coverage, computed from a plain
transactions DataFrame (columns: date, amount, merchant, category,
account_id, is_recurring). Positive amount = inflow, negative = outflow,
matching schemas.Transaction.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from app.schemas import TxnCategory

# Categories treated as "essential" spend for emergency-fund sizing.
_ESSENTIAL_CATEGORIES = {
    TxnCategory.rent_housing.value,
    TxnCategory.emi_loan.value,
    TxnCategory.utilities.value,
    TxnCategory.groceries.value,
}


def savings_rate(total_income: float, total_expenses: float) -> float:
    """(income - expenses) / income. `total_expenses` should be a positive
    magnitude. Returns 0 if income is non-positive (avoid div-by-zero /
    nonsensical negative-income ratios)."""
    if total_income <= 0:
        return 0.0
    return (total_income - total_expenses) / total_income


def trailing_savings_rate(df: pd.DataFrame, months: int, as_of: date | None = None) -> float:
    """Savings rate over the trailing `months` months of transaction history.
    Income = sum of positive amounts; expenses = sum of |negative amounts|,
    excluding transfers between the user's own accounts (category=transfer)
    which are not real spend."""
    if df.empty:
        return 0.0

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    as_of_ts = pd.Timestamp(as_of) if as_of is not None else work["date"].max()
    window_start = as_of_ts - pd.DateOffset(months=months)
    window = work[(work["date"] > window_start) & (work["date"] <= as_of_ts)]
    # Exclude transfers between the user's own accounts, AND credit-card bill
    # payments: a CC bill payment moves cash from checking to pay off charges
    # that were already counted as spend (dining/shopping/etc.) at the time
    # they were made, so including it too double-counts that spend. (Bug
    # found during integration: real persona data has both the original
    # credit-card purchase AND the monthly bill-payment transaction, which
    # without this exclusion pushed several personas' savings rate strongly
    # negative even though their discretionary spend alone was reasonable.)
    # SIPs are contributions to the user's own investments (saving, not spend), so they are excluded too.
    _excluded = {TxnCategory.transfer.value, TxnCategory.credit_card_payment.value, TxnCategory.investment_sip.value}
    window = window[~window["category"].isin(_excluded)]

    income_total = window.loc[window["amount"] > 0, "amount"].sum()
    expense_total = -window.loc[window["amount"] < 0, "amount"].sum()
    return savings_rate(float(income_total), float(expense_total))


def emergency_fund_months(
    liquid_balance: float, df: pd.DataFrame, months_window: int = 3, as_of: date | None = None
) -> float:
    """liquid savings balance / average monthly essential expenses (rent,
    EMI, utilities, groceries) over the trailing `months_window` months."""
    if df.empty:
        return 0.0

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    as_of_ts = pd.Timestamp(as_of) if as_of is not None else work["date"].max()
    window_start = as_of_ts - pd.DateOffset(months=months_window)
    window = work[(work["date"] > window_start) & (work["date"] <= as_of_ts)]

    essential = window[window["category"].isin(_ESSENTIAL_CATEGORIES) & (window["amount"] < 0)]
    total_essential = -essential["amount"].sum()
    avg_monthly_essential = total_essential / months_window if months_window > 0 else 0.0

    if avg_monthly_essential <= 0:
        return 0.0
    return liquid_balance / avg_monthly_essential
