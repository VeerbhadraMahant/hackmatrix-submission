"""Pydantic contract for the multi-period planner + probabilistic forecaster.

Mirrored by the frontend (lib/types.ts). All amounts are INR; periods are
1-based monthly periods starting after the last observed history month.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Band(BaseModel):
    p10: float
    p50: float
    p90: float


class ForecastMethod(BaseModel):
    name: str
    horizon_months: int
    n_paths: int
    seed: int
    window_months: int
    pi_level: float
    description: str


class PeriodForecast(BaseModel):
    period: int
    month: str
    income: Band
    essential: Band
    discretionary: Band
    debt_min: float
    net: Band


class Goal(BaseModel):
    kind: Literal["savings_or_debt"] = "savings_or_debt"
    amount: float
    by_period: int


class Constraints(BaseModel):
    min_reserve: float
    max_discretionary_cut: float = 0.30
    goal: Goal | None = None
    risk_tolerance: float = 0.10
    policy_cut: float = 0.20  # additive field: discretionary cut used by the cutting sequences


class PeriodPlan(BaseModel):
    period: int
    month: str
    income: float  # P50 forecast
    essential: float  # P50 forecast
    discretionary: float  # P50 forecast AFTER the cut
    discretionary_cut: float  # INR removed by the cut
    debt_min: float
    extra_debt: float
    savings_contrib: float
    cash_end: float  # planned (P50-input) end-of-period cash
    cash_p10: float
    cash_p50: float
    cash_p90: float
    debt_balance: float
    reserve_ok: bool  # planned cash_end >= min_reserve


class SequenceResult(BaseModel):
    id: str
    label: str
    description: str
    periods: list[PeriodPlan]
    shortfall_risk: float  # P(cash < reserve in any period)
    p_negative: float  # P(cash < 0 in any period)
    goal_met_p50: bool
    goal_progress: float  # 0..1 of goal amount by goal.by_period (0 when no goal)
    interest_saved: float
    objective: float  # INR toward goal/debt (capped at goal by deadline) + interest saved


class Conflict(BaseModel):
    constraint: str
    required: float
    available: float
    message: str


class Relaxation(BaseModel):
    kind: Literal["extend_deadline", "lower_target", "lower_reserve", "deeper_cut"]
    from_value: float
    to_value: float
    message: str
    feasible: bool


class PlanResult(BaseModel):
    method: ForecastMethod
    constraints: Constraints
    starting_cash: float
    forecast: list[PeriodForecast]
    sequences: list[SequenceResult]
    feasible: bool
    conflicts: list[Conflict] = Field(default_factory=list)
    relaxations: list[Relaxation] = Field(default_factory=list)
    recommended_id: str
    p50_only_best_id: str
    uncertainty_changed_choice: bool
    rationale: str
    risk_adjusted: SequenceResult | None = None


class Shock(BaseModel):
    kind: Literal["income_change", "essential_expense"]
    from_period: int
    pct: float | None = None  # income_change: e.g. -30 for -30%
    amount: float | None = None  # essential_expense: one-off INR in from_period


class ReplanResult(BaseModel):
    shock: Shock
    before: PlanResult
    after: PlanResult
    changed_periods: list[int]


class BacktestRow(BaseModel):
    model: Literal["bootstrap", "hist_avg", "recurring"]
    stream: Literal["income", "essential", "discretionary", "net"]
    mae: float
    coverage: float
    mean_width: float


class Timeline(BaseModel):
    train: list[int]
    validation: list[int]
    test: list[int]
    chosen_window: int


class OutcomeRow(BaseModel):
    period: int
    planned_cash: float
    realized_cash: float
    reserve_breached: bool


class Scenario(BaseModel):
    name: str
    title: str
    assumptions: dict
    timeline: Timeline
    plan: PlanResult
    replan: ReplanResult | None = None
    outcome: list[OutcomeRow]
    backtest: list[BacktestRow]
