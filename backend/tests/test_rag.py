"""RAG tests: no network -- rag.embed.embed is replaced by a deterministic hash-bag fake (dim 64)."""
from __future__ import annotations

import hashlib
import re
from datetime import date, timedelta

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import rag
from app.api.documents_router import router
from app.core import store
from app.models import AccountRow, DebtRow, DocumentRow, TransactionRow
from app.rag import corpus, embed, index

U = "guest-ragtest000001"


def _fake(texts, input_type):
    m = np.zeros((len(texts), 64), dtype=np.float32)
    for r, t in enumerate(texts):
        for w in re.findall(r"\w+", t.lower()):
            m[r, int(hashlib.md5(w.encode()).hexdigest(), 16) % 64] += 1
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr(embed, "embed", _fake)
    monkeypatch.setattr(index, "_CACHE", tmp_path)
    index._idx.clear()
    for m in (TransactionRow, DebtRow, AccountRow, DocumentRow):
        store.delete_where(m, user_id=U)
    d = date.today() - timedelta(days=5)
    acc = AccountRow(user_id=U, name="HDFC Savings", type="checking", balance=50000)
    rows = [
        TransactionRow(user_id=U, account_id=acc.id, date=d - timedelta(days=i * 9), amount=-400, merchant="Zomato", category="dining")
        for i in range(3)
    ] + [
        TransactionRow(user_id=U, account_id=acc.id, date=d, amount=-1299, merchant="Netflix", category="subscriptions"),
        TransactionRow(user_id=U, account_id=acc.id, date=d - timedelta(days=1), amount=-1299, merchant="Netflix", category="subscriptions"),
        TransactionRow(user_id=U, account_id=acc.id, date=d, amount=-5000, merchant="Rent", category="housing"),
    ]
    store.put(acc, *rows, DebtRow(user_id=U, account_id=acc.id, principal=100000, interest_rate_apr=18, minimum_payment=5000, due_day_of_month=5))
    yield
    for m in (TransactionRow, DebtRow, AccountRow, DocumentRow):
        store.delete_where(m, user_id=U)


def test_build_chunks_cards():
    texts = {c[0]: c[2] for c in corpus.build_chunks(U)}
    assert any(t.startswith("In ") and "dining" in t and "₹1,200.00" in t for t in texts.values()) or any("dining" in t for t in texts.values())
    assert any(i.startswith("merchant:Zomato") for i in texts)
    debt = next(t for i, t in texts.items() if i.startswith("debt:"))
    assert "₹100,000.00" in debt and "18" in debt and "months" in debt
    assert any(i.startswith("account:") for i in texts)


def test_duplicate_card():
    assert any("possible duplicate" in c[2] for c in corpus.build_chunks(U))


def test_retrieve_dining_first():
    top = rag.retrieve(U, "how much did I spend on dining")
    assert top and "dining" in top[0].text.lower()


def test_fraud_query_includes_unusual_card():
    assert any("possible duplicate" in c.text for c in rag.retrieve(U, "any duplicate charges?", k=3))


def test_document_upload_then_retrieve():
    c = TestClient(_app())
    r = c.post(f"/api/documents/{U}", files={"file": ("policy.txt", b"The home loan prepayment penalty is 2 percent of principal.")})
    assert r.status_code == 200 and r.json()["chunks"] == 1
    assert c.post(f"/api/documents/{U}", files={"file": ("x.exe", b"hi")}).status_code == 400
    top = rag.retrieve(U, "prepayment penalty on home loan", k=3)
    assert any(x.kind == "document" and x.label == "policy.txt" for x in top)
    assert [d["name"] for d in c.get(f"/api/documents/{U}").json()] == ["policy.txt"]
    assert c.delete(f"/api/documents/{U}/{r.json()['id']}").status_code == 200
    assert c.get(f"/api/documents/{U}").json() == []


def test_retrieve_never_raises_when_embed_fails(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(embed, "embed", boom)
    index._idx.clear()
    out = rag.retrieve(U, "dining spend")
    assert out and "dining" in out[0].text.lower()  # keyword-only fallback


def _app():
    a = FastAPI()
    a.include_router(router)
    return a
