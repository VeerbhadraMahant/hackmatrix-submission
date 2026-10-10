"""Tests for app.api.goals_router -- built as its own isolated FastAPI app
(rather than importing app.main.app) since main.py is intentionally not
touched by this agent (a sibling agent's router gets wired in there by the
integration lead). Demo personas bypass auth entirely (see
app.core.auth.resolve_user_id), so no token is needed here.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.goals_router import router
from app.core import store
from app.ingest.seed import seed_all
from app.models import GoalRow

seed_all()

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _cleanup_goals(user_id: str) -> None:
    store.delete_where(GoalRow, user_id=user_id)


def test_create_then_list_shows_goal_with_progress():
    _cleanup_goals("demo-priya")
    r = client.post(
        "/api/goals/demo-priya",
        json={"name": "Emergency fund", "target_amount": 100000, "current_amount": 10000},
    )
    assert r.status_code == 200
    created = r.json()
    assert created["goal"]["name"] == "Emergency fund"
    assert "on_track" in created

    r = client.get("/api/goals/demo-priya")
    assert r.status_code == 200
    goals = r.json()
    names = [g["goal"]["name"] for g in goals]
    assert "Emergency fund" in names
    match = next(g for g in goals if g["goal"]["name"] == "Emergency fund")
    assert match["goal"]["current_amount"] == 10000
    assert "months_remaining" in match


def test_goal_already_met_is_on_track_with_near_zero_months_remaining():
    _cleanup_goals("demo-arjun")
    r = client.post(
        "/api/goals/demo-arjun",
        json={"name": "Already done", "target_amount": 5000, "current_amount": 5000},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["on_track"] is True
    assert body["months_remaining"] == 0


def test_patch_updates_current_amount_and_recalculates():
    _cleanup_goals("demo-meera")
    r = client.post(
        "/api/goals/demo-meera",
        json={"name": "New laptop", "target_amount": 80000, "current_amount": 0},
    )
    goal_id = r.json()["goal"]["id"]

    r2 = client.patch(f"/api/goals/demo-meera/{goal_id}", json={"current_amount": 80000})
    assert r2.status_code == 200
    body = r2.json()
    assert body["goal"]["current_amount"] == 80000
    assert body["on_track"] is True
    assert body["months_remaining"] == 0


def test_delete_removes_goal():
    _cleanup_goals("demo-priya")
    r = client.post(
        "/api/goals/demo-priya",
        json={"name": "To delete", "target_amount": 1000},
    )
    goal_id = r.json()["goal"]["id"]

    r2 = client.delete(f"/api/goals/demo-priya/{goal_id}")
    assert r2.status_code == 200

    r3 = client.get("/api/goals/demo-priya")
    names = [g["goal"]["name"] for g in r3.json()]
    assert "To delete" not in names


def test_cross_user_ownership_check_returns_404_on_patch_and_delete():
    _cleanup_goals("demo-priya")
    r = client.post(
        "/api/goals/demo-priya",
        json={"name": "Priya's goal", "target_amount": 1000},
    )
    goal_id = r.json()["goal"]["id"]

    r2 = client.patch(f"/api/goals/demo-arjun/{goal_id}", json={"current_amount": 500})
    assert r2.status_code == 404

    r3 = client.delete(f"/api/goals/demo-arjun/{goal_id}")
    assert r3.status_code == 404

    # still exists, untouched, for the real owner
    r4 = client.get("/api/goals/demo-priya")
    match = next(g for g in r4.json() if g["goal"]["id"] == goal_id)
    assert match["goal"]["current_amount"] == 0


def test_patch_nonexistent_goal_returns_404():
    r = client.patch("/api/goals/demo-priya/not-a-real-goal-id", json={"current_amount": 1})
    assert r.status_code == 404
