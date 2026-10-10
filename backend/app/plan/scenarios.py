"""Named, fully synthetic demo scenarios (history -> plan -> realized outcome on held-out months)."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from app.plan.forecast import (
    N_PATHS,
    SEED,
    Split,
    backtest,
    choose_window,
    fit_forecaster,
    forecast_paths,
    method_block,
    timeline,
)
from app.plan.planner import MAX_HORIZON, DebtIn, PlanInputs, _plan, shock_paths
from app.plan.schemas import Constraints, Goal, OutcomeRow, ReplanResult, Scenario, Shock
from app.plan.synthetic import TOTAL, TRAIN_END, VAL_END, generate_monthly_history

SPLIT = Split(TRAIN_END, VAL_END, TOTAL)
HORIZON = 6
DEBTS = [DebtIn(250_000, 18.0, 6_000), DebtIn(400_000, 11.0, 9_000)]


@dataclass
class Spec:
    title: str
    synth: dict = field(default_factory=dict)
    cash0: float = 150_000.0
    reserve: float = 60_000.0
    goal: Goal | None = None
    tolerance: float = 0.10
    shock: Shock | None = None


SPECS: dict[str, Spec] = {
    "stable_income": Spec(
        "Stable income, achievable goal",
        synth={"income_cv": 0.04, "zero_bonus_prob": 0.0, "disc_cv": 0.10},
        goal=Goal(amount=120_000, by_period=6),
    ),
    "income_reduction": Spec(
        "Income drops 30% from month 3",
        synth={"income_cv": 0.10, "zero_bonus_prob": 0.0, "disc_cv": 0.15},
        goal=Goal(amount=120_000, by_period=6),
        shock=Shock(kind="income_change", from_period=3, pct=-30),
    ),
    "unexpected_expense": Spec(
        "Unexpected INR 60,000 medical expense in month 2",
        synth={"income_cv": 0.10, "zero_bonus_prob": 0.0, "disc_cv": 0.15},
        goal=Goal(amount=120_000, by_period=6),
        shock=Shock(kind="essential_expense", from_period=2, amount=60_000),
    ),
    "infeasible_target": Spec(
        "Target larger than the cash the plan can free up",
        synth={"income_cv": 0.10, "zero_bonus_prob": 0.0, "disc_cv": 0.15},
        goal=Goal(amount=300_000, by_period=6),
    ),
    "volatile_income_flip": Spec(
        "Volatile income: uncertainty changes the preferred plan",
        synth={"income_cv": 0.28, "zero_bonus_prob": 0.10, "disc_cv": 0.30},
        goal=None,
    ),
}


def build_inputs(df, txns, spec: Spec, window: int) -> PlanInputs:
    hist = df.loc[:VAL_END]
    paths = forecast_paths(fit_forecaster(hist, window), MAX_HORIZON)
    last = hist["month"].iloc[-1]
    import pandas as pd

    return PlanInputs(
        paths=paths,
        method=method_block(window, HORIZON, N_PATHS, SEED),
        cash0=spec.cash0,
        debts=DEBTS,
        constraints=Constraints(min_reserve=spec.reserve, goal=spec.goal, risk_tolerance=spec.tolerance),
        start_month=str(pd.Period(last) + 1),
        horizon=HORIZON,
    )


@lru_cache(maxsize=None)
def run_scenario(name: str) -> Scenario:
    spec = SPECS[name]
    df, txns, assumptions = generate_monthly_history(**spec.synth)
    window = choose_window(df, SPLIT)
    inp = build_inputs(df, txns, spec, window)
    plan, scheds = _plan(inp)

    replan = None
    if spec.shock:
        from app.plan.planner import replan as do_replan

        replan = do_replan(inp, spec.shock)
        assumptions = {**assumptions, "shock": spec.shock.model_dump(exclude_none=True)}

    # realized outcome of the originally recommended schedule on the held-out test months
    actual = df.loc[VAL_END + 1 : VAL_END + HORIZON, ["income", "essential", "discretionary"]].to_numpy()[None]
    if spec.shock:
        shock_paths(actual, spec.shock)
    sched = scheds[plan.recommended_id]
    rec = next(s for s in ([plan.risk_adjusted] if plan.risk_adjusted else []) + plan.sequences if s.id == plan.recommended_id)
    cash, out = spec.cash0, []
    for t, (cut, extra, sav) in enumerate(sched):
        inc, ess, disc = actual[0, t]
        cash += inc - ess - disc * (1 - cut) - rec.periods[t].debt_min - extra - sav
        out.append(OutcomeRow(
            period=t + 1, planned_cash=rec.periods[t].cash_end, realized_cash=round(float(cash), 2),
            reserve_breached=bool(cash < spec.reserve),
        ))

    assumptions = {
        **assumptions,
        "debts": [d.__dict__ for d in DEBTS],
        "starting_cash": spec.cash0,
        "realized": "held-out test months " f"{VAL_END + 1}-{VAL_END + HORIZON} (drawn from test_seed), plan fitted on months 1-{VAL_END}",
    }
    return Scenario(
        name=name, title=spec.title, assumptions=assumptions, timeline=timeline(SPLIT, window), plan=plan,
        replan=replan, outcome=out, backtest=backtest(df, SPLIT, window, txns),
    )


def list_scenarios() -> list[dict]:
    return [{"name": n, "title": s.title} for n, s in SPECS.items()]
