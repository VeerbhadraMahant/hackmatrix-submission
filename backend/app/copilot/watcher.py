"""Always-on copilot: deterministic (no LLM) review of freshly ingested
transactions. Produces short opinionated CopilotInsights that the UI shows as
a pop-up. Amounts follow routes.py: positive = income, negative = spend.
"""
from __future__ import annotations

import logging
import statistics
from datetime import date, datetime, timedelta, timezone

from app.analytics.recurring import normalize_merchant
from app.core import store
from app.models import AccountRow, CopilotInsightRow, TransactionRow
from app.schemas import CopilotAction, CopilotInsight, TxnCategory

log = logging.getLogger(__name__)

_LIQUID = {"checking", "savings"}
_ESSENTIAL = {c.value for c in (TxnCategory.rent_housing, TxnCategory.emi_loan, TxnCategory.utilities, TxnCategory.groceries)}
_SEV_RANK = {"critical": 0, "warning": 1, "positive": 2, "info": 3}
# shortcut: uploads review only the largest rows, to bound O(rows x history); raise if notable small rows matter.
_MAX_REVIEWED_UPLOAD_ROWS = 25


def _inr(x: float) -> str:
    return f"₹{abs(x):,.0f}"


def _spend(r: TransactionRow) -> bool:
    return r.amount < 0 and r.category != TxnCategory.transfer.value


def _ins(row: TransactionRow, severity: str, title: str, body: str, label: str, href: str) -> CopilotInsight:
    return CopilotInsight(
        id=f"ci-{row.id}", created_at=datetime.now(timezone.utc), txn_id=row.id, severity=severity,
        title=title[:60], body=body, action=CopilotAction(label=label, href=href),
    )


def _review_one(row: TransactionRow, history: list[TransactionRow], liquid: float, new_gap: bool) -> CopilotInsight:
    a = row.amount
    m = _inr(a)
    month = [h for h in history if h.date.year == row.date.year and h.date.month == row.date.month]
    if a > 0:
        inc = sum(h.amount for h in month if h.amount > 0) + a
        out = -sum(h.amount for h in month if _spend(h))
        rate = f" Month-to-date savings rate is now {(inc - out) / inc:.0%}." if inc > 0 else ""
        return _ins(row, "positive", f"{m} received from {row.merchant}", f"Income landed.{rate}", "See budgets", "/budgets")
    if not _spend(row):
        return _ins(row, "info", f"{m} transfer logged", "Transfers between your own accounts are not counted as spend.",
                    "See transactions", "/transactions")

    mag = -a
    spends = [-h.amount for h in history if _spend(h)]
    med = statistics.median(spends) if spends else 0.0

    essential_by_month: dict[tuple[int, int], float] = {}
    for h in history:
        if h.category in _ESSENTIAL and h.amount < 0:
            k = (h.date.year, h.date.month)
            essential_by_month[k] = essential_by_month.get(k, 0.0) - h.amount
    buffer = statistics.mean(essential_by_month.values()) if essential_by_month else 0.0
    recent = row.date >= date.today() - timedelta(days=31)
    if recent and (new_gap or (buffer > 0 and liquid >= buffer > liquid - mag)):
        why = ("It creates a projected cash gap." if new_gap
               else f"It drops your cash below one month of essentials ({_inr(buffer)}).")
        return _ins(row, "critical", f"{m} at {row.merchant} is risky", why + " Simulate before spending more.",
                    "Run simulation", "/simulate")

    if med > 0 and mag > max(3 * med, 0.10 * liquid):
        return _ins(row, "warning", f"Large spend: {m} at {row.merchant}",
                    f"That is {mag / med:.0f}x your typical expense of {_inr(med)}.", "Review it", "/transactions")

    key = normalize_merchant(row.merchant)
    if any(h.amount == a and normalize_merchant(h.merchant) == key and abs((h.date - row.date).days) <= 3 for h in history):
        return _ins(row, "warning", f"Possible duplicate: {row.merchant}",
                    f"You already paid {m} to {row.merchant} within 3 days.", "Check transactions", "/transactions")

    cat = row.category.replace("_", " ")
    cat_hist = [h for h in history if h.category == row.category and _spend(h)]
    start = row.date.replace(day=1)
    avg = -sum(h.amount for h in cat_hist if start - timedelta(days=92) <= h.date < start) / 3
    mtd = -sum(h.amount for h in cat_hist if h.date >= start) + mag
    if avg > 0 and mtd > 1.3 * avg:
        return _ins(row, "warning", f"{cat.title()} is running {mtd / avg - 1:.0%} over",
                    f"{_inr(mtd)} this month vs a {_inr(avg)} monthly average.", "Adjust budget", "/budgets")

    if history and med > 0 and mag >= 2 * med and key not in {normalize_merchant(h.merchant) for h in history}:
        return _ins(row, "warning", f"New merchant: {row.merchant}",
                    f"First time paying {row.merchant}, and {m} is well above your usual spend.", "Review it", "/transactions")

    cat_total = -sum(h.amount for h in month if _spend(h) and h.category == row.category) + mag
    return _ins(row, "info", f"{m} logged under {cat}",
                f"That is {mag / cat_total:.0%} of this month's {cat} spend ({_inr(cat_total)}).", "Ask copilot", "/copilot")


def review_new_transactions(user_id: str, new_rows: list[TransactionRow], *, new_gap: bool = False) -> list[CopilotInsight]:
    """new_gap: a forecast cash gap appeared because of this data (caller diffs the snapshots)."""
    if not new_rows:
        return []
    ids = {r.id for r in new_rows}
    history = [r for r in store.query(TransactionRow, user_id=user_id) if r.id not in ids]
    liquid = sum(a.balance for a in store.query(AccountRow, user_id=user_id) if a.type in _LIQUID)
    if len(new_rows) == 1:
        return [_review_one(new_rows[0], history, liquid, new_gap)]

    top = sorted(new_rows, key=lambda r: -abs(r.amount))[:_MAX_REVIEWED_UPLOAD_ROWS]
    reviewed = [_review_one(r, history, liquid, False) for r in top]
    notable = sorted((i for i in reviewed if i.severity in ("critical", "warning")), key=lambda i: _SEV_RANK[i.severity])[:2]

    inflow = sum(r.amount for r in new_rows if r.amount > 0)
    outflow = -sum(r.amount for r in new_rows if _spend(r))
    mix: dict[str, float] = {}
    for r in new_rows:
        if _spend(r):
            mix[r.category] = mix.get(r.category, 0.0) - r.amount
    top_cats = ", ".join(f"{c.replace('_', ' ')} {_inr(v)}" for c, v in sorted(mix.items(), key=lambda kv: -kv[1])[:3])
    summary = CopilotInsight(
        id=f"ci-batch-{new_rows[0].id}", created_at=datetime.now(timezone.utc), txn_id=None,
        severity="critical" if new_gap else "info",
        title=f"Reviewed {len(new_rows)} new transactions",
        body=f"{_inr(inflow)} in, {_inr(outflow)} out." + (f" Top spend: {top_cats}." if top_cats else "")
             + (" A cash gap now appears in your forecast." if new_gap else ""),
        action=CopilotAction(label="Open transactions", href="/transactions"),
    )
    return [summary, *notable]


def watch(user_id: str, new_rows: list[TransactionRow], *, new_gap: bool = False) -> list[CopilotInsight]:
    """Review + persist; analysis failure must never break the caller."""
    try:
        insights = review_new_transactions(user_id, new_rows, new_gap=new_gap)
        if insights:
            store.put(*[CopilotInsightRow(
                id=i.id, user_id=user_id, txn_id=i.txn_id, severity=i.severity, title=i.title, body=i.body,
                action_label=i.action.label if i.action else None, action_href=i.action.href if i.action else None,
                created_at=i.created_at) for i in insights])
        return insights
    except Exception:  # noqa: BLE001
        log.exception("copilot watcher failed")
        return []
