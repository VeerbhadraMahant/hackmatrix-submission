"""Firestore access for the SQLModel row classes in app.models.

Collection = Model.__tablename__, document id = row.id. Rows are stored as
JSON-mode dicts (ISO date strings), so reads go through model_validate -- never
Model(**d), which doesn't coerce types on table=True models.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from google.cloud import firestore as gcf
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.config import get_settings

_BATCH = 500

# When Firestore credentials are missing/invalid (e.g. a Vercel deploy without
# FIREBASE_SERVICE_ACCOUNT_JSON, or local dev without ADC) the store degrades to
# a per-process in-memory dict instead of crashing every request with a 500.
# Serverless instances are ephemeral, so data written here is demo-only.
_MEMORY: dict[str, dict[str, dict]] = {}


def using_memory() -> bool:
    """True when the store is running on the in-memory fallback."""
    return _db() is None


@lru_cache
def _db():
    # Lazy so pure tests never need credentials or an emulator.
    pid = get_settings().firestore_project_id
    if os.getenv("FIRESTORE_EMULATOR_HOST"):
        return gcf.Client(project=pid)  # anonymous creds, auto-routed to the emulator
    import firebase_admin
    from firebase_admin import credentials, firestore as admin_firestore

    info = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    try:
        cred = credentials.Certificate(json.loads(info)) if info else credentials.ApplicationDefault()
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {"projectId": pid})
        return admin_firestore.client()
    except Exception as exc:  # noqa: BLE001 - any credential/config problem -> demo fallback
        print(f"[store] Firestore unavailable ({exc!r}); using in-memory fallback store.")
        return None


def _coll(model):
    return _db().collection(model.__tablename__)


def _table(model) -> dict[str, dict]:
    return _MEMORY.setdefault(model.__tablename__, {})


def _matches(doc: dict, eq: dict) -> bool:
    return all(doc.get(k) == v for k, v in eq.items())


def _q(model, eq):
    q = _coll(model)
    for k, v in eq.items():
        q = q.where(filter=FieldFilter(k, "==", v))
    return q


def get(model, id: str):
    if using_memory():
        doc = _table(model).get(id)
        return model.model_validate(doc) if doc else None
    snap = _coll(model).document(id).get()
    return model.model_validate(snap.to_dict()) if snap.exists else None


def query(model, **eq) -> list:
    if using_memory():
        return [model.model_validate(d) for d in list(_table(model).values()) if _matches(d, eq)]
    return [model.model_validate(s.to_dict()) for s in _q(model, eq).stream()]


def first(model, **eq):
    if using_memory():
        found = query(model, **eq)
        return found[0] if found else None
    for s in _q(model, eq).limit(1).stream():
        return model.model_validate(s.to_dict())
    return None


def put(*rows) -> None:
    """Upsert rows; split into batches of 500 (atomic per batch, not across them)."""
    if using_memory():
        for r in rows:
            _table(type(r))[r.id] = r.model_dump(mode="json")
        return
    for i in range(0, len(rows), _BATCH):
        batch = _db().batch()
        for r in rows[i : i + _BATCH]:
            batch.set(_coll(type(r)).document(r.id), r.model_dump(mode="json"))
        batch.commit()


def delete(model, id: str) -> None:
    if using_memory():
        _table(model).pop(id, None)
        return
    _coll(model).document(id).delete()


def delete_where(model, **eq) -> None:
    if using_memory():
        tbl = _table(model)
        for k in [k for k, d in tbl.items() if _matches(d, eq)]:
            del tbl[k]
        return
    refs = [s.reference for s in _q(model, eq).stream()]
    for i in range(0, len(refs), _BATCH):
        batch = _db().batch()
        for ref in refs[i : i + _BATCH]:
            batch.delete(ref)
        batch.commit()
