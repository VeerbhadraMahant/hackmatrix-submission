"""Decide whether a question needs the live web. Layer 1 is a free regex prefilter, layer 2 one cheap LLM call."""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date

from app.copilot import nvidia

log = logging.getLogger("finpilot.web")


@dataclass
class WebPlan:
    search: bool
    query: str
    reason: str


_SMALL = re.compile(
    r"^\s*(hi|hello|hey|yo|thanks?|thank you|ok(ay)?|cool|bye|good (morning|evening|night)|who are you|what('s| is) your name|what can you do|how are you)\b[\s!.?]*$",
    re.I,
)
_OWN = re.compile(
    r"my (spend|spent|balance|transactions?|budget|debts?|goals?|subscriptions?)|how much did i|what did i|\bmy spending\b", re.I
)
_TRIGGERS = [
    r"schemes?", r"yojana", r"polic(y|ies)", r"mutual funds?", r"\bsips?\b", r"\betfs?\b", r"fd rates?", r"interest rates?",
    r"repo rate", r"\brbi\b", r"\bsebi\b", r"\bnps\b", r"\bppf\b", r"\bepf\b", r"\belss\b", r"sovereign gold", r"gold bonds?",
    r"\bipo\b", r"\bnav\b", r"credit card offers?", r"best .* (card|fund|bank)", r"latest", r"current", r"today", r"news",
    r"new rules?", r"deadline extended", r"budget 20\d\d", r"tax slabs?", r"income tax (rule|slab|change)", r"eligibility",
    r"how to apply", r"apply for", r"compare", r"top \d+", r"\bvs\b",
]
_TRIG = [re.compile(t, re.I) for t in _TRIGGERS]

_SYSTEM = (
    "You decide if a finance question needs live web search. Reply with ONLY JSON: "
    '{"search": true|false, "query": "<standalone web search query, <=12 words, add India and the current year '
    f"({date.today().year}) when relevant>\"}}. "
    "search=true ONLY if answering well needs current external facts (rates, scheme rules/eligibility, fund performance, "
    "news, deadline changes) that are not in the user's own finances. Otherwise search=false."
)


def plan(message: str, history: list[tuple[str, str]] | None = None) -> WebPlan:
    if _SMALL.match(message):
        return WebPlan(False, "", "small talk")
    hits = sum(1 for t in _TRIG if t.search(message))
    if not hits:
        return WebPlan(False, "", "own data / no web trigger" if _OWN.search(message) else "no web trigger")
    try:
        raw = nvidia.chat(message, history or [], _SYSTEM)
        try:
            d = json.loads(re.search(r"\{.*?\}", raw, re.S).group(0))
            want, q = bool(d.get("search")), str(d.get("query") or message).strip()
        except Exception:  # noqa: BLE001 - the model sometimes returns near-JSON; read the two fields directly
            want = bool(re.search(r'"search"\s*:\s*true', raw, re.I))
            m = re.search(r'"query"\s*:\s*"([^"]+)', raw)
            q = (m.group(1) if m else message).strip()
            if not want and not re.search(r'"search"\s*:\s*false', raw, re.I):
                raise
        return WebPlan(want, q if want else "", "gate model decision")
    except Exception as e:  # noqa: BLE001
        log.warning("web gate LLM failed (%s); using trigger count", e)
        strong = hits >= 2 or not _OWN.search(message)  # a lone trigger like 'schemes' is enough unless it is about their own data
        return WebPlan(strong, message if strong else "", f"fallback, {hits} trigger(s)")
