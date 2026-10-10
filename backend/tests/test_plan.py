"""Tests for app.plan (probabilistic monthly forecast + constrained multi-period planner).

Pure (no DB) except the one HTTP test of the public synthetic scenario endpoint.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.plan.forecast import Split, backtest, choose_window, fit_forecaster, forecast_paths
from app.plan.planner import _plan, plan, replan
from app.plan.scenarios import HORIZON, SPECS, build_inputs, run_scenario, SPLIT
from app.plan.synthetic import generate_monthly_history


def _inputs(name: str):
    spec = SPECS[name]
    df, txns, _ = generate_monthly_history(**spec.synth)
    return build_inputs(df, txns, spec, choose_window(df, SPLIT)), spec


def _bt(seed: int, **kw):
    df, txns, _ = generate_monthly_history(seed=seed, test_seed=seed + 100, months=96, **kw)
    split = Split(48, 60, 96)
    w = choose_window(df, split)
    return {(r.model, r.stream): r for r in backtest(df, split, w, txns)}


def test_history_seeds_are_separate():
    a, _, _ = generate_monthly_history(seed=1, test_seed=5)
    b, _, _ = generate_monthly_history(seed=1, test_seed=6)
    c, _, _ = generate_monthly_history(seed=2, test_seed=5)
    assert a.loc[:30].equals(b.loc[:30]) and not a.loc[31:].equals(b.loc[31:])
    assert a.loc[31:].drop(columns="essential").equals(c.loc[31:].drop(columns="essential"))


def test_forecast_paths_deterministic_and_prefix_stable():
    df, _, _ = generate_monthly_history()
    m = fit_forecaster(df.loc[:30], 12)
    p6, p24 = forecast_paths(m, 6), forecast_paths(m, 24)
    assert p6.shape == (2000, 6, 3) and (p6 >= 0).all()
    assert (p6 == forecast_paths(m, 6)).all() and (p6 == p24[:, :6]).all()


def test_backtest_coverage_and_mae_on_volatile_data():
    d = _bt(1, income_cv=0.45, zero_bonus_prob=0.2)
    assert 0.6 <= d["bootstrap", "net"].coverage <= 0.95
    assert d["bootstrap", "net"].mae <= d["hist_avg", "net"].mae
    assert d["bootstrap", "net"].mae < d["recurring", "net"].mae


def test_stable_income_feasible_and_p50_cash_above_reserve():
    p = run_scenario("stable_income").plan
    rec = next(s for s in p.sequences if s.id == p.recommended_id)
    assert p.feasible and rec.goal_met_p50
    assert all(x.cash_p50 >= p.constraints.min_reserve for x in rec.periods)
    assert not p.uncertainty_changed_choice


def test_infeasible_target_has_conflict_and_verified_relaxations():
    inp, _ = _inputs("infeasible_target")
    p = plan(inp)
    assert not p.feasible and p.conflicts and p.relaxations
    for r in p.relaxations:
        g, c = inp.constraints.goal, inp.constraints
        if r.kind == "extend_deadline":
            nc = c.model_copy(update={"goal": g.model_copy(update={"by_period": int(r.to_value)})})
        elif r.kind == "lower_target":
            nc = c.model_copy(update={"goal": g.model_copy(update={"amount": r.to_value})})
        elif r.kind == "lower_reserve":
            nc = c.model_copy(update={"min_reserve": r.to_value})
        else:
            nc = c.model_copy(update={"policy_cut": r.to_value})
        inp2 = type(inp)(**{**inp.__dict__, "constraints": nc, "horizon": max(HORIZON, nc.goal.by_period)})
        assert r.feasible and plan(inp2).feasible, r.kind


def test_income_reduction_replan_keeps_past_and_changes_future():
    inp, spec = _inputs("income_reduction")
    r = replan(inp, spec.shock)
    k = spec.shock.from_period
    assert r.changed_periods and min(r.changed_periods) >= k
    for b, a in zip(r.before.sequences, r.after.sequences):
        assert b.periods[: k - 1] == a.periods[: k - 1]
    assert r.before.sequences != r.after.sequences


def test_volatile_income_flip_changes_preferred_plan():
    p = run_scenario("volatile_income_flip").plan
    assert p.uncertainty_changed_choice and p.p50_only_best_id != p.recommended_id
    risk = {s.id: s.shortfall_risk for s in p.sequences}
    assert risk[p.p50_only_best_id] > p.constraints.risk_tolerance >= risk[p.recommended_id]


def test_plan_is_deterministic():
    inp, _ = _inputs("volatile_income_flip")
    assert _plan(inp)[0].model_dump() == _plan(inp)[0].model_dump()


def test_scenario_endpoint_is_public_and_complete():
    client = TestClient(app)
    r = client.get("/api/planning/scenarios/volatile_income_flip")
    assert r.status_code == 200
    j = r.json()
    assert {"assumptions", "timeline", "plan", "outcome", "backtest"} <= j.keys()
    assert {b["model"] for b in j["backtest"]} == {"bootstrap", "hist_avg", "recurring"}
    assert len(client.get("/api/planning/scenarios").json()) == 5
    assert client.get("/api/planning/scenarios/nope").status_code == 404


def test_demo_personas_get_seeded_plan_profiles():
    from fastapi.testclient import TestClient

    from app.ingest.seed import seed_all
    from app.main import app

    seed_all()
    c = TestClient(app)
    out = {u: c.get(f"/api/plan/{u}").json() for u in ("demo-priya", "demo-arjun", "demo-meera")}
    assert out["demo-priya"]["feasible"] and out["demo-arjun"]["feasible"]
    assert not out["demo-meera"]["feasible"] and out["demo-meera"]["relaxations"]
    assert out["demo-arjun"]["uncertainty_changed_choice"]


def test_connected_guest_inherits_declared_reserve_and_six_periods():
    from app.ingest.personas import PLAN_PROFILES

    c = TestClient(app)
    uid = "guest-plantest0000001"
    try:
        assert c.post(f"/api/connectors/{uid}/google_pay/connect", json={"profile": "priya"}).status_code == 200
        out = c.get(f"/api/plan/{uid}").json()
        assert out["constraints"]["min_reserve"] == PLAN_PROFILES["demo-priya"]["reserve"]
        assert out["constraints"]["goal"] is not None
        assert len(out["forecast"]) >= 6 and out["forecast"][0]["debt_min"] > 0
    finally:
        c.delete(f"/api/connectors/{uid}/google_pay")
