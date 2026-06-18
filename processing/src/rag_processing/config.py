"""Load and resolve the processing configuration (config.yaml)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import psutil
import yaml


@dataclass
class ResourceConfig:
    max_workers: int
    max_ram_gb: float
    per_worker_ram_gb: float
    embed_batch_size: int


@dataclass
class Config:
    resources: ResourceConfig
    min_chars: int
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    device: str
    normalize: bool
    corpus_dir: Path
    output_dir: Path
    hf_cache_dir: Path
    raw: dict = field(default_factory=dict)


def _resolve_workers(requested, max_ram_gb: float, per_worker_ram_gb: float) -> int:
    """Pick a worker count that respects both CPU count and the RAM budget."""
    cpu_workers = max(1, (os.cpu_count() or 2) - 1)
    ram_workers = max(1, int(max_ram_gb / max(per_worker_ram_gb, 0.05)))
    ceiling = min(cpu_workers, ram_workers)

    if isinstance(requested, str) and requested.strip().lower() == "auto":
        return ceiling
    try:
        return max(1, min(int(requested), ceiling))
    except (TypeError, ValueError):
        return ceiling


def load_config(config_path: str | os.PathLike = "config.yaml") -> Config:
    config_path = Path(config_path)
    base = config_path.parent.resolve()

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    res = raw.get("resources", {})
    max_ram_gb = float(res.get("max_ram_gb", 2.0))
    per_worker_ram_gb = float(res.get("per_worker_ram_gb", 0.4))
    workers = _resolve_workers(
        res.get("max_workers", "auto"), max_ram_gb, per_worker_ram_gb
    )

    def _path(key: str, default: str) -> Path:
        return (base / raw.get("paths", {}).get(key, default)).resolve()

    return Config(
        resources=ResourceConfig(
            max_workers=workers,
            max_ram_gb=max_ram_gb,
            per_worker_ram_gb=per_worker_ram_gb,
            embed_batch_size=int(res.get("embed_batch_size", 16)),
        ),
        min_chars=int(raw.get("parsing", {}).get("min_chars", 50)),
        chunk_size=int(raw.get("chunking", {}).get("chunk_size", 512)),
        chunk_overlap=int(raw.get("chunking", {}).get("chunk_overlap", 64)),
        embedding_model=raw.get("embedding", {}).get("model", "Qwen/Qwen3-Embedding-0.6B"),
        device=raw.get("embedding", {}).get("device", "auto"),
        normalize=bool(raw.get("embedding", {}).get("normalize", True)),
        corpus_dir=_path("corpus_dir", "../corpus"),
        output_dir=_path("output_dir", "../data/index"),
        hf_cache_dir=_path("hf_cache_dir", "../.hf_cache"),
        raw=raw,
    )


def current_ram_gb() -> float:
    """Resident memory of this process tree, in GB (best-effort).

    Never raises: on a memory-starved machine even psutil's own bookkeeping can
    fail (e.g. WinError 1455, paging file too small). In that case we fall back
    to the main process RSS, or 0.0, so the RAM check can't crash the pipeline.
    """
    try:
        proc = psutil.Process()
        total = proc.memory_info().rss
        try:
            for child in proc.children(recursive=True):
                try:
                    total += child.memory_info().rss
                except Exception:
                    pass
        except Exception:
            pass  # children enumeration failed; main RSS is good enough
        return total / (1024**3)
    except Exception:
        return 0.0
