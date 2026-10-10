"""Turn a user's rows + uploaded documents into self-contained "fact card" chunks."""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import date, timedelta

from app.copilot.tools import _is_spend
from app.core import store
from app.models import AccountRow, BudgetRow, DebtRow, DocumentRow, GoalRow, IncomeRow, TransactionRow

Card = tuple[str, str, str, str]  # (id, kind, text, label)
_WIN, _OVERLAP = 800, 100


def _inr(x: float) -> str:
    return f"₹{x:,.2f}"


def _prev_month(m: str) -> str:
    y, mo = int(m[:4]), int(m[5:])
    return f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"


def _tags(t) -> list[str]:
    try:
        return json.loads(t.tags) if t.tags else []
    except ValueError:
        return []


def _txn_cards(txns: list) -> list[Card]:
    spend = [t for t in txns if _is_spend(t)]
    cards: list[Card] = []

    # (a) month x category
    groups: dict[tuple[str, str], list] = defaultdict(list)
    for t in spend:
        groups[(t.date.strftime("%Y-%m"), t.category)].append(t)
    for (m, cat), ts in sorted(groups.items()):
        total = sum(-t.amount for t in ts)
        by_m: dict[str, float] = defaultdict(float)
        for t in ts:
            by_m[t.merchant] += -t.amount
        top = max(by_m, key=by_m.get)
        text = f"In {m} you spent {_inr(total)} on {cat} across {len(ts)} transactions; top merchant {top} ({_inr(by_m[top])})."
        prev = sum(-t.amount for t in groups.get((_prev_month(m), cat), []))
        if prev:
            text += f" That is {(total - prev) / prev * 100:+.0f}% vs {_prev_month(m)} ({_inr(prev)})."
        cards.append((f"spend:{m}:{cat}", "transaction_summary", text, f"{cat.title()}, {m}"))

    # (b) merchants over last 120 days
    cutoff = date.today() - timedelta(days=120)
    recent: dict[str, list] = defaultdict(list)
    for t in spend:
        if t.date >= cutoff:
            recent[t.merchant].append(t)
    for mer, ts in recent.items():
        if len(ts) >= 3:
            total = sum(-t.amount for t in ts)
            cards.append((
                f"merchant:{mer}", "transaction_summary",
                f"At {mer} over the last 120 days you spent {_inr(total)} in {len(ts)} transactions "
                f"(average {_inr(total / len(ts))}), most recently on {max(t.date for t in ts)}.",
                f"{mer} (120 days)",
            ))

    # (d) unusual / duplicate transactions
    by_mer: dict[str, list] = defaultdict(list)
    by_cat: dict[str, list] = defaultdict(list)
    for t in sorted(spend, key=lambda t: t.date):
        by_mer[t.merchant].append(t)
        by_cat[t.category].append(t)
    flagged: dict[str, str] = {}
    for t in spend:
        for pool in (by_mer[t.merchant], by_cat[t.category]):
            med = statistics.median(-p.amount for p in pool) if len(pool) >= 3 else 0
            if med and -t.amount > 3 * med:
                flagged[t.id] = f"unusual, more than 3x the typical {_inr(med)}"
                break
        else:
            if {"demo-threat", "fishy"} & set(_tags(t)):
                flagged[t.id] = "unusual, flagged as suspicious"
    for mer, ts in by_mer.items():
        for i, a in enumerate(ts):
            for b in ts[i + 1 :]:
                if a.amount == b.amount and abs((a.date - b.date).days) <= 3:
                    flagged.setdefault(b.id, f"possible duplicate of the same {_inr(-a.amount)} charge at {mer} on {a.date}")
    for t in spend:
        if t.id in flagged:
            cards.append((
                f"unusual:{t.id}", "transaction_summary",
                f"Unusual transaction on {t.date}: {t.merchant} charged {_inr(-t.amount)} ({t.category}); {flagged[t.id]}.",
                f"{t.merchant} {t.date}",
            ))
    return cards


def _debt_text(d, name: str) -> str:
    text = f"Debt {name}: balance {_inr(d.principal)}, APR {d.interest_rate_apr}%, minimum payment {_inr(d.minimum_payment)} due on day {d.due_day_of_month} of each month."
    r = d.interest_rate_apr / 100 / 12
    if d.minimum_payment > 0:
        if r == 0:
            text += f" Paying the minimum clears it in about {math.ceil(d.principal / d.minimum_payment)} months."
        elif d.minimum_payment > r * d.principal:
            n = -math.log(1 - r * d.principal / d.minimum_payment) / math.log(1 + r)
            text += f" Paying only the minimum clears it in about {math.ceil(n)} months."
        else:
            text += " The minimum payment does not cover the monthly interest, so the balance never shrinks."
    return text


def _static_cards(user_id: str, txns: list) -> list[Card]:
    accts = {a.id: a for a in store.query(AccountRow, user_id=user_id)}
    cards: list[Card] = []
    for d in store.query(DebtRow, user_id=user_id):
        name = accts[d.account_id].name if d.account_id in accts else d.account_id
        cards.append((f"debt:{d.id}", "debt", _debt_text(d, name), f"Debt: {name}"))
    for g in store.query(GoalRow, user_id=user_id):
        due = f", deadline {g.target_date}" if g.target_date else ""
        cards.append((f"goal:{g.id}", "goal", f"Goal {g.name}: target {_inr(g.target_amount)}, saved {_inr(g.current_amount)}{due}.", f"Goal: {g.name}"))
    month = date.today().strftime("%Y-%m")
    for b in store.query(BudgetRow, user_id=user_id):
        spent = sum(-t.amount for t in txns if _is_spend(t) and t.category == b.category and t.date.strftime("%Y-%m") == month)
        cards.append((f"budget:{b.id}", "budget", f"Budget for {b.category} this month ({month}): limit {_inr(b.monthly_limit)}, spent {_inr(spent)}, {_inr(b.monthly_limit - spent)} remaining.", f"Budget: {b.category}"))
    for i in store.query(IncomeRow, user_id=user_id):
        cards.append((f"income:{i.id}", "income", f"Income source {i.source}: {_inr(i.amount)} {i.frequency}, next on {i.next_date}.", f"Income: {i.source}"))
    for a in accts.values():
        cards.append((f"account:{a.id}", "account", f"Account {a.name} ({a.type}) balance {_inr(a.balance)}.", f"Account: {a.name}"))
    return cards


def split_document(text: str) -> list[str]:
    """~800-char windows, 100 overlap, cut on paragraph/line boundaries where possible."""
    out, i = [], 0
    while i < len(text):
        end = min(i + _WIN, len(text))
        if end < len(text):
            cut = max(text.rfind("\n\n", i, end), text.rfind("\n", i + _WIN // 2, end))
            if cut > i + _WIN // 2:
                end = cut
        piece = text[i:end].strip()
        if piece:
            out.append(piece)
        if end >= len(text):
            break
        i = max(end - _OVERLAP, i + 1)
    return out


def build_chunks(user_id: str) -> list[Card]:
    txns = store.query(TransactionRow, user_id=user_id)
    cards = _txn_cards(txns) + _static_cards(user_id, txns)
    for doc in store.query(DocumentRow, user_id=user_id):
        for n, piece in enumerate(split_document(doc.text)):
            cards.append((f"doc:{doc.id}:{n}", "document", piece, doc.name))
    return cards
