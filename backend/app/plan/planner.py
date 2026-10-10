"""Constrained multi-period action planner.

Each sequence is a committed monthly schedule (discretionary cut, extra debt
payment, savings contribution) planned on the per-period P50 forecast, then
replayed over every forecast path to measure shortfall risk. A recommendation
is the best-objective sequence whose shortfall risk is within tolerance; the
P50-only winner is reported next to it so the effect of uncertainty is explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.plan.forecast import month_labels, summarize
from app.plan.schemas import (
    Conflict,
    Constraints,
    ForecastMethod,
    PeriodPlan,
    PlanResult,
    Relaxation,
    ReplanResult,
    SequenceResult,
    Shock,
)

S1_MARGIN = 0.5  # debt_first keeps reserve + this fraction of monthly essentials (deterministic margin)
S3_Z = 1.65  # reserve_then_debt buffer: z * sd(net) * sqrt(horizon)
MAX_HORIZON = 24

Sched = list[tuple[float, float, float]]  # per period: (cut fraction, extra debt, savings)


@dataclass
class DebtIn:
    principal: float
    apr: float  # percent
    minimum: float


@dataclass
class PlanInputs:
    paths: np.ndarray  # (n, L>=horizon, 3): income, essential, discretionary
    method: ForecastMethod
    cash0: float
    debts: list[DebtIn]
    constraints: Constraints
    start_month: str
    horizon: int = 6
    locked: dict[str, Sched] = field(default_factory=dict)


class DebtBook:
    def __init__(self, debts: list[DebtIn]):
        self.d = debts
        self.bal = [x.principal for x in debts]

    def due(self) -> tuple[float, float]:
        """(minimums payable this month, max extra that can still be applied)."""
        grown = [b * (1 + d.apr / 1200) for b, d in zip(self.bal, self.d)]
        mins = sum(min(d.minimum, g) for g, d in zip(grown, self.d))
        return mins, sum(grown) - mins

    def step(self, extra: float) -> tuple[float, float, float]:
        """Advance one month -> (minimums paid, extra applied, interest accrued)."""
        interest = 0.0
        for i, d in enumerate(self.d):
            it = self.bal[i] * d.apr / 1200
            self.bal[i] += it
            interest += it
        paid = 0.0
        for i, d in enumerate(self.d):
            p = min(d.minimum, self.bal[i])
            self.bal[i] -= p
            paid += p
        applied, rem = 0.0, extra
        for i in sorted(range(len(self.d)), key=lambda j: -self.d[j].apr):
            a = min(rem, self.bal[i])
            self.bal[i] -= a
            rem -= a
            applied += a
        return paid, applied, interest

    def balance(self) -> float:
        return sum(self.bal)


@dataclass
class Row:
    cut: float
    extra: float
    sav: float
    mins: float
    cash: float
    debt: float
    interest: float


def _p50(paths: np.ndarray, h: int) -> np.ndarray:
    return np.percentile(paths[:, :h, :], 50, axis=0)  # (h, 3)


def _build(decide, p50: np.ndarray, cash0: float, debts: list[DebtIn], locked: Sched | None) -> list[Row]:
    book, cash, cum, rows = DebtBook(debts), cash0, 0.0, []
    for t in range(len(p50)):
        inc, ess, disc = p50[t]
        mins, cap = book.due()
        if locked and t < len(locked):
            cut, extra, sav = locked[t]
        else:
            cut, extra, sav = decide(t, cash, inc, ess, disc, mins, cum)
        pm, applied, interest = book.step(min(extra, cap))
        cash += inc - ess - disc * (1 - cut) - pm - applied - sav
        cum += applied + sav
        rows.append(Row(cut, applied, sav, pm, cash, book.balance(), interest))
    return rows


def _sched(rows: list[Row]) -> Sched:
    return [(r.cut, r.extra, r.sav) for r in rows]


def _check(p50, mins, cash0, reserve, cut, amount, k) -> tuple[bool, float, float]:
    """P50 feasibility of putting `amount` toward the goal by period k (1-based) while
    cash stays >= reserve. Returns (feasible, available, shortfall_of_reserve_alone).
    Debt minimums come from the no-extra-payment schedule (a conservative approximation)."""
    net = p50[:, 0] - p50[:, 1] - p50[:, 2] * (1 - cut) - mins
    m = cash0 + np.cumsum(net) - reserve
    pre = m[: k - 1].min() if k > 1 else np.inf
    post = m[k - 1 :].min()
    avail = post if pre >= 0 else min(pre, post)
    return bool(pre >= 0 and post >= amount - 1e-6), float(max(0.0, avail)), float(min(0.0, m.min()))


def _status_quo_mins(debts: list[DebtIn], h: int) -> tuple[list[float], float]:
    book, mins, interest = DebtBook(debts), [], 0.0
    for _ in range(h):
        pm, _, it = book.step(0.0)
        mins.append(pm)
        interest += it
    return mins, interest


def _evaluate(sid, label, desc, rows, paths, inp: PlanInputs, base_interest, labels, p50) -> SequenceResult:
    c, h = inp.constraints, inp.horizon
    net = paths[:, :h, 0] - paths[:, :h, 1]
    cut = np.array([r.cut for r in rows])
    out = np.array([r.mins + r.extra + r.sav for r in rows])
    cash = inp.cash0 + np.cumsum(net - paths[:, :h, 2] * (1 - cut) - out, axis=1)  # (n, h)
    pcts = np.percentile(cash, [10, 50, 90], axis=0)
    alloc = np.cumsum([r.extra + r.sav for r in rows])
    g = c.goal
    prog = min(1.0, alloc[g.by_period - 1] / g.amount) if g and g.amount > 0 else 0.0
    saved = base_interest - sum(r.interest for r in rows)
    toward = min(alloc[g.by_period - 1], g.amount) if g else alloc[-1]
    periods = [
        PeriodPlan(
            period=t + 1, month=labels[t], income=round(p50[t, 0], 2), essential=round(p50[t, 1], 2),
            discretionary=round(p50[t, 2] * (1 - r.cut), 2), discretionary_cut=round(p50[t, 2] * r.cut, 2),
            debt_min=round(r.mins, 2), extra_debt=round(r.extra, 2), savings_contrib=round(r.sav, 2),
            cash_end=round(r.cash, 2), cash_p10=round(float(pcts[0, t]), 2), cash_p50=round(float(pcts[1, t]), 2),
            cash_p90=round(float(pcts[2, t]), 2), debt_balance=round(r.debt, 2),
            reserve_ok=bool(r.cash >= c.min_reserve - 0.5),
        )
        for t, r in enumerate(rows)
    ]
    return SequenceResult(
        id=sid, label=label, description=desc, periods=periods,
        shortfall_risk=round(float((cash < c.min_reserve - 1e-6).any(axis=1).mean()), 4),
        p_negative=round(float((cash < 0).any(axis=1).mean()), 4),
        goal_met_p50=bool(g is None or prog >= 1 - 1e-9), goal_progress=round(float(prog), 4),
        interest_saved=round(float(saved), 2), objective=round(float(toward + saved), 2),
    )


def _policies(inp: PlanInputs, p50: np.ndarray, paths: np.ndarray, mins0: list[float]):
    c, h = inp.constraints, inp.horizon
    pc = c.policy_cut
    sd = float((paths[:, :h, 0] - paths[:, :h, 1] - paths[:, :h, 2]).std(axis=0).mean())
    ess = float(p50[:, 1].mean())
    surplus = float(np.mean(p50[:, 0] - p50[:, 1] - p50[:, 2] - np.array(mins0)))
    fixed_sav = max(0.0, 0.5 * surplus)

    def sweep(cut, target):
        def d(t, cash, inc, e, disc, mins, cum):
            pre = cash + inc - e - disc * (1 - cut) - mins
            return cut, max(0.0, pre - target(t)), 0.0
        return d

    def save(t, cash, inc, e, disc, mins, cum):
        g = c.goal
        if g is None:
            return 0.0, 0.0, fixed_sav
        left = g.by_period - t
        return 0.0, 0.0, max(0.0, g.amount - cum) / left if left > 0 else 0.0

    return [
        ("status_quo", "Status quo", "No cuts, no extra payments, no new savings.", lambda *a: (0.0, 0.0, 0.0)),
        ("debt_first", "Debt first",
         f"Cut discretionary {pc:.0%}; send all cash above reserve + {S1_MARGIN:.0%} of monthly essentials to the highest-APR debt.",
         sweep(pc, lambda t: c.min_reserve + S1_MARGIN * ess)),
        ("save_first", "Save first",
         "Fixed monthly savings contribution sized to reach the goal by its deadline" if c.goal
         else "Fixed monthly savings contribution of half the forecast surplus.", save),
        ("reserve_then_debt", "Reserve, then debt",
         f"Cut discretionary {pc:.0%}; first build reserve + a volatility buffer (at least the debt_first margin; {S3_Z} sd of monthly net cash flow x sqrt({h} months)), then send the surplus to debt.",
         sweep(pc, lambda t: c.min_reserve + max(S1_MARGIN * ess, S3_Z * sd * np.sqrt(h)))),
    ]


def _fmt(x: float) -> str:
    return f"INR {x:,.0f}"


def _relaxations(inp, p50, mins, k, amount) -> list[Relaxation]:
    c, cash0 = inp.constraints, inp.cash0
    reserve, cut = c.min_reserve, c.policy_cut
    out: list[Relaxation] = []
    _, avail, _ = _check(p50, mins, cash0, reserve, cut, amount, k)
    # extend deadline (uses the longer P50 horizon; debt minimums beyond h assumed flat at the last value)
    long_p50 = _p50(inp.paths, inp.paths.shape[1])
    long_mins = np.array(list(mins) + [mins[-1]] * (len(long_p50) - len(mins)))
    for n in range(k + 1, len(long_p50) + 1):
        if _check(long_p50, long_mins, cash0, reserve, cut, amount, n)[0]:
            out.append(Relaxation(kind="extend_deadline", from_value=k, to_value=n, feasible=True,
                                  message=f"Extend the deadline from month {k} to month {n}."))
            break
    t = float(np.floor(avail / 100) * 100)
    if t > 0:
        ok = _check(p50, mins, cash0, reserve, cut, t, k)[0]
        out.append(Relaxation(kind="lower_target", from_value=amount, to_value=t, feasible=ok,
                              message=f"Lower the target from {_fmt(amount)} to {_fmt(t)}."))
    net = p50[:, 0] - p50[:, 1] - p50[:, 2] * (1 - cut) - mins
    m = cash0 + np.cumsum(net) - reserve
    delta = max(amount - m[k - 1 :].min(), -(m[: k - 1].min() if k > 1 else 0.0), 0.0)
    r2 = float(np.ceil(reserve - delta))
    if r2 >= 0:
        ok = _check(p50, mins, cash0, r2, cut, amount, k)[0]
        out.append(Relaxation(kind="lower_reserve", from_value=reserve, to_value=r2, feasible=ok,
                              message=f"Lower the minimum reserve from {_fmt(reserve)} to {_fmt(r2)}."))
    mx = c.max_discretionary_cut
    if cut < mx and _check(p50, mins, cash0, reserve, mx, amount, k)[0]:
        lo, hi = cut, mx
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if _check(p50, mins, cash0, reserve, mid, amount, k)[0] else (mid, hi)
        c2 = float(np.ceil(hi * 100) / 100)
        ok = _check(p50, mins, cash0, reserve, c2, amount, k)[0]
        out.append(Relaxation(kind="deeper_cut", from_value=cut, to_value=c2, feasible=ok,
                              message=f"Cut discretionary spending {c2:.0%} instead of {cut:.0%} (limit {mx:.0%})."))
    return out


def _plan(inp: PlanInputs) -> tuple[PlanResult, dict[str, Sched]]:
    c, h = inp.constraints, inp.horizon
    paths, labels = inp.paths, month_labels(inp.start_month, inp.horizon)
    p50 = _p50(paths, h)
    mins0, base_interest = _status_quo_mins(inp.debts, h)

    results: list[SequenceResult] = []
    scheds: dict[str, Sched] = {}
    for sid, label, desc, decide in _policies(inp, p50, paths, mins0):
        rows = _build(decide, p50, inp.cash0, inp.debts, inp.locked.get(sid))
        scheds[sid] = _sched(rows)
        results.append(_evaluate(sid, label, desc, rows, paths, inp, base_interest, labels, p50))

    # --- feasibility on the P50 (best case: discretionary cut at the policy level)
    conflicts: list[Conflict] = []
    relax: list[Relaxation] = []
    g = c.goal
    if g:
        ok, avail, _ = _check(p50, mins0, inp.cash0, c.min_reserve, c.policy_cut, g.amount, g.by_period)
        if not ok:
            conflicts.append(Conflict(
                constraint="goal_vs_reserve", required=round(g.amount / g.by_period, 2),
                available=round(avail / g.by_period, 2),
                message=(f"Goal needs {_fmt(g.amount / g.by_period)}/mo for {g.by_period} months, but max allocatable is "
                         f"{_fmt(avail / g.by_period)}/mo after essentials, debt minimums, a {c.policy_cut:.0%} discretionary cut "
                         f"and the {_fmt(c.min_reserve)} reserve."),
            ))
            relax = _relaxations(inp, p50, mins0, g.by_period, g.amount)
    else:
        ok, avail, worst = _check(p50, mins0, inp.cash0, c.min_reserve, c.policy_cut, 0.0, 1)
        if not ok:
            conflicts.append(Conflict(
                constraint="min_reserve", required=c.min_reserve, available=round(max(0.0, c.min_reserve + worst), 2),
                message=f"Cash would fall below the {_fmt(c.min_reserve)} reserve even with a {c.policy_cut:.0%} discretionary cut.",
            ))
            r2 = float(np.ceil(max(0.0, c.min_reserve + worst)))
            relax = [Relaxation(
                kind="lower_reserve", from_value=c.min_reserve, to_value=r2, message=f"Lower the minimum reserve to {_fmt(r2)}.",
                feasible=_check(p50, mins0, inp.cash0, r2, c.policy_cut, 0.0, 1)[0])]
    feasible = not conflicts

    # --- choice: P50-only vs risk-aware
    p50_ok = [r for r in results if all(p.reserve_ok for p in r.periods)]
    p50_best = max(p50_ok, key=lambda r: r.objective) if p50_ok else max(results, key=lambda r: min(p.cash_end for p in r.periods))
    within = [r for r in results if r.shortfall_risk <= c.risk_tolerance]
    risk_adj: SequenceResult | None = None
    base_label = ""
    if within:
        rec = max(within, key=lambda r: r.objective)
    else:
        base = max(results, key=lambda r: r.objective)
        base_label = base.label
        risk_adj, scheds[f"risk_adjusted_{base.id}"] = _risk_adjust(
            base, scheds[base.id], inp, p50, paths, base_interest, labels)
        rec = risk_adj if risk_adj.shortfall_risk <= c.risk_tolerance else min(results, key=lambda r: r.shortfall_risk)
    changed = rec.id != p50_best.id

    tol = f"{c.risk_tolerance:.0%}"
    parts = [f"On the P50 forecast alone the best sequence is {p50_best.label} (objective {_fmt(p50_best.objective)}, "
             f"shortfall risk {p50_best.shortfall_risk:.0%})."]
    if within:
        parts.append(f"Among sequences with shortfall risk <= {tol}, {rec.label} has the best objective ({_fmt(rec.objective)}, "
                     f"risk {rec.shortfall_risk:.0%}).")
    elif risk_adj is not None and rec.id == risk_adj.id:
        parts.append(f"No sequence is within the {tol} tolerance; committed amounts of {base_label} "
                     f"were scaled down until risk <= {tol} ({risk_adj.label}, risk {risk_adj.shortfall_risk:.0%}).")
    else:
        parts.append(f"No sequence reaches the {tol} tolerance; showing the lowest-risk option ({rec.label}, risk {rec.shortfall_risk:.0%}).")
    parts.append("Uncertainty changed the choice." if changed else "Uncertainty did not change the choice.")
    if conflicts:
        parts.append("The goal is infeasible: " + conflicts[0].message)

    plan = PlanResult(
        method=inp.method, constraints=c, starting_cash=round(inp.cash0, 2),
        forecast=summarize(paths[:, :h], mins0, labels), sequences=results, feasible=feasible,
        conflicts=conflicts, relaxations=relax, recommended_id=rec.id, p50_only_best_id=p50_best.id,
        uncertainty_changed_choice=changed, rationale=" ".join(parts), risk_adjusted=risk_adj,
    )
    return plan, scheds


def plan(inp: PlanInputs) -> PlanResult:
    return _plan(inp)[0]


def replan(inp: PlanInputs, shock: Shock) -> ReplanResult:
    before, scheds = _plan(inp)
    k = shock.from_period
    shocked = inp.paths.copy()
    shock_paths(shocked, shock)
    after, _ = _plan(PlanInputs(
        paths=shocked, method=inp.method, cash0=inp.cash0, debts=inp.debts, constraints=inp.constraints,
        start_month=inp.start_month, horizon=inp.horizon,
        locked={sid: s[: k - 1] for sid, s in scheds.items() if not sid.startswith("risk_adjusted_")},
    ))
    prev = {s.id: s for s in before.sequences}
    changed = sorted({
        p.period for s in after.sequences for p in s.periods
        if p.period >= k and (p.extra_debt, p.savings_contrib, p.discretionary_cut)
        != next((q.extra_debt, q.savings_contrib, q.discretionary_cut) for q in prev[s.id].periods if q.period == p.period)
    })
    return ReplanResult(shock=shock, before=before, after=after, changed_periods=changed)


def shock_paths(paths: np.ndarray, shock: Shock) -> None:
    """In-place: income_change scales income from the period on; essential_expense is one-off."""
    k = shock.from_period - 1
    if shock.kind == "income_change":
        paths[:, k:, 0] *= 1 + (shock.pct or 0.0) / 100
    else:
        paths[:, k, 1] += shock.amount or 0.0


def _risk_adjust(base: SequenceResult, sched: Sched, inp, p50, paths, base_interest, labels) -> tuple[SequenceResult, Sched]:
    """Scale the committed extra-debt/savings amounts down (bisection) until shortfall risk <= tolerance."""
    rid, label = f"risk_adjusted_{base.id}", f"{base.label} (risk-adjusted)"
    desc = f"{base.label} with committed extra payments scaled down until shortfall risk is within tolerance."

    def run(scale: float):
        rows = _build(None, p50, inp.cash0, inp.debts, [(c, e * scale, v * scale) for c, e, v in sched])
        return _evaluate(rid, label, desc, rows, paths, inp, base_interest, labels, p50), _sched(rows)

    lo, hi = 0.0, 1.0
    for _ in range(20):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if run(mid)[0].shortfall_risk <= inp.constraints.risk_tolerance else (lo, mid)
    return run(lo)
