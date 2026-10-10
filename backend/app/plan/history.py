"""Aggregate transactions into the monthly streams the planner forecasts."""
from __future__ import annotations

import pandas as pd

from app.schemas import TxnCategory

# rent/utilities/groceries/healthcare = savings._ESSENTIAL_CATEGORIES U recommend PROTECTED, minus emi_loan
ESSENTIAL = {
    TxnCategory.rent_housing.value,
    TxnCategory.utilities.value,
    TxnCategory.groceries.value,
    TxnCategory.healthcare.value,
}
# emi_loan is covered by Debt.minimum_payment; transfers/card-bill payments are not new spend
_EXCLUDED = {TxnCategory.transfer.value, TxnCategory.credit_card_payment.value, TxnCategory.emi_loan.value}


def monthly_flows(df: pd.DataFrame) -> pd.DataFrame:
    """Index 1..N (month index), columns month ('YYYY-MM'), income, essential,
    discretionary (positive INR). Drops a partial first/last calendar month."""
    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work = work[~work["category"].isin(_EXCLUDED)]
    work["month"] = work["date"].dt.strftime("%Y-%m")
    first, last = work["date"].min(), work["date"].max()
    if first.day > 3:
        work = work[work["month"] != first.strftime("%Y-%m")]
    if (last + pd.Timedelta(days=3)).month == last.month:
        work = work[work["month"] != last.strftime("%Y-%m")]
    out = pd.DataFrame({"month": sorted(work["month"].unique())})
    g = lambda mask: work[mask].groupby("month")["amount"].sum().abs()  # noqa: E731
    out["income"] = out["month"].map(g(work["amount"] > 0)).fillna(0.0)
    out["essential"] = out["month"].map(g((work["amount"] < 0) & work["category"].isin(ESSENTIAL))).fillna(0.0)
    out["discretionary"] = out["month"].map(g((work["amount"] < 0) & ~work["category"].isin(ESSENTIAL))).fillna(0.0)
    out.index = range(1, len(out) + 1)
    return out
