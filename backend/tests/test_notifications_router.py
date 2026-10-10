"""Tests for app.api.notifications_router -- isolated FastAPI app (see
test_goals_router.py docstring for why this doesn't import app.main.app).
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.notifications_router import router
from app.core.auth import resolve_user_id
from app.core import store
from app.ingest.seed import seed_all
from app.models import AccountRow, TransactionRow

seed_all()

app = FastAPI()
app.include_router(router)
# Auth (resolve_user_id) is exhaustively covered in test_auth.py; here we
# only exercise the notifications feed, including against synthetic
# non-demo user ids that would otherwise 401 without a real Firebase token,
# so the dependency is overridden to trust the path param.
app.dependency_overrides[resolve_user_id] = lambda user_id: user_id
client = TestClient(app)


def test_persona_with_near_term_gap_produces_critical_cash_flow_gap_item():
    # demo-meera is the deliberately "fragile" persona with a near-term
    # forecast gap (see test_integration.py's persona ordering test).
    r = client.get("/api/notifications/demo-meera")
    assert r.status_code == 200
    items = r.json()
    gap_items = [i for i in items if i["type"] == "cash_flow_gap"]
    assert gap_items, f"expected a cash_flow_gap item for demo-meera, got: {items}"
    assert gap_items[0]["severity"] == "critical"
    # critical items sort first
    assert items[0]["severity"] == "critical"


def test_persona_with_recurring_obligations_due_this_week_produces_upcoming_bill_items():
    r = client.get("/api/notifications/demo-priya")
    assert r.status_code == 200
    items = r.json()
    bills = [i for i in items if i["type"] == "upcoming_bill"]
    assert bills, f"expected upcoming_bill items for demo-priya, got: {items}"
    for b in bills:
        d = date.fromisoformat(b["date"])
        assert date.today() <= d <= date.today() + timedelta(days=7)
        assert b["severity"] == "info"


def test_response_well_formed_for_persona_with_no_urgent_items():
    """A fresh synthetic user with a single account and zero transactions has
    no anomalies, no recurring bills, no forecast gap -- the feed should be
    empty (or near-empty) but a well-formed 200, not an error."""
    user_id = "test-notifications-no-urgent-items"
    store.delete_where(TransactionRow, user_id=user_id)
    store.delete_where(AccountRow, user_id=user_id)
    store.put(AccountRow(user_id=user_id, name="Checking", type="checking", balance=50000.0))

    r = client.get(f"/api/notifications/{user_id}")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    # No transaction history at all -> no anomalies, no obligations, and
    # build_dashboard_snapshot's forecast with no recurring outflows and a
    # healthy starting balance should not project a gap.
    assert not any(i["type"] == "cash_flow_gap" for i in items)
    assert not any(i["type"] == "anomaly" for i in items)
    assert not any(i["type"] == "upcoming_bill" for i in items)

    store.delete_where(AccountRow, user_id=user_id)


def test_never_raises_for_unknown_user_id():
    r = client.get("/api/notifications/totally-unknown-user-id-xyz")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
