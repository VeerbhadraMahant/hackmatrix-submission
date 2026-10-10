"""Tests for 5D COLLABORATE: Household models, multi-member co-piloting, hashed invites, and combined net worth."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import HouseholdInviteRow, HouseholdMemberRow, HouseholdRow
from app.ingest.seed import seed_all


@pytest.fixture(autouse=True)
def _clean_seed():
    seed_all()
    yield


client = TestClient(app)


def test_get_household_demo_priya():
    resp = client.get("/api/household/demo-priya")
    assert resp.status_code == 200
    data = resp.json()

    assert data["household"]["name"] == "Priya & Partner Family"
    assert data["user_role"] == "owner"
    assert len(data["members"]) == 2

    # Check member names
    member_names = [m["display_name"] for m in data["members"]]
    assert "Priya" in member_names
    assert "Arjun" in member_names

    # Check combined net worth
    nw_summary = data["net_worth_summary"]
    assert "total_net_worth" in nw_summary
    assert "total_assets" in nw_summary
    assert "total_liabilities" in nw_summary
    assert len(nw_summary["members_breakdown"]) == 2

    # Check pending invites
    assert len(data["invites"]) >= 1
    assert data["invites"][0]["invited_email"] == "rohan.sharma@example.com"
    assert data["invites"][0]["status"] == "pending"


def test_get_household_unassigned_user():
    resp = client.get("/api/household/demo-meera")
    assert resp.status_code == 404


def test_create_household_demo_meera():
    payload = {"name": "Meera's Financial Hub"}
    resp = client.post("/api/household/demo-meera", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["household"]["name"] == "Meera's Financial Hub"
    assert data["user_role"] == "owner"
    assert len(data["members"]) == 1
    assert data["members"][0]["user_id"] == "demo-meera"


def test_create_and_accept_invite():
    # Priya invites Meera
    invite_resp = client.post(
        "/api/household/demo-priya/invites",
        json={"email": "meera@example.com", "role": "editor"},
    )
    assert invite_resp.status_code == 200
    invite_data = invite_resp.json()
    assert invite_data["invited_email"] == "meera@example.com"
    assert invite_data["token"] is not None
    token = invite_data["token"]

    # Try accepting with invalid token as Meera
    bad_resp = client.post(
        "/api/household/demo-meera/invites/accept",
        json={"token": "completely-invalid-token"},
    )
    assert bad_resp.status_code == 404

    # Meera accepts valid token
    accept_resp = client.post(
        "/api/household/demo-meera/invites/accept",
        json={"token": token},
    )
    assert accept_resp.status_code == 200
    accepted_data = accept_resp.json()
    assert len(accepted_data["members"]) == 3
    meera_member = next(m for m in accepted_data["members"] if m["user_id"] == "demo-meera")
    assert meera_member["role"] == "editor"


def test_revoke_invite():
    # Priya creates an invite and revokes it
    inv_resp = client.post(
        "/api/household/demo-priya/invites",
        json={"email": "temp-invite@test.com", "role": "viewer"},
    )
    assert inv_resp.status_code == 200
    inv_id = inv_resp.json()["id"]

    del_resp = client.delete(f"/api/household/demo-priya/invites/{inv_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["revoked"] is True


def test_remove_member_permission():
    # Arjun (editor) cannot remove Priya (owner)
    del_resp = client.delete("/api/household/demo-arjun/members/demo-priya")
    assert del_resp.status_code == 403

    # Priya (owner) can remove Arjun
    owner_del_resp = client.delete("/api/household/demo-priya/members/demo-arjun")
    assert owner_del_resp.status_code == 200
    assert owner_del_resp.json()["removed"] is True


def test_household_networth_endpoint():
    resp = client.get("/api/household/demo-priya/networth")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_net_worth" in data
    assert "members_breakdown" in data
