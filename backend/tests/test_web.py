import types

import pytest

from app import web
from app.copilot import nvidia
from app.web import firecrawl, gate


class R:
    def __init__(self, code=200, js=None):
        self.status_code, self._js = code, js or {}

    def json(self):
        return self._js


def item(url, n=300):
    return {"url": url, "title": url, "markdown": "word " * n}


def boom(*a, **k):
    raise AssertionError("network called")


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    firecrawl._cache.clear()
    firecrawl._calls.clear()
    monkeypatch.setattr(firecrawl, "get_settings", lambda: types.SimpleNamespace(has_firecrawl=True, firecrawl_api_key="k"))
    monkeypatch.setattr(web, "get_settings", lambda: types.SimpleNamespace(has_firecrawl=True))
    monkeypatch.setattr(firecrawl.httpx, "post", boom)
    monkeypatch.setattr(nvidia, "chat", boom)


@pytest.mark.parametrize("m", ["hi", "who are you?", "how much did I spend on food", "what is my balance"])
def test_no_search(m):
    p, src = web.gather_with_plan(m)
    assert not p.search and src == []


def test_schemes_search_and_lenient_json(monkeypatch):
    monkeypatch.setattr(nvidia, "chat", lambda m, h, s: 'sure!\n```json\n{"search": true, "query": "farmer schemes India 2026"}\n```')
    p = gate.plan("which govt schemes for farmers")
    assert p.search and p.query == "farmer schemes India 2026"


def test_gate_fallback():
    # nvidia.chat raises (boom): a lone trigger still searches unless it is about the user's own data
    assert gate.plan("which govt schemes for farmers").search
    assert not gate.plan("how much did I spend on my sip").search
    assert gate.plan("compare latest sip vs ppf").search


def test_cache_official_first_and_errors(monkeypatch):
    calls = []

    def post(*a, **k):
        calls.append(1)
        return R(js={"data": {"web": [item("https://blog.com/a"), item("https://x.com/short", 2), item("https://www.rbi.org.in/p")]}})

    monkeypatch.setattr(firecrawl.httpx, "post", post)
    out = firecrawl.search_and_scrape("Repo Rate")
    assert [w.url for w in out] == ["https://www.rbi.org.in/p", "https://blog.com/a"]
    assert len(out[0].content) <= 2500
    firecrawl.search_and_scrape("repo  rate")
    assert len(calls) == 1
    monkeypatch.setattr(firecrawl.httpx, "post", lambda *a, **k: R(500))
    assert firecrawl.search_and_scrape("other") == []


def test_missing_key(monkeypatch):
    monkeypatch.setattr(firecrawl, "get_settings", lambda: types.SimpleNamespace(has_firecrawl=False, firecrawl_api_key=""))
    assert firecrawl.search_and_scrape("q") == []


def test_rate_guard(monkeypatch):
    monkeypatch.setattr(firecrawl.httpx, "post", lambda *a, **k: R(js={"data": []}))
    for i in range(20):
        firecrawl.search_and_scrape(f"q{i}")
    monkeypatch.setattr(firecrawl.httpx, "post", boom)
    assert firecrawl.search_and_scrape("q99") == []
