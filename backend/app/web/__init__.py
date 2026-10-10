"""Gated live web search (Firecrawl). Layer 1 regex + layer 2 cheap LLM gate decide; Firecrawl is only called when needed."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import get_settings

log = logging.getLogger("finpilot.web")


@dataclass
class WebSource:
    title: str
    url: str
    content: str  # cleaned markdown excerpt, <= ~2500 chars


from app.web import firecrawl, gate  # noqa: E402
from app.web.gate import WebPlan  # noqa: E402,F401


def gather_with_plan(message: str, history: list[tuple[str, str]] | None = None) -> tuple[WebPlan, list[WebSource]]:
    """Returns (plan, sources); engine can show 'Searched the web for: <plan.query>'. Never raises."""
    try:
        p = gate.plan(message, history)
        log.info("web gate: search=%s query=%r reason=%s", p.search, p.query, p.reason)
        if not p.search or not get_settings().has_firecrawl:
            return p, []
        return p, firecrawl.search_and_scrape(p.query)
    except Exception as e:  # noqa: BLE001
        log.warning("web gather failed: %s", e)
        return WebPlan(False, "", "error"), []


def gather(message: str, history: list[tuple[str, str]] | None = None) -> list[WebSource]:
    """Search+scrape up to 3 sources when the question needs the live web, else []. Never raises."""
    return gather_with_plan(message, history)[1]
