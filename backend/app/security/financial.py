"""Financial security: how safe the user's own money data looks, built from the Evidence Room checks.

`build(user_id)` is pure code over real rows (no AI). `brief(facts)` asks the NVIDIA model to write the
plain-language analysis from those facts only; if it fails, a rules-based write-up is returned instead.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from pydantic import BaseModel

from app.copilot import nvidia
from app.core import store
from app.core.config import get_settings
from app.models import AccountRow, TransactionRow
from app.security import agents

logger = logging.getLogger(__name__)

_PILLARS = [
    ("data_guardian", "Data integrity", "Broken, missing or future-dated records"),
    ("duplicate_detector", "Duplicate charges", "The same payment taken twice"),
    ("fraud_hunter", "Unusual amounts", "Payments far outside your normal spending"),
    ("merchant_verifier", "Merchant trust", "Look-alike and unknown merchant names"),
    ("subscription_sleuth", "Subscription leakage", "Price hikes and overlapping plans"),
    ("pattern_analyst", "Payment patterns", "Bursts and card-testing shapes"),
]
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _grade(score: int) -> str:
    return "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 55 else "D" if score >= 35 else "E"


def build(user_id: str) -> dict:
    rows = store.query(TransactionRow, user_id=user_id)
    accounts = store.query(AccountRow, user_id=user_id)
    by_agent = agents.run_checks(rows, accounts)
    findings = [f for fs in by_agent.values() for f in fs]
    risk = agents.risk_score(findings)

    pillars = []
    for key, label, hint in _PILLARS:
        fs = by_agent.get(key, [])
        pillar_risk = agents.risk_score(fs)
        pillars.append({
            "key": key, "label": label, "hint": hint, "findings": len(fs),
            "amount_at_risk": round(sum(f["amount"] for f in fs), 2),
            "score": max(0, 100 - min(100, pillar_risk * 3)),
        })

    flagged_ids = {i for f in findings for i in f["txn_ids"]}
    by_id = {r.id: r for r in rows}
    account_rows = []
    for a in accounts:
        mine = [r for r in rows if r.account_id == a.id]
        hit = [by_id[i] for i in flagged_ids if i in by_id and by_id[i].account_id == a.id]
        account_rows.append({
            "name": a.name, "type": a.type, "balance": a.balance, "transactions": len(mine),
            "flagged": len(hit), "flagged_amount": round(sum(-r.amount for r in hit if r.amount < 0), 2),
        })

    top = sorted(findings, key=lambda f: (_SEVERITY_ORDER[f["severity"]], -f["amount"]))[:8]
    return {
        "generated_at": date.today().isoformat(),
        "score": max(0, 100 - risk), "grade": _grade(max(0, 100 - risk)), "risk_level": agents.risk_level(risk),
        "transactions_checked": len(rows), "flagged_transactions": len(flagged_ids),
        "amount_at_risk": round(sum(-by_id[i].amount for i in flagged_ids if i in by_id and by_id[i].amount < 0), 2),
        "findings_total": len(findings),
        "severity_counts": {s: sum(1 for f in findings if f["severity"] == s) for s in _SEVERITY_ORDER},
        "pillars": pillars, "accounts": account_rows,
        "top_findings": [{k: f[k] for k in ("agent", "severity", "title", "detail", "merchant", "amount")} for f in top],
    }


class _Brief(BaseModel):
    headline: str
    summary: str
    risks: list[str]
    actions: list[str]


_SYSTEM = (
    "You are FinPilot's financial security analyst for an Indian retail user. You are given real security check results "
    "about THEIR OWN transactions and accounts. Write a short briefing using ONLY these facts; quote ₹ amounts exactly; "
    "never invent numbers, merchants or dates. Never name any AI model or vendor. Return ONLY JSON: "
    '{"headline": "<one sentence>", "summary": "<3 to 5 plain sentences on how safe their money data looks and why>", '
    '"risks": ["<up to 4 concrete risks, each naming the merchant/amount>"], '
    '"actions": ["<3 to 5 imperative next steps, most urgent first, e.g. Dispute the duplicate ₹849 Zomato charge>"]}'
)


def _rules_brief(facts: dict) -> dict:
    tops = facts["top_findings"][:4]
    return {
        "headline": f"Your financial security score is {facts['score']}/100 (grade {facts['grade']}).",
        "summary": (
            f"We checked {facts['transactions_checked']} transactions and flagged {facts['flagged_transactions']} "
            f"worth a look, with about ₹{facts['amount_at_risk']:,.0f} involved."
            if facts["findings_total"] else "No suspicious activity was found in your recent transactions."
        ),
        "risks": [f"{f['title']}: {f['detail']}" for f in tops],
        "actions": [f"Review: {f['title']}" for f in tops] or ["Re-check after your next bank sync."],
    }


def brief(facts: dict) -> dict:
    """AI write-up of `facts`; falls back to a rules-based one so the page never breaks."""
    if not get_settings().has_nvidia:
        return {**_rules_brief(facts), "source": "rules"}
    try:
        out = _Brief.model_validate(nvidia.complete_json(_SYSTEM, json.dumps(facts, default=str))).model_dump()
        return {**out, "source": "finpilot"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("financial security brief failed: %s", exc)
        return {**_rules_brief(facts), "source": "rules"}
