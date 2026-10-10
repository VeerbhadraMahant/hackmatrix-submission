"""Copilot engine: NVIDIA-hosted models only.

`answer(user_id, message, history, force_offline, model) -> AnswerContract` is the single entry point used by
/api/chat. Money questions go to the deep model with the user's real numbers; small talk goes to the fast chat model.
Identity questions are answered locally. Offline mode uses the rule-based router and sends nothing anywhere.
"""
import json
from datetime import date
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from app import rag, web
from app.copilot import nugen, nvidia, offline_router
from app.core.config import get_settings
from pydantic import BaseModel, Field

from app.schemas import (
    ActionType,
    AnswerContract,
    ChatMessage,
    DataGap,
    Fact,
    ImpactEstimate,
    NextStep,
    Prediction,
    Source,
)

logger = logging.getLogger(__name__)



# Mirror of AnswerContract without the free-form `action_params` dict, so the schema we show the model stays simple.
# The result is re-validated into the real AnswerContract.
class _RecommendationSchema(BaseModel):
    action: ActionType
    text: str
    rationale: str
    impact: ImpactEstimate
    confidence: float = Field(ge=0, le=1)


class _NextStepSchema(BaseModel):
    title: str
    why: str
    when: Optional[str] = None
    link: Optional[str] = None


class _AnswerSchema(BaseModel):
    query: Optional[str] = None
    facts: list[Fact] = Field(default_factory=list)
    predictions: list[Prediction] = Field(default_factory=list)
    recommendations: list[_RecommendationSchema] = Field(default_factory=list)
    data_gaps: list[DataGap] = Field(default_factory=list)
    narrative: str = ""
    next_steps: list[_NextStepSchema] = Field(default_factory=list)

_SYSTEM_PROMPT_STRUCTURE = """You convert a financial copilot's grounded findings into strict JSON matching
the AnswerContract schema.

Hard rules:
- Only include a number in `facts` or `predictions.value` if it appears in
  the grounded findings below (which come from real tool calls) -- never
  invent one.
- `predictions` are for speculative/future statements only, each with a
  `confidence` (0-1) and a `basis` string explaining what it's derived from.
- `recommendations[].impact` must be populated from an actual
  `simulate_action`/`check_affordability` tool result in the grounded
  findings -- never invent an impact. If no simulation was run for a
  recommendation you want to make, omit that recommendation instead.
- If something the user asked about could not be answered from the grounded
  findings, add a `data_gaps` entry describing what's missing instead of
  guessing.
- `narrative` is a short natural-language summary tying it together.

Return ONLY the JSON object, nothing else.
"""


def _last_month() -> str:
    t = date.today()
    return f"{t.year - (t.month == 1)}-{(t.month - 2) % 12 + 1:02d}"


def _history_to_text(history: Optional[list[ChatMessage]]) -> str:
    if not history:
        return ""
    lines = []
    for msg in history[-10:]:
        lines.append(f"{msg.role}: {msg.content}")
    return "\n".join(lines)



_IDENTITY = re.compile(
    r"who are you|what are you|your name|which (ai |llm |language )?model|what (ai |llm |language )?model|are you (chat ?gpt|gpt|gemini|grok|claude|llama|nemotron|nvidia|an? ai|a bot|a robot)|"
    r"who (made|built|created|trained|developed) you|(which|what) company|powered by|underlying model|\bllm\b",
    re.I,
)
_IDENTITY_REPLY = (
    "I'm FinPilot, your personal finance copilot. I look at your own money data, explain it in plain words, "
    "and keep you posted on deadlines and schemes. Ask me anything about your money."
)

_FINANCE = re.compile(
    r"₹|scheme|yojana|deadline|due date|ppf|nps|elss|80c|itr|advance tax|gold bond|rupee|rs|spend|spent|expens|income|salary|earn|debt|loan|emi|sip|subscri|saving|budget|forecast|invoice|bill|invest|mutual|stock|"
    r"transaction|cash|afford|balance|net worth|tax|goal|credit|card|rent|insurance|health score|emergency fund|cancel|prepay|my (money|account|finance)",
    re.I,
)

_GENERAL_SYSTEM = (
    "You are FinPilot's friendly assistant inside a personal-finance app. Chat naturally and be concise. "
    "You have NO access to the user's accounts in this reply, so never state their balances or spending. "
    "If they want numbers about their money, invite them to ask a specific money question."
    + " Your name is FinPilot. If asked who or what you are, or which model, company or technology is behind you, say only that you are FinPilot, a personal finance copilot; never name any AI model, vendor or provider."
)


def _is_general(message: str) -> bool:
    """Small talk and non-money questions go to the fast chat model; money questions get grounded data."""
    return not _FINANCE.search(message)


_GROUNDING_RULES = (
    "Answer ONLY from DATA, RETRIEVED and WEB. Quote ₹ amounts exactly. When a claim uses a web source cite it as [n]. "
    "If web content conflicts with what you know, say to confirm on the official site. Personalise to the user's own situation "
    "(income level, debts, goals, recent unusual activity) and state which of THEIR records led to the advice."
)


def _retrieved_block(chunks) -> str:
    return "\n".join(f"- [{c.label}] {c.text}" for c in chunks) or "(none)"


def _web_block(sources) -> str:
    return "\n".join(f"[{n}] {w.title} ({w.url}): {w.content}" for n, w in enumerate(sources, 1)) or "(none)"


def _next_step_from_text(text: str) -> list[NextStep]:
    m = re.search(r"^\W*Next step:\s*(.+)$", text, re.I | re.M)
    return [NextStep(title=m.group(1).strip(), why="")] if m else []


def _general_answer(message: str, history: Optional[list[ChatMessage]], user_id: Optional[str] = None, chunks=(), sources=()) -> AnswerContract:
    """Fast chat model. With `user_id` it also gets the user's real numbers to answer money questions."""
    turns = [(m.role, m.content) for m in (history or []) if m.role in ("user", "assistant")]
    system = _GENERAL_SYSTEM + (("\n\nDATA (answer only from this, quote amounts exactly):\n" + json.dumps(nugen._context(user_id), default=str)) if user_id else "")
    if user_id and chunks:
        system += "\n\nRETRIEVED:\n" + _retrieved_block(chunks)
    if sources:
        system += "\n\nWEB:\n" + _web_block(sources)
    if user_id or sources:
        system += "\n\n" + _GROUNDING_RULES
    if user_id:
        system += " End with a last paragraph that starts with 'Next step:' giving one concrete action."
    narrative = nvidia.chat(message, turns, system)
    return AnswerContract(query=message, narrative=narrative, source="FinPilot", next_steps=_next_step_from_text(narrative) if user_id else [])


def _nvidia_answer(user_id: str, message: str, history: Optional[list[ChatMessage]], chunks=(), sources=()) -> AnswerContract:
    """One NVIDIA call over the real, pre-fetched numbers (no recommendations: those need a simulation)."""
    convo = _history_to_text(history)
    user = (
        (f"Conversation so far:\n{convo}\n\n" if convo else "")
        + f"Today is {date.today().isoformat()}; 'last month' means {_last_month()}. Never add up or estimate figures yourself: quote month totals from RETRIEVED/DATA exactly.\n\n"
        + f"User question: {message}\n\nDATA (real data, JSON):\n{json.dumps(nugen._context(user_id), default=str)}\n\n"
        f"RETRIEVED:\n{_retrieved_block(chunks)}\n\nWEB:\n{_web_block(sources)}\n\n{_GROUNDING_RULES}\n\n"
        "Produce the strict AnswerContract JSON. Leave `recommendations` empty. Use EXACTLY this JSON schema:\n"
        f"{json.dumps(_AnswerSchema.model_json_schema())}\n"
        'Example fact: {"text": "Monthly income is ₹94,431", "value": 94431, "source_txn_ids": []}. '
        "`text` is a full sentence and `value` is a plain number or null. Write `narrative` as 2 to 4 friendly plain sentences.\n"
        "For every money, security or scheme question give 1 to 4 `next_steps`, ordered by urgency, each a concrete imperative tied to the user's data and a deadline. "
        "`link` is null or one of /transactions /budgets /goals /security /evidence-room /simulate /plan /tax /connect, or an official https URL taken from WEB or the schemes feed; never invent URLs. "
        'Example next_step: {"title": "Dispute the duplicate ₹649 Netflix charge on 12 Sep", "why": "Netflix billed you twice in September.", "when": "this week", "link": "/transactions"}. '
        "For small talk leave `next_steps` empty."
    )
    result = AnswerContract.model_validate(_AnswerSchema.model_validate(nvidia.complete_json(_SYSTEM_PROMPT_STRUCTURE, user)).model_dump(mode="json"))
    if not result.query:
        result.query = message
    return result


def _prefetch(user_id: str, message: str, history: Optional[list[ChatMessage]]):
    """RAG and web planning in parallel. Returns (chunks, plan, sources); never raises, both share a 40 s budget."""
    prior = next((m.content for m in reversed(history or []) if m.role == "user"), "")
    query = f"{prior}\n{message}" if prior else message
    turns = [(m.role, m.content) for m in (history or [])]
    gather = getattr(web, "gather_with_plan", None)
    pool = ThreadPoolExecutor(max_workers=2)
    rf = pool.submit(rag.retrieve, user_id, query, 8)
    wf = pool.submit(gather, message, turns) if gather else None
    pool.shutdown(wait=False)
    deadline = time.monotonic() + 40  # one shared budget: both run in parallel, so neither waits twice
    try:
        chunks = rf.result(timeout=max(1, deadline - time.monotonic()))
    except Exception as exc:  # noqa: BLE001
        logger.warning("rag failed: %r", exc)
        chunks = []
    plan, sources = None, []
    if wf is not None:
        try:
            plan, sources = wf.result(timeout=max(1, deadline - time.monotonic()))
        except Exception as exc:  # noqa: BLE001
            logger.warning("web failed: %r", exc)
    logger.info("web_plan search=%s query=%r", getattr(plan, "search", None), getattr(plan, "query", None))
    logger.info("rag_chunks=%d", len(chunks))
    return chunks, plan, list(sources)


def answer(
    user_id: str,
    message: str,
    history: Optional[list[ChatMessage]] = None,
    force_offline: bool = False,
    model: str = "auto",
) -> AnswerContract:
    """Answer a user's question. Never raises.

    `model`: auto = money questions get the deep, number-checking engine and everything else the fast chat engine
    (each tries the other if it fails); deep = always the deep engine; fast = always the fast engine (given your data
    for money questions). An AI failure is reported honestly, never replaced by a canned answer. The rule-based
    router answers only in offline mode (`force_offline`: data never leaves this process) or when no key is set.
    """
    settings = get_settings()
    if _IDENTITY.search(message):
        return AnswerContract(query=message, narrative=_IDENTITY_REPLY, source="FinPilot")
    if force_offline or not (settings.has_nvidia or settings.nvidia_chat_api_key):
        result = offline_router.route(user_id, message)
        result.source = "FinPilot rules"
        return result

    # a short follow-up ("and last month?") inherits the topic of the previous user turn
    prior = next((m.content for m in reversed(history or []) if m.role == "user"), "")
    money = not _is_general(message) or (len(message) < 40 and not _is_general(prior))
    chunks, plan, sources = _prefetch(user_id, message, history)
    deep = lambda: _nvidia_answer(user_id, message, history, chunks, sources)  # noqa: E731
    fast = lambda: _general_answer(message, history, user_id if money else None, chunks, sources)  # noqa: E731
    steps = [fast, deep] if model == "fast" or (model == "auto" and not money) else [deep, fast]

    # Nugen's second opinion runs alongside money questions only
    pool = ThreadPoolExecutor(max_workers=1)
    second = pool.submit(nugen.second_opinion, user_id, message, history) if money and settings.has_nugen else None
    result, last = None, None
    for step in steps:
        try:
            result = step()
            result.source = "FinPilot"
            break
        except Exception as exc:  # noqa: BLE001 - deliberate broad boundary
            last = exc
            logger.warning("Copilot engine step failed: %s", exc)
    if result is None:
        why = "it is busy right now" if "429" in str(last) else "it did not respond in time"
        result = AnswerContract(
            query=message,
            narrative=f"I couldn't answer right now because {why}. Please try again in a minute.",
            data_gaps=[DataGap(text="The AI engine was unavailable.", what_would_help="Retry shortly, or turn on 'Keep my data on this device' for basic rule-based answers.")],
        )
    if sources:
        result.sources = [Source(title=w.title, url=w.url) for w in sources]
    elif getattr(plan, "search", False):
        result.data_gaps.append(DataGap(text="Live web search was not available for this question.", what_would_help="Add FIRECRAWL_API_KEY on the server."))
    if second is not None:
        result.nugen_narrative, result.nugen_confidence = second.result()
    pool.shutdown(wait=False)
    return result
