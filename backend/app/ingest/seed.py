"""CLI to (re)seed the 3 demo personas into the configured database.

Usage (from backend/):
    python -m app.ingest.seed

Idempotent: safe to re-run -- clears and reinserts all rows for each demo
user_id (demo-priya, demo-arjun, demo-meera) rather than accumulating
duplicates.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from app.core import store
from app.models import (
    AccountRow,
    BudgetRow,
    CategorizationRuleRow,
    DebtRow,
    GoalRow,
    HouseholdInviteRow,
    HouseholdMemberRow,
    HouseholdRow,
    IncomeRow,
    TransactionRow,
)
from app.ingest.personas import PERSONA_CONFIGS, generate_persona


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _clear_user(user_id: str) -> None:
    for model in (TransactionRow, DebtRow, IncomeRow, AccountRow, CategorizationRuleRow,
                  BudgetRow, GoalRow, HouseholdMemberRow):
        store.delete_where(model, user_id=user_id)
    store.delete_where(HouseholdRow, owner_user_id=user_id)
    store.delete_where(HouseholdInviteRow, invited_by_user_id=user_id)


def seed_all() -> None:
    for user_id, config in PERSONA_CONFIGS.items():
        _clear_user(user_id)

        data = generate_persona(config)
        store.put(*data.accounts, *data.transactions, *data.debts, *data.incomes,
                  *data.rules, *data.budgets, *data.goals)

        print(
            f"Seeded {user_id}: {len(data.accounts)} accounts, "
            f"{len(data.transactions)} transactions, {len(data.debts)} debts, "
            f"{len(data.incomes)} incomes, {len(data.rules)} rules, {len(data.budgets)} budgets, "
            f"{len(data.goals)} goals"
        )

    # Seed shared household for Priya & Arjun
    now = datetime.now(timezone.utc)
    hh = HouseholdRow(
        id="hh-priya-arjun",
        name="Priya & Partner Family",
        owner_user_id="demo-priya",
        created_at=now - timedelta(days=60),
    )
    m1 = HouseholdMemberRow(
        household_id="hh-priya-arjun",
        user_id="demo-priya",
        role="owner",
        joined_at=now - timedelta(days=60),
    )
    m2 = HouseholdMemberRow(
        household_id="hh-priya-arjun",
        user_id="demo-arjun",
        role="editor",
        joined_at=now - timedelta(days=45),
    )

    inv1 = HouseholdInviteRow(
        household_id="hh-priya-arjun",
        invited_email="rohan.sharma@example.com",
        role="editor",
        token_hash=_hash_token("demo-partner-token-rohan"),
        status="pending",
        invited_by_user_id="demo-priya",
        created_at=now - timedelta(days=2),
        expires_at=now + timedelta(days=5),
    )
    store.put(hh, m1, m2, inv1)
    print("Seeded demo household: 'Priya & Partner Family' (Members: Priya, Arjun; Pending: Rohan)")


def seed_if_empty() -> None:
    """Seed the demo personas only if they're missing (fresh/ephemeral DB,
    e.g. a serverless cold start). Cheap no-op otherwise."""
    if store.first(AccountRow, user_id="demo-priya") is None:
        seed_all()


if __name__ == "__main__":
    seed_all()
