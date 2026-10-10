"""User categorization rules router: list, create, and delete rules.

Allows users to define custom matching patterns (contains, exact, starts_with, regex)
that map merchants to categories and optional tags. Supports applying rules to
existing transactions immediately upon rule creation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core import store
from app.core.auth import resolve_user_id
from app.ingest.categorize import matches_pattern
from app.models import CategorizationRuleRow, TransactionRow
from app.schemas import (
    CategorizationRule,
    CategorizationRuleCreate,
    CategorizationRuleList,
    RuleMatchType,
    TxnCategory,
)

router = APIRouter(tags=["rules"])


def _row_to_rule(row: CategorizationRuleRow) -> CategorizationRule:
    tags_list: list[str] = []
    if row.tags:
        try:
            parsed = json.loads(row.tags)
            if isinstance(parsed, list):
                tags_list = [str(t) for t in parsed]
        except (json.JSONDecodeError, TypeError):
            tags_list = []

    return CategorizationRule(
        id=row.id,
        user_id=row.user_id,
        match_type=RuleMatchType(row.match_type) if row.match_type in RuleMatchType._value2member_map_ else RuleMatchType.contains,
        pattern=row.pattern,
        category=TxnCategory(row.category) if row.category in TxnCategory._value2member_map_ else TxnCategory.other,
        tags=tags_list,
        created_at=row.created_at,
    )


@router.get("/api/rules/{user_id}", response_model=CategorizationRuleList)
def list_rules(
    user_id: str = Depends(resolve_user_id),
) -> CategorizationRuleList:
    rows = sorted(
        store.query(CategorizationRuleRow, user_id=user_id), key=lambda r: r.created_at, reverse=True
    )

    items = [_row_to_rule(r) for r in rows]
    return CategorizationRuleList(items=items, total=len(items))


@router.post("/api/rules/{user_id}", response_model=CategorizationRule)
def create_rule(
    payload: CategorizationRuleCreate,
    user_id: str = Depends(resolve_user_id),
) -> CategorizationRule:
    pattern = payload.pattern.strip()
    if not pattern:
        raise HTTPException(400, "Rule pattern cannot be empty")

    tags_json = json.dumps(payload.tags) if payload.tags else None

    row = CategorizationRuleRow(
        user_id=user_id,
        match_type=payload.match_type.value,
        pattern=pattern,
        category=payload.category.value,
        tags=tags_json,
    )

    to_put: list = [row]

    if payload.apply_to_existing:
        # Match transactions and retroactively recategorize & review them
        txns = store.query(TransactionRow, user_id=user_id)

        now = datetime.now(timezone.utc)
        for t in txns:
            if matches_pattern(t.merchant, row.match_type, row.pattern):
                t.category = row.category
                if row.tags:
                    existing_tags: list[str] = []
                    if t.tags:
                        try:
                            p = json.loads(t.tags)
                            if isinstance(p, list):
                                existing_tags = p
                        except Exception:
                            pass
                    new_tags = list(dict.fromkeys(existing_tags + (payload.tags or [])))
                    t.tags = json.dumps(new_tags)
                t.review_status = "reviewed"
                t.reviewed_at = now
                to_put.append(t)

    store.put(*to_put)
    return _row_to_rule(row)


@router.delete("/api/rules/{user_id}/{rule_id}")
def delete_rule(
    rule_id: str,
    user_id: str = Depends(resolve_user_id),
) -> dict:
    row = store.get(CategorizationRuleRow, rule_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "Rule not found")

    store.delete(CategorizationRuleRow, rule_id)

    return {"ok": True, "deleted_id": rule_id}
