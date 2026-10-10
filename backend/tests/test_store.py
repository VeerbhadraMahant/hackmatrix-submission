from datetime import date

from app import models
from app.core import store


def test_round_trip_preserves_types():
    row = models.TransactionRow(user_id="store-u1", account_id="a", date=date(2026, 1, 5), amount=-12.5, merchant="Chai", category="food")
    store.put(row)
    got = store.get(models.TransactionRow, row.id)
    assert got == row and isinstance(got.date, date)


def test_query_first_delete_where_and_batching():
    rows = [
        models.TransactionRow(user_id="store-u2", account_id="a", date=date(2026, 1, 1), amount=-1.0, merchant=f"m{i}", category="food")
        for i in range(600)
    ]
    store.put(*rows)  # 600 > 500 exercises batch splitting
    assert len(store.query(models.TransactionRow, user_id="store-u2")) == 600
    assert store.first(models.TransactionRow, user_id="store-u2", merchant="m7").merchant == "m7"
    store.delete_where(models.TransactionRow, user_id="store-u2")
    assert store.first(models.TransactionRow, user_id="store-u2") is None
    assert store.get(models.TransactionRow, "missing") is None
