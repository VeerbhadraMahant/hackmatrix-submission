"""Per-user in-memory index (chunks + embedding matrix), disk-cached by fingerprint."""
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import numpy as np

from app.rag import corpus, embed

_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "rag"
_TTL = 30  # shortcut: store edits show up within 30 s; lower it if that hurts
_idx: dict[str, dict] = {}
_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def ensure_indexed(user_id: str) -> dict:
    """Return {fingerprint, chunks, matrix|None, checked}; matrix is None when embeddings are unavailable."""
    with _guard:
        lock = _locks.setdefault(user_id, threading.Lock())
    with lock:
        cur = _idx.get(user_id)
        if cur and cur["matrix"] is not None and time.time() - cur["checked"] < _TTL:
            return cur
        chunks = corpus.build_chunks(user_id)
        # fingerprint of the card texts: covers counts, dates, amounts and document content
        fp = hashlib.sha1("\n".join(f"{c[0]}|{c[2]}" for c in chunks).encode()).hexdigest()
        if cur and cur["fingerprint"] == fp and cur["matrix"] is not None:
            cur["checked"] = time.time()
            return cur
        matrix = _load(user_id, fp)
        if matrix is None and chunks:
            try:
                matrix = embed.embed([c[2] for c in chunks], "passage")
                _save(user_id, fp, matrix)
            except Exception:
                matrix = None  # keyword-only; embedding retried on next call
        _idx[user_id] = cur = {"fingerprint": fp, "chunks": chunks, "matrix": matrix, "checked": time.time()}
        return cur


def _path(user_id: str) -> Path:
    return _CACHE / f"{hashlib.sha1(user_id.encode()).hexdigest()[:16]}.npz"


def _load(user_id: str, fp: str):
    try:
        z = np.load(_path(user_id))
        return z["matrix"] if str(z["fp"]) == fp else None
    except Exception:
        return None


def _save(user_id: str, fp: str, matrix: np.ndarray) -> None:
    try:
        _CACHE.mkdir(parents=True, exist_ok=True)
        np.savez(_path(user_id), fp=fp, matrix=matrix)
    except OSError:
        pass
