"""Net worth over time -- reconstructed live from Account + Transaction
history (no stored historical-balance table exists, so we don't fabricate
one; see `_reconstruct_account_daily_balances` for the exact method).

Not wired into app.main by this module -- the lead integrates
`networth_router.router` into main.py, to avoid touching the same file as
the sibling ledger/budgets agent.

Reconstruction method (documented once here, this is the load-bearing part):

For a single account with CURRENT balance `B` and transaction history, the
balance as-of the end of day `d` is:

    balance(d) = B - sum(txn.amount for txn in this account where txn.date > d)

i.e. walk backward from today, undoing each transaction's effect on the
running balance one day at a time. This is exact (not a synthetic/fabricated
trend) as long as `B` really is the sum of every transaction ever posted to
the account (true for both the seeded personas and any uploaded-CSV user,
since `balance` is never independently edited outside of transaction
ingestion in this codebase).

Accounts that did not exist for the full requested window: we do NOT
extrapolate a balance before the account's own first transaction (there is
no `opened_date` field on AccountRow, and a reconstructed number before the
account had any activity would be fabricated). Chosen, documented rule:
  - If the account has >=1 transaction: for days strictly before its
    earliest transaction date, the account is simply excluded from that
    day's net-worth sum (it didn't exist yet, so it shouldn't inflate or
    deflate a total for a day before it existed).
  - If the account has zero transactions at all, there is no history to
    reconstruct from either way -- its current balance is used flat across
    the entire window (the only defensible value we have for every day).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from app.core.auth import resolve_user_id
from app.core import store
from app.models import AccountRow, TransactionRow
from app.schemas import Account, CreateAccountRequest, NetWorthHistory, NetWorthPoint

router = APIRouter()

_DEFAULT_DAYS = 180
_MAX_DAYS = 730


def _account_row_to_schema(row: AccountRow) -> Account:
    return Account(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        type=row.type,
        balance=row.balance,
        credit_limit=row.credit_limit,
        interest_rate_apr=row.interest_rate_apr,
        currency=row.currency,
    )


def _reconstruct_account_daily_balances(
    account: AccountRow, txns: list[TransactionRow], days: int, today: date
) -> dict[date, float]:
    """Returns {day: balance-as-of-end-of-day} for `days` days ending at
    `today` (inclusive), for this single account. Days before the account's
    earliest transaction (if it has any) are simply absent from the result
    dict -- see module docstring."""
    window_start = today - timedelta(days=days - 1)

    if not txns:
        # No history to reconstruct from either way -- flat current balance.
        return {today - timedelta(days=i): account.balance for i in range(days)}

    by_date: dict[date, float] = defaultdict(float)
    for t in txns:
        by_date[t.date] += t.amount

    earliest_txn_date = min(t.date for t in txns)

    balances: dict[date, float] = {}
    cumulative_subtract = 0.0
    d = today
    while d >= window_start:
        if d >= earliest_txn_date:
            balances[d] = account.balance - cumulative_subtract
        # about to step to d-1: transactions dated exactly `d` must now be
        # undone for every earlier day.
        cumulative_subtract += by_date.get(d, 0.0)
        d = d - timedelta(days=1)
    return balances


@router.get("/api/networth/{user_id}/history", response_model=NetWorthHistory)
def net_worth_history(
    user_id: str = Depends(resolve_user_id),
    days: int = Query(default=_DEFAULT_DAYS, ge=1, le=_MAX_DAYS),
) -> NetWorthHistory:
    today = date.today()
    accounts = store.query(AccountRow, user_id=user_id)
    current = float(sum(a.balance for a in accounts))
    if not accounts:
        return NetWorthHistory(points=[], current=0.0)

    txns_by_account: dict[str, list[TransactionRow]] = defaultdict(list)
    for t in store.query(TransactionRow, user_id=user_id):
        txns_by_account[t.account_id].append(t)

    totals: dict[date, float] = defaultdict(float)
    counts: dict[date, int] = defaultdict(int)
    for account in accounts:
        per_day = _reconstruct_account_daily_balances(account, txns_by_account.get(account.id, []), days, today)
        for d, bal in per_day.items():
            totals[d] += bal
            counts[d] += 1

    points = [
        NetWorthPoint(date=d, net_worth=totals[d])
        for d in sorted(totals.keys())
        if counts[d] > 0
    ]
    return NetWorthHistory(points=points, current=current)


@router.get("/api/accounts/{user_id}", response_model=list[Account])
def list_accounts(user_id: str = Depends(resolve_user_id)) -> list[Account]:
    return [_account_row_to_schema(a) for a in store.query(AccountRow, user_id=user_id)]


@router.post("/api/accounts/{user_id}", response_model=Account, status_code=201)
def create_account(req: CreateAccountRequest, user_id: str = Depends(resolve_user_id)) -> Account:
    row = AccountRow(
        user_id=user_id,
        name=req.name.strip(),
        type=req.type.value,
        balance=req.balance,
        credit_limit=req.credit_limit,
        interest_rate_apr=req.interest_rate_apr,
    )
    store.put(row)
    return _account_row_to_schema(row)
