"""Tests for app.api.budgets_router (budget CRUD, spend-vs-limit status,
safe-to-spend). Uses hand-built TransactionRow/BudgetRow fixtures under a
dedicated synthetic user_id, all dated relative to `date.today()` so the
"this calendar month" logic is exercised regardless of when the suite runs.

Auth itself is covered by test_auth.py; here we override the
`resolve_user_id` dependency to a fixed trusted user_id so these tests
exercise the router's business logic directly.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.budgets_router import router as budgets_router
from app.core.auth import resolve_user_id
from app.core import store
from app.models import TransactionRow

USER = f"test-budget-user-{uuid.uuid4()}"
OTHER_USER = f"test-budget-user-other-{uuid.uuid4()}"

app = FastAPI()
app.include_router(budgets_router, prefix="/api")
app.dependency_overrides[resolve_user_id] = lambda: USER
client = TestClient(app)

TODAY = datetime.now(timezone.utc).date()  # app code uses UTC dates


def _add_txn(user_id: str, *, days_ago: int, amount: float, merchant: str, category: str, is_recurring: bool = False):
    store.put(
        TransactionRow(
            user_id=user_id,
            account_id="acc-test",
            date=TODAY - timedelta(days=days_ago),
            amount=amount,
            merchant=merchant,
            category=category,
            is_recurring=is_recurring,
        )
    )


def setup_module(_module):
    # A recurring monthly salary (income) so `safe-to-spend` has a nonzero
    # income basis, and a recurring monthly rent obligation so the
    # "committed recurring" term is nonzero too.
    for i in (60, 30, 0):
        _add_txn(USER, days_ago=i, amount=60000.0, merchant="Employer Salary", category="income", is_recurring=True)
        _add_txn(USER, days_ago=i, amount=-10000.0, merchant="Monthly Rent", category="rent_housing", is_recurring=True)

    # Groceries spend THIS month only (for budget-status tests).
    _add_txn(USER, days_ago=1, amount=-2000.0, merchant="Reliance Fresh", category="groceries")
    # Some dining spend from LAST month (must not count toward this month).
    _add_txn(USER, days_ago=45, amount=-9000.0, merchant="Fancy Restaurant", category="dining")


# ---------------------------------------------------------------------------
# Budget CRUD
# ---------------------------------------------------------------------------


def test_create_budget_then_status_reflects_real_spend():
    r = client.post(f"/api/budgets/{USER}", json={"category": "groceries", "monthly_limit": 5000.0})
    assert r.status_code == 200
    budget = r.json()
    assert budget["category"] == "groceries"
    assert budget["monthly_limit"] == 5000.0

    r2 = client.get(f"/api/budgets/{USER}/status")
    assert r2.status_code == 200
    groceries = next(b for b in r2.json() if b["category"] == "groceries")
    assert groceries["spent_so_far"] == 2000.0
    assert groceries["remaining"] == 3000.0
    assert groceries["status"] == "under"


def test_upsert_updates_existing_budget_for_same_category():
    r = client.post(f"/api/budgets/{USER}", json={"category": "groceries", "monthly_limit": 8000.0})
    assert r.status_code == 200
    r2 = client.get(f"/api/budgets/{USER}")
    groceries_budgets = [b for b in r2.json() if b["category"] == "groceries"]
    assert len(groceries_budgets) == 1
    assert groceries_budgets[0]["monthly_limit"] == 8000.0


def test_category_with_no_transactions_this_month_shows_zero_spent():
    client.post(f"/api/budgets/{USER}", json={"category": "entertainment", "monthly_limit": 3000.0})
    r = client.get(f"/api/budgets/{USER}/status")
    entertainment = next(b for b in r.json() if b["category"] == "entertainment")
    assert entertainment["spent_so_far"] == 0.0
    assert entertainment["status"] == "under"


def test_dining_spend_from_last_month_not_counted_this_month():
    client.post(f"/api/budgets/{USER}", json={"category": "dining", "monthly_limit": 5000.0})
    r = client.get(f"/api/budgets/{USER}/status")
    dining = next(b for b in r.json() if b["category"] == "dining")
    assert dining["spent_so_far"] == 0.0


def test_status_buckets_near_and_over_thresholds():
    client.post(f"/api/budgets/{USER}", json={"category": "utilities", "monthly_limit": 1000.0})
    _add_txn(USER, days_ago=1, amount=-850.0, merchant="BESCOM", category="utilities")  # 85% -> near
    r = client.get(f"/api/budgets/{USER}/status")
    utilities = next(b for b in r.json() if b["category"] == "utilities")
    assert utilities["status"] == "near"

    _add_txn(USER, days_ago=1, amount=-300.0, merchant="BESCOM", category="utilities")  # 115% -> over
    r2 = client.get(f"/api/budgets/{USER}/status")
    utilities2 = next(b for b in r2.json() if b["category"] == "utilities")
    assert utilities2["status"] == "over"


def test_delete_budget_removes_it_from_list():
    r = client.post(f"/api/budgets/{USER}", json={"category": "transport", "monthly_limit": 2000.0})
    budget_id = r.json()["id"]

    r2 = client.delete(f"/api/budgets/{USER}/{budget_id}")
    assert r2.status_code == 200

    r3 = client.get(f"/api/budgets/{USER}")
    assert all(b["id"] != budget_id for b in r3.json())


def test_delete_someone_elses_budget_returns_404():
    from app.models import BudgetRow

    row = BudgetRow(user_id=OTHER_USER, category="shopping", monthly_limit=1000.0)
    store.put(row)
    other_budget_id = row.id

    r = client.delete(f"/api/budgets/{USER}/{other_budget_id}")
    assert r.status_code == 404


def test_delete_nonexistent_budget_returns_404():
    r = client.delete(f"/api/budgets/{USER}/does-not-exist")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Safe to spend
# ---------------------------------------------------------------------------


def test_safe_to_spend_is_non_negative():
    r = client.get(f"/api/budgets/{USER}/safe-to-spend")
    assert r.status_code == 200
    body = r.json()
    assert body["amount"] >= 0.0
    assert body["as_of_date"] == TODAY.isoformat()
    assert body["basis"]


def test_safe_to_spend_changes_after_large_transaction_this_month():
    before = client.get(f"/api/budgets/{USER}/safe-to-spend").json()["amount"]

    _add_txn(USER, days_ago=0, amount=-20000.0, merchant="Big One-Off Purchase", category="shopping")

    after = client.get(f"/api/budgets/{USER}/safe-to-spend").json()["amount"]
    assert after != before
    assert after >= 0.0
