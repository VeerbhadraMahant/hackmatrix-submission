"""Nugen second opinion for the copilot (OpenAI-style chat completions).

Docs: https://docs.nugen.in/api-reference/inference/generate-chat-completions
Nugen gets a compact, pre-fetched bundle of the user's real numbers (the same tools
NVIDIA calls) and answers in prose. Never raises: any failure returns (None, None)
so the chat keeps working with the NVIDIA model / the offline router alone.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.copilot import schemes, tools
from app.core.config import get_settings
from app.schemas import ChatMessage

logger = logging.getLogger(__name__)

URL = "https://api.nugen.in/api/v3/inference/chat/completions"

_SYSTEM = """You are FinPilot's financial copilot for an Indian retail user.
Answer ONLY from the JSON data provided. Quote ₹ amounts exactly as given; never invent numbers.
If the data does not cover the question, say what is missing. Be concise: at most 5 sentences.
Separate what you observed from what you suggest. This is general guidance, not licensed advice."""


def _context(user_id: str) -> dict:
    return {
        "summary": tools.get_summary(user_id),
        "spending_last_90_days": tools.get_spending_breakdown(user_id, 90),
        "recurring": tools.get_recurring(user_id),
        "debt": tools.get_debt(user_id),
        "invoices": tools.get_invoices(user_id),
        "investments": tools.get_investments(user_id),
        "schemes_and_deadlines": schemes.upcoming(),
    }


def second_opinion(user_id: str, message: str, history: Optional[list[ChatMessage]] = None) -> tuple[Optional[str], Optional[float]]:
    s = get_settings()
    try:
        msgs = [{"role": "system", "content": _SYSTEM + "\n\nDATA:\n" + json.dumps(_context(user_id), default=str)}]
        msgs += [{"role": m.role, "content": m.content} for m in (history or [])[-6:] if m.role in ("user", "assistant")]
        msgs.append({"role": "user", "content": message})
        r = httpx.post(
            URL,
            headers={"Authorization": f"Bearer {s.nugen_api_key}"},
            json={"model": s.nugen_model, "messages": msgs, "max_tokens": 400, "temperature": 0.3, "prompt_truncate_len": 6000},
            timeout=45,
        )
        r.raise_for_status()
        body = r.json()
        text = (body["choices"][0]["message"]["content"] or "").strip()
        return (text or None), body.get("confidence_score")
    except Exception as exc:  # noqa: BLE001 - second opinion is best-effort
        logger.warning("Nugen second opinion failed: %s", exc)
        return None, None


def complete(system: str, user: str, max_tokens: int = 700) -> Optional[str]:
    """One-shot Nugen completion; None on any failure (used as the backup)."""
    s = get_settings()
    if not s.has_nugen:
        return None
    try:
        r = httpx.post(
            URL,
            headers={"Authorization": f"Bearer {s.nugen_api_key}"},
            json={"model": s.nugen_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "max_tokens": max_tokens, "temperature": 0.2},
            timeout=45,
        )
        r.raise_for_status()
        return (r.json()["choices"][0]["message"]["content"] or "").strip() or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Nugen completion failed: %s", exc)
        return None
