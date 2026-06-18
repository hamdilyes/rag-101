"""Vector store: load the committed index and do cosine top-k search.

The corpus is small enough that an exact numpy dot-product search is both
simplest and fast. Embeddings are L2-normalized at processing time, so a dot
product is cosine similarity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class ChunkRecord:
    id: int
    doc: str
    page: int
    text: str


class VectorStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.meta: dict = {}
        self.chunks: list[ChunkRecord] = []
        self.embeddings: np.ndarray | None = None
        self._load()

    def _load(self) -> None:
        meta_path = self.index_dir / "meta.json"
        chunks_path = self.index_dir / "chunks.jsonl"
        emb_path = self.index_dir / "embeddings.npy"

        if not (meta_path.exists() and chunks_path.exists() and emb_path.exists()):
            # No index yet — the server still boots so the UI can explain this.
            return

        with meta_path.open("r", encoding="utf-8") as f:
            self.meta = json.load(f)

        records: list[ChunkRecord] = []
        with chunks_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    d = json.loads(line)
                    records.append(
                        ChunkRecord(id=d["id"], doc=d["doc"], page=d["page"], text=d["text"])
                    )
        self.chunks = records
        self.embeddings = np.load(emb_path).astype(np.float32)

    @property
    def ready(self) -> bool:
        return self.embeddings is not None and len(self.chunks) > 0

    def search(self, query_vec: np.ndarray, top_k: int) -> list[tuple[ChunkRecord, float]]:
        if not self.ready:
            return []
        q = query_vec.astype(np.float32).reshape(-1)
        # embeddings are normalized; normalize the query too for safety.
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm
        scores = self.embeddings @ q  # (N,) cosine similarities
        k = min(top_k, scores.shape[0])
        # argpartition for the top-k, then sort those by score desc.
        idx = np.argpartition(-scores, k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        return [(self.chunks[i], float(scores[i])) for i in idx]
