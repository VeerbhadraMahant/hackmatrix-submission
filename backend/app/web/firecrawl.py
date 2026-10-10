"""Firecrawl search+scrape with a 6h cache and a 20 calls/hour guard."""
from __future__ import annotations

import logging
import time
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

log = logging.getLogger("finpilot.web")

URL = "https://api.firecrawl.dev/v2/search"
TTL = 6 * 3600
MAX_CALLS_PER_HOUR = 20
OFFICIAL = ("gov.in", "rbi.org.in", "sebi.gov.in", "incometax.gov.in", "nsdl.co.in", "amfiindia.com", "indiapost.gov.in")

_cache: dict[str, tuple[float, list]] = {}
_calls: list[float] = []


def _official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL)


def search_and_scrape(query: str) -> list:
    from app.web import WebSource

    s = get_settings()
    if not s.has_firecrawl:
        return []
    key = " ".join(query.lower().split())
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < TTL:
        return hit[1]
    _calls[:] = [t for t in _calls if now - t < 3600]
    if len(_calls) >= MAX_CALLS_PER_HOUR:
        log.warning("Firecrawl rate guard hit (%d/h); skipping search", MAX_CALLS_PER_HOUR)
        return []
    _calls.append(now)
    r = httpx.post(
        URL,
        headers={"Authorization": f"Bearer {s.firecrawl_api_key}"},
        json={"query": query, "limit": 4, "country": "IN", "scrapeOptions": {"formats": ["markdown"], "onlyMainContent": True}},
        timeout=40,
    )
    if r.status_code >= 400:
        log.warning("Firecrawl %s", r.status_code)
        return []
    data = r.json().get("data") or {}
    items = data if isinstance(data, list) else (data.get("web") or [])
    out = []
    for it in items:
        md = " ".join((it.get("markdown") or "").split())
        meta = it.get("metadata") or {}
        url = it.get("url") or meta.get("sourceURL") or ""
        if len(md) < 200 or not url:
            continue
        out.append(WebSource(title=it.get("title") or meta.get("title") or urlparse(url).hostname or url, url=url, content=md[:2500]))
    out.sort(key=lambda w: not _official(w.url))  # stable: official first
    out = out[:3]
    _cache[key] = (now, out)
    return out
