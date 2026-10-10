"""Multi-period action plan + probabilistic monthly forecast.

Mounted in app.main with prefix="/api". `/plan/{user_id}` uses the user's own
history; `/planning/scenarios*` serve the synthetic demo scenarios (public).
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.routes import _starting_balance_for_user
from app.core import store
from app.core.auth import resolve_user_id
from app.ingest.personas import PLAN_PROFILES
from app.ingest.snapshot import _transactions_df
from app.models import ConnectionRow, DebtRow, TransactionRow
from app.plan.forecast import (
    N_PATHS,
    SEED,
    choose_window,
    fit_forecaster,
    forecast_paths,
    make_split,
    method_block,
)
from app.plan.history import monthly_flows
from app.plan.planner import MAX_HORIZON, DebtIn, PlanInputs, plan, replan
from app.plan.scenarios import SPECS, list_scenarios, run_scenario
from app.plan.schemas import Constraints, Goal, PlanResult, ReplanResult, Scenario, Shock

router = APIRouter()

_MIN_MONTHS = 4


class PlanParams(BaseModel):
    reserve: float | None = None
    goal_amount: float | None = None
    goal_month: int | None = None
    tolerance: float = 0.10
    cut: float = 0.20
    horizon: int = 6


class ReplanRequest(PlanParams):
    shock: Shock


def _inputs(user_id: str, p: PlanParams) -> PlanInputs:
    if p.reserve is None and p.goal_amount is None and p.goal_month is None:
        # Connected sandbox users inherit the declared reserve/goal of the persona they linked.
        link = store.get(ConnectionRow, f"{user_id}:google_pay")
        source = f"demo-{link.detail.lower()}" if link and link.detail else user_id
        p = p.model_copy(update=PLAN_PROFILES.get(source, {}))
    if not 1 <= p.horizon <= MAX_HORIZON:
        raise HTTPException(422, f"horizon must be 1..{MAX_HORIZON}")
    if not 0 <= p.cut <= 0.30:
        raise HTTPException(422, "cut must be between 0 and 0.30")
    if (p.goal_amount is None) != (p.goal_month is None):
        raise HTTPException(422, "goal_amount and goal_month must be given together")
    if p.goal_month is not None and not 1 <= p.goal_month <= p.horizon:
        raise HTTPException(422, "goal_month must be within the horizon")
    df = _transactions_df(store.query(TransactionRow, user_id=user_id))
    flows = monthly_flows(df) if not df.empty else pd.DataFrame()
    if len(flows) < _MIN_MONTHS:
        raise HTTPException(422, f"Need at least {_MIN_MONTHS} complete months of history to plan; found {len(flows)}")
    window = choose_window(flows, make_split(len(flows)))
    paths = forecast_paths(fit_forecaster(flows, window), max(MAX_HORIZON, p.horizon))
    reserve = p.reserve if p.reserve is not None else float(flows["essential"].tail(window).median())
    debts = [DebtIn(d.principal, d.interest_rate_apr, d.minimum_payment) for d in store.query(DebtRow, user_id=user_id)]
    return PlanInputs(
        paths=paths,
        method=method_block(window, p.horizon, N_PATHS, SEED),
        cash0=_starting_balance_for_user(user_id),
        debts=debts,
        constraints=Constraints(
            min_reserve=reserve,
            goal=Goal(amount=p.goal_amount, by_period=p.goal_month) if p.goal_amount is not None else None,
            risk_tolerance=p.tolerance,
            policy_cut=p.cut,
        ),
        start_month=str(pd.Period(flows["month"].iloc[-1]) + 1),
        horizon=p.horizon,
    )


@router.get("/plan/{user_id}", response_model=PlanResult)
def get_plan(
    reserve: float | None = Query(None, ge=0),
    goal_amount: float | None = Query(None, gt=0),
    goal_month: int | None = Query(None, ge=1),
    tolerance: float = Query(0.10, ge=0, le=1),
    cut: float = Query(0.20),
    horizon: int = Query(6),
    user_id: str = Depends(resolve_user_id),
) -> PlanResult:
    return plan(_inputs(user_id, PlanParams(
        reserve=reserve, goal_amount=goal_amount, goal_month=goal_month, tolerance=tolerance, cut=cut, horizon=horizon)))


@router.post("/plan/{user_id}/replan", response_model=ReplanResult)
def post_replan(req: ReplanRequest, user_id: str = Depends(resolve_user_id)) -> ReplanResult:
    if not 1 <= req.shock.from_period <= req.horizon:
        raise HTTPException(422, "shock.from_period must be within the horizon")
    return replan(_inputs(user_id, req), req.shock)


@router.get("/planning/scenarios")
def get_scenarios() -> list[dict]:
    return list_scenarios()


@router.get("/planning/scenarios/{name}", response_model=Scenario)
def get_scenario(name: str) -> Scenario:
    if name not in SPECS:
        raise HTTPException(404, f"Unknown scenario {name!r}")
    return run_scenario(name)
