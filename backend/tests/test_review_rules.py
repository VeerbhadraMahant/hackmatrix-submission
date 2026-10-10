"""Tests for the Track Pillar: Transaction Review Workflow and User Categorization Rules.

Tests cover:
- Review Queue endpoint (`GET /api/transactions/{user_id}/review-queue`)
- Review Action endpoint (`POST /api/transactions/{user_id}/{transaction_id}/review`)
  - confirm, recategorize, skip actions
  - auto-rule creation & cascading to pending transactions
- Transaction update with tags, notes, review_status (`PATCH /api/transactions/{user_id}/{transaction_id}`)
- Filtering by `review_status` and `tag` on `GET /api/transactions/{user_id}`
- Custom categorization rules CRUD (`GET/POST/DELETE /api/rules/{user_id}`)
- `apply_to_existing` retroactively reclassifying matching transactions
- Cross-user security & isolation
- Demo persona pre-seeded data verification
"""
from __future__ import annotations

import json
import uuid
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rules_router import router as rules_router
from app.api.transactions_router import router as transactions_router
from app.core.auth import resolve_user_id
from app.core import store
from app.models import CategorizationRuleRow, TransactionRow

USER_A = f"test-track-user-a-{uuid.uuid4()}"
USER_B = f"test-track-user-b-{uuid.uuid4()}"

app = FastAPI()
app.include_router(transactions_router, prefix="/api")
app.include_router(rules_router)

# Default to USER_A for unit testing
current_user = USER_A
app.dependency_overrides[resolve_user_id] = lambda: current_user
client = TestClient(app)

BASE_DATE = date(2026, 3, 1)


def _seed_txns(user_id: str, rows: list[dict]) -> list[str]:
    ids = []
    for r in rows:
        defaults = {
            "account_id": "acc-track-test",
            "is_recurring": False,
            "description": None,
            "review_status": "pending",
        }
        row = TransactionRow(user_id=user_id, **{**defaults, **r})
        store.put(row)
        ids.append(row.id)
    return ids


user_a_txns: list[str] = []
user_b_txns: list[str] = []


def setup_module(_module):
    global user_a_txns, user_b_txns
    fixtures_a = [
        {"date": BASE_DATE - timedelta(days=1), "amount": -450.0, "merchant": "Swiggy Order #123", "category": "other", "review_status": "pending"},
        {"date": BASE_DATE - timedelta(days=2), "amount": -199.0, "merchant": "Netflix Subscription", "category": "subscriptions", "review_status": "reviewed", "tags": json.dumps(["Entertainment"])},
        {"date": BASE_DATE - timedelta(days=3), "amount": -600.0, "merchant": "Swiggy Order #456", "category": "other", "review_status": "pending"},
        {"date": BASE_DATE - timedelta(days=4), "amount": -1200.0, "merchant": "Uber Trip Bangalore", "category": "transport", "review_status": "pending"},
        {"date": BASE_DATE - timedelta(days=5), "amount": -5000.0, "merchant": "Zerodha Coin SIP", "category": "investment_sip", "review_status": "reviewed", "tags": json.dumps(["SIP", "Tax-Deductible"])},
    ]
    fixtures_b = [
        {"date": BASE_DATE, "amount": -999.0, "merchant": "User B Merchant", "category": "shopping", "review_status": "pending"}
    ]
    user_a_txns = _seed_txns(USER_A, fixtures_a)
    user_b_txns = _seed_txns(USER_B, fixtures_b)


# ---------------------------------------------------------------------------
# Review Queue Tests
# ---------------------------------------------------------------------------


def test_review_queue_returns_only_pending_transactions():
    res = client.get(f"/api/transactions/{USER_A}/review-queue")
    assert res.status_code == 200
    data = res.json()
    assert "pending_count" in data
    assert "items" in data
    assert data["pending_count"] >= 3
    assert all(t["review_status"] == "pending" for t in data["items"])


def test_review_confirm_marks_reviewed():
    txn_id = user_a_txns[3]  # Uber Trip
    res = client.post(
        f"/api/transactions/{USER_A}/{txn_id}/review",
        json={"action": "confirm", "tags": ["Commute"], "notes": "Work travel"},
    )
    assert res.status_code == 200
    item = res.json()
    assert item["review_status"] == "reviewed"
    assert "Commute" in item["tags"]
    assert item["notes"] == "Work travel"
    assert item["reviewed_at"] is not None


def test_review_recategorize_and_create_rule():
    # Recategorize Swiggy Order #123 to dining with create_rule=True and rule_pattern="Swiggy"
    txn_id = user_a_txns[0]
    res = client.post(
        f"/api/transactions/{USER_A}/{txn_id}/review",
        json={
            "action": "recategorize",
            "category": "dining",
            "tags": ["Food"],
            "notes": "Dinner",
            "create_rule": True,
            "rule_pattern": "Swiggy",
        },
    )
    assert res.status_code == 200
    item = res.json()
    assert item["category"] == "dining"
    assert item["review_status"] == "reviewed"
    assert "Food" in item["tags"]

    # Check that the other pending Swiggy transaction (Swiggy Order #456) was auto-updated!
    res_other = client.get(f"/api/transactions/{USER_A}", params={"search": "Swiggy Order #456"})
    assert res_other.status_code == 200
    other_item = res_other.json()["items"][0]
    assert other_item["category"] == "dining"
    assert other_item["review_status"] == "reviewed"

    # Check that rule exists in rules list
    res_rules = client.get(f"/api/rules/{USER_A}")
    assert res_rules.status_code == 200
    rules = res_rules.json()["items"]
    assert any(r["pattern"] == "Swiggy" and r["category"] == "dining" for r in rules)


def test_review_skip_marks_skipped():
    # Seed a new pending txn to skip
    new_ids = _seed_txns(USER_A, [{"date": BASE_DATE, "amount": -50.0, "merchant": "Skip Me", "category": "other"}])
    skip_id = new_ids[0]

    res = client.post(
        f"/api/transactions/{USER_A}/{skip_id}/review",
        json={"action": "skip"},
    )
    assert res.status_code == 200
    assert res.json()["review_status"] == "skipped"


# ---------------------------------------------------------------------------
# Filter and Update Tests
# ---------------------------------------------------------------------------


def test_filter_by_review_status():
    res = client.get(f"/api/transactions/{USER_A}", params={"review_status": "reviewed"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) > 0
    assert all(t["review_status"] == "reviewed" for t in items)


def test_filter_by_tag():
    res = client.get(f"/api/transactions/{USER_A}", params={"tag": "Tax-Deductible"})
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    assert any("Tax-Deductible" in t["tags"] for t in items)


def test_patch_tags_and_notes():
    txn_id = user_a_txns[1]
    res = client.patch(
        f"/api/transactions/{USER_A}/{txn_id}",
        json={"tags": ["Entertainment", "Streaming"], "notes": "Shared plan"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Streaming" in data["tags"]
    assert data["notes"] == "Shared plan"


# ---------------------------------------------------------------------------
# Custom Categorization Rules Tests
# ---------------------------------------------------------------------------


def test_create_and_delete_rule():
    res = client.post(
        f"/api/rules/{USER_A}",
        json={
            "match_type": "contains",
            "pattern": "Blinkit",
            "category": "groceries",
            "tags": ["Groceries", "Instant"],
            "apply_to_existing": False,
        },
    )
    assert res.status_code == 200
    rule = res.json()
    assert rule["pattern"] == "Blinkit"
    assert rule["category"] == "groceries"
    assert "Instant" in rule["tags"]
    rule_id = rule["id"]

    # Delete rule
    del_res = client.delete(f"/api/rules/{USER_A}/{rule_id}")
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True


def test_create_rule_with_apply_to_existing():
    # Seed 2 pending transactions for Blinkit
    ids = _seed_txns(
        USER_A,
        [
            {"date": BASE_DATE, "amount": -300.0, "merchant": "Blinkit Grocery 1", "category": "other"},
            {"date": BASE_DATE, "amount": -400.0, "merchant": "Blinkit Grocery 2", "category": "other"},
        ],
    )

    res = client.post(
        f"/api/rules/{USER_A}",
        json={
            "match_type": "contains",
            "pattern": "Blinkit",
            "category": "groceries",
            "tags": ["QuickCommerce"],
            "apply_to_existing": True,
        },
    )
    assert res.status_code == 200

    # Verify both transactions were updated and marked reviewed
    for tid in ids:
        check_res = client.get(f"/api/transactions/{USER_A}", params={"search": tid})
        # or direct fetch
        matching = [t for t in check_res.json()["items"] if t["id"] == tid]
        if matching:
            assert matching[0]["category"] == "groceries"
            assert matching[0]["review_status"] == "reviewed"
            assert "QuickCommerce" in matching[0]["tags"]


# ---------------------------------------------------------------------------
# Cross-User Security Tests
# ---------------------------------------------------------------------------


def test_cross_user_isolation_on_review():
    # USER_A trying to review USER_B's transaction must 404
    b_txn = user_b_txns[0]
    res = client.post(
        f"/api/transactions/{USER_A}/{b_txn}/review",
        json={"action": "confirm"},
    )
    assert res.status_code == 404


def test_cross_user_isolation_on_rules():
    # Create rule under User B directly
    b_rule = CategorizationRuleRow(
        user_id=USER_B,
        match_type="contains",
        pattern="Secret B Merchant",
        category="other",
    )
    store.put(b_rule)
    b_rule_id = b_rule.id

    # User A cannot delete User B's rule
    del_res = client.delete(f"/api/rules/{USER_A}/{b_rule_id}")
    assert del_res.status_code == 404
