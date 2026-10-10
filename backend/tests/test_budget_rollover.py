"""Tests for 5B BUDGET: Envelope Rollover, Budget Status, and Over-Budget Notifications.

Tests cover:
- Envelope surplus rollover formula across prior calendar months
- Rollover capping when rollover_cap is set
- Budget creation and PATCH endpoints (`PATCH /api/budgets/{user_id}/{budget_id}`)
- Total available computation (`monthly_limit + rollover_amount - spent_so_far`)
- Live over-budget and near-limit alerts in `GET /api/notifications/{user_id}`
- Cross-user authorization and security isolation
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.budgets_router import router as budgets_router
from app.api.notifications_router import router as notifications_router
from app.core.auth import resolve_user_id
from app.core import store
from app.models import BudgetRow, TransactionRow

USER_A = f"test-budget-user-a-{uuid.uuid4()}"
USER_B = f"test-budget-user-b-{uuid.uuid4()}"

app = FastAPI()
app.include_router(budgets_router, prefix="/api")
app.include_router(notifications_router)

current_user = USER_A
app.dependency_overrides[resolve_user_id] = lambda: current_user
client = TestClient(app)

TODAY = date.today()


def setup_module(_module):
    # Seed historical transactions for USER_A:
    # 1 month ago: spent 6,000 on dining (limit will be 10,000 -> surplus 4,000)
    # 2 months ago: spent 5,000 on dining (limit will be 10,000 -> surplus 5,000)
    # Current month: spent 3,000 on dining
    # Current month: spent 9,500 on shopping (limit 10,000 -> 95% near-limit warning)
    # Current month: spent 6,000 on utilities (limit 5,000 -> 120% critical over-budget alert)
    last_month = TODAY.replace(day=1) - timedelta(days=15)
    two_months_ago = TODAY.replace(day=1) - timedelta(days=45)

    txns = [
        # Prior months
        TransactionRow(user_id=USER_A, account_id="acc1", date=two_months_ago, amount=-5000.0, merchant="Old Swiggy", category="dining"),
        TransactionRow(user_id=USER_A, account_id="acc1", date=last_month, amount=-6000.0, merchant="Prev Swiggy", category="dining"),
        # Current month
        TransactionRow(user_id=USER_A, account_id="acc1", date=TODAY, amount=-3000.0, merchant="Swiggy Current", category="dining"),
        TransactionRow(user_id=USER_A, account_id="acc1", date=TODAY, amount=-9500.0, merchant="Amazon Shopping", category="shopping"),
        TransactionRow(user_id=USER_A, account_id="acc1", date=TODAY, amount=-6000.0, merchant="BESCOM Power", category="utilities"),
        TransactionRow(user_id=USER_A, account_id="acc1", date=TODAY, amount=-1800.0, merchant="Apollo Pharmacy", category="healthcare"),
        # User B transaction
        TransactionRow(user_id=USER_B, account_id="acc2", date=TODAY, amount=-1000.0, merchant="User B Txn", category="dining"),
    ]
    # User A budgets
    b_dining = BudgetRow(user_id=USER_A, category="dining", monthly_limit=10000.0, rollover_enabled=True, rollover_cap=6000.0)
    b_shopping = BudgetRow(user_id=USER_A, category="shopping", monthly_limit=10000.0, rollover_enabled=False)
    b_utilities = BudgetRow(user_id=USER_A, category="utilities", monthly_limit=5000.0, rollover_enabled=False)
    b_healthcare = BudgetRow(user_id=USER_A, category="healthcare", monthly_limit=2000.0, rollover_enabled=False)

    # User B budget
    b_user_b = BudgetRow(user_id=USER_B, category="dining", monthly_limit=8000.0, rollover_enabled=False)

    store.put(*txns, b_dining, b_shopping, b_utilities, b_healthcare, b_user_b)


# ---------------------------------------------------------------------------
# Budget Status & Rollover Calculation Tests
# ---------------------------------------------------------------------------


def test_budget_status_computes_rollover_and_cap():
    res = client.get(f"/api/budgets/{USER_A}/status")
    assert res.status_code == 200
    statuses = {s["category"]: s for s in res.json()}

    dining = statuses.get("dining")
    assert dining is not None
    assert dining["monthly_limit"] == 10000.0
    assert dining["rollover_enabled"] is True
    # Prior surplus = (10000-5000) + (10000-6000) = 5000 + 4000 = 9000, capped at 6000!
    assert dining["rollover_amount"] == 6000.0
    # Total available = 10000 (limit) + 6000 (rollover) - 3000 (spent) = 13000
    assert dining["total_available"] == 13000.0
    assert dining["status"] == "under"


def test_budget_status_without_rollover():
    res = client.get(f"/api/budgets/{USER_A}/status")
    assert res.status_code == 200
    statuses = {s["category"]: s for s in res.json()}

    shopping = statuses.get("shopping")
    assert shopping is not None
    assert shopping["monthly_limit"] == 10000.0
    assert shopping["rollover_enabled"] is False
    assert shopping["rollover_amount"] == 0.0
    assert shopping["spent_so_far"] == 9500.0
    assert shopping["percent_used"] == 95.0
    assert shopping["status"] == "near"


# ---------------------------------------------------------------------------
# Budget CRUD & PATCH Tests
# ---------------------------------------------------------------------------


def test_patch_budget_toggle_rollover_and_cap():
    # Get shopping budget ID
    res_list = client.get(f"/api/budgets/{USER_A}")
    assert res_list.status_code == 200
    shopping_b = next(b for b in res_list.json() if b["category"] == "shopping")

    patch_res = client.patch(
        f"/api/budgets/{USER_A}/{shopping_b['id']}",
        json={"rollover_enabled": True, "rollover_cap": 2500.0, "monthly_limit": 11000.0},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["rollover_enabled"] is True
    assert updated["rollover_cap"] == 2500.0
    assert updated["monthly_limit"] == 11000.0


def test_create_budget_with_rollover():
    res = client.post(
        f"/api/budgets/{USER_A}",
        json={
            "category": "entertainment",
            "monthly_limit": 4000.0,
            "rollover_enabled": True,
            "rollover_cap": 2000.0,
        },
    )
    assert res.status_code == 200
    item = res.json()
    assert item["category"] == "entertainment"
    assert item["monthly_limit"] == 4000.0
    assert item["rollover_enabled"] is True
    assert item["rollover_cap"] == 2000.0


# ---------------------------------------------------------------------------
# Live Over-Budget Notifications Tests
# ---------------------------------------------------------------------------


def test_notifications_include_over_budget_alerts():
    res = client.get(f"/api/notifications/{USER_A}")
    assert res.status_code == 200
    notifs = res.json()

    # Utilities is spent 6,000 of 5,000 -> critical over-budget alert
    over_budget_items = [n for n in notifs if n["type"] == "over_budget" and n["severity"] == "critical"]
    assert len(over_budget_items) >= 1
    assert any("Utilities" in n["text"] and n["source_ref"] == "/budgets" for n in over_budget_items)

    # Shopping was at 95% -> warning near_budget alert
    near_budget_items = [n for n in notifs if n["type"] == "over_budget" and n["severity"] == "warning"]
    assert len(near_budget_items) >= 1
    assert any(n["source_ref"] == "/budgets" for n in near_budget_items)


# ---------------------------------------------------------------------------
# Cross-User Security Isolation Tests
# ---------------------------------------------------------------------------


def test_cross_user_isolation_on_budget_patch():
    # User B's budget
    b = store.first(BudgetRow, user_id=USER_B)
    assert b is not None
    b_id = b.id

    # User A attempting to patch User B's budget must 404
    res = client.patch(
        f"/api/budgets/{USER_A}/{b_id}",
        json={"monthly_limit": 15000.0},
    )
    assert res.status_code == 404
