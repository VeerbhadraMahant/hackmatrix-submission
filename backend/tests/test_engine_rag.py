"""Engine wiring for RAG, web and next_steps. No network: rag, web and NVIDIA are faked."""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from app import rag, web
from app.copilot import engine, nugen, nvidia, offline_router


class _S:
    has_nvidia = True
    has_nugen = False
    nvidia_chat_api_key = "x"


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(engine, "get_settings", lambda: _S())
    monkeypatch.setattr(nugen, "_context", lambda uid: {"summary": {"income": 94431}})
    calls = SimpleNamespace(json_prompts=[], chat_systems=[], rag=0, web=0)
    monkeypatch.setattr(rag, "retrieve", lambda u, q, k=8: (setattr(calls, "rag", calls.rag + 1), [rag.Chunk("1", "debt", "Credit card owes ₹40,000", 1.0, "Debts")])[1])
    src = web.WebSource(title="Gov", url="https://gov.in/x", content="Limit is ₹1.5 lakh")

    def gwp(msg, history=None):
        calls.web += 1
        return web.WebPlan(search=True, query="q", reason="r"), [src]

    monkeypatch.setattr(web, "gather_with_plan", gwp)

    def cj(system, user):
        calls.json_prompts.append(user)
        return {"narrative": "ok", "next_steps": [{"title": "Move ₹10,000 to savings", "why": "Tax date near", "when": "before 15 Dec", "link": "/tax"}]}

    monkeypatch.setattr(nvidia, "complete_json", cj)
    monkeypatch.setattr(nvidia, "chat", lambda m, t, s: (calls.chat_systems.append(s), "Hi!")[1])
    return calls


def test_money_prompt_grounded_and_mapped(fakes):
    r = engine.answer("u", "How much ₹ tax can I save under 80C?")
    p = fakes.json_prompts[0]
    assert "Credit card owes ₹40,000" in p and "[1] Gov (https://gov.in/x)" in p
    assert r.next_steps[0].title.startswith("Move") and r.next_steps[0].link == "/tax"
    assert [(s.title, s.url) for s in r.sources] == [("Gov", "https://gov.in/x")]


def test_small_talk_has_no_next_steps(fakes):
    r = engine.answer("u", "hello there")
    assert r.next_steps == [] and "owes ₹40,000" not in fakes.chat_systems[0]


def test_fast_path_parses_next_step(fakes, monkeypatch):
    monkeypatch.setattr(nvidia, "chat", lambda m, t, s: "You spend a lot.\n\nNext step: Cancel unused subscriptions")
    r = engine.answer("u", "how is my spending", model="fast")
    assert r.next_steps[0].title == "Cancel unused subscriptions"


def test_web_exception_does_not_break(fakes, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(web, "gather_with_plan", boom)
    r = engine.answer("u", "what is my budget")
    assert r.narrative == "ok" and r.sources == []


def test_web_timeout_and_gap(fakes, monkeypatch):
    monkeypatch.setattr(web, "gather_with_plan", lambda m, h=None: (web.WebPlan(search=True, query="q", reason="r"), []))
    r = engine.answer("u", "what is my budget")
    assert any("Live web search was not available" in g.text for g in r.data_gaps)


def test_offline_calls_neither(fakes, monkeypatch):
    monkeypatch.setattr(offline_router, "route", lambda u, m: engine.AnswerContract(query=m))
    engine.answer("u", "my budget", force_offline=True)
    assert fakes.rag == 0 and fakes.web == 0
