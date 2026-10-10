"""Tests for app.api.networth_router -- isolated FastAPI app (see
test_goals_router.py docstring for why this doesn't import app.main.app).
"""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.networth_router import router
from app.core.auth import resolve_user_id
from app.core import store
from app.ingest.seed import seed_all
from app.models import AccountRow, TransactionRow

seed_all()

app = FastAPI()
app.include_router(router)
# Auth (resolve_user_id) is exhaustively covered in test_auth.py; here we
# only exercise the net-worth reconstruction logic, including against
# synthetic non-demo user ids that would otherwise 401 without a real
# Firebase token, so the dependency is overridden to trust the path param.
app.dependency_overrides[resolve_user_id] = lambda user_id: user_id
client = TestClient(app)


def test_history_has_requested_number_of_points():
    r = client.get("/api/networth/demo-priya/history?days=30")
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 30


def test_history_most_recent_point_matches_current_balance():
    r = client.get("/api/networth/demo-arjun/history?days=60")
    assert r.status_code == 200
    body = r.json()
    points = sorted(body["points"], key=lambda p: p["date"])
    most_recent = points[-1]
    assert most_recent["date"] == date.today().isoformat()
    assert abs(most_recent["net_worth"] - body["current"]) < 0.01


def test_history_caps_at_max_days():
    r = client.get("/api/networth/demo-priya/history?days=5000")
    assert r.status_code == 422  # ge/le validation on the query param


def test_accounts_endpoint_lists_real_accounts():
    r = client.get("/api/accounts/demo-priya")
    assert r.status_code == 200
    accounts = r.json()
    assert len(accounts) >= 1
    assert all(a["user_id"] == "demo-priya" for a in accounts)


def test_unknown_user_returns_empty_history_not_error():
    r = client.get("/api/networth/totally-unknown-user-id/history")
    assert r.status_code == 200
    body = r.json()
    assert body["points"] == []
    assert body["current"] == 0.0


# ---------------------------------------------------------------------------
# Synthetic, hand-built scenario: proves the reconstruction math exactly,
# not just "doesn't crash".
# ---------------------------------------------------------------------------

_SYNTH_USER = "test-networth-synthetic-user"


def _reset_synth_user() -> None:
    store.delete_where(TransactionRow, user_id=_SYNTH_USER)
    store.delete_where(AccountRow, user_id=_SYNTH_USER)


def test_synthetic_two_account_reconstruction_is_exact():
    """Two accounts with known transactions, by hand:

    Account A (checking): current balance = 1000.
      - today:    +200
      - today-1:  -100

    Account B (savings): current balance = 500, no transactions at all
      -> flat 500 every day in the window (documented no-history rule).

    Window: days=3 -> today, today-1, today-2.

    Reconstructing A by walking backward from 1000 (balance(d) = current -
    sum of txns with date > d):
      today:   1000                       (no txns dated > today)
      today-1: 1000 - 200 = 800            (undo today's +200)
      today-2: excluded -- today-2 is BEFORE A's earliest transaction
                (today-1), and the documented rule is to exclude an account
                from a day's total rather than extrapolate before its first
                known transaction.

    So the expected total net worth per day is:
      today:   1000 + 500 = 1500
      today-1: 800  + 500 = 1300
      today-2: (A excluded) 500 only
    """
    _reset_synth_user()
    today = date.today()
    acct_a = AccountRow(user_id=_SYNTH_USER, name="Checking", type="checking", balance=1000.0)
    acct_b = AccountRow(user_id=_SYNTH_USER, name="Savings", type="savings", balance=500.0)
    store.put(
        acct_a,
        acct_b,
        TransactionRow(
            user_id=_SYNTH_USER, account_id=acct_a.id, date=today, amount=200.0,
            merchant="Deposit", category="income",
        ),
        TransactionRow(
            user_id=_SYNTH_USER, account_id=acct_a.id, date=today - timedelta(days=1), amount=-100.0,
            merchant="Purchase", category="shopping",
        ),
    )

    r = client.get(f"/api/networth/{_SYNTH_USER}/history?days=3")
    assert r.status_code == 200
    body = r.json()
    by_date = {p["date"]: p["net_worth"] for p in body["points"]}

    expected = {
        today.isoformat(): 1500.0,
        (today - timedelta(days=1)).isoformat(): 1300.0,
        (today - timedelta(days=2)).isoformat(): 500.0,
    }
    assert by_date == expected
    assert body["current"] == 1500.0

    _reset_synth_user()
