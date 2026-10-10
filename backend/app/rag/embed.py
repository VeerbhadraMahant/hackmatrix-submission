"""NVIDIA embeddings (nvidia/nemotron-3-embed-1b, 2048-dim) -> L2-normalised float32 matrix."""
from __future__ import annotations

import httpx
import numpy as np

from app.core.config import get_settings

_URL = "https://integrate.api.nvidia.com/v1/embeddings"
_BATCH = 32


def embed(texts: list[str], input_type: str) -> np.ndarray:
    """input_type: "passage" | "query". Raises on missing key / HTTP error (callers fall back)."""
    s = get_settings()
    if not s.nvidia_api_key:
        raise RuntimeError("NVIDIA_API_KEY not set")
    out: list[list[float]] = []
    with httpx.Client(timeout=60) as client:
        for i in range(0, len(texts), _BATCH):
            r = client.post(
                _URL,
                headers={"Authorization": f"Bearer {s.nvidia_api_key}"},
                json={"model": s.nvidia_embed_model, "input": texts[i : i + _BATCH], "input_type": input_type, "encoding_format": "float"},
            )
            r.raise_for_status()
            out.extend(d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"]))
    m = np.asarray(out, dtype=np.float32)
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)
