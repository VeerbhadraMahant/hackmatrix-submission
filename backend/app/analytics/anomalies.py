"""Anomaly detection over a transactions DataFrame.

Flags:
  1. Transactions > 2.5 std-dev above the rolling per-category mean, using
     only prior same-category samples (min 5) so we never "peek" at future
     data -- this is meant to run incrementally, the same way it would in
     production against a growing transaction log.
  2. A never-seen-before merchant whose amount is > 3x the category's
     (historical, i.e. prior-to-this-txn) median.

Returns `Fact` objects (schemas.py) with self-contained, human-readable text.
"""
from __future__ import annotations

import statistics

import pandas as pd

from app.schemas import Fact

_MIN_PRIOR_SAMPLES = 5
_STD_DEV_THRESHOLD = 2.5
_NEW_MERCHANT_MULTIPLE = 3.0


def detect_anomalies(df: pd.DataFrame) -> list[Fact]:
    """Only considers outflows (amount < 0); inflows (salary, refunds) are
    not spend anomalies in this sense."""
    if df.empty:
        return []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work = work.sort_values("date").reset_index(drop=True)
    work = work[work["amount"] < 0].copy()
    if work.empty:
        return []
    work["abs_amount"] = -work["amount"]

    facts: list[Fact] = []

    # running per-category history, in chronological order
    category_history: dict[str, list[float]] = {}
    seen_merchants: set[str] = set()

    for _, row in work.iterrows():
        category = row["category"]
        merchant = row["merchant"]
        amount = float(row["abs_amount"])
        txn_id = row.get("id", "")
        when = row["date"].date()

        prior = category_history.setdefault(category, [])

        # --- rule 1: statistical outlier vs prior same-category spend ------
        if len(prior) >= _MIN_PRIOR_SAMPLES:
            mean = statistics.mean(prior)
            stdev = statistics.pstdev(prior)
            if stdev > 0:
                z = (amount - mean) / stdev
                if z > _STD_DEV_THRESHOLD:
                    multiple = amount / mean if mean > 0 else float("inf")
                    facts.append(
                        Fact(
                            text=(
                                f"An unusually large ₹{amount:,.0f} transaction at "
                                f"{merchant} on {when.isoformat()} is {multiple:.1f}x "
                                f"your typical spend in {category}."
                            ),
                            value=amount,
                            source_txn_ids=[txn_id] if txn_id else [],
                        )
                    )

        # --- rule 2: brand-new merchant at an outsized amount ---------------
        if merchant not in seen_merchants and len(prior) >= 1:
            median = statistics.median(prior)
            if median > 0 and amount > _NEW_MERCHANT_MULTIPLE * median:
                multiple = amount / median
                facts.append(
                    Fact(
                        text=(
                            f"A new merchant, {merchant}, charged ₹{amount:,.0f} on "
                            f"{when.isoformat()} -- {multiple:.1f}x the median "
                            f"{category} transaction, and you have no prior history "
                            f"with this merchant."
                        ),
                        value=amount,
                        source_txn_ids=[txn_id] if txn_id else [],
                    )
                )

        seen_merchants.add(merchant)
        prior.append(amount)

    return facts
