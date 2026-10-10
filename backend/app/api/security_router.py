"""Security suite: Evidence Room (agent investigation), Twin Simulator (money-flow graph) and My Data."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.connectors_router import CATALOG, DATASET_FILES, _dataset
from app.core import store
from app.core.audit import log_audit_event
from app.core.auth import resolve_user_id
from app.models import AccountRow, AuditLogRow, ConnectionRow, TransactionRow
from app.security import agents

router = APIRouter(prefix="/api/security", tags=["security"])


def _log(request: Request, user_id: str, what: str) -> None:
    log_audit_event(user_id=user_id, event_type="data_access", method=request.method, path=request.url.path, status_code=200,
                    client_ip=request.client.host if request.client else None, detail=what)


@router.post("/{user_id}/investigate")
def investigate(request: Request, user_id: str = Depends(resolve_user_id)) -> StreamingResponse:
    _log(request, user_id, "Evidence Room investigation read your transactions and accounts")
    return StreamingResponse((json.dumps(e, default=str) + "\n" for e in agents.investigate(user_id)), media_type="application/x-ndjson")


@router.get("/{user_id}/report")
def report(user_id: str = Depends(resolve_user_id)) -> dict | None:
    return agents.latest_report(user_id)


@router.post("/{user_id}/demo-threats")
def plant(user_id: str = Depends(resolve_user_id)) -> dict:
    try:
        return {"planted": agents.plant_demo_threats(user_id)}
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete("/{user_id}/demo-threats")
def clear(user_id: str = Depends(resolve_user_id)) -> dict:
    return {"removed": agents.clear_demo_threats(user_id)}


@router.get("/{user_id}/graph")
def graph(request: Request, months: int = 6, user_id: str = Depends(resolve_user_id)) -> dict:
    months = max(1, min(months, 12))
    since = date.today() - timedelta(days=30 * months)
    all_rows, accounts = store.query(TransactionRow, user_id=user_id), store.query(AccountRow, user_id=user_id)
    rows = [t for t in agents._spend(all_rows) if t.date >= since]
    flagged: dict[str, list[str]] = defaultdict(list)
    for fs in agents.run_checks(all_rows, accounts).values():
        for f in fs:
            if f["merchant"]:
                flagged[f["merchant"]].append(f["title"])
    acc_name = {a.id: a.name for a in accounts}
    totals: dict[str, float] = defaultdict(float)
    for t in rows:
        totals[t.merchant] += -t.amount
    top = {m for m, _ in sorted(totals.items(), key=lambda kv: -kv[1])[:18]} | {m for m in totals if m in flagged}
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str], dict] = {}

    def node(i, label, kind, amt, m=None):
        n = nodes.setdefault(i, {"id": i, "label": label, "kind": kind, "amount": 0.0, "flagged": False, "findings": list(flagged.get(m, [])) if m else []})
        n["amount"] += amt
        n["flagged"] = n["flagged"] or bool(n["findings"])

    def edge(a, b, amt, bad):
        e = edges.setdefault((a, b), {"source": a, "target": b, "amount": 0.0, "flagged": False})
        e["amount"] += amt
        e["flagged"] = e["flagged"] or bad

    for t in rows:
        a, c, m = f"acc:{t.account_id}", f"cat:{t.category}", t.merchant if t.merchant in top else "Other merchants"
        bad, amt = m in flagged, -t.amount
        node("you", "You", "you", amt)
        node(a, acc_name.get(t.account_id, "Account"), "account", amt)
        node(c, t.category.replace("_", " ").title(), "category", amt)
        node(f"m:{m}", m, "merchant", amt, m)
        edge("you", a, amt, False)
        edge(a, c, amt, bad)
        edge(c, f"m:{m}", amt, bad)
    for n in nodes.values():
        if n["kind"] in ("account", "category"):
            n["flagged"] = any(e["flagged"] for k, e in edges.items() if n["id"] in k)
    _log(request, user_id, "Twin Simulator read your transactions")
    return {
        "months": months, "nodes": list(nodes.values()), "edges": list(edges.values()),
        "summary": {"flagged_merchants": len(flagged), "money_at_risk": round(sum(totals[m] for m in flagged if m in totals), 2), "total_spend": round(sum(totals.values()), 2)},
    }


class FraudSim(BaseModel):
    merchant: str
    amount: float


@router.post("/{user_id}/simulate-fraud")
def simulate_fraud(body: FraudSim, user_id: str = Depends(resolve_user_id)) -> dict:
    """Run the agents on your ledger plus one hypothetical payment (nothing is stored)."""
    rows, accounts = store.query(TransactionRow, user_id=user_id), store.query(AccountRow, user_id=user_id)
    if not accounts:
        raise HTTPException(409, "Connect a data source first")
    sim = [TransactionRow(id="sim", user_id=user_id, account_id=accounts[0].id, date=date.today(), amount=-abs(body.amount),
                          merchant=body.merchant.strip() or "Unknown", category="shopping")]
    before = {f["title"] for fs in agents.run_checks(rows, accounts).values() for f in fs}
    caught = [f for fs in agents.run_checks(rows + sim, accounts).values() for f in fs if "sim" in f["txn_ids"] or f["title"] not in before]
    return {"caught": bool(caught), "findings": caught}


def _preview(connector: str, rows: list[TransactionRow]) -> tuple[int, list]:
    if connector == "ledger":
        recent = sorted(rows, key=lambda t: t.date, reverse=True)[:5]
        return len(rows), [{"date": str(t.date), "merchant": t.merchant, "amount": t.amount} for t in recent]
    data = _dataset(connector)
    first = next(iter(data.values()), [])
    return sum(len(v) for v in data.values()), first[:5]


@router.get("/{user_id}/data")
def my_data(request: Request, user_id: str = Depends(resolve_user_id)) -> dict:
    rows = store.query(TransactionRow, user_id=user_id)
    linked = {c.connector: c for c in store.query(ConnectionRow, user_id=user_id)}
    sources = []
    if rows:
        n, prev = _preview("ledger", rows)
        src = next((c for c in ("google_pay", "google_sheets") if c in linked), None)
        sources.append({"id": src or "ledger", "name": CATALOG[src][0] if src else "Transactions & accounts",
                        "detail": f"{len(store.query(AccountRow, user_id=user_id))} accounts", "records": n, "preview": prev, "disconnectable": src is not None})
    for cid in DATASET_FILES:
        if cid in linked:
            n, prev = _preview(cid, rows)
            sources.append({"id": cid, "name": CATALOG[cid][0], "detail": linked[cid].detail, "records": n, "preview": prev, "disconnectable": True})
    log = sorted(store.query(AuditLogRow, user_id=user_id), key=lambda r: r.created_at, reverse=True)[:30]
    _log(request, user_id, "My Data page listed your connected sources")
    return {"sources": sources, "access_log": [{"when": r.created_at.isoformat(), "event": r.event_type, "method": r.method, "path": r.path, "detail": r.detail, "status": r.status_code} for r in log]}


@router.get("/{user_id}/data/export")
def export_all(request: Request, user_id: str = Depends(resolve_user_id)) -> JSONResponse:
    _log(request, user_id, "Exported all your data")
    linked = store.query(ConnectionRow, user_id=user_id)
    out = {
        "accounts": [a.model_dump(mode="json") for a in store.query(AccountRow, user_id=user_id)],
        "transactions": [t.model_dump(mode="json") for t in store.query(TransactionRow, user_id=user_id)],
        **{c.connector: _dataset(c.connector) for c in linked if c.connector in DATASET_FILES},
    }
    return JSONResponse(out, headers={"Content-Disposition": 'attachment; filename="finpilot-all-data.json"'})


@router.get("/{user_id}/financial")
def financial(request: Request, user_id: str = Depends(resolve_user_id)) -> dict:
    """Security score and breakdown of the user's own financial data (no AI)."""
    _log(request, user_id, "Financial security read your transactions and accounts")
    from app.security import financial as fin

    return fin.build(user_id)


@router.get("/{user_id}/financial/brief")
def financial_brief(user_id: str = Depends(resolve_user_id)) -> dict:
    """Copilot's written analysis of the same facts (AI, rules fallback)."""
    from app.security import financial as fin

    return fin.brief(fin.build(user_id))
