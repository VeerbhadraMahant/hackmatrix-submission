"""Verifies the audit-log middleware (app/main.py) actually persists a row
for an auth denial and for a successful mutation -- not just that requests
still succeed with the middleware installed."""
from __future__ import annotations

from fastapi.testclient import TestClient
from app.core import store
from app.main import app
from app.models import AuditLogRow

client = TestClient(app)


def _latest_audit_rows(event_type: str, limit: int = 5) -> list[AuditLogRow]:
    rows = store.query(AuditLogRow, event_type=event_type)
    rows.sort(key=lambda r: r.created_at, reverse=True)
    return rows[:limit]


def test_auth_denial_is_audited():
    before = len(_latest_audit_rows("auth_denied", limit=1000))
    r = client.get("/api/dashboard/some-real-user-not-a-demo-persona")
    assert r.status_code == 401
    after = _latest_audit_rows("auth_denied", limit=1000)
    assert len(after) == before + 1
    assert after[0].path == "/api/dashboard/some-real-user-not-a-demo-persona"
    assert after[0].status_code == 401


def test_successful_mutation_is_audited():
    before = len(_latest_audit_rows("mutation", limit=1000))
    r = client.post(
        "/api/events/demo-priya",
        json={"kind": "transaction", "amount": -100, "merchant": "Audit Test Merchant"},
    )
    assert r.status_code == 200
    after = _latest_audit_rows("mutation", limit=1000)
    assert len(after) == before + 1
    assert after[0].path == "/api/events/demo-priya"
    assert after[0].user_id == "demo-priya"


def test_successful_read_is_not_audited_as_mutation():
    before = len(_latest_audit_rows("mutation", limit=1000))
    r = client.get("/api/dashboard/demo-priya")
    assert r.status_code == 200
    after = _latest_audit_rows("mutation", limit=1000)
    assert len(after) == before  # a GET must never be logged as a mutation
