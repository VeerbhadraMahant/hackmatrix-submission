"""Recurring obligation + redundant-subscription detection.

Pure functions over a plain ``pandas.DataFrame`` of transactions with columns
``date, amount, merchant, category, account_id, is_recurring`` so this module
is independent of data-agent's generator/DB models and unit-testable with
small hand-built fixtures.
"""
from __future__ import annotations

import re
import statistics
from datetime import date, timedelta

import pandas as pd

from app.schemas import RecurrenceFrequency, RecurringObligation, TxnCategory

# ---------------------------------------------------------------------------
# Merchant normalization
# ---------------------------------------------------------------------------

# Trailing store/terminal/txn-id numbers, e.g. "Amazon 4482", "SWIGGY*9981",
# "IRCTC-00213" -- strip so the same merchant recurs under one key.
_TRAILING_ID_RE = re.compile(r"[\s#*_\-]*\d{2,}\s*$")
_MULTI_SPACE_RE = re.compile(r"\s+")


def normalize_merchant(name: str) -> str:
    """Lowercase, strip trailing numeric IDs/terminal codes, collapse
    whitespace/punctuation so recurring charges from the same biller group
    together even when the raw descriptor varies slightly."""
    s = (name or "").strip().lower()
    # repeatedly strip trailing numeric/ID suffixes (handles "netflix 123 456")
    prev = None
    while prev != s:
        prev = s
        s = _TRAILING_ID_RE.sub("", s).strip()
    s = re.sub(r"[^a-z0-9&+.\s]", " ", s)
    s = _MULTI_SPACE_RE.sub(" ", s).strip()
    return s or (name or "").strip().lower()


# ---------------------------------------------------------------------------
# Frequency classification
# ---------------------------------------------------------------------------

# (label, typical_days, tolerance_days)
_FREQUENCY_BUCKETS: list[tuple[RecurrenceFrequency, int, int]] = [
    (RecurrenceFrequency.weekly, 7, 2),
    (RecurrenceFrequency.biweekly, 14, 3),
    (RecurrenceFrequency.monthly, 30, 5),
    (RecurrenceFrequency.quarterly, 90, 10),
    (RecurrenceFrequency.annual, 365, 20),
]


def _classify_frequency(median_gap: float) -> tuple[RecurrenceFrequency, int]:
    """Return (frequency, typical_interval_days) for a median inter-txn gap.
    Falls back to irregular if it doesn't fit any bucket within tolerance."""
    best: tuple[RecurrenceFrequency, int] | None = None
    best_dist = None
    for freq, typical, tol in _FREQUENCY_BUCKETS:
        dist = abs(median_gap - typical)
        if dist <= tol and (best_dist is None or dist < best_dist):
            best = (freq, typical)
            best_dist = dist
    if best is not None:
        return best
    return RecurrenceFrequency.irregular, max(1, round(median_gap))


def _coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    stdev = statistics.pstdev(values)
    return abs(stdev / mean)


def detect_recurring(df: pd.DataFrame) -> list[RecurringObligation]:
    """Group transactions by normalized merchant and flag recurring series.

    Criteria:
      (a) count >= 3 occurrences
      (b) consistent amount: coefficient of variation <= 0.05, OR same sign
          + same category throughout (looser, lowers confidence a bit)
      (c) consistent interval: cluster inter-transaction day gaps and
          classify into weekly/biweekly/monthly/quarterly/annual with
          tolerance; irregular gaps -> RecurrenceFrequency.irregular and a
          lower confidence score.

    Confidence blends amount-tightness and interval-tightness: a clean
    monthly subscription at a fixed price scores near 1.0; a series with
    loose timing or drifting amounts scores lower.
    """
    if df.empty:
        return []

    work = df.copy()
    work["date"] = pd.to_datetime(work["date"])
    work["merchant_norm"] = work["merchant"].apply(normalize_merchant)

    results: list[RecurringObligation] = []

    for merchant_norm, group in work.groupby("merchant_norm"):
        if len(group) < 3:
            continue
        group = group.sort_values("date")
        dates: list[date] = [d.date() for d in group["date"]]
        amounts: list[float] = group["amount"].tolist()

        # dominant category (mode)
        category = group["category"].mode().iloc[0]
        category = TxnCategory(category) if not isinstance(category, TxnCategory) else category

        same_sign = all(a >= 0 for a in amounts) or all(a <= 0 for a in amounts)
        amount_cov = _coefficient_of_variation(amounts)
        amount_consistent = amount_cov <= 0.05 or same_sign

        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        gaps = [g for g in gaps if g > 0]
        if not gaps:
            continue
        median_gap = statistics.median(gaps)
        gap_cov = _coefficient_of_variation([float(g) for g in gaps])

        frequency, typical_interval = _classify_frequency(median_gap)

        if not amount_consistent:
            # amounts drift too much to call this a clean recurring charge;
            # still report it (data-agent's generator may add small drift)
            # but at reduced confidence and only if the interval is tight.
            if gap_cov > 0.35:
                continue

        # --- confidence scoring -------------------------------------------------
        # amount_score: 1.0 for CoV=0, decays to 0 by CoV=0.3
        amount_score = max(0.0, 1 - amount_cov / 0.3)
        # interval_score: 1.0 for CoV=0, decays to 0 by CoV=0.5
        interval_score = max(0.0, 1 - gap_cov / 0.5)
        confidence = 0.5 * amount_score + 0.5 * interval_score
        if frequency == RecurrenceFrequency.irregular:
            confidence = min(confidence, 0.5)
        confidence = max(0.05, min(1.0, confidence))

        last_date = dates[-1]
        next_expected_date = last_date + timedelta(days=typical_interval)

        # representative amount: median (robust to outlier one-off surcharges)
        rep_amount = statistics.median(amounts)

        results.append(
            RecurringObligation(
                group_id=f"rg-{merchant_norm.replace(' ', '-')}",
                merchant=merchant_norm,
                category=category,
                amount=rep_amount,
                frequency=frequency,
                next_expected_date=next_expected_date,
                confidence=round(confidence, 3),
            )
        )

    return results


# ---------------------------------------------------------------------------
# Redundant subscription detection
# ---------------------------------------------------------------------------

# Small static merchant -> subgroup map for common Indian OTT/music apps.
# Not exhaustive; extend as new personas surface merchant names.
_SUBSCRIPTION_SUBGROUPS: dict[str, str] = {
    "netflix": "video_streaming",
    "amazon prime video": "video_streaming",
    "prime video": "video_streaming",
    "disney+ hotstar": "video_streaming",
    "disney hotstar": "video_streaming",
    "hotstar": "video_streaming",
    "sonyliv": "video_streaming",
    "zee5": "video_streaming",
    "jiocinema": "video_streaming",
    "apple tv+": "video_streaming",
    "apple tv": "video_streaming",
    "youtube premium": "video_streaming",
    "spotify": "music_streaming",
    "gaana": "music_streaming",
    "jiosaavn": "music_streaming",
    "wynk music": "music_streaming",
    "wynk": "music_streaming",
    "apple music": "music_streaming",
    "youtube music": "music_streaming",
}

# 2+ active subscriptions in the same subgroup (e.g. two OTT video services)
# is treated as likely-redundant since a household rarely needs both at once.
_REDUNDANCY_THRESHOLD = 2


def find_redundant_subscriptions(
    recurring: list[RecurringObligation],
) -> list[RecurringObligation]:
    """Flag recurring `subscriptions`-category obligations that look
    redundant: 2+ services mapped to the same subgroup (e.g. two video
    streaming subscriptions). We have no usage data, so this is a coarse
    heuristic, not a certainty -- callers should present it as a suggestion,
    not a fact."""
    subs = [r for r in recurring if r.category == TxnCategory.subscriptions]

    by_subgroup: dict[str, list[RecurringObligation]] = {}
    for r in subs:
        subgroup = _SUBSCRIPTION_SUBGROUPS.get(r.merchant.lower())
        if subgroup is None:
            continue
        by_subgroup.setdefault(subgroup, []).append(r)

    redundant: list[RecurringObligation] = []
    for _subgroup, items in by_subgroup.items():
        if len(items) >= _REDUNDANCY_THRESHOLD:
            redundant.extend(items)
    return redundant
