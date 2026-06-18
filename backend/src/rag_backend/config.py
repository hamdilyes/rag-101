"""Backend configuration, loaded from environment (.env at repo root)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env (backend/src/rag_backend -> repo root is parents[3]).
_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # LLM
    llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")
    llm_model: str = os.getenv("LLM_MODEL", "claude-opus-4-8")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

    # Retrieval
    retrieve_top_k: int = int(os.getenv("RETRIEVE_TOP_K", "20"))
    rerank_top_n: int = int(os.getenv("RERANK_TOP_N", "5"))
    rerank_enabled: bool = _bool("RERANK_ENABLED", True)

    # Models (embedding model MUST match the one used to build the index)
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    reranker_model: str = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

    # Paths
    index_dir: Path = (_REPO_ROOT / os.getenv("INDEX_DIR", "./data/index")).resolve()
    hf_cache_dir: Path = (_REPO_ROOT / ".hf_cache").resolve()

    # Server
    host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    port: int = int(os.getenv("BACKEND_PORT", "8000"))


settings = Settings()
