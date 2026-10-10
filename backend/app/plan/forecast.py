"""Probabilistic monthly forecaster (joint month-bootstrap) + baselines + backtest.

Per stream (income, essential, discretionary) the point forecast is the median
of the last `window` training months. The residual vector of a whole month
(all three streams together) is resampled jointly, which keeps the
cross-stream correlation. Intervals are the empirical P10-P90 of the paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from app.analytics.recurring import detect_recurring
from app.plan.history import ESSENTIAL
from app.plan.schemas import BacktestRow, Band, ForecastMethod, PeriodForecast, Timeline
from app.schemas import RecurrenceFrequency

STREAMS = ("income", "essential", "discretionary")
WINDOWS = (3, 6, 12, 24)
RESID_CAP = 24  # most recent months used as the residual pool
PI_LEVEL = 0.80
Z80 = NormalDist().inv_cdf(0.5 + PI_LEVEL / 2)  # 1.2816
N_PATHS = 2000
SEED = 20240601

_PER_MONTH = {
    RecurrenceFrequency.weekly: 52 / 12,
    RecurrenceFrequency.biweekly: 26 / 12,
    RecurrenceFrequency.monthly: 1.0,
    RecurrenceFrequency.quarterly: 1 / 3,
    RecurrenceFrequency.annual: 1 / 12,
}


@dataclass
class Model:
    window: int
    point: np.ndarray  # (3,)
    resid: np.ndarray  # (M, 3)


@dataclass
class Split:
    train_end: int
    val_end: int
    total: int


def make_split(n: int) -> Split:
    k = n // 6 if n >= 24 else max(1, n // 4)
    return Split(n - 2 * k, n - k, n)


def _x(df: pd.DataFrame) -> np.ndarray:
    return df[list(STREAMS)].to_numpy(dtype=float)


def fit_forecaster(df: pd.DataFrame, window: int) -> Model:
    x = _x(df)
    pool = x[-RESID_CAP:]
    return Model(window, np.median(x[-window:], axis=0), pool - np.median(pool, axis=0))


def forecast_paths(model: Model, horizon: int, n: int = N_PATHS, seed: int = SEED) -> np.ndarray:
    """(n, horizon, 3). Draw shape is (horizon, n) so a longer horizon keeps the same prefix."""
    idx = np.random.default_rng(seed).integers(0, len(model.resid), size=(horizon, n))
    return np.clip(model.point + model.resid[idx], 0.0, None).transpose(1, 0, 2)


def method_block(window: int, horizon: int, n: int = N_PATHS, seed: int = SEED) -> ForecastMethod:
    return ForecastMethod(
        name="joint_month_bootstrap",
        horizon_months=horizon,
        n_paths=n,
        seed=seed,
        window_months=window,
        pi_level=PI_LEVEL,
        description=(
            f"Point = median of last {window} months per stream; whole-month residuals "
            f"(income, essential, discretionary together) resampled with replacement from the last "
            f"{RESID_CAP} months; {n} paths; 80% PI = P10-P90."
        ),
    )


def _band(a: np.ndarray) -> Band:
    p10, p50, p90 = np.percentile(a, [10, 50, 90])
    return Band(p10=round(float(p10), 2), p50=round(float(p50), 2), p90=round(float(p90), 2))


def month_labels(start: str, n: int) -> list[str]:
    return [str(pd.Period(start) + i) for i in range(n)]


def summarize(paths: np.ndarray, debt_mins: list[float], labels: list[str]) -> list[PeriodForecast]:
    out = []
    for t in range(len(labels)):
        p = paths[:, t, :]
        out.append(
            PeriodForecast(
                period=t + 1,
                month=labels[t],
                income=_band(p[:, 0]),
                essential=_band(p[:, 1]),
                discretionary=_band(p[:, 2]),
                debt_min=round(debt_mins[t], 2),
                net=_band(p[:, 0] - p[:, 1] - p[:, 2]),
            )
        )
    return out


# ---------------------------------------------------------------- backtest

def choose_window(df: pd.DataFrame, split: Split) -> int:
    """Pick W on the validation window (1-step-ahead rolling origin, MAE of net).
    The validation window is short and noisy, so the longest window wins unless a
    shorter one beats it by more than 5%."""
    err = {}
    for w in WINDOWS:
        errs = []
        for o in range(split.train_end + 1, split.val_end + 1):
            pt = fit_forecaster(df.loc[: o - 1], w).point
            actual = _x(df.loc[[o]])[0]
            errs.append(abs((pt[0] - pt[1] - pt[2]) - (actual[0] - actual[1] - actual[2])))
        err[w] = float(np.mean(errs))
    best = WINDOWS[-1]
    for w in reversed(WINDOWS[:-1]):
        if err[w] < err[best] * 0.95:
            best = w
    return best


def _net(a: np.ndarray) -> np.ndarray:
    return a[..., 0] - a[..., 1] - a[..., 2]


def _recurring_point(txns: pd.DataFrame, months: list[str]) -> np.ndarray:
    t = txns[pd.to_datetime(txns["date"]).dt.strftime("%Y-%m").isin(months)]
    out = np.zeros(3)
    for r in detect_recurring(t):
        m = abs(r.amount) * _PER_MONTH.get(r.frequency, 0.0)
        if r.amount > 0:
            out[0] += m
        elif r.category.value in ESSENTIAL:
            out[1] += m
        else:
            out[2] += m
    return out


def backtest(
    df: pd.DataFrame, split: Split, window: int, txns: pd.DataFrame | None = None
) -> list[BacktestRow]:
    """Rolling-origin 1-step-ahead on the held-out test months; each origin refits on all earlier months."""
    names = list(STREAMS) + ["net"]
    acc: dict[str, dict[str, list[list[float]]]] = {
        m: {s: [] for s in names} for m in ("bootstrap", "hist_avg", "recurring")
    }  # per model/stream: rows of [abs_err, covered, width]

    def rec(model: str, vals: np.ndarray, lo: np.ndarray, hi: np.ndarray, actual: np.ndarray) -> None:
        for i, s in enumerate(names):
            acc[model][s].append(
                [abs(vals[i] - actual[i]), float(lo[i] <= actual[i] <= hi[i]), hi[i] - lo[i]]
            )

    for o in range(split.val_end + 1, split.total + 1):
        hist = df.loc[: o - 1]
        a = _x(df.loc[[o]])[0]
        a = np.append(a, _net(a))
        # bootstrap
        p = forecast_paths(fit_forecaster(hist, window), 1, n=1000, seed=SEED + o)[:, 0, :]
        p = np.column_stack([p, _net(p)])
        q = np.percentile(p, [10, 50, 90], axis=0)
        rec("bootstrap", q[1], q[0], q[2], a)
        # historical average +/- z*sigma
        x = _x(hist)[-RESID_CAP:]
        x = np.column_stack([x, _net(x)])
        mu, sd = x.mean(axis=0), x.std(axis=0, ddof=1) if len(x) > 1 else np.zeros(4)
        rec("hist_avg", mu, mu - Z80 * sd, mu + Z80 * sd, a)
        # recurring-payment baseline (point forecast -> zero-width interval)
        if txns is not None:
            pt = _recurring_point(txns, list(hist["month"]))
            pt = np.append(pt, _net(pt))
            rec("recurring", pt, pt, pt, a)

    rows = []
    for m, per in acc.items():
        for s, vals in per.items():
            if vals:
                v = np.array(vals)
                rows.append(
                    BacktestRow(
                        model=m, stream=s, mae=round(float(v[:, 0].mean()), 2),
                        coverage=round(float(v[:, 1].mean()), 3), mean_width=round(float(v[:, 2].mean()), 2),
                    )
                )
    return rows


def timeline(split: Split, window: int) -> Timeline:
    return Timeline(
        train=[1, split.train_end],
        validation=[split.train_end + 1, split.val_end],
        test=[split.val_end + 1, split.total],
        chosen_window=window,
    )
