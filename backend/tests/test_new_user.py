"""A real (non-demo) user starts empty -- never shown demo data -- and can
build up their own data via accounts / events / CSV upload."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.core.auth import resolve_user_id
from app.core import store
from app.main import app

UID = "11111111-2222-3333-4444-555555555555"


@pytest.fixture()
def client():
    app.dependency_overrides[resolve_user_id] = lambda user_id: user_id
    yield TestClient(app)
    app.dependency_overrides.clear()
    from app.models import AccountRow, EventRow, InsightsSnapshotRow, TransactionRow
    for m in (AccountRow, TransactionRow, EventRow, InsightsSnapshotRow):
        store.delete_where(m, user_id=UID)


def test_new_user_gets_empty_snapshot_not_demo(client):
    snap = client.get(f"/api/dashboard/{UID}").json()
    assert snap["has_data"] is False
    assert snap["net_worth"] == 0 and snap["recurring_obligations"] == [] and snap["debts"] == []


def test_demo_persona_still_has_data(client):
    assert client.get("/api/dashboard/demo-priya").json()["has_data"] is True


def test_create_account_then_snapshot_has_data(client):
    r = client.post(f"/api/accounts/{UID}", json={"name": "HDFC Savings", "type": "savings", "balance": 50000})
    assert r.status_code == 201
    assert [a["name"] for a in client.get(f"/api/accounts/{UID}").json()] == ["HDFC Savings"]
    snap = client.get(f"/api/dashboard/{UID}").json()
    assert snap["has_data"] is True and snap["net_worth"] == 50000


def test_first_transaction_creates_default_account(client):
    r = client.post(f"/api/events/{UID}", json={"kind": "transaction", "amount": -450, "merchant": "Cafe"})
    assert r.status_code == 200
    assert len(client.get(f"/api/accounts/{UID}").json()) == 1
    assert client.get(f"/api/dashboard/{UID}").json()["has_data"] is True


def test_csv_upload_for_new_user(client):
    csv = b"date,amount,merchant\n2026-09-01,-500,Swiggy\n2026-09-02,50000,Salary\n"
    r = client.post(f"/api/upload/{UID}", files={"file": ("s.csv", io.BytesIO(csv), "text/csv")})
    assert r.status_code == 200, r.text
    assert client.get(f"/api/dashboard/{UID}").json()["has_data"] is True


def test_transaction_uses_existing_savings_account_before_creating_one(client):
    client.post(f"/api/accounts/{UID}", json={"name": "Savings", "type": "savings", "balance": 100})
    client.post(f"/api/events/{UID}", json={"kind": "transaction", "amount": -10, "merchant": "Tea"})
    assert len(client.get(f"/api/accounts/{UID}").json()) == 1
