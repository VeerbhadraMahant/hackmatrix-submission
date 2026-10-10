"""Live-computed (not persisted) notification feed.

Not wired into app.main by this module -- the lead integrates
`notifications_router.router` into main.py, to avoid touching the same file
as the sibling ledger/budgets agent.

Never raises: builds on `build_dashboard_snapshot`, which already falls back
to fixture data for an unknown user_id and never 500s, and every section
below is defensive (missing/empty inputs just contribute zero items).

Sections merged into one feed:
  - anomalies (from app.analytics.anomalies.detect_anomalies, run directly
    against the same transactions DataFrame the snapshot builder uses, so we
    get the structured Fact objects rather than re-parsing snapshot text)
    -> severity "warning"
  - top 1-2 recommendations from snapshot.insights.recommendations
    -> severity "info", type "recommendation"
  - recurring obligations due within the next 7 days
    -> severity "info", type "upcoming_bill"
  - a cash-flow gap within the next 30 days
    -> severity "critical", type "cash_flow_gap"

Sorted critical -> warning -> info, then by date ascending within each
severity. Each item gets a stable-ish id (type + source + date) so a future
"mark as read" feature could reference one without us persisting read-state
now.
"""
from __future__ import annotations

import hashlib
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from app.analytics.anomalies import detect_anomalies
from app.core.auth import resolve_user_id
from app.core import store
from app.ingest.snapshot import _transactions_df, build_dashboard_snapshot
from app.models import TransactionRow
from app.schemas import NotificationItem

router = APIRouter()

_UPCOMING_BILL_WINDOW_DAYS = 7
_CASH_FLOW_GAP_WINDOW_DAYS = 30
_MAX_RECOMMENDATIONS = 2

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


@router.get("/api/notifications/{user_id}", response_model=list[NotificationItem])
def get_notifications(user_id: str = Depends(resolve_user_id)) -> list[NotificationItem]:
    items: list[NotificationItem] = []
    today = date.today()

    try:
        snapshot = build_dashboard_snapshot(user_id)
        txn_rows = store.query(TransactionRow, user_id=user_id)
    except Exception:
        # Defensive: never let a notifications-feed failure break the page
        # that renders it. An empty feed is always a valid response.
        return []

    # --- anomalies -----------------------------------------------------
    try:
        df = _transactions_df(list(txn_rows))
        for fact in detect_anomalies(df):
            source_ref = fact.source_txn_ids[0] if fact.source_txn_ids else None
            items.append(
                NotificationItem(
                    id=_stable_id("anomaly", source_ref or "", fact.text, today.isoformat()),
                    type="anomaly",
                    severity="warning",
                    text=fact.text,
                    date=today,
                    source_ref=source_ref,
                )
            )
    except Exception:
        pass

    # --- recommendations -------------------------------------------------
    try:
        for rec in snapshot.insights.recommendations[:_MAX_RECOMMENDATIONS]:
            items.append(
                NotificationItem(
                    id=_stable_id("recommendation", rec.action.value, today.isoformat()),
                    type="recommendation",
                    severity="info",
                    text=rec.text,
                    date=today,
                    source_ref=rec.action.value,
                )
            )
    except Exception:
        pass

    # --- upcoming bills ----------------------------------------------------
    try:
        horizon = today + timedelta(days=_UPCOMING_BILL_WINDOW_DAYS)
        for ob in snapshot.recurring_obligations:
            if today <= ob.next_expected_date <= horizon:
                items.append(
                    NotificationItem(
                        id=_stable_id("upcoming_bill", ob.group_id, ob.next_expected_date.isoformat()),
                        type="upcoming_bill",
                        severity="info",
                        text=(
                            f"{ob.merchant} (₹{abs(ob.amount):,.0f}) is due "
                            f"{ob.next_expected_date.isoformat()}."
                        ),
                        date=ob.next_expected_date,
                        source_ref=ob.group_id,
                    )
                )
    except Exception:
        pass

    # --- over-budget & near-limit envelope alerts -------------------------
    try:
        from app.api.budgets_router import budget_status as compute_budget_status

        budgets_statuses = compute_budget_status(user_id=user_id)
        for bs in budgets_statuses:
            cat_val = bs.category.value if hasattr(bs.category, "value") else str(bs.category)
            cat_name = cat_val.replace("_", " ").title()
            effective_lim = bs.monthly_limit + bs.rollover_amount
            if bs.status == "over" or bs.percent_used >= 100.0:
                over_amt = bs.spent_so_far - effective_lim
                items.append(
                    NotificationItem(
                        id=_stable_id("over_budget", cat_val, today.strftime("%Y-%m")),
                        type="over_budget",
                        severity="critical",
                        text=f"'{cat_name}' budget exceeded by ₹{over_amt:,.0f} (spent ₹{bs.spent_so_far:,.0f} of ₹{effective_lim:,.0f}).",
                        date=today,
                        source_ref="/budgets",
                    )
                )
            elif bs.status == "near" or bs.percent_used >= 80.0:
                items.append(
                    NotificationItem(
                        id=_stable_id("near_budget", cat_val, today.strftime("%Y-%m")),
                        type="over_budget",
                        severity="warning",
                        text=f"'{cat_name}' budget at {bs.percent_used:.0f}% capacity (spent ₹{bs.spent_so_far:,.0f} of ₹{effective_lim:,.0f}).",
                        date=today,
                        source_ref="/budgets",
                    )
                )
    except Exception:
        pass

    # --- cash-flow gap ----------------------------------------------------
    try:
        gap_date = snapshot.forecast.first_gap_date
        if gap_date is not None and today <= gap_date <= today + timedelta(days=_CASH_FLOW_GAP_WINDOW_DAYS):
            items.append(
                NotificationItem(
                    id=_stable_id("cash_flow_gap", gap_date.isoformat()),
                    type="cash_flow_gap",
                    severity="critical",
                    text=(
                        f"Your projected cash balance may dip below ₹0 around "
                        f"{gap_date.isoformat()}."
                    ),
                    date=gap_date,
                    source_ref=None,
                )
            )
    except Exception:
        pass

    items.sort(key=lambda i: (_SEVERITY_ORDER.get(i.severity, 3), i.date))
    # ids are React keys on the client: never ship two items with the same one
    return list({i.id: i for i in reversed(items)}.values())[::-1]
