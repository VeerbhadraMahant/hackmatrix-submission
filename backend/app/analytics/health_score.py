"""Overall financial health score: combines 5 sub-scores (0-100 each) with
the weights already sketched in app/ingest/fixtures.py's demo snapshot:

    Cash-flow stability   weight 0.30
    Debt pressure         weight 0.25
    Savings behaviour     weight 0.20
    Emergency fund        weight 0.15
    Spending consistency  weight 0.10

Each sub-score formula is documented inline -- this is a judged feature, so
defensibility (a human can read the code and see exactly why the number is
what it is) matters more than statistical sophistication.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.schemas import CashFlowForecast, HealthScore, SubScore

_WEIGHTS = {
    "cash_flow": 0.30,
    "debt_pressure": 0.25,
    "savings": 0.20,
    "emergency_fund": 0.15,
    "spending_consistency": 0.10,
}


def _clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, x))


def score_cash_flow_stability(forecast: Optional[CashFlowForecast]) -> tuple[float, str]:
    """100 = no projected low-balance days in the forecast horizon.
    Penalize by the fraction of horizon days flagged `is_gap_risk`, plus an
    extra penalty if the first gap is imminent (within 14 days) since a
    near-term shortfall is more actionable/urgent than a distant one."""
    if forecast is None or not forecast.points:
        return 70.0, "No forecast available; default neutral score."

    total_days = len(forecast.points)
    gap_days = sum(1 for p in forecast.points if p.is_gap_risk)
    gap_ratio = gap_days / total_days

    score = 100.0 - gap_ratio * 150.0  # a fully gap-risk horizon -> 0

    if forecast.first_gap_date is not None:
        days_to_first_gap = (forecast.first_gap_date - forecast.points[0].date).days
        if days_to_first_gap <= 14:
            score -= 20.0

    score = _clamp(score)
    detail = (
        f"{gap_days}/{total_days} forecast days show low-balance risk"
        + (f"; first gap on {forecast.first_gap_date}" if forecast.first_gap_date else "")
    )
    return score, detail


def score_debt_pressure(dti: float, credit_utilization: Optional[float]) -> tuple[float, str]:
    """DTI component: healthy DTI is conventionally <=36%; score decays
    linearly to 0 at DTI=50% (0.7 weight within this sub-score).
    Utilization component: 0% used -> 100, 100%+ used -> 0 (0.3 weight),
    neutral 70 if no credit-limit data is available (e.g. no revolving debt)."""
    dti_score = _clamp(100.0 - (dti / 0.50) * 100.0)

    if credit_utilization is None:
        util_score = 70.0
        util_detail = "no revolving credit utilization data"
    else:
        util_score = _clamp(100.0 - credit_utilization * 100.0)
        util_detail = f"{credit_utilization * 100:.0f}% credit utilization"

    score = 0.7 * dti_score + 0.3 * util_score
    detail = f"DTI {dti * 100:.0f}% of income; {util_detail}"
    return _clamp(score), detail


def score_savings_behaviour(savings_rate_trailing: float) -> tuple[float, str]:
    """Linear scale: a 20% savings rate (a commonly cited healthy target)
    or higher scores 100; 0% or below scores 0."""
    score = _clamp((savings_rate_trailing / 0.20) * 100.0)
    detail = f"{savings_rate_trailing * 100:.0f}% average monthly savings rate"
    return score, detail


def score_emergency_fund(emergency_fund_months: float) -> tuple[float, str]:
    """Linear scale against the standard 6-months-of-expenses guideline:
    6+ months -> 100, 0 months -> 0."""
    score = _clamp((emergency_fund_months / 6.0) * 100.0)
    detail = f"{emergency_fund_months:.1f} months of essential expenses covered"
    return score, detail


def score_spending_consistency(spending_cov: float) -> tuple[float, str]:
    """Coefficient of variation of monthly spend across recent months/
    categories: 0 (perfectly steady) -> 100, 1.0+ (highly erratic) -> 0."""
    score = _clamp(100.0 - spending_cov * 100.0)
    detail = f"spend coefficient of variation {spending_cov:.2f}"
    return score, detail


def compute_health_score(
    *,
    forecast: Optional[CashFlowForecast],
    dti: float,
    credit_utilization: Optional[float],
    savings_rate_trailing: float,
    emergency_fund_months: float,
    spending_cov: float,
    prior_health_score: Optional[HealthScore] = None,
) -> HealthScore:
    """Combine the five sub-scores into an overall HealthScore.
    `trend_30d` is the delta vs `prior_health_score.overall` if provided."""
    cash_flow_score, cash_flow_detail = score_cash_flow_stability(forecast)
    debt_score, debt_detail = score_debt_pressure(dti, credit_utilization)
    savings_score, savings_detail = score_savings_behaviour(savings_rate_trailing)
    ef_score, ef_detail = score_emergency_fund(emergency_fund_months)
    consistency_score, consistency_detail = score_spending_consistency(spending_cov)

    sub_scores = [
        SubScore(name="Cash-flow stability", score=round(cash_flow_score, 1), weight=_WEIGHTS["cash_flow"], detail=cash_flow_detail),
        SubScore(name="Debt pressure", score=round(debt_score, 1), weight=_WEIGHTS["debt_pressure"], detail=debt_detail),
        SubScore(name="Savings behaviour", score=round(savings_score, 1), weight=_WEIGHTS["savings"], detail=savings_detail),
        SubScore(name="Emergency fund", score=round(ef_score, 1), weight=_WEIGHTS["emergency_fund"], detail=ef_detail),
        SubScore(name="Spending consistency", score=round(consistency_score, 1), weight=_WEIGHTS["spending_consistency"], detail=consistency_detail),
    ]

    overall = sum(s.score * s.weight for s in sub_scores)
    overall = _clamp(overall)

    trend_30d = None
    if prior_health_score is not None:
        trend_30d = round(overall - prior_health_score.overall, 2)

    return HealthScore(
        overall=round(overall, 1),
        sub_scores=sub_scores,
        computed_at=datetime.now(timezone.utc),
        trend_30d=trend_30d,
    )
