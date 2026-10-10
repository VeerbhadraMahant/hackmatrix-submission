"""Always-on copilot insight feed (written by app.copilot.watcher)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.core import store
from app.core.auth import resolve_user_id
from app.models import CopilotInsightRow
from app.schemas import CopilotAction, CopilotInsight

router = APIRouter()


@router.get("/copilot/insights/{user_id}", response_model=list[CopilotInsight])
def get_copilot_insights(
    since: datetime | None = None,
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(resolve_user_id),
) -> list[CopilotInsight]:
    if since and since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    rows = [r for r in store.query(CopilotInsightRow, user_id=user_id) if not since or r.created_at > since]
    rows.sort(key=lambda r: r.created_at, reverse=True)
    return [
        CopilotInsight(id=r.id, created_at=r.created_at, txn_id=r.txn_id, severity=r.severity, title=r.title,
                       body=r.body, action=CopilotAction(label=r.action_label, href=r.action_href) if r.action_href else None)
        for r in rows[:limit]
    ]
