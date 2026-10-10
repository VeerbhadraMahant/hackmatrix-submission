"""Transactions ledger: paginated/filterable/searchable list, review workflow,
and manual recategorization.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core import store
from app.core.auth import resolve_user_id
from app.ingest.categorize import matches_pattern
from app.models import CategorizationRuleRow, TransactionRow
from app.schemas import (
    ReviewAction,
    ReviewQueueResponse,
    ReviewTransactionRequest,
    Transaction,
    TransactionPage,
    TransactionUpdate,
    TxnCategory,
)

router = APIRouter()

_MAX_PAGE_SIZE = 200


def _row_to_transaction(row: TransactionRow) -> Transaction:
    tags_list: list[str] = []
    if row.tags:
        try:
            parsed = json.loads(row.tags)
            if isinstance(parsed, list):
                tags_list = [str(t) for t in parsed]
        except (json.JSONDecodeError, TypeError):
            tags_list = []

    cat_enum = TxnCategory(row.category) if row.category in TxnCategory._value2member_map_ else TxnCategory.other

    return Transaction(
        id=row.id,
        user_id=row.user_id,
        account_id=row.account_id,
        date=row.date,
        amount=row.amount,
        merchant=row.merchant,
        category=cat_enum,
        description=row.description,
        is_recurring=row.is_recurring,
        recurring_group_id=row.recurring_group_id,
        tags=tags_list,
        notes=row.notes,
        review_status=row.review_status or "pending",
        reviewed_at=row.reviewed_at,
    )


@router.get("/transactions/{user_id}", response_model=TransactionPage)
def list_transactions(
    user_id: str = Depends(resolve_user_id),
    category: str | None = Query(default=None),
    merchant: str | None = Query(default=None, description="Case-insensitive substring match"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None, description="Matches merchant OR description, case-insensitive"),
    review_status: str | None = Query(default=None, description="pending | reviewed | skipped"),
    tag: str | None = Query(default=None, description="Filter by tag name"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1),
) -> TransactionPage:
    page_size = min(page_size, _MAX_PAGE_SIZE)

    if category is not None:
        try:
            TxnCategory(category)
        except ValueError:
            raise HTTPException(400, f"Unknown category: {category!r}")

    rows = store.query(TransactionRow, user_id=user_id)
    if category is not None:
        rows = [r for r in rows if r.category == category]
    if merchant is not None:
        rows = [r for r in rows if merchant.lower() in r.merchant.lower()]
    if date_from is not None:
        rows = [r for r in rows if r.date >= date_from]
    if date_to is not None:
        rows = [r for r in rows if r.date <= date_to]
    if review_status is not None:
        rows = [r for r in rows if r.review_status == review_status]
    if tag is not None:
        rows = [r for r in rows if tag.lower() in (r.tags or "").lower()]
    if search is not None:
        needle = search.lower()
        rows = [
            r for r in rows
            if any(needle in (v or "").lower() for v in (r.merchant, r.description, r.notes, r.tags))
        ]

    total = len(rows)
    rows.sort(key=lambda r: (r.date, r.created_at), reverse=True)
    rows = rows[(page - 1) * page_size : page * page_size]

    items = [_row_to_transaction(row) for row in rows]
    return TransactionPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/transactions/{user_id}/review-queue", response_model=ReviewQueueResponse)
def get_review_queue(
    user_id: str = Depends(resolve_user_id),
    limit: int = Query(default=20, ge=1, le=100),
) -> ReviewQueueResponse:
    pending = [r for r in store.query(TransactionRow, user_id=user_id) if r.review_status in ("pending", None)]
    pending.sort(key=lambda r: (r.date, r.created_at), reverse=True)
    rows = pending[:limit]

    items = [_row_to_transaction(r) for r in rows]
    return ReviewQueueResponse(pending_count=len(pending), items=items)


@router.post("/transactions/{user_id}/{transaction_id}/review", response_model=Transaction)
def review_transaction(
    transaction_id: str,
    payload: ReviewTransactionRequest,
    user_id: str = Depends(resolve_user_id),
) -> Transaction:
    now = datetime.now(timezone.utc)

    row = store.get(TransactionRow, transaction_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "Transaction not found")

    if payload.action == ReviewAction.confirm:
        row.review_status = "reviewed"
        row.reviewed_at = now
        if payload.category is not None:
            row.category = payload.category.value
        if payload.tags is not None:
            row.tags = json.dumps(payload.tags)
        if payload.notes is not None:
            row.notes = payload.notes

    elif payload.action == ReviewAction.recategorize:
        if not payload.category:
            raise HTTPException(400, "Category is required for recategorize action")
        row.category = payload.category.value
        row.review_status = "reviewed"
        row.reviewed_at = now
        if payload.tags is not None:
            row.tags = json.dumps(payload.tags)
        if payload.notes is not None:
            row.notes = payload.notes

    elif payload.action == ReviewAction.skip:
        row.review_status = "skipped"
        row.reviewed_at = now

    to_put: list = [row]

    # If create_rule is requested on confirm or recategorize
    if payload.create_rule and payload.action in (ReviewAction.confirm, ReviewAction.recategorize):
        pattern = (payload.rule_pattern or row.merchant).strip()
        if pattern:
            target_cat = payload.category.value if payload.category else row.category
            rule_row = CategorizationRuleRow(
                user_id=user_id,
                match_type="contains",
                pattern=pattern,
                category=target_cat,
                tags=row.tags,
            )
            to_put.append(rule_row)

            # Auto-apply to any other pending transactions for this user matching pattern
            other_pending = [
                t for t in store.query(TransactionRow, user_id=user_id)
                if t.id != row.id and t.review_status in ("pending", None)
            ]

            for opt in other_pending:
                if matches_pattern(opt.merchant, "contains", pattern):
                    opt.category = target_cat
                    if row.tags:
                        opt.tags = row.tags
                    opt.review_status = "reviewed"
                    opt.reviewed_at = now
                    to_put.append(opt)

    store.put(*to_put)

    return _row_to_transaction(row)


@router.patch("/transactions/{user_id}/{transaction_id}", response_model=Transaction)
def update_transaction(
    transaction_id: str,
    update: TransactionUpdate,
    user_id: str = Depends(resolve_user_id),
) -> Transaction:
    row = store.get(TransactionRow, transaction_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "Transaction not found")

    if update.category is not None:
        row.category = update.category.value
    if update.merchant is not None:
        row.merchant = update.merchant
    if update.tags is not None:
        row.tags = json.dumps(update.tags)
    if update.notes is not None:
        row.notes = update.notes
    if update.review_status is not None:
        row.review_status = update.review_status
        if update.review_status in ("reviewed", "skipped"):
            row.reviewed_at = datetime.now(timezone.utc)

    store.put(row)

    return _row_to_transaction(row)
