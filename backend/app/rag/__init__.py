"""Hybrid RAG (dense NVIDIA embeddings + BM25-style keywords, fused with RRF) over the user's own data + uploaded documents."""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import date
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)
_FRAUD = re.compile(r"fraud|duplicate|suspicious|unusual|security", re.I)
_RRF_K = 60
_POOL = 30


_MONTHS = ["jan(?:uary)?", "feb(?:ruary)?", "mar(?:ch)?", "apr(?:il)?", "(?:(?<=in )|(?<=of )|(?<=for )|(?<=during ))may", "june?", "july?", "aug(?:ust)?", "sep(?:t|tember)?", "oct(?:ober)?", "nov(?:ember)?", "dec(?:ember)?"]


def _months_in(query: str, today: date | None = None) -> set[str]:
    """YYYY-MM strings the question points at: 'last month', 'this month', or a named month (latest such month)."""
    today = today or date.today()
    q, out = query.lower(), set()

    def shift(n: int) -> str:
        m = today.year * 12 + today.month - 1 + n
        return f"{m // 12}-{m % 12 + 1:02d}"

    if re.search(r"last month|previous month|past month", q):
        out.add(shift(-1))
    if re.search(r"this month|current month|so far this month", q):
        out.add(shift(0))
    for i, name in enumerate(_MONTHS):
        if re.search(rf"\b{name}\b", q):
            y = today.year if i + 1 <= today.month else today.year - 1
            ym = re.search(rf"\b{name}\W+(20\d\d)", q)
            out.add(f"{ym.group(1) if ym else y}-{i + 1:02d}")
    return out


@dataclass
class Chunk:
    id: str
    kind: str  # "transaction_summary" | "debt" | "goal" | "budget" | "income" | "account" | "recurring" | "document" | "scheme"
    text: str  # self-contained sentence(s) the LLM can quote
    score: float  # fused retrieval score, higher is better
    label: str  # short human label shown in the UI, e.g. "Statement.pdf" or "Dining, Sep 2026"


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower())


def _bm25(query: str, docs: list[str]) -> np.ndarray:
    toks = [_tok(d) for d in docs]
    avg = (sum(map(len, toks)) / len(toks)) or 1
    df = Counter(w for t in toks for w in set(t))
    scores = np.zeros(len(docs))
    for w in set(_tok(query)):
        if w not in df:
            continue
        idf = math.log(1 + (len(docs) - df[w] + 0.5) / (df[w] + 0.5))
        for i, t in enumerate(toks):
            tf = t.count(w)
            if tf:
                scores[i] += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(t) / avg))
    return scores


def retrieve(user_id: str, query: str, k: int = 8) -> list[Chunk]:
    """Top-k chunks for this user and question. Never raises (returns [] on any failure)."""
    try:
        from app.rag import embed, index

        idx = index.ensure_indexed(user_id)
        chunks = idx["chunks"]
        if not chunks:
            return []
        kw = _bm25(query, [c[2] for c in chunks])
        rankings = [[int(i) for i in np.argsort(-kw)[:_POOL] if kw[i] > 0]]
        if idx["matrix"] is not None:
            try:
                q = embed.embed([query], "query")[0]
                rankings.append([int(i) for i in np.argsort(-(idx["matrix"] @ q))[:_POOL]])
            except Exception as exc:
                logger.warning("rag: query embedding failed, keyword-only: %s", exc)
        fused: dict[int, float] = {}
        for ranking in rankings:
            for r, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1 / (_RRF_K + r + 1)
        if _FRAUD.search(query):
            top = max(fused.values(), default=1 / (_RRF_K + 1))
            for i, c in enumerate(chunks):
                if c[0].startswith("unusual:"):
                    fused[i] = max(fused.get(i, 0.0), top)
        months = _months_in(query)
        if months:  # a dated question must see that month's cards; ones for a category it names rank first
            top = max(fused.values(), default=1 / (_RRF_K + 1))
            qw = set(_tok(query))
            for i, c in enumerate(chunks):
                if any(m in c[3] or m in c[2][:12] for m in months):
                    cat = _tok(c[3].split(",")[0])
                    fused[i] = max(fused.get(i, 0.0), top) + (top if cat and cat[0] in qw else 0)
        order = sorted(fused, key=fused.get, reverse=True)
        return [Chunk(chunks[i][0], chunks[i][1], chunks[i][2], round(fused[i], 5), chunks[i][3]) for i in order[:k]]
    except Exception as exc:
        logger.warning("rag.retrieve failed: %s", exc)
        return []
