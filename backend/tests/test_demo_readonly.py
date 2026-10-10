"""Demo personas are shared public fixtures: reads and compute-only POSTs work, persisting writes are refused."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _guard_on(monkeypatch):
    monkeypatch.setenv("FINPILOT_DEMO_READONLY", "true")


@pytest.mark.parametrize("method,path,body", [
    ("post", "/api/goals/demo-priya", {"name": "x", "target_amount": 1, "target_date": "2030-01-01"}),
    ("delete", "/api/connectors/demo-priya/google_pay", None),
    ("post", "/api/events/demo-priya", {"kind": "transaction", "amount": 1}),
    ("post", "/api/alerts/gap/demo-priya", {"email": "a@b.co"}),
    ("post", "/api/budgets/demo-arjun", {"category": "dining", "monthly_limit": 1}),
])
def test_persisting_writes_to_demo_personas_are_refused(method, path, body):
    r = getattr(client, method)(path, **({"json": body} if body is not None else {}))
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"]


@pytest.mark.parametrize("path,body", [
    ("/api/simulate/demo-priya", {"action": "reduce_category_spend", "action_params": {"category": "dining", "reduction_pct": 10}}),
    ("/api/security/demo-priya/simulate-fraud", {"merchant": "Binance", "amount": 50000}),
])
def test_compute_only_posts_still_work_on_demo_personas(path, body):
    assert client.post(path, json=body).status_code == 200


def test_reads_and_chat_still_work():
    assert client.get("/api/dashboard/demo-priya").status_code == 200
    r = client.post("/api/chat", json={"user_id": "demo-priya", "message": "hi", "force_offline": True})
    assert r.status_code == 200


def test_guest_sandbox_stays_writable():
    uid = "guest-abcdef123456abcd"
    r = client.post(f"/api/goals/{uid}", json={"name": "Trip", "target_amount": 1000, "target_date": "2030-01-01"})
    assert r.status_code == 200
