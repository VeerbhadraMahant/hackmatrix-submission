"""Upload / list / delete text documents that the Copilot RAG can cite."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.core import store
from app.core.auth import resolve_user_id
from app.core.ratelimit import upload_limiter
from app.models import DocumentRow
from app.rag.corpus import split_document

router = APIRouter()

_EXTS = (".txt", ".md", ".csv", ".json")
_MAX_BYTES = 2 * 1024 * 1024
_MAX_CHARS = 200_000


@router.post("/api/documents/{user_id}")
async def upload_document(file: UploadFile, user_id: str = Depends(resolve_user_id)) -> dict:
    upload_limiter.check(user_id)
    name = file.filename or "document.txt"
    if not name.lower().endswith(_EXTS):
        raise HTTPException(400, f"Only {', '.join(_EXTS)} files are supported")
    raw = await file.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise HTTPException(400, "File too large (max 2MB)")
    text = raw.decode("utf-8", errors="replace")[:_MAX_CHARS]
    if not text.strip():
        raise HTTPException(400, "uploaded file is empty")
    row = DocumentRow(user_id=user_id, name=name, text=text)
    store.put(row)
    return {"id": row.id, "name": name, "chars": len(text), "chunks": len(split_document(text))}


@router.get("/api/documents/{user_id}")
def list_documents(user_id: str = Depends(resolve_user_id)) -> list[dict]:
    rows = sorted(store.query(DocumentRow, user_id=user_id), key=lambda r: r.created_at, reverse=True)
    return [{"id": r.id, "name": r.name, "chars": len(r.text), "created_at": r.created_at} for r in rows]


@router.delete("/api/documents/{user_id}/{doc_id}")
def delete_document(doc_id: str, user_id: str = Depends(resolve_user_id)) -> dict:
    row = store.get(DocumentRow, doc_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(404, "Document not found")
    store.delete(DocumentRow, doc_id)
    return {"deleted": True, "id": doc_id}
