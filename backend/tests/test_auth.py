"""Tests for app.core.auth -- the Firebase ID-token verification that closes the IDOR gap
(previously every route trusted a raw user_id path param with zero auth).
Google's verifier is monkeypatched for the happy paths; the forged-token test
runs the real verifier with no certs so it stays offline.
"""
from __future__ import annotations

import base64
import json
import time

import pytest
from fastapi import HTTPException

from app.core import auth as auth_module
from app.core.auth import resolve_user_id


def _fake_jwt(claims: dict, alg: str = "HS256") -> str:
    """Unsigned-looking JWT shape; signature is junk. Only used where verification is mocked or must fail."""
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{enc({'alg': alg, 'typ': 'JWT'})}.{enc(claims)}.c2ln"


def _as_firebase_user(monkeypatch, sub: str):
    monkeypatch.setattr(auth_module.google_id_token, "verify_firebase_token", lambda *a, **k: {"sub": sub})
    return _fake_jwt({"sub": sub})


@pytest.mark.asyncio
async def test_resolve_user_id_allows_demo_persona_with_no_token():
    result = await resolve_user_id(user_id="demo-priya", authorization=None)
    assert result == "demo-priya"


@pytest.mark.asyncio
async def test_resolve_user_id_rejects_real_user_with_no_token():
    with pytest.raises(HTTPException) as exc_info:
        await resolve_user_id(user_id="real-user-uuid", authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_user_id_rejects_token_user_id_mismatch(monkeypatch):
    """The core IDOR fix: a valid token for user A must not grant access to
    user B's data just because B's id is in the URL."""
    token = _as_firebase_user(monkeypatch, "user-A")

    with pytest.raises(HTTPException) as exc_info:
        await resolve_user_id(user_id="user-B", authorization=f"Bearer {token}")
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_resolve_user_id_allows_matching_token(monkeypatch):
    token = _as_firebase_user(monkeypatch, "user-A")

    result = await resolve_user_id(user_id="user-A", authorization=f"Bearer {token}")
    assert result == "user-A"


@pytest.mark.asyncio
async def test_resolve_user_id_allows_demo_persona_even_with_valid_token_for_someone_else(monkeypatch):
    """Signed-in users can still browse the public demo personas."""
    token = _as_firebase_user(monkeypatch, "user-A")

    result = await resolve_user_id(user_id="demo-meera", authorization=f"Bearer {token}")
    assert result == "demo-meera"


@pytest.mark.asyncio
async def test_resolve_user_id_rejects_malformed_auth_header():
    with pytest.raises(HTTPException) as exc_info:
        await resolve_user_id(user_id="demo-priya", authorization="NotBearer sometoken")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_forged_unsigned_firebase_token_is_rejected(monkeypatch):
    """Regression: a token claiming a Firebase issuer used to be trusted
    without signature verification, letting anyone impersonate any user."""
    monkeypatch.setattr(auth_module.google_id_token, "_fetch_certs", lambda *a, **k: {})  # no network
    forged = _fake_jwt({"iss": "https://securetoken.google.com/hackmatrix-3764f", "sub": "user-A", "exp": time.time() + 3600})
    with pytest.raises(HTTPException) as exc_info:
        await resolve_user_id(user_id="user-A", authorization=f"Bearer {forged}")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verified_firebase_token_is_accepted(monkeypatch):
    token = _as_firebase_user(monkeypatch, "user-A")
    assert await resolve_user_id(user_id="user-A", authorization=f"Bearer {token}") == "user-A"
