# Copyright (c) Huawei Technologies Co., Ltd. 2023-2025. All rights reserved.
"""Runtime settings for the phenomenon index.

All values come from deployment-injected environment variables;
none of them are business state and none are written back to the database.
"""
from __future__ import annotations

import os
from pathlib import Path


def _bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def index_enabled() -> bool:
    return _bool("PHENOMENON_INDEX_ENABLED", False)


def search_enabled() -> bool:
    return _bool("PHENOMENON_SEARCH_ENABLED", False)


def self_check_enabled() -> bool:
    return _bool("PHENOMENON_SELF_CHECK", True)


def rag_core_url() -> str | None:
    value = (os.environ.get("RAG_CORE_URL") or "").strip()
    return value.rstrip("/") or None


def rag_access_key_file() -> str | None:
    value = (os.environ.get("RAG_ACCESS_KEY_FILE") or "").strip()
    return value or None


def rag_access_key() -> str | None:
    path = rag_access_key_file()
    if not path:
        return None
    try:
        key = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return key or None


def rag_kb_id() -> str | None:
    value = (os.environ.get("RAG_PHENOMENON_KB_ID") or "").strip()
    return value or None


def rag_min_score() -> float:
    return _float("RAG_MIN_SCORE", 0.1)


def rag_default_top_k() -> int:
    return _int("RAG_TOP_K", 5)


def rag_score_scale() -> float:
    """Raw score scale observed on the target RAG version."""
    return _float("RAG_SCORE_SCALE", 100.0)


def rag_is_rerank() -> bool:
    return _bool("RAG_IS_RERANK", False)


def rag_ratio() -> float:
    return _float("RAG_SEARCH_RATIO", 0.5)


def rag_index_interval() -> int:
    return _int("RAG_INDEX_INTERVAL", 120)


def rag_publish_workers() -> int:
    return max(1, _int("RAG_WORKERS", 2))


def rag_cleanup_interval() -> int:
    return _int("RAG_CLEANUP_INTERVAL", 60)


def rag_event_interval() -> int:
    return _int("RAG_EVENT_INTERVAL", 5)


def rag_reconcile_interval() -> int:
    return _int("RAG_RECONCILE_INTERVAL", 86400)


def publish_lease_seconds() -> int:
    return _int("RAG_PUBLISH_LEASE_SECONDS", 120)


def cleanup_lease_seconds() -> int:
    return _int("RAG_CLEANUP_LEASE_SECONDS", 300)


def event_lease_seconds() -> int:
    return _int("RAG_EVENT_LEASE_SECONDS", 120)
