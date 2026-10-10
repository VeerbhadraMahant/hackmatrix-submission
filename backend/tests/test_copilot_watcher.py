"""Copilot watcher: pure rule tests on in-memory rows + one HTTP round trip."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.copilot.watcher import _review_one
from app.main import app
from app.ingest.seed import seed_all
from app.models import TransactionRow

TODAY = date.today()


def _t(amount, merchant="Cafe", category="dining", days_ago=0, **kw):
    return TransactionRow(user_id="u", account_id="a", date=TODAY - timedelta(days=days_ago),
                          amount=amount, merchant=merchant, category=category, **kw)


def _hist():
    # 8 small dining spends on distinct merchants + monthly rent as the essential buffer
    rows = [_t(-300, f"Place {i}", days_ago=40 + i * 5) for i in range(8)]
    rows += [_t(-20000, "Landlord", "rent_housing", days_ago=d) for d in (10,)]
    return rows


def test_large_spend_is_warning():
    i = _review_one(_t(-9000, "Fancy Bistro"), _hist(), liquid=50_000, new_gap=False)
    assert i.severity == "warning" and "₹9,000" in i.title and i.action.href == "/transactions"


def test_buffer_breach_is_critical():
    i = _review_one(_t(-9000, "Fancy Bistro"), _hist(), liquid=25_000, new_gap=False)
    assert i.severity == "critical" and i.action.href == "/simulate"


def test_new_gap_is_critical():
    assert _review_one(_t(-100), _hist(), 500_000, new_gap=True).severity == "critical"


def test_duplicate_is_warning():
    h = _hist() + [_t(-450, "Cafe Mocha", days_ago=2)]
    i = _review_one(_t(-450, "Cafe Mocha"), h, 500_000, False)
    assert i.severity == "warning" and "duplicate" in i.title.lower()


def test_income_is_positive():
    i = _review_one(_t(50000, "Employer", "income"), _hist(), 500_000, False)
    assert i.severity == "positive" and "₹50,000" in i.title and "savings rate" in i.body


def test_small_known_spend_is_info():
    h = _hist() + [_t(-250, "Cafe", days_ago=20)]
    i = _review_one(_t(-250, "Cafe", days_ago=0), h, 500_000, False)
    assert i.severity == "info" and i.action.href == "/copilot" and len(i.title) <= 60


def test_http_large_dining_event_surfaces_insight():
    seed_all()
    c = TestClient(app)
    r = c.post("/api/events/demo-meera", json={"kind": "transaction", "amount": -45000, "merchant": "Taj Fine Dining", "category": "dining"})
    assert r.status_code == 200, r.text
    ins = r.json()["insights"]
    assert len(ins) == 1 and ins[0]["severity"] in ("warning", "critical")
    feed = c.get("/api/copilot/insights/demo-meera").json()
    assert ins[0]["id"] in [f["id"] for f in feed]
    assert c.get("/api/copilot/insights/demo-meera", params={"since": "2999-01-01T00:00:00Z"}).json() == []
