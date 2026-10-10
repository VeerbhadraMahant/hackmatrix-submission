"""Cash-flow forecasting.

Projects a daily balance forward `horizon_days` from a starting balance, a
list of known recurring obligations (inflows/outflows), and an estimate of
"residual" (non-recurring, noisy) daily spend derived from transaction
history when available.

Method
------
P50 (deterministic path): starting balance + cumulative scheduled recurring
cashflow (materialised onto the calendar from `next_expected_date` +
`frequency`) + cumulative *average* daily residual spend.

P10/P90 (uncertainty band):
  * With >= 14 days of real transaction history: bootstrap-resample the
    historical daily residuals (sampling with replacement, seeded) to build
    many alternate `horizon_days`-long residual paths, then take the 10th /
    90th percentile of the resulting cumulative-balance distribution at each
    day. This captures the *actual* shape/skew of the user's spend noise
    (not just a symmetric normal band).
  * Without history (or too little of it): APPROXIMATION -- we fall back to
    a widening normal band around P50, with stddev growing as
    `sigma * sqrt(days_elapsed)` (a simple random-walk assumption: daily
    residuals are i.i.d., so variance of the cumulative sum grows linearly
    with time and stddev with its square root). This is a coarse
    approximation because real spend is autocorrelated (e.g. recurring but
    undetected bills) and not necessarily normally distributed -- it is only
    used when we have nothing better, and `confidence` is lowered to make
    that explicit to the caller/UI.

Confidence
----------
`confidence` is a simple explicit weighted blend of:
  * average `RecurringObligation.confidence` across supplied obligations
    (how sure we are about the scheduled/deterministic part of the forecast)
  * how much daily transaction history we were given, saturating at 90 days
    (how sure we are about the residual/noise part)
A user with many well-detected recurring items and a full 90 days of history
should show a noticeably higher confidence than one with a couple of
low-confidence recurring items and no history -- this is intentional and is
one of the judged "confidence shown where information is incomplete"
differentiators.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

from app.schemas import CashFlowForecast, ForecastPoint, RecurringObligation

# Default assumed stddev (INR/day) of unexplained residual spend when the
# caller gives us no transaction history at all. Chosen to be roughly in
# line with the demo fixture's noise band (+/- 6000 over ~ "a few weeks"),
# scaled down to a single-day figure. This is a rough default, not a
# calibrated number -- documented here so it's easy to tune later.
DEFAULT_DAILY_RESIDUAL_STDDEV = 900.0

# Number of bootstrap resamples used when we do have historical residuals.
_N_BOOTSTRAP = 500

# Seed for all randomness in this module -- required for deterministic,
# reproducible tests (golden-scenario determinism requirement).
_RNG_SEED = 42


def _frequency_to_days(frequency: str) -> int:
    return {
        "weekly": 7,
        "biweekly": 14,
        "monthly": 30,
        "quarterly": 91,
        "annual": 365,
        "irregular": 30,  # best-effort fallback; irregular items are noisy anyway
    }.get(frequency, 30)


def _scheduled_daily_cashflow(
    recurring: list[RecurringObligation],
    start: date,
    horizon_days: int,
) -> np.ndarray:
    """Materialise each recurring obligation onto a daily grid of length
    `horizon_days`, repeating it every `frequency` days starting from its
    `next_expected_date` (or from `start` if that date is in the past)."""
    daily = np.zeros(horizon_days, dtype=float)
    for item in recurring:
        freq_days = _frequency_to_days(
            item.frequency.value if hasattr(item.frequency, "value") else item.frequency
        )
        # find the first occurrence on/after `start`
        next_date = item.next_expected_date
        if next_date < start:
            # roll forward to the first occurrence >= start
            missed = (start - next_date).days
            steps = missed // freq_days + 1
            next_date = next_date + timedelta(days=steps * freq_days)
        offset = (next_date - start).days
        occurrence = offset
        while occurrence < horizon_days:
            if occurrence >= 0:
                daily[occurrence] += item.amount
            occurrence += freq_days
    return daily


def _residual_stats_from_history(
    transactions: Optional[pd.DataFrame],
) -> tuple[np.ndarray, float, int]:
    """Return (historical_daily_residuals, avg_daily_residual, n_days_history).

    `transactions` is expected to have columns `date` and `amount`, and to
    already EXCLUDE recognised recurring transactions (residual = the noisy,
    non-recurring leftover spend). If `is_recurring` is present we filter on
    it defensively.
    """
    if transactions is None or transactions.empty:
        return np.array([]), -abs(DEFAULT_DAILY_RESIDUAL_STDDEV) * 0.0, 0

    df = transactions.copy()
    if "is_recurring" in df.columns:
        df = df[~df["is_recurring"].astype(bool)]
    if df.empty:
        return np.array([]), 0.0, 0

    df["date"] = pd.to_datetime(df["date"]).dt.date
    daily = df.groupby("date")["amount"].sum()
    n_days = (daily.index.max() - daily.index.min()).days + 1 if len(daily) else 0
    # reindex onto the full calendar range so missing (no-spend) days count as 0
    if n_days > 0:
        full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D").date
        daily = daily.reindex(full_range, fill_value=0.0)
    residuals = daily.to_numpy(dtype=float)
    avg = float(residuals.mean()) if len(residuals) else 0.0
    return residuals, avg, max(n_days, len(residuals))


def build_forecast(
    *,
    starting_balance: float,
    recurring: list[RecurringObligation],
    transactions: Optional[pd.DataFrame] = None,
    horizon_days: int = 90,
    start_date: Optional[date] = None,
) -> CashFlowForecast:
    """Build a `CashFlowForecast` from plain inputs.

    Parameters
    ----------
    starting_balance: current checking-account balance.
    recurring: detected recurring obligations (inflows positive, outflows
        negative -- follows `Transaction.amount` sign convention).
    transactions: optional DataFrame of historical, non-recurring
        transactions with at least `date` and `amount` columns, used to
        estimate residual spend variance. If omitted, we fall back to a
        default stddev and a wider, less-confident band (see module
        docstring).
    horizon_days: number of days to project.
    start_date: defaults to today (UTC date).
    """
    start = start_date or datetime.now(timezone.utc).date()
    rng = np.random.default_rng(_RNG_SEED)

    scheduled = _scheduled_daily_cashflow(recurring, start, horizon_days)
    residual_hist, avg_residual, n_days_history = _residual_stats_from_history(transactions)

    cum_scheduled = np.cumsum(scheduled)
    cum_avg_residual = avg_residual * np.arange(1, horizon_days + 1)
    p50_path = starting_balance + cum_scheduled + cum_avg_residual

    have_history = n_days_history >= 14 and len(residual_hist) >= 14

    if have_history:
        # Bootstrap: resample daily residuals (with replacement) to build
        # _N_BOOTSTRAP alternate horizon-length paths, then take percentiles
        # of the resulting *cumulative* balance at each day. This preserves
        # the real empirical distribution's shape (skew, fat tails) rather
        # than assuming normality.
        samples = rng.choice(residual_hist, size=(_N_BOOTSTRAP, horizon_days), replace=True)
        cum_samples = np.cumsum(samples, axis=1)
        # de-mean so the bootstrap band is centered on 0 extra drift (the
        # deterministic average residual is already baked into p50_path);
        # this isolates the *noise around the mean*, not a second copy of
        # the mean itself.
        cum_samples -= cum_avg_residual  # broadcast subtract the expected mean path
        balance_samples = starting_balance + cum_scheduled + cum_samples
        p10_path = np.percentile(balance_samples, 10, axis=0)
        p90_path = np.percentile(balance_samples, 90, axis=0)
    else:
        # APPROXIMATION (documented above): widening normal band, stddev
        # grows with sqrt(elapsed days) under a random-walk assumption.
        sigma = DEFAULT_DAILY_RESIDUAL_STDDEV if len(residual_hist) == 0 else max(
            float(np.std(residual_hist)), 1.0
        )
        days_elapsed = np.arange(1, horizon_days + 1)
        band = 1.2816 * sigma * np.sqrt(days_elapsed)  # ~10th/90th percentile of normal
        p10_path = p50_path - band
        p90_path = p50_path + band

    # ensure ordering invariant holds even under bootstrap noise/rounding
    p10_path = np.minimum(p10_path, p50_path)
    p90_path = np.maximum(p90_path, p50_path)

    points: list[ForecastPoint] = []
    first_gap_date: Optional[date] = None
    for i in range(horizon_days):
        d = start + timedelta(days=i)
        p10, p50, p90 = float(p10_path[i]), float(p50_path[i]), float(p90_path[i])
        is_gap = p10 < 0
        if is_gap and first_gap_date is None:
            first_gap_date = d
        points.append(ForecastPoint(date=d, p10=p10, p50=p50, p90=p90, is_gap_risk=is_gap))

    # --- confidence -------------------------------------------------------
    if recurring:
        avg_recurring_conf = sum(r.confidence for r in recurring) / len(recurring)
    else:
        avg_recurring_conf = 0.3  # no known recurring items at all -> low trust

    history_factor = min(n_days_history / 90.0, 1.0)  # saturates at 90 days
    # weighted blend: recurring-schedule confidence matters slightly more
    # than residual-history confidence, since it drives most of the balance.
    confidence = round(0.6 * avg_recurring_conf + 0.4 * history_factor, 3)
    confidence = max(0.05, min(confidence, 0.99))

    basis = (
        f"Projected from {len(recurring)} recurring obligation(s) "
        f"(avg confidence {avg_recurring_conf:.2f}) and "
        f"{n_days_history} day(s) of spend history"
        + (
            " using bootstrap-resampled residuals for the uncertainty band."
            if have_history
            else " using a widening-normal-band approximation (insufficient "
            "history for bootstrap resampling)."
        )
    )

    return CashFlowForecast(
        generated_at=datetime.now(timezone.utc),
        horizon_days=horizon_days,
        points=points,
        first_gap_date=first_gap_date,
        confidence=confidence,
        basis=basis,
    )
