"""Tests for 5C PLAN: goal covers, funding account auto-tracking, and required monthly calculation."""
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.core import store
from app.main import app
from app.models import AccountRow, GoalRow
from app.ingest.seed import seed_all


def setup_module():
    seed_all()


client = TestClient(app)


def test_list_goals_demo_priya():
    resp = client.get("/api/goals/demo-priya")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3

    # Check first goal has required fields
    g1 = data[0]
    assert "goal" in g1
    goal = g1["goal"]
    assert "cover_key" in goal
    assert "funding_account_id" in goal
    assert "auto_track" in goal
    assert "required_monthly" in g1
    assert isinstance(g1["required_monthly"], (int, float))
    assert g1["required_monthly"] >= 0


def test_create_goal_with_auto_track():
    # Find Priya's savings account
    acc = next(a for a in store.query(AccountRow, user_id="demo-priya") if "Savings" in a.name)
    acc_id = acc.id
    acc_balance = acc.balance

    future_date = (date.today() + timedelta(days=365)).isoformat()
    payload = {
        "name": "House Downpayment",
        "target_amount": 1000000.0,
        "target_date": future_date,
        "current_amount": 0.0,
        "cover_key": "home_downpayment",
        "funding_account_id": acc_id,
        "auto_track": True,
    }

    resp = client.post("/api/goals/demo-priya", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["goal"]["name"] == "House Downpayment"
    assert res_data["goal"]["cover_key"] == "home_downpayment"
    assert res_data["goal"]["funding_account_id"] == acc_id
    assert res_data["goal"]["auto_track"] is True
    # Auto-track should reflect the account balance
    assert res_data["goal"]["current_amount"] == acc_balance
    assert res_data["required_monthly"] > 0


def test_create_goal_invalid_funding_account():
    payload = {
        "name": "Invalid Account Goal",
        "target_amount": 500000.0,
        "cover_key": "general",
        "funding_account_id": "non-existent-account-id-123",
        "auto_track": True,
    }
    resp = client.post("/api/goals/demo-priya", json=payload)
    assert resp.status_code == 400


def test_update_goal_cover_and_target():
    # List goals to get an existing ID
    list_resp = client.get("/api/goals/demo-priya")
    assert list_resp.status_code == 200
    goal_id = list_resp.json()[0]["goal"]["id"]

    new_target_date = (date.today() + timedelta(days=180)).isoformat()
    patch_payload = {
        "cover_key": "luxury_travel",
        "target_amount": 750000.0,
        "target_date": new_target_date,
    }
    patch_resp = client.patch(f"/api/goals/demo-priya/{goal_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["goal"]["cover_key"] == "luxury_travel"
    assert updated["goal"]["target_amount"] == 750000.0
    assert updated["required_monthly"] > 0


def test_cross_user_isolation():
    # Arjun cannot access or edit Priya's goals
    list_resp = client.get("/api/goals/demo-priya")
    priya_goal_id = list_resp.json()[0]["goal"]["id"]

    # Arjun tries to patch Priya's goal
    patch_resp = client.patch(
        f"/api/goals/demo-arjun/{priya_goal_id}",
        json={"target_amount": 1.0},
    )
    assert patch_resp.status_code == 404

    # Arjun tries to delete Priya's goal
    del_resp = client.delete(f"/api/goals/demo-arjun/{priya_goal_id}")
    assert del_resp.status_code == 404


def test_delete_goal():
    # Create a temporary goal then delete it
    create_resp = client.post(
        "/api/goals/demo-priya",
        json={"name": "Temp Goal", "target_amount": 10000.0},
    )
    assert create_resp.status_code == 200
    temp_id = create_resp.json()["goal"]["id"]

    del_resp = client.delete(f"/api/goals/demo-priya/{temp_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # Verify deleted
    list_resp = client.get("/api/goals/demo-priya")
    ids = [g["goal"]["id"] for g in list_resp.json()]
    assert temp_id not in ids
