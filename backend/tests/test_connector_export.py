"""Connector exports are CSV (Excel-friendly), not JSON."""
import csv
import io

from app.api.connectors_router import _dataset, _to_csv


def test_multi_table_csv_has_titled_sections():
    text = _to_csv(_dataset("bank"))
    assert text.startswith("Accounts\r\nname,type,balance") and "\r\n\r\nLoans\r\n" in text


def test_single_table_csv_is_plain():
    rows = list(csv.reader(io.StringIO(_to_csv({"transactions": [{"id": "a", "tags": ["x"], "amount": -5.0}]}))))
    assert rows == [["id", "tags", "amount"], ["a", '["x"]', "-5.0"]]


def test_demo_persona_sheet_link_keeps_fixture_and_unlinks_cleanly(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api import connectors_router as cr
    from app.ingest.seed import seed_all
    from app.main import app
    from app.core import store
    from app.models import TransactionRow

    seed_all()
    csv_bytes = b"date,amount,merchant,category\n2026-10-01,-100,Chai Point,dining\n2026-10-02,5000,Salary,income\n"
    resp = type("R", (), {"content": csv_bytes, "headers": {"content-type": "text/csv"}, "raise_for_status": lambda self: None})()
    monkeypatch.setattr(cr.httpx, "get", lambda *a, **k: resp)
    c = TestClient(app)
    base = len(store.query(TransactionRow, user_id="demo-priya"))
    url = "https://docs.google.com/spreadsheets/d/abc123/edit"
    try:
        r = c.post("/api/connectors/demo-priya/google_sheets/connect", json={"url": url})
        assert r.status_code == 200 and r.json()["transactions"] == 2
        assert len(store.query(TransactionRow, user_id="demo-priya")) == base + 2
    finally:
        assert c.delete("/api/connectors/demo-priya/google_sheets").status_code == 204
    assert len(store.query(TransactionRow, user_id="demo-priya")) == base


def test_notification_ids_are_unique():
    from fastapi.testclient import TestClient

    from app.ingest.seed import seed_all
    from app.main import app

    seed_all()
    c = TestClient(app)
    for uid in ("demo-priya", "demo-arjun", "demo-meera"):
        ids = [n["id"] for n in c.get(f"/api/notifications/{uid}").json()]
        assert ids and len(ids) == len(set(ids)), uid
