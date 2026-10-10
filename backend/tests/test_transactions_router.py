"""Tests for app.api.transactions_router (ledger list/filter/search/paginate
+ manual recategorization). Uses hand-built TransactionRow fixtures under
dedicated synthetic user_ids for full isolation from the seeded demo
personas and other test modules.

Auth itself is covered by test_auth.py; here we override the
`resolve_user_id` dependency to a fixed trusted user_id so these tests
exercise the router's query/authorization logic directly.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.transactions_router import router as transactions_router
from app.core.auth import resolve_user_id
from app.core import store
from app.models import TransactionRow

USER_A = f"test-ledger-user-a-{uuid.uuid4()}"
USER_B = f"test-ledger-user-b-{uuid.uuid4()}"

app = FastAPI()
app.include_router(transactions_router, prefix="/api")
app.dependency_overrides[resolve_user_id] = lambda: USER_A
client = TestClient(app)


def _seed(user_id: str, rows: list[dict]) -> list[str]:
    ids = []
    for r in rows:
        defaults = {"account_id": "acc-test", "is_recurring": False, "description": None}
        row = TransactionRow(user_id=user_id, **{**defaults, **r})
        store.put(row)
        ids.append(row.id)
    return ids


BASE_DATE = date(2026, 1, 1)

FIXTURE_ROWS = [
    {"date": BASE_DATE - timedelta(days=i), "amount": -100.0 - i, "merchant": m, "category": c, "description": d}
    for i, (m, c, d) in enumerate(
        [
            ("Swiggy Bangalore", "dining", "food delivery"),
            ("Amazon Retail", "shopping", "electronics"),
            ("Netflix", "subscriptions", None),
            ("BESCOM Electricity", "utilities", None),
            ("Swiggy Instamart", "groceries", "grocery run"),
            ("Uber Trip", "transport", None),
            ("Big Bazaar", "groceries", None),
            ("Spotify", "subscriptions", None),
            ("Zomato Order", "dining", "late night snack"),
            ("Ola Cabs", "transport", None),
            ("Amazon Prime", "subscriptions", None),
            ("Reliance Fresh", "groceries", None),
        ]
    )
]

seeded_ids: list[str] = []


def setup_module(_module):
    global seeded_ids
    seeded_ids = _seed(USER_A, FIXTURE_ROWS)
    # A distinct row for USER_B to verify cross-user isolation on PATCH.
    other_ids = _seed(USER_B, [{"date": BASE_DATE, "amount": -50.0, "merchant": "Other User Txn", "category": "other", "description": None}])
    global OTHER_USER_TXN_ID
    OTHER_USER_TXN_ID = other_ids[0]


# ---------------------------------------------------------------------------
# GET /api/transactions/{user_id}
# ---------------------------------------------------------------------------


def test_pagination_returns_different_rows_across_pages():
    r1 = client.get(f"/api/transactions/{USER_A}", params={"page": 1, "page_size": 5})
    r2 = client.get(f"/api/transactions/{USER_A}", params={"page": 2, "page_size": 5})
    assert r1.status_code == 200 and r2.status_code == 200
    ids1 = {t["id"] for t in r1.json()["items"]}
    ids2 = {t["id"] for t in r2.json()["items"]}
    assert ids1.isdisjoint(ids2)
    assert r1.json()["total"] >= len(FIXTURE_ROWS)


def test_pagination_caps_page_size_at_200():
    r = client.get(f"/api/transactions/{USER_A}", params={"page_size": 5000})
    assert r.status_code == 200
    assert r.json()["page_size"] == 200


def test_category_filter_returns_only_matching_rows():
    r = client.get(f"/api/transactions/{USER_A}", params={"category": "groceries", "page_size": 100})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    assert all(t["category"] == "groceries" for t in items)


def test_merchant_search_is_case_insensitive_substring():
    r = client.get(f"/api/transactions/{USER_A}", params={"merchant": "swiggy", "page_size": 100})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    assert all("swiggy" in t["merchant"].lower() for t in items)


def test_search_matches_merchant_or_description():
    r = client.get(f"/api/transactions/{USER_A}", params={"search": "grocery run", "page_size": 100})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(t["merchant"] == "Swiggy Instamart" for t in items)


def test_date_range_filtering():
    date_from = (BASE_DATE - timedelta(days=3)).isoformat()
    date_to = BASE_DATE.isoformat()
    r = client.get(
        f"/api/transactions/{USER_A}",
        params={"date_from": date_from, "date_to": date_to, "page_size": 100},
    )
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    for t in items:
        assert date_from <= t["date"] <= date_to


def test_results_ordered_by_date_descending():
    r = client.get(f"/api/transactions/{USER_A}", params={"page_size": 100})
    dates = [t["date"] for t in r.json()["items"]]
    assert dates == sorted(dates, reverse=True)


# ---------------------------------------------------------------------------
# PATCH /api/transactions/{user_id}/{transaction_id}
# ---------------------------------------------------------------------------


def test_patch_updates_category_and_persists():
    txn_id = seeded_ids[0]
    r = client.patch(f"/api/transactions/{USER_A}/{txn_id}", json={"category": "entertainment"})
    assert r.status_code == 200
    assert r.json()["category"] == "entertainment"

    # Follow-up GET confirms persistence.
    r2 = client.get(f"/api/transactions/{USER_A}", params={"category": "entertainment", "page_size": 100})
    assert any(t["id"] == txn_id for t in r2.json()["items"])


def test_patch_updates_merchant():
    txn_id = seeded_ids[1]
    r = client.patch(f"/api/transactions/{USER_A}/{txn_id}", json={"merchant": "Renamed Merchant"})
    assert r.status_code == 200
    assert r.json()["merchant"] == "Renamed Merchant"


def test_patch_on_someone_elses_transaction_returns_404():
    r = client.patch(f"/api/transactions/{USER_A}/{OTHER_USER_TXN_ID}", json={"category": "other"})
    assert r.status_code == 404


def test_patch_on_nonexistent_id_returns_404():
    r = client.patch(f"/api/transactions/{USER_A}/does-not-exist", json={"category": "other"})
    assert r.status_code == 404


def test_invalid_category_filter_rejected():
    r = client.get(f"/api/transactions/{USER_A}", params={"category": "not_a_real_category"})
    assert r.status_code == 400
