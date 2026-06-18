"""Query-time retrieval: embed the query, vector-search, then (optionally) rerank.

Query embedding uses the same SentenceTransformers model that built the index
(BAAI/bge-small-en-v1.5 by default), with that model's recommended retrieval
instruction prefixed to the query (documents were embedded plain at processing
time). Reranking, when enabled, uses a cross-encoder; it is off by default and
degrades gracefully to vector-only if the model can't load.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Settings
from .store import ChunkRecord, VectorStore

# bge-v1.5 retrieval: prepend this instruction to the QUERY only (not documents).
_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def _resolve_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


@dataclass
class RetrievedChunk:
    doc: str
    page: int
    text: str
    score: float


class QueryEmbedder:
    def __init__(self, model_name: str, cache_dir: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.device = _resolve_device()
        self.model = SentenceTransformer(model_name, device=self.device, cache_folder=cache_dir)

    def embed_query(self, query: str) -> np.ndarray:
        text = f"{_QUERY_INSTRUCTION}{query}"
        vec = self.model.encode([text], normalize_embeddings=True, convert_to_numpy=True)[0]
        return vec.astype(np.float32)


class Reranker:
    """Cross-encoder reranker (sentence-transformers CrossEncoder), lazy-loaded."""

    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name, device=_resolve_device())

    def score(self, query: str, docs: list[str]) -> list[float]:
        if not docs:
            return []
        pairs = [[query, d] for d in docs]
        scores = self.model.predict(pairs)
        return [float(s) for s in scores]


class Retriever:
    def __init__(self, settings: Settings, store: VectorStore):
        self.settings = settings
        self.store = store
        cache = str(settings.hf_cache_dir)
        self.embedder = QueryEmbedder(settings.embedding_model, cache_dir=cache)
        self._reranker: Reranker | None = None
        self._reranker_failed = False

    def _get_reranker(self) -> Reranker | None:
        if not self.settings.rerank_enabled or self._reranker_failed:
            return None
        if self._reranker is None:
            try:
                self._reranker = Reranker(self.settings.reranker_model)
            except Exception as exc:  # degrade gracefully to vector-only
                print(f"[reranker] disabled (load failed): {exc}")
                self._reranker_failed = True
                return None
        return self._reranker

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        if not self.store.ready:
            return []

        qvec = self.embedder.embed_query(query)
        hits = self.store.search(qvec, top_k=self.settings.retrieve_top_k)
        if not hits:
            return []

        reranker = self._get_reranker()
        if reranker is not None:
            try:
                scores = reranker.score(query, [c.text for c, _ in hits])
                ranked = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)
                top = ranked[: self.settings.rerank_top_n]
                return [
                    RetrievedChunk(doc=c.doc, page=c.page, text=c.text, score=float(s))
                    for (c, _vec_score), s in top
                ]
            except Exception as exc:
                print(f"[reranker] scoring failed, using vector order: {exc}")

        # Vector-only (default).
        top = hits[: self.settings.rerank_top_n]
        return [
            RetrievedChunk(doc=c.doc, page=c.page, text=c.text, score=score)
            for c, score in top
        ]
