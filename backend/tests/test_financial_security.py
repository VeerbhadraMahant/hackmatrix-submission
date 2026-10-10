"""Financial security summary is built from real rows; the brief falls back to rules without NVIDIA."""
import pytest

from app.ingest.personas import PERSONA_CONFIGS, generate_persona
from app.models import AccountRow
from app.security import financial


@pytest.fixture()
def priya(monkeypatch):
    data = generate_persona(PERSONA_CONFIGS["demo-priya"])
    monkeypatch.setattr(financial.store, "query", lambda model, **_: data.accounts if model is AccountRow else data.transactions)
    return data


def test_build_scores_and_counts(priya):
    d = financial.build("demo-priya")
    assert d["transactions_checked"] == len(priya.transactions)
    assert 0 <= d["score"] <= 100 and d["grade"] in "ABCDE"
    assert len(d["pillars"]) == 6 and all(0 <= p["score"] <= 100 for p in d["pillars"])
    assert d["findings_total"] == sum(d["severity_counts"].values())
    assert d["flagged_transactions"] > 0 and d["top_findings"]


def test_brief_falls_back_to_rules(priya, monkeypatch):
    monkeypatch.setattr(financial, "get_settings", lambda: type("S", (), {"has_nvidia": False})())
    b = financial.brief(financial.build("demo-priya"))
    assert b["source"] == "rules" and b["actions"] and str(financial.build("demo-priya")["score"]) in b["headline"]
