"""Household & Co-Piloting collaboration router (Pillar 5D).

Allows inviting partners, managing roles (owner, editor, viewer), hashing
invite tokens securely, aggregating real-time household net worth across
members, and providing multi-player financial visibility.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import resolve_user_id
from app.core import store
from app.models import AccountRow, HouseholdInviteRow, HouseholdMemberRow, HouseholdRow
from app.schemas import (
    AcceptInviteRequest,
    CreateHouseholdRequest,
    CreateInviteRequest,
    Household,
    HouseholdInvite,
    HouseholdMember,
    HouseholdNetWorthSummary,
    HouseholdRole,
    HouseholdSummary,
    InviteStatus,
    MemberWealthContribution,
)

router = APIRouter()

_PERSONA_NAMES = {
    "demo-priya": "Priya",
    "demo-arjun": "Arjun",
    "demo-meera": "Meera",
}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is not None:
        return expires_at < datetime.now(timezone.utc)
    return expires_at < datetime.now(timezone.utc).replace(tzinfo=None)


def _get_user_membership(user_id: str) -> tuple[HouseholdRow, HouseholdMemberRow] | None:
    member_row = store.first(HouseholdMemberRow, user_id=user_id)
    if not member_row:
        return None
    household_row = store.get(HouseholdRow, member_row.household_id)
    if not household_row:
        return None
    return household_row, member_row


def _compute_user_wealth(user_id: str) -> tuple[float, float, float]:
    accounts = store.query(AccountRow, user_id=user_id)
    assets = sum(max(0.0, acc.balance) for acc in accounts)
    liabilities = sum(abs(acc.balance) for acc in accounts if acc.balance < 0)
    net_worth = assets - liabilities
    return assets, liabilities, net_worth


def _build_household_summary(
    household: HouseholdRow, current_user_id: str
) -> HouseholdSummary:
    member_rows = store.query(HouseholdMemberRow, household_id=household.id)
    invite_rows = store.query(HouseholdInviteRow, household_id=household.id)

    # Check invite expiry
    expired = [inv for inv in invite_rows if inv.status == "pending" and _is_expired(inv.expires_at)]
    for inv in expired:
        inv.status = "expired"
    if expired:
        store.put(*expired)


    user_role = HouseholdRole.viewer
    members_breakdown: list[MemberWealthContribution] = []
    members_list: list[HouseholdMember] = []

    total_assets = 0.0
    total_liabilities = 0.0

    for m in member_rows:
        if m.user_id == current_user_id:
            user_role = HouseholdRole(m.role)

        assets, liabilities, nw = _compute_user_wealth(m.user_id)
        total_assets += assets
        total_liabilities += liabilities

        display_name = _PERSONA_NAMES.get(m.user_id, m.user_id.replace("demo-", "").capitalize())
        avatar_letter = display_name[:1].upper()

        members_list.append(
            HouseholdMember(
                id=m.id,
                household_id=m.household_id,
                user_id=m.user_id,
                role=HouseholdRole(m.role),
                joined_at=m.joined_at,
                display_name=display_name,
                avatar_letter=avatar_letter,
                net_worth=nw,
            )
        )

        members_breakdown.append(
            MemberWealthContribution(
                user_id=m.user_id,
                display_name=display_name,
                role=m.role,
                assets=assets,
                liabilities=liabilities,
                net_worth=nw,
                pct_of_household=0.0,
            )
        )

    total_net_worth = total_assets - total_liabilities

    # Compute percentage contribution
    for mb in members_breakdown:
        if total_net_worth > 0:
            mb.pct_of_household = round(max(0.0, (mb.net_worth / total_net_worth) * 100), 1)
        else:
            mb.pct_of_household = round(100.0 / max(1, len(members_breakdown)), 1)

    invites_list = [
        HouseholdInvite(
            id=inv.id,
            household_id=inv.household_id,
            invited_email=inv.invited_email,
            role=HouseholdRole(inv.role),
            status=InviteStatus(inv.status),
            created_at=inv.created_at,
            expires_at=inv.expires_at,
            invite_link=f"/household?invite_id={inv.id}",
        )
        for inv in invite_rows
    ]

    net_worth_summary = HouseholdNetWorthSummary(
        total_net_worth=total_net_worth,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        members_breakdown=members_breakdown,
    )

    return HouseholdSummary(
        household=Household(
            id=household.id,
            name=household.name,
            owner_user_id=household.owner_user_id,
            created_at=household.created_at,
        ),
        members=members_list,
        invites=invites_list,
        net_worth_summary=net_worth_summary,
        user_role=user_role,
    )


@router.get("/api/household/{user_id}", response_model=HouseholdSummary)
def get_household(user_id: str = Depends(resolve_user_id)) -> HouseholdSummary:
    membership = _get_user_membership(user_id)
    if not membership:
        raise HTTPException(404, "User does not belong to any household")
    household, _ = membership
    return _build_household_summary(household, user_id)


@router.post("/api/household/{user_id}", response_model=HouseholdSummary)
def create_household(
    req: CreateHouseholdRequest, user_id: str = Depends(resolve_user_id)
) -> HouseholdSummary:
    existing = _get_user_membership(user_id)
    if existing:
        raise HTTPException(400, "User is already a member of a household")

    household = HouseholdRow(
        name=req.name.strip() or f"{user_id.capitalize()}'s Household",
        owner_user_id=user_id,
    )
    member = HouseholdMemberRow(
        household_id=household.id,
        user_id=user_id,
        role="owner",
    )
    store.put(household, member)

    return _build_household_summary(household, user_id)


@router.post("/api/household/{user_id}/invites", response_model=HouseholdInvite)
def create_invite(
    req: CreateInviteRequest, user_id: str = Depends(resolve_user_id)
) -> HouseholdInvite:
    membership = _get_user_membership(user_id)
    if not membership:
        raise HTTPException(404, "User does not belong to any household")
    household, member = membership
    if member.role not in ["owner", "editor"]:
        raise HTTPException(403, "Viewer role cannot invite new members")

    raw_token = secrets.token_urlsafe(24)
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=7)

    invite = HouseholdInviteRow(
        household_id=household.id,
        invited_email=req.email.strip().lower(),
        role=req.role.value,
        token_hash=token_hash,
        status="pending",
        invited_by_user_id=user_id,
        created_at=now,
        expires_at=expires_at,
    )
    store.put(invite)

    return HouseholdInvite(
        id=invite.id,
        household_id=invite.household_id,
        invited_email=invite.invited_email,
        role=HouseholdRole(invite.role),
        status=InviteStatus(invite.status),
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        token=raw_token,
        invite_link=f"/household?invite={raw_token}",
    )


@router.post("/api/household/{user_id}/invites/accept", response_model=HouseholdSummary)
def accept_invite(
    req: AcceptInviteRequest, user_id: str = Depends(resolve_user_id)
) -> HouseholdSummary:
    existing = _get_user_membership(user_id)
    if existing:
        raise HTTPException(400, "User is already a member of a household")

    token_hash = _hash_token(req.token.strip())
    invite = store.first(HouseholdInviteRow, token_hash=token_hash)

    if not invite:
        raise HTTPException(404, "Invalid or expired invitation token")

    if invite.status != "pending" or _is_expired(invite.expires_at):
        if _is_expired(invite.expires_at) and invite.status == "pending":
            invite.status = "expired"
            store.put(invite)
        raise HTTPException(400, f"Invitation is no longer active (status: {invite.status})")

    household = store.get(HouseholdRow, invite.household_id)
    if not household:
        raise HTTPException(404, "Household no longer exists")

    # Join member
    now = datetime.now(timezone.utc)
    member = HouseholdMemberRow(
        household_id=household.id,
        user_id=user_id,
        role=invite.role,
        joined_at=now,
    )
    invite.status = "accepted"
    # shortcut: read-check-write is not transactional; concurrent accepts can race, upgrade to member id=user_id + create()
    store.put(member, invite)

    return _build_household_summary(household, user_id)


@router.delete("/api/household/{user_id}/invites/{invite_id}")
def revoke_invite(
    invite_id: str, user_id: str = Depends(resolve_user_id)
) -> dict:
    membership = _get_user_membership(user_id)
    if not membership:
        raise HTTPException(404, "User does not belong to any household")
    household, member = membership
    if member.role not in ["owner", "editor"]:
        raise HTTPException(403, "Viewer role cannot revoke invites")

    invite = store.get(HouseholdInviteRow, invite_id)
    if not invite or invite.household_id != household.id:
        raise HTTPException(404, "Invite not found")

    invite.status = "revoked"
    store.put(invite)
    return {"revoked": True, "id": invite_id}


@router.delete("/api/household/{user_id}/members/{member_user_id}")
def remove_member(
    member_user_id: str, user_id: str = Depends(resolve_user_id)
) -> dict:
    membership = _get_user_membership(user_id)
    if not membership:
        raise HTTPException(404, "User does not belong to any household")
    household, member = membership

    # Allow user to leave themselves, or owner to remove other members
    if user_id != member_user_id and member.role != "owner":
        raise HTTPException(403, "Only the household owner can remove other members")

    if member_user_id == household.owner_user_id and user_id == member_user_id:
        # Check if other members exist
        other_members = [
            m for m in store.query(HouseholdMemberRow, household_id=household.id)
            if m.user_id != user_id
        ]
        if other_members:
            raise HTTPException(400, "Owner cannot leave while other members exist; transfer ownership first or delete household")

    target_member = store.first(
        HouseholdMemberRow, household_id=household.id, user_id=member_user_id
    )

    if not target_member:
        raise HTTPException(404, "Member not found in household")

    store.delete(HouseholdMemberRow, target_member.id)
    return {"removed": True, "user_id": member_user_id}


@router.get("/api/household/{user_id}/networth", response_model=HouseholdNetWorthSummary)
def get_household_networth(user_id: str = Depends(resolve_user_id)) -> HouseholdNetWorthSummary:
    membership = _get_user_membership(user_id)
    if not membership:
        raise HTTPException(404, "User does not belong to any household")
    household, _ = membership
    summary = _build_household_summary(household, user_id)
    return summary.net_worth_summary
