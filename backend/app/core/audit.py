"""Security audit trail: persists authentication denials and data-mutating
requests to `audit_logs` (Firestore collection, see app.core.store).

Kept deliberately fire-and-forget: a failure to write an audit row must
never break the actual request it's describing.
"""
from __future__ import annotations

import logging

from app.core import store
from app.models import AuditLogRow

logger = logging.getLogger("app.audit")


def log_audit_event(
    *,
    user_id: str | None,
    event_type: str,
    method: str,
    path: str,
    status_code: int,
    client_ip: str | None = None,
    detail: str = "",
) -> None:
    try:
        store.put(
            AuditLogRow(
                user_id=user_id,
                event_type=event_type,
                method=method,
                path=path,
                status_code=status_code,
                client_ip=client_ip,
                detail=detail[:500],
            )
        )
    except Exception:  # noqa: BLE001 - audit logging must never break the request
        logger.exception("Failed to write audit log row (event_type=%s path=%s)", event_type, path)
