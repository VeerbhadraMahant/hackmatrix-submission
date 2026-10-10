"""API routes. Phase-0 stubs return fixture data so the frontend can build
against a stable contract immediately; each background agent replaces the
relevant stub with real logic (see comments) without changing response
shapes (those are fixed in app.schemas).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile

from app.analytics.recurring import normalize_merchant
from app.copilot.engine import answer as copilot_answer
from app.core.auth import DEMO_USER_IDS, resolve_user_id
from app.core.config import get_settings
from app.core import store
from app.core.ratelimit import chat_limiter, upload_limiter
from app.copilot.watcher import watch
from app.forecast.alerts import maybe_send_gap_alert
from app.ingest.categorize import categorize
from app.ingest.snapshot import build_dashboard_snapshot, get_last_snapshot
from app.ingest.upload import parse_transaction_csv
from app.models import AccountRow, EventRow, TransactionRow
from app.schemas import (
    AnswerContract,
    ChatRequest,
    DashboardSnapshot,
    RecomputeDiff,
    SimulationRequest,
    SimulationResult,
)
from app.simulate.engine import ForecastInputs, simulate

router = APIRouter()

_LIQUID_ACCOUNT_TYPES = {"checking", "savings"}

# CSV upload hardening: cap both raw size and parsed row count so a huge or
# malformed file can't exhaust memory/DB time (resource-exhaustion DoS).
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB
_MAX_UPLOAD_ROWS = 20_000

# Typical interval (days) per frequency -- mirrors the buckets
# app/analytics/recurring.py's detect_recurring() classifies into, so
# backdated occurrences we synthesize below land in the same bucket the
# detector would assign them.
_FREQUENCY_INTERVAL_DAYS = {
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,
    "quarterly": 90,
    "annual": 365,
}


def _starting_balance_for_user(user_id: str) -> float:
    """Real starting balance: sum of the user's checking+savings account
    balances (see app.ingest.snapshot module docstring for the rationale).
    Recomputed here directly from Account rows (rather than stashed on
    DashboardSnapshot, which has no dedicated field for it) so this stays a
    single source of truth shared with build_dashboard_snapshot."""
    accounts = store.query(AccountRow, user_id=user_id)
    if not accounts:
        return 42_000.0  # fixture-fallback users have no Account rows
    return float(sum(a.balance for a in accounts if a.type in _LIQUID_ACCOUNT_TYPES))


def _forecast_inputs_from_snapshot(snap: DashboardSnapshot, user_id: str) -> ForecastInputs:
    """Build simulate.engine.ForecastInputs from a DashboardSnapshot plus a
    real starting balance looked up from the DB."""
    starting_balance = _starting_balance_for_user(user_id)
    return ForecastInputs(
        starting_balance=starting_balance,
        recurring=snap.recurring_obligations,
        debts=snap.debts,
        transactions=None,
        horizon_days=snap.forecast.horizon_days,
        monthly_income=snap.monthly_income,
    )


@router.get("/health")
def health_check() -> dict:
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/dashboard/{user_id}", response_model=DashboardSnapshot)
def get_dashboard(user_id: str = Depends(resolve_user_id)) -> DashboardSnapshot:
    return build_dashboard_snapshot(user_id)


async def _resolve_body_user_id(req: ChatRequest, authorization: str | None = Header(default=None)) -> str:
    """Same trust rule as `resolve_user_id`, but for endpoints (like /chat)
    where user_id arrives in the JSON body rather than the URL path."""
    return await resolve_user_id(req.user_id, authorization)


@router.post("/chat", response_model=AnswerContract)
def chat(req: ChatRequest, user_id: str = Depends(_resolve_body_user_id)) -> AnswerContract:
    if not req.message.strip():
        raise HTTPException(400, "message must not be empty")
    chat_limiter.check(user_id)
    return copilot_answer(user_id, req.message, force_offline=req.force_offline, model=req.model, history=req.history[-10:])


@router.get("/schemes")
def schemes_feed() -> dict:
    """Upcoming money deadlines + always-open schemes, plus friendly chat nudges."""
    from app.copilot import schemes

    return {**schemes.upcoming(), "nudges": schemes.nudges()}


@router.post("/simulate/{user_id}", response_model=SimulationResult)
def run_simulation(req: SimulationRequest, user_id: str = Depends(resolve_user_id)) -> SimulationResult:
    snap = build_dashboard_snapshot(user_id)
    inputs = _forecast_inputs_from_snapshot(snap, user_id)
    try:
        return simulate(
            req.action,
            req.action_params,
            current_forecast_inputs=inputs,
            current_health_score=snap.health_score.overall,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/upload/{user_id}", response_model=RecomputeDiff)
async def upload_transactions(file: UploadFile, user_id: str = Depends(resolve_user_id)) -> RecomputeDiff:
    """Accepts a multipart bank-statement CSV, parses + categorizes it, and
    persists the resulting transactions for `user_id`. account_id defaults to
    a synthetic per-user "uploaded" account since bank CSV exports rarely
    carry our internal account ids.

    Returns a real before/after RecomputeDiff: "before" is whatever snapshot
    was last cached for this user (or a freshly computed one if none was
    cached yet), "after" is recomputed post-ingest.
    """
    upload_limiter.check(user_id)
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "uploaded file is empty")
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (max {_MAX_UPLOAD_BYTES // 1024 // 1024}MB)")

    account_id = f"acc-uploaded-{user_id}"
    try:
        rows = parse_transaction_csv(raw, user_id=user_id, account_id=account_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if len(rows) > _MAX_UPLOAD_ROWS:
        raise HTTPException(413, f"Too many transactions in one upload (max {_MAX_UPLOAD_ROWS})")

    before = get_last_snapshot(user_id) or build_dashboard_snapshot(user_id)

    # A real user with no account yet gets one backing the synthetic id,
    # so the snapshot leaves the empty placeholder state.
    has_account = store.first(AccountRow, user_id=user_id)
    new_rows = list(rows)
    if not has_account and user_id not in DEMO_USER_IDS:
        new_rows.insert(0, AccountRow(id=account_id, user_id=user_id, name="Uploaded statement", type="checking", balance=0))
    store.put(*new_rows)  # shortcut: batches of 500 are not atomic across batches; a mid-upload failure leaves a partial upload

    after = build_dashboard_snapshot(user_id)

    diff = _build_recompute_diff(trigger="csv_upload", before=before, after=after,
                                  extra_narrative=f"Ingested {len(rows)} transactions from {file.filename or 'uploaded file'}.")
    diff.insights = watch(user_id, list(rows), new_gap=_new_gap(before, after))
    return diff


def _new_gap(before: DashboardSnapshot, after: DashboardSnapshot) -> bool:
    b, a = before.forecast.first_gap_date, after.forecast.first_gap_date
    return a is not None and (b is None or a < b)


def _build_recompute_diff(*, trigger: str, before: DashboardSnapshot, after: DashboardSnapshot,
                           extra_narrative: str = "") -> RecomputeDiff:
    """Diff two DashboardSnapshots into a RecomputeDiff: which recommended
    actions are new, which are no longer recommended, and how the headline
    numbers (health score, first cash-flow gap) moved."""
    before_actions = {r.action for r in before.insights.recommendations}
    after_by_action = {r.action: r for r in after.insights.recommendations}

    new_recommendations = [r for r in after.insights.recommendations if r.action not in before_actions]
    removed_actions = [a for a in before_actions if a not in after_by_action]

    delta = after.health_score.overall - before.health_score.overall
    narrative_parts = [extra_narrative] if extra_narrative else []
    if abs(delta) < 0.05:
        narrative_parts.append(f"Health score is essentially unchanged ({after.health_score.overall:.1f}).")
    else:
        direction = "improved" if delta > 0 else "declined"
        narrative_parts.append(
            f"Health score {direction} from {before.health_score.overall:.1f} to "
            f"{after.health_score.overall:.1f} ({delta:+.1f})."
        )
    if before.forecast.first_gap_date != after.forecast.first_gap_date:
        narrative_parts.append(
            f"Projected cash-flow gap date moved from {before.forecast.first_gap_date} to "
            f"{after.forecast.first_gap_date}."
        )
    if new_recommendations:
        narrative_parts.append(f"{len(new_recommendations)} new recommendation(s) surfaced.")
    if removed_actions:
        narrative_parts.append(f"{len(removed_actions)} recommendation(s) are no longer relevant.")

    return RecomputeDiff(
        trigger=trigger,
        health_score_before=before.health_score.overall,
        health_score_after=after.health_score.overall,
        forecast_first_gap_before=before.forecast.first_gap_date,
        forecast_first_gap_after=after.forecast.first_gap_date,
        new_recommendations=new_recommendations,
        removed_recommendation_actions=removed_actions,
        narrative=" ".join(narrative_parts),
    )


@router.post("/events/{user_id}", response_model=RecomputeDiff)
def add_event(payload: dict, user_id: str = Depends(resolve_user_id)) -> RecomputeDiff:
    """Persist a new event (transaction, income, or debt) for `user_id`, then
    recompute the dashboard snapshot before vs. after so the UI can show
    exactly how recommendations/health score/forecast changed.

    Expected payload shapes (all keyed by "kind"):
      {"kind": "transaction", "amount": -450, "merchant": "...",
       "category": "dining" (optional -- categorized if omitted),
       "date": "2026-09-29" (optional -- defaults to today),
       "account_id": "..." (optional -- defaults to the user's first
       checking account, or a synthetic "acc-events-{user_id}")}
    """
    kind = payload.get("kind", "transaction")
    new_txns: list[TransactionRow] = []

    def _default_checking_account(account_id: str | None) -> str:
        if account_id:
            return account_id
        checking = store.first(AccountRow, user_id=user_id, type="checking")
        if checking:
            return checking.id
        savings = store.first(AccountRow, user_id=user_id, type="savings")
        if savings and user_id not in DEMO_USER_IDS:
            return savings.id
        if user_id in DEMO_USER_IDS:
            return f"acc-events-{user_id}"
        # Real user adding their first transaction without any account yet:
        # create a default one so the snapshot stops being the empty
        # placeholder (it keys off the user having >= 1 AccountRow).
        default = AccountRow(user_id=user_id, name="Main account", type="checking", balance=0)
        store.put(default)
        return default.id

    before = get_last_snapshot(user_id) or build_dashboard_snapshot(user_id)

    if kind == "transaction":
        amount = payload.get("amount")
        if amount is None:
            raise HTTPException(400, "transaction event requires 'amount'")
        merchant = payload.get("merchant", "Manual entry")
        category = payload.get("category")
        if category:
            category_value = category
        else:
            category_value = categorize(merchant, float(amount)).value
        txn_date_str = payload.get("date")
        txn_date = (
            datetime.strptime(txn_date_str, "%Y-%m-%d").date()
            if txn_date_str
            else datetime.now(timezone.utc).date()
        )
        account_id = _default_checking_account(payload.get("account_id"))

        new_txns.append(
            TransactionRow(
                user_id=user_id,
                account_id=account_id,
                date=txn_date,
                amount=float(amount),
                merchant=merchant,
                category=category_value,
                description=payload.get("description"),
                is_recurring=bool(payload.get("is_recurring", False)),
                recurring_group_id=payload.get("recurring_group_id"),
            )
        )
        store.put(*new_txns)
    elif kind == "recurring":
        # The frontend's "New recurring obligation" form (Timeline page)
        # posts {merchant, amount, frequency, next_expected_date} -- this
        # branch was previously missing entirely, so every submission
        # 400'd. detect_recurring() (app/analytics/recurring.py) only
        # surfaces a merchant once it has >= 3 historical occurrences, so
        # a single future-dated row would be invisible to it; backdate 3
        # occurrences at the chosen cadence instead, which makes the new
        # obligation show up on the very next dashboard fetch exactly
        # like every other recurring obligation.
        amount = payload.get("amount")
        if amount is None:
            raise HTTPException(400, "recurring event requires 'amount'")
        merchant = payload.get("merchant", "Manual entry")
        frequency = payload.get("frequency", "monthly")
        interval_days = _FREQUENCY_INTERVAL_DAYS.get(frequency, 30)
        anchor_str = payload.get("next_expected_date")
        anchor = (
            datetime.strptime(anchor_str, "%Y-%m-%d").date()
            if anchor_str
            else datetime.now(timezone.utc).date()
        )
        # A recurring "obligation" is a commitment (rent, EMI,
        # subscription, ...) -- always an outflow, regardless of the sign
        # the caller passed in.
        signed_amount = -abs(float(amount))
        category = payload.get("category")
        category_value = category if category else categorize(merchant, signed_amount).value
        account_id = _default_checking_account(payload.get("account_id"))

        # Use the same normalization detect_recurring() applies so a
        # group id assigned here matches what recurring-detection would
        # independently compute for the same merchant (previously this
        # used a naive lower/replace that diverged from
        # app.analytics.recurring.normalize_merchant, e.g. dropping
        # trailing numeric IDs differently).
        group_id = f"rg-{normalize_merchant(merchant).replace(' ', '-')}"
        for i in range(3, 0, -1):
            store.put(
                TransactionRow(
                    user_id=user_id,
                    account_id=account_id,
                    date=anchor - timedelta(days=interval_days * i),
                    amount=signed_amount,
                    merchant=merchant,
                    category=category_value,
                    description=payload.get("description"),
                    is_recurring=True,
                    recurring_group_id=group_id,
                )
            )
    else:
        raise HTTPException(400, f"Unsupported event kind: {kind!r}")

    store.put(EventRow(user_id=user_id, kind=kind, payload_json=json.dumps(payload, default=str)))

    after = build_dashboard_snapshot(user_id)

    diff = _build_recompute_diff(trigger=kind, before=before, after=after)
    diff.insights = watch(user_id, new_txns, new_gap=_new_gap(before, after))
    return diff


@router.post("/alerts/gap/{user_id}")
def send_gap_alert(payload: dict, user_id: str = Depends(resolve_user_id)) -> dict:
    """Explicit, user-triggered cash-flow gap alert email. Not called
    automatically by any other route -- must be invoked by a frontend
    button so we never spam users on every dashboard load."""
    settings = get_settings()
    if not settings.has_resend:
        raise HTTPException(503, "Email alerts are not configured (no RESEND_API_KEY).")

    user_email = payload.get("email")
    if not user_email:
        raise HTTPException(400, "payload must include 'email'")

    snap = build_dashboard_snapshot(user_id)
    sent = maybe_send_gap_alert(user_email, snap.forecast)
    return {"sent": sent}
