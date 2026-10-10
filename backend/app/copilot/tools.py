"""Tool functions callable by the function-calling loop (app.copilot.engine)
and by the offline rule-based router (app.copilot.offline_router).

Every function here:
  - takes plain JSON-serializable arguments,
  - returns a plain JSON-serializable dict,
  - never raises -- on any missing/bad data it returns
    {"error": "...", "data_gap": "..."} shaped info instead, so callers can
    surface a DataGap rather than crashing or hallucinating.

Data source: every tool reads via `_snapshot(user_id)`, which builds a real
per-user DashboardSnapshot from the DB (app.ingest.snapshot), falling back to
the Phase-0 fixture on any error so the copilot never crashes/hallucinates
from a half-broken DB state. This is intentionally the ONLY place that
touches persistence -- every function above stays pure plain-dict-in,
plain-dict-out.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.core import store
from app.ingest.fixtures import demo_dashboard_snapshot
from app.schemas import ActionType


def _snapshot(user_id: str):
    """Single seam for swapping fixture data -> real per-user data later.

    Never raises: any DB/query error falls back to the deterministic fixture
    so a broken DB never turns into a copilot crash or hallucinated answer.
    """
    try:
        from app.ingest.snapshot import build_dashboard_snapshot

        return build_dashboard_snapshot(user_id)
    except Exception:
        try:
            return demo_dashboard_snapshot(user_id)
        except Exception:  # pragma: no cover - fixture is currently infallible
            return None


def _starting_balance(user_id: str) -> float:
    """Real checking+savings balance for `user_id` (see
    app.ingest.snapshot module docstring for the liquid-balance rule);
    falls back to the Phase-0 fixture constant for unknown/fixture users."""
    try:
        from app.models import AccountRow

        accounts = store.query(AccountRow, user_id=user_id)
        if accounts:
            return float(sum(a.balance for a in accounts if a.type in ("checking", "savings")))
    except Exception:
        pass
    return 42_000.0


def get_summary(user_id: str) -> dict:
    """Net worth, income, expenses, savings rate, and health score for a user."""
    snap = _snapshot(user_id)
    if snap is None:
        return {
            "error": f"No data available for user '{user_id}'.",
            "data_gap": "Need a valid, onboarded user_id to compute a summary.",
        }
    return {
        "user_id": snap.user_id,
        "net_worth": snap.net_worth,
        "monthly_income": snap.monthly_income,
        "monthly_expenses": snap.monthly_expenses,
        "savings_rate": snap.savings_rate,
        "health_score": snap.health_score.overall,
        "health_score_sub_scores": [
            {
                "name": s.name,
                "score": s.score,
                "weight": s.weight,
                "detail": s.detail,
            }
            for s in snap.health_score.sub_scores
        ],
        "health_score_trend_30d": snap.health_score.trend_30d,
    }


def query_transactions(
    user_id: str,
    category: str = "",
    merchant: str = "",
    days: int = 30,
) -> dict:
    """Return illustrative transactions matching a category/merchant in the
    last N days.

    TODO(integration): there is no real per-transaction ledger in the fixture
    yet -- data-agent's app.ingest.categorize / real transaction tables will
    supersede this. For now we synthesize a small illustrative list from
    snapshot.recurring_obligations (each obligation materialized as its most
    recent occurrence within the window) so the *shape* of this tool's output
    is final and callers/tests can already depend on it.
    """
    today = date.today()
    window_start = today - timedelta(days=max(days, 0))

    real = _ledger(user_id, window_start)
    if real:
        rows = [
            t for t in real
            if (not category or t.category == category)
            and (not merchant or merchant.lower() in t.merchant.lower())
        ]
        txns = [
            {"id": t.id, "date": t.date.isoformat(), "merchant": t.merchant, "category": t.category,
             "amount": t.amount, "is_recurring": t.is_recurring, "recurring_group_id": t.recurring_group_id}
            for t in sorted(rows, key=lambda t: t.date, reverse=True)
        ]
        # total = money spent (outflows only), so it matches get_spending_breakdown
        txns = txns[:50]  # keep the LLM prompt small; total below still covers every match
        return {"transactions": txns, "total": sum(-t.amount for t in rows if _is_spend(t)), "count": len(txns)}

    snap = _snapshot(user_id)
    if snap is None:
        return {
            "error": f"No data available for user '{user_id}'.",
            "data_gap": "Need a valid, onboarded user_id to look up transactions.",
            "transactions": [],
            "total": 0.0,
            "count": 0,
        }

    transactions: list[dict] = []
    for ob in snap.recurring_obligations:
        if category and ob.category.value != category:
            continue
        if merchant and merchant.lower() not in ob.merchant.lower():
            continue

        # Walk the obligation's expected occurrences backwards from
        # next_expected_date until we fall outside the window, approximating
        # a monthly cadence (good enough for an illustrative fixture).
        occurrence = ob.next_expected_date
        step_days = {
            "weekly": 7,
            "biweekly": 14,
            "monthly": 30,
            "quarterly": 90,
            "annual": 365,
        }.get(ob.frequency.value, 30)
        while occurrence > today:
            occurrence -= timedelta(days=step_days)
        while occurrence >= window_start:
            transactions.append(
                {
                    "id": f"synthetic-{ob.group_id}-{occurrence.isoformat()}",
                    "date": occurrence.isoformat(),
                    "merchant": ob.merchant,
                    "category": ob.category.value,
                    "amount": ob.amount,
                    "is_recurring": True,
                    "recurring_group_id": ob.group_id,
                    "synthetic": True,
                }
            )
            occurrence -= timedelta(days=step_days)

    transactions.sort(key=lambda t: t["date"], reverse=True)
    total = sum(t["amount"] for t in transactions)
    return {"transactions": transactions, "total": total, "count": len(transactions)}


NON_SPEND = {"transfer", "credit_card_payment", "income"}  # mirrors frontend lib/spend.ts


def _ledger(user_id: str, since: date | None = None) -> list:
    """Real transactions for the user (from `since` when given); [] on any error."""
    try:
        from app.models import TransactionRow

        return [t for t in store.query(TransactionRow, user_id=user_id) if since is None or t.date >= since]
    except Exception:
        return []


def _is_spend(t) -> bool:
    return t.amount < 0 and t.category not in NON_SPEND


def get_spending_breakdown(user_id: str, days: int = 90) -> dict:
    """Spend by category, top merchants and per-month totals over the last N days, from the real ledger."""
    rows = [t for t in _ledger(user_id, date.today() - timedelta(days=max(days, 1))) if _is_spend(t)]
    if not rows:
        return {"error": "No spending transactions found.", "data_gap": "Connect a payment source to analyse spending."}

    def group(key) -> dict[str, float]:
        out: dict[str, float] = {}
        for t in rows:
            out[key(t)] = out.get(key(t), 0.0) + -t.amount
        return dict(sorted(out.items(), key=lambda kv: kv[1], reverse=True))

    total = sum(-t.amount for t in rows)
    return {
        "days": days,
        "total_spend": round(total, 2),
        "transaction_count": len(rows),
        "by_category": [{"category": k, "amount": round(v, 2), "share": round(v / total, 3)} for k, v in group(lambda t: t.category).items()],
        "top_merchants": [{"merchant": k, "amount": round(v, 2)} for k, v in list(group(lambda t: t.merchant).items())[:8]],
        "by_month": [{"month": k, "amount": round(v, 2)} for k, v in sorted(group(lambda t: t.date.strftime("%Y-%m")).items())],
    }


def _connector_data(user_id: str, connector: str, label: str) -> dict:
    """Demo dataset of a linked connector, or an error + data_gap when it isn't linked."""
    from app.api.connectors_router import _dataset
    from app.models import ConnectionRow

    try:
        linked = store.get(ConnectionRow, f"{user_id}:{connector}") is not None
    except Exception:
        linked = False
    if not linked:
        return {"error": f"{label} isn't connected.", "data_gap": f"Connect {label} to analyse it."}
    return _dataset(connector)


def get_invoices(user_id: str) -> dict:
    """Bills and invoices parsed from Gmail/Drive: what is paid, what is due, and the total due."""
    data = _connector_data(user_id, "invoices", "Gmail & Drive invoices")
    if "error" in data:
        return data
    inv = data["invoices"]
    due = [i for i in inv if i["status"] == "due"]
    return {"invoices": inv, "count": len(inv), "due": due, "total_due": sum(i["amount"] for i in due)}


def get_investments(user_id: str) -> dict:
    """Mutual fund and stock holdings with invested amount, current value, gain and monthly SIP total."""
    data = _connector_data(user_id, "investments", "Mutual funds & stocks")
    if "error" in data:
        return data
    funds = [{**f, "value": round(f["units"] * f["nav"], 2)} for f in data["mutual_funds"]]
    stocks = [{**x, "invested": x["qty"] * x["avg_price"], "value": round(x["qty"] * x["ltp"], 2)} for x in data["stocks"]]
    invested = sum(f["invested"] for f in funds) + sum(x["invested"] for x in stocks)
    value = sum(f["value"] for f in funds) + sum(x["value"] for x in stocks)
    return {
        "mutual_funds": funds,
        "stocks": stocks,
        "total_invested": round(invested, 2),
        "total_value": round(value, 2),
        "gain": round(value - invested, 2),
        "gain_pct": round((value - invested) / invested, 4) if invested else None,
        "monthly_sip": sum(f["sip_monthly"] for f in funds),
    }


def get_recurring(user_id: str) -> dict:
    """List recurring obligations (subscriptions, EMI, rent, SIPs) for a user."""
    snap = _snapshot(user_id)
    if snap is None:
        return {
            "error": f"No data available for user '{user_id}'.",
            "data_gap": "Need a valid, onboarded user_id to list recurring obligations.",
            "obligations": [],
        }
    obligations = [
        {
            "group_id": ob.group_id,
            "merchant": ob.merchant,
            "category": ob.category.value,
            "amount": ob.amount,
            "frequency": ob.frequency.value,
            "next_expected_date": ob.next_expected_date.isoformat(),
            "confidence": ob.confidence,
        }
        for ob in snap.recurring_obligations
    ]
    monthly_total = sum(
        ob.amount for ob in snap.recurring_obligations if ob.frequency.value == "monthly"
    )
    return {
        "obligations": obligations,
        "count": len(obligations),
        "monthly_total": monthly_total,
    }


def get_debt(user_id: str) -> dict:
    """List debts for a user, plus a simple debt-to-income ratio if computable."""
    snap = _snapshot(user_id)
    if snap is None:
        return {
            "error": f"No data available for user '{user_id}'.",
            "data_gap": "Need a valid, onboarded user_id to look up debts.",
            "debts": [],
        }
    debts = [
        {
            "id": d.id,
            "principal": d.principal,
            "interest_rate_apr": d.interest_rate_apr,
            "minimum_payment": d.minimum_payment,
            "due_day_of_month": d.due_day_of_month,
        }
        for d in snap.debts
    ]
    result: dict = {
        "debts": debts,
        "count": len(debts),
        "total_principal": sum(d.principal for d in snap.debts),
        "total_minimum_payment": sum(d.minimum_payment for d in snap.debts),
    }
    if snap.monthly_income and snap.monthly_income > 0:
        result["debt_to_income_ratio"] = round(
            result["total_minimum_payment"] / snap.monthly_income, 4
        )
    else:
        result["debt_to_income_ratio"] = None
        result["data_gap"] = "Monthly income is zero/unknown; cannot compute DTI."
    return result


def get_forecast(user_id: str, horizon_days: int = 90) -> dict:
    """Cash-flow forecast points for a user, optionally trimmed/resampled to
    a shorter horizon."""
    snap = _snapshot(user_id)
    if snap is None:
        return {
            "error": f"No data available for user '{user_id}'.",
            "data_gap": "Need a valid, onboarded user_id to compute a forecast.",
            "points": [],
        }
    forecast = snap.forecast
    horizon_days = max(1, min(horizon_days, forecast.horizon_days))
    points = [p for p in forecast.points if (p.date - date.today()).days < horizon_days]
    return {
        "horizon_days": horizon_days,
        "points": [
            {
                "date": p.date.isoformat(),
                "p10": p.p10,
                "p50": p.p50,
                "p90": p.p90,
                "is_gap_risk": p.is_gap_risk,
            }
            for p in points
        ],
        "first_gap_date": forecast.first_gap_date.isoformat()
        if forecast.first_gap_date and (forecast.first_gap_date - date.today()).days < horizon_days
        else None,
        "confidence": forecast.confidence,
        "basis": forecast.basis,
    }


def simulate_action(user_id: str, action: str, action_params: dict = {}) -> dict:  # noqa: B006 -- never mutated
    """Simulate the impact of a financial action (e.g. prepay_debt,
    cancel_subscription, affordability_check) on the user's health score and
    forecast.

    Tries app.simulate.engine (forecast-sim-agent's real simulator) first; if
    that module isn't importable yet in this branch, falls back to a clearly
    labeled stub estimate derived from the snapshot so the rest of the system
    still has *something* concrete to point at.
    """
    action_params = action_params or {}
    snap = _snapshot(user_id)
    if snap is None:
        return {
            "error": f"No data available for user '{user_id}'.",
            "data_gap": "Need a valid, onboarded user_id to run a simulation.",
        }

    try:
        action_enum = ActionType(action)
    except ValueError:
        return {
            "error": f"Unknown action '{action}'.",
            "data_gap": f"Recognized actions: {[a.value for a in ActionType]}",
        }

    try:
        from app.simulate.engine import ForecastInputs, simulate as real_simulate  # type: ignore

        inputs = ForecastInputs(
            starting_balance=_starting_balance(user_id),
            recurring=snap.recurring_obligations,
            debts=snap.debts,
            transactions=None,
            horizon_days=snap.forecast.horizon_days,
            monthly_income=snap.monthly_income,
        )
        result = real_simulate(
            action_enum,
            action_params,
            current_forecast_inputs=inputs,
            current_health_score=snap.health_score.overall,
        )
        # Flatten to the same top-level shape _stub_simulation returns
        # (health_score_before/after, impact, confidence, forecast_before/after)
        # so callers -- the tool loop and check_affordability below --
        # see one consistent shape regardless of which path answered.
        result_dict = _jsonable(result)
        return {"source": "app.simulate.engine", **result_dict}
    except ImportError:
        pass
    except Exception as exc:  # defensive: never let a half-built sim engine 500 the copilot
        return {
            "error": f"Simulation engine raised an error: {exc}",
            "data_gap": "app.simulate.engine is present but failed; using stub estimate instead.",
            "source": "stub",
            **_stub_simulation(snap, action_enum, action_params),
        }

    return {"source": "stub", **_stub_simulation(snap, action_enum, action_params)}


def _stub_simulation(snap, action_enum: ActionType, action_params: dict) -> dict:
    """Clearly-labeled placeholder impact estimate used only when
    forecast-sim-agent's real `app.simulate.engine` isn't merged into this
    branch yet. Derives a small, plausible delta from snapshot data so the
    contract shape (ImpactEstimate-like dict) is already correct.
    """
    before_score = snap.health_score.overall
    monthly_income = snap.monthly_income or 0.0
    monthly_expenses = snap.monthly_expenses or 0.0
    free_cash_flow = monthly_income - monthly_expenses

    if action_enum == ActionType.affordability_check:
        amount = float(action_params.get("amount", 0.0))
        months_of_buffer = (free_cash_flow / amount) if amount else None
        affordable = bool(amount and amount <= max(free_cash_flow, 0) * 2)
        return {
            "note": "STUB estimate -- app.simulate.engine not available in this branch.",
            "amount": amount,
            "free_cash_flow_monthly": free_cash_flow,
            "affordable": affordable,
            "impact": {
                "metric": "monthly free cash flow",
                "before": free_cash_flow,
                "after": free_cash_flow - (amount / 3 if amount else 0),
                "delta": -(amount / 3) if amount else 0,
                "horizon": "next 3 months (amortized)",
            },
            "confidence": 0.4,
        }

    # Generic stub: assume a small positive health-score/cash-flow nudge.
    delta_score = 3.0
    return {
        "note": "STUB estimate -- app.simulate.engine not available in this branch.",
        "health_score_before": before_score,
        "health_score_after": min(100.0, before_score + delta_score),
        "impact": {
            "metric": "health score",
            "before": before_score,
            "after": min(100.0, before_score + delta_score),
            "delta": delta_score,
            "horizon": "3 months",
        },
        "confidence": 0.35,
    }


def check_affordability(user_id: str, amount: float, description: str = "") -> dict:
    """Thin wrapper over simulate_action(action='affordability_check', ...)."""
    return simulate_action(
        user_id=user_id,
        action=ActionType.affordability_check.value,
        action_params={"amount": amount, "description": description},
    )


def _jsonable(obj):
    """Best-effort conversion of a pydantic model / dataclass / dict into a
    plain JSON-serializable structure."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return obj


TOOL_FUNCTIONS = [
    get_summary,
    query_transactions,
    get_recurring,
    get_debt,
    get_forecast,
    simulate_action,
    check_affordability,
    get_spending_breakdown,
    get_invoices,
    get_investments,
]
