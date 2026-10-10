"""Central configuration loaded from the repo-root .env.local (never committed).

Falls back to safe defaults so the app boots (and tests run) even with no
secrets present -- this is what lets "demo mode" work offline.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# repo root is two levels up from this file: backend/app/core/config.py -> repo/
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env.local", override=False)
load_dotenv(_REPO_ROOT / "backend" / ".env", override=False)


class Settings:
    # NVIDIA NIM hosted chat (the copilot's AI)
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_model: str = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    # general (non-finance) conversation: a fast model, optionally on its own key
    nvidia_chat_api_key: str = os.getenv("NVIDIA_CHAT_API_KEY") or os.getenv("NVIDIA_API_KEY", "")
    nvidia_chat_model: str = os.getenv("NVIDIA_CHAT_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
    nvidia_embed_model: str = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b")  # 2048-dim; verified live
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")

    # Nugen (second opinion in the copilot; optional)
    nugen_api_key: str = os.getenv("NUGEN_API_KEY", "")
    nugen_model: str = os.getenv("NUGEN_MODEL", "meta-llama/Llama-3.2-3B-Instruct")

    # Resend (optional cash-flow-gap alert emails)
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "FinPilot <onboarding@resend.dev>")
    hr_alert_email: str = os.getenv("HR_ALERT_EMAIL", "")

    # Auth behaviour
    demo_mode: bool = os.getenv("FINPILOT_DEMO_MODE", "true").lower() == "true"

    # Firebase
    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID") or os.getenv("NEXT_PUBLIC_FIREBASE_PROJECT_ID", "hackmatrix-3764f")
    # Firestore project may differ (e.g. demo-* with the emulator) from the Auth project that signs ID tokens.
    firestore_project_id: str = os.getenv("FIRESTORE_PROJECT_ID") or firebase_project_id

    @property
    def has_firebase(self) -> bool:
        return bool(self.firebase_project_id)

    @property
    def has_firecrawl(self) -> bool:
        return bool(self.firecrawl_api_key)

    @property
    def has_nvidia(self) -> bool:
        return bool(self.nvidia_api_key)

    @property
    def has_nugen(self) -> bool:
        return bool(self.nugen_api_key)

    @property
    def has_resend(self) -> bool:
        return bool(self.resend_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
