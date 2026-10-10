"""Static benchmark context by income bracket.

IMPORTANT: these are illustrative benchmarks based on general
financial-planning heuristics (e.g. the "50/30/20" rule and typical
debt-to-income guidance), NOT sourced from any real population survey or
dataset. Do not present them as statistically representative -- they exist
to give a rough sense of "is this normal for my income level", not to claim
false precision.
"""
from __future__ import annotations

# Each bracket: (min_monthly_income_inr, max_monthly_income_inr_or_None,
#                (savings_rate_low, savings_rate_high), (dti_low, dti_high))
_BRACKETS: list[tuple[float, float | None, tuple[float, float], tuple[float, float]]] = [
    (0, 50_000, (0.05, 0.15), (0.0, 0.40)),
    (50_000, 100_000, (0.10, 0.20), (0.0, 0.35)),
    (100_000, 200_000, (0.15, 0.25), (0.0, 0.30)),
    (200_000, None, (0.20, 0.30), (0.0, 0.25)),
]


def _bracket_for(monthly_income: float):
    for low, high, savings_range, dti_range in _BRACKETS:
        if monthly_income >= low and (high is None or monthly_income < high):
            return savings_range, dti_range
    return _BRACKETS[-1][2], _BRACKETS[-1][3]


def benchmark_context(monthly_income: float, savings_rate: float, dti: float) -> list[str]:
    """Return short comparative strings usable as Fact/Prediction text,
    e.g. "Your savings rate of 12% is below the typical 15-20% range for
    your income bracket." Illustrative only -- see module docstring."""
    (sr_low, sr_high), (dti_low, dti_high) = _bracket_for(monthly_income)

    messages: list[str] = []

    savings_pct = savings_rate * 100
    sr_low_pct, sr_high_pct = sr_low * 100, sr_high * 100
    if savings_rate < sr_low:
        messages.append(
            f"Your savings rate of {savings_pct:.0f}% is below the typical "
            f"{sr_low_pct:.0f}-{sr_high_pct:.0f}% range for your income bracket "
            f"(illustrative benchmark, not survey data)."
        )
    elif savings_rate > sr_high:
        messages.append(
            f"Your savings rate of {savings_pct:.0f}% is above the typical "
            f"{sr_low_pct:.0f}-{sr_high_pct:.0f}% range for your income bracket "
            f"(illustrative benchmark, not survey data)."
        )
    else:
        messages.append(
            f"Your savings rate of {savings_pct:.0f}% is within the typical "
            f"{sr_low_pct:.0f}-{sr_high_pct:.0f}% range for your income bracket."
        )

    dti_pct = dti * 100
    dti_high_pct = dti_high * 100
    if dti > dti_high:
        messages.append(
            f"Your debt-to-income ratio of {dti_pct:.0f}% is above the typical "
            f"ceiling of {dti_high_pct:.0f}% for your income bracket "
            f"(illustrative benchmark, not survey data)."
        )
    else:
        messages.append(
            f"Your debt-to-income ratio of {dti_pct:.0f}% is within a "
            f"reasonable range (typically under {dti_high_pct:.0f}% for your "
            f"income bracket)."
        )

    return messages
