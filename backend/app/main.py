from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api.budgets_router import router as budgets_router
from app.api.connectors_router import router as connectors_router
from app.api.copilot_feed_router import router as copilot_feed_router
from app.api.documents_router import router as documents_router
from app.api.goals_router import router as goals_router
from app.api.household_router import router as household_router
from app.api.networth_router import router as networth_router
from app.api.notifications_router import router as notifications_router
from app.api.plan_router import router as plan_router
from app.api.routes import router
from app.api.rules_router import router as rules_router
from app.api.security_router import router as security_router
from app.api.tax_router import router as tax_router
from app.api.transactions_router import router as transactions_router
from app.core.audit import log_audit_event

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


_seeded = False


def _ensure_seeded() -> None:
    """Seed the demo personas once per process if the store is empty (fresh
    Firestore, or the ephemeral in-memory fallback after a serverless cold
    start). Never raises: a seeding problem must not take the API down."""
    global _seeded
    if _seeded:
        return
    try:
        from app.ingest.seed import seed_if_empty

        seed_if_empty()
        _seeded = True
    except Exception as exc:  # noqa: BLE001
        print(f"[seed] skipped: {exc!r}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_in_threadpool(_ensure_seeded)
    yield


app = FastAPI(title="FinPilot API", version="0.1.0", lifespan=lifespan)

# SECURITY: in dev, allow any localhost/127.0.0.1 port (next dev picks a
# different one whenever 3000 is busy). In production, ALLOWED_ORIGINS must
# be set explicitly to the real deployed frontend origin(s) -- comma
# separated -- so the API can't be called cross-origin from an arbitrary
# site with a signed-in user's cookies/token. Unset in prod = no prod
# origins trusted (fails closed, not open).
_prod_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_prod_origins,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(budgets_router, prefix="/api")
app.include_router(plan_router, prefix="/api")
app.include_router(copilot_feed_router, prefix="/api")
# These already embed "/api/..." in each route's own path decorator
# (unlike routes.py/transactions_router/budgets_router, which rely on the
# prefix="/api" above) -- no prefix here, or paths would double up.
app.include_router(connectors_router)
app.include_router(goals_router)
app.include_router(documents_router)
app.include_router(household_router)
app.include_router(networth_router)
app.include_router(notifications_router)
app.include_router(tax_router)
app.include_router(rules_router)
app.include_router(security_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Return a JSON 500 with the error type instead of letting the serverless
    runtime replace it with an opaque FUNCTION_INVOCATION_FAILED page."""
    print(f"[error] {request.method} {request.url.path}: {exc!r}")
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    """Best-effort security audit trail (see app.core.audit): records every
    auth denial/rate-limit hit and every successful mutating request. The
    user_id here is extracted heuristically from the path (the last path
    segment after a known prefix) since middleware runs outside the
    per-route Depends() that resolves+verifies it -- good enough for a
    human reviewing logs, not used for any access-control decision."""
    # Some serverless runtimes skip ASGI lifespan, so also seed lazily on the
    # first request (cheap no-op afterwards).
    await run_in_threadpool(_ensure_seeded)
    response = await call_next(request)

    path = request.url.path
    method = request.method
    status = response.status_code

    def _guess_user_id() -> str | None:
        parts = [p for p in path.split("/") if p]
        if len(parts) < 3 or parts[0] != "api":
            return None
        # user_id is always the 3rd segment for these resources (even when
        # further sub-path segments follow, e.g. /api/budgets/{user_id}/status
        # or /api/transactions/{user_id}/{transaction_id}).
        if parts[1] in {"transactions", "budgets", "goals", "tax", "rules", "household", "plan"}:
            return parts[2]

        # For these, user_id is the LAST segment (/api/dashboard/{user_id},
        # /api/alerts/gap/{user_id}, /api/accounts/{user_id}, etc.).
        if parts[1] in {"dashboard", "simulate", "upload", "events", "alerts", "accounts", "notifications"}:
            return parts[-1]
        # /api/networth/{user_id}/history
        if parts[1] == "networth":
            return parts[2]
        # /api/copilot/insights/{user_id}
        if parts[1] == "copilot":
            return parts[-1]
        return None

    try:
        if status in (401, 403, 429):
            await run_in_threadpool(
                log_audit_event,
                user_id=_guess_user_id(),
                event_type="rate_limited" if status == 429 else "auth_denied",
                method=method,
                path=path,
                status_code=status,
                client_ip=request.client.host if request.client else None,
            )
        elif method in _MUTATING_METHODS and 200 <= status < 300 and path.startswith("/api/"):
            await run_in_threadpool(
                log_audit_event,
                user_id=_guess_user_id(),
                event_type="mutation",
                method=method,
                path=path,
                status_code=status,
                client_ip=request.client.host if request.client else None,
            )
    except Exception:  # noqa: BLE001 - audit logging must never break a response
        pass

    return response
