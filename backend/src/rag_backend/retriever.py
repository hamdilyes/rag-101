"""Query-time retrieval: embed the query, vector-search, then rerank.

Query embedding uses Qwen3-Embedding with the recommended instruction prefix on
the query side (documents were embedded plain at processing time). Reranking
uses Qwen3-Reranker, a causal LM scored on its yes/no next-token logits per the
model card. The reranker is heavier; it can be disabled via RERANK_ENABLED.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import Settings
from .store import ChunkRecord, VectorStore

_QUERY_INSTRUCTION = "Given a web search query, retrieve relevant passages that answer the query"


@dataclass
class RetrievedChunk:
    doc: str
    page: int
    text: str
    score: float


class QueryEmbedder:
    def __init__(self, model_name: str, cache_dir: str | None = None):
        from sentence_transformers import SentenceTransformer

        device = self._device()
        self.model = SentenceTransformer(model_name, device=device, cache_folder=cache_dir)
        self.device = device

    @staticmethod
    def _device() -> str:
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def embed_query(self, query: str) -> np.ndarray:
        text = f"Instruct: {_QUERY_INSTRUCTION}\nQuery: {query}"
        vec = self.model.encode(
            [text], normalize_embeddings=True, convert_to_numpy=True
        )[0]
        return vec.astype(np.float32)


class Reranker:
    """Qwen3-Reranker scored via yes/no logits (lazy-loaded)."""

    def __init__(self, model_name: str, cache_dir: str | None = None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, padding_side="left", cache_dir=cache_dir
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, cache_dir=cache_dir
        ).eval()
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")

        self.token_false_id = self.tokenizer.convert_tokens_to_ids("no")
        self.token_true_id = self.tokenizer.convert_tokens_to_ids("yes")
        self.max_length = 4096

        prefix = (
            "<|im_start|>system\nJudge whether the Document meets the requirements "
            'based on the Query and the Instruct provided. Note that the answer can '
            'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
        )
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        self.prefix_tokens = self.tokenizer.encode(prefix, add_special_tokens=False)
        self.suffix_tokens = self.tokenizer.encode(suffix, add_special_tokens=False)

    def _format(self, query: str, doc: str) -> str:
        return (
            f"<Instruct>: {_QUERY_INSTRUCTION}\n<Query>: {query}\n<Document>: {doc}"
        )

    def score(self, query: str, docs: list[str]) -> list[float]:
        if not docs:
            return []
        pairs = [self._format(query, d) for d in docs]
        budget = self.max_length - len(self.prefix_tokens) - len(self.suffix_tokens)
        inputs = self.tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=budget,
        )
        for i, ids in enumerate(inputs["input_ids"]):
            inputs["input_ids"][i] = self.prefix_tokens + ids + self.suffix_tokens
        inputs = self.tokenizer.pad(
            inputs, padding=True, return_tensors="pt", max_length=self.max_length
        )
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with self.torch.no_grad():
            logits = self.model(**inputs).logits[:, -1, :]
            true_v = logits[:, self.token_true_id]
            false_v = logits[:, self.token_false_id]
            stacked = self.torch.stack([false_v, true_v], dim=1)
            probs = self.torch.nn.functional.log_softmax(stacked, dim=1)
            return probs[:, 1].exp().tolist()


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
                self._reranker = Reranker(
                    self.settings.reranker_model, cache_dir=str(self.settings.hf_cache_dir)
                )
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

        # Vector-only fallback.
        top = hits[: self.settings.rerank_top_n]
        return [
            RetrievedChunk(doc=c.doc, page=c.page, text=c.text, score=score)
            for c, score in top
        ]
