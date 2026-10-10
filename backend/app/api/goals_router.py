"""Goals CRUD + live progress projection.

Integrated in app.main alongside budgets and transactions routers.
Provides goal creation, updates with cover art, funding account auto-tracking,
and required monthly savings calculations.
"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Depends, HTTPException

from app.analytics.goals import project_goal
from app.analytics.savings import trailing_savings_rate
from app.core.auth import resolve_user_id
from app.core import store
from app.ingest.snapshot import _avg_income_expenses, _transactions_df
from app.models import AccountRow, GoalRow, TransactionRow
from app.schemas import Goal, GoalCreateRequest, GoalProgress, GoalUpdateRequest

router = APIRouter()

_TRAILING_MONTHS = 3


def _goal_row_to_schema(row: GoalRow, linked_balance: float | None = None) -> Goal:
    curr_amount = row.current_amount
    if row.auto_track and linked_balance is not None:
        curr_amount = linked_balance
    return Goal(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        target_amount=row.target_amount,
        target_date=row.target_date,
        current_amount=curr_amount,
        cover_key=row.cover_key or "general",
        funding_account_id=row.funding_account_id,
        auto_track=bool(row.auto_track),
    )


def _estimated_monthly_contribution(user_id: str) -> float:
    """Trailing-3-month avg income * trailing savings rate, floored at 0."""
    df = _transactions_df(store.query(TransactionRow, user_id=user_id))
    if df.empty:
        return 0.0
    monthly_income, _ = _avg_income_expenses(df, months=_TRAILING_MONTHS)
    rate = trailing_savings_rate(df, months=_TRAILING_MONTHS)
    return max(0.0, monthly_income * rate)


def _to_progress(goal: Goal, monthly_contribution: float) -> GoalProgress:
    projection = project_goal(goal, monthly_contribution)
    required_monthly = 0.0
    if goal.target_date:
        today = date.today()
        months = (goal.target_date.year - today.year) * 12 + (goal.target_date.month - today.month)
        if goal.target_date.day < today.day and months > 0:
            months = max(1, months)
        months_to_target = max(1, months) if goal.target_date > today else 1
        remaining = max(0.0, goal.target_amount - goal.current_amount)
        if remaining > 0:
            required_monthly = round(remaining / months_to_target, 2)

    return GoalProgress(
        goal=goal,
        monthly_contribution=monthly_contribution,
        projected_completion_date=projection["projected_completion_date"],
        on_track=projection["on_track"],
        months_remaining=projection["months_remaining"],
        required_monthly=required_monthly,
    )


@router.get("/api/goals/{user_id}", response_model=list[GoalProgress])
def list_goals(user_id: str = Depends(resolve_user_id)) -> list[GoalProgress]:
    rows = store.query(GoalRow, user_id=user_id)
    accounts = {acc.id: acc for acc in store.query(AccountRow, user_id=user_id)}
    monthly_contribution = _estimated_monthly_contribution(user_id)
    result = []
    for row in rows:
        linked_bal = None
        if row.funding_account_id and row.funding_account_id in accounts:
            linked_bal = max(0.0, accounts[row.funding_account_id].balance)
        schema = _goal_row_to_schema(row, linked_balance=linked_bal)
        result.append(_to_progress(schema, monthly_contribution))
    return result


@router.post("/api/goals/{user_id}", response_model=GoalProgress)
def create_goal(req: GoalCreateRequest, user_id: str = Depends(resolve_user_id)) -> GoalProgress:
    if req.funding_account_id:
        acc = store.get(AccountRow, req.funding_account_id)
        if not acc or acc.user_id != user_id:
            raise HTTPException(400, "Funding account does not exist or does not belong to user")

    current_amount = req.current_amount
    if req.auto_track and req.funding_account_id:
        acc = store.get(AccountRow, req.funding_account_id)
        if acc:
            current_amount = max(0.0, acc.balance)

    row = GoalRow(
        user_id=user_id,
        name=req.name,
        target_amount=req.target_amount,
        target_date=req.target_date,
        current_amount=current_amount,
        cover_key=req.cover_key or "general",
        funding_account_id=req.funding_account_id,
        auto_track=req.auto_track,
    )
    store.put(row)
    monthly_contribution = _estimated_monthly_contribution(user_id)
    return _to_progress(_goal_row_to_schema(row), monthly_contribution)


def _get_owned_goal(user_id: str, goal_id: str) -> GoalRow:
    row = store.get(GoalRow, goal_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "Goal not found")
    return row


@router.patch("/api/goals/{user_id}/{goal_id}", response_model=GoalProgress)
def update_goal(
    goal_id: str, req: GoalUpdateRequest, user_id: str = Depends(resolve_user_id)
) -> GoalProgress:
    row = _get_owned_goal(user_id, goal_id)
    if req.funding_account_id is not None:
        if req.funding_account_id != "":
            acc = store.get(AccountRow, req.funding_account_id)
            if not acc or acc.user_id != user_id:
                raise HTTPException(400, "Funding account does not exist or does not belong to user")
            row.funding_account_id = req.funding_account_id
        else:
            row.funding_account_id = None
    if req.name is not None:
        row.name = req.name
    if req.current_amount is not None:
        row.current_amount = req.current_amount
    if req.target_amount is not None:
        row.target_amount = req.target_amount
    if req.target_date is not None:
        row.target_date = req.target_date
    if req.cover_key is not None:
        row.cover_key = req.cover_key
    if req.auto_track is not None:
        row.auto_track = req.auto_track
        if row.auto_track and row.funding_account_id:
            acc = store.get(AccountRow, row.funding_account_id)
            if acc:
                row.current_amount = max(0.0, acc.balance)

    store.put(row)
    monthly_contribution = _estimated_monthly_contribution(user_id)
    return _to_progress(_goal_row_to_schema(row), monthly_contribution)


@router.delete("/api/goals/{user_id}/{goal_id}")
def delete_goal(goal_id: str, user_id: str = Depends(resolve_user_id)) -> dict:
    _get_owned_goal(user_id, goal_id)
    store.delete(GoalRow, goal_id)
    return {"deleted": True, "id": goal_id}
