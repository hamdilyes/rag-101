"""Embedding stage: encode chunk texts with Qwen3-Embedding via SentenceTransformers.

Run once in the main process (the model is loaded a single time and texts are
encoded in batches) so we don't pay model-load RAM per worker. The expensive,
parallelizable work (parse + chunk) already happened upstream.
"""

from __future__ import annotations

import numpy as np


class Embedder:
    def __init__(
        self,
        model_name: str,
        device: str = "auto",
        normalize: bool = True,
        cache_dir: str | None = None,
    ):
        from sentence_transformers import SentenceTransformer

        resolved = self._resolve_device(device)
        self.model = SentenceTransformer(
            model_name,
            device=resolved,
            cache_folder=cache_dir,
        )
        self.normalize = normalize
        self.device = resolved
        self.dim = self.model.get_sentence_embedding_dimension()

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device != "auto":
            return device
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _encode(self, batch: list[str]) -> np.ndarray:
        return self.model.encode(
            batch,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)

    def encode_documents(
        self, texts: list[str], batch_size: int = 16
    ) -> tuple[np.ndarray, list[int]]:
        """Embed corpus chunks resiliently.

        Returns (embeddings, kept_indices). A batch that errors is retried one
        item at a time, and any individual chunk that still fails is skipped
        (logged) rather than aborting the run. `kept_indices` lets the caller
        keep chunks.jsonl row-aligned with the embeddings matrix. Documents get
        no instruction prefix (Qwen3 applies that on the query side only).
        """
        vectors: list[np.ndarray] = []
        kept: list[int] = []
        n = len(texts)

        for start in range(0, n, batch_size):
            idx = list(range(start, min(start + batch_size, n)))
            batch = [texts[i] for i in idx]
            try:
                embs = self._encode(batch)
                for j, i in enumerate(idx):
                    vectors.append(embs[j])
                    kept.append(i)
            except Exception as exc:
                print(f"  [embed] batch {start}-{idx[-1]} failed ({exc}); retrying per item")
                for i in idx:
                    try:
                        vectors.append(self._encode([texts[i]])[0])
                        kept.append(i)
                    except Exception as exc2:
                        print(f"  [embed] skipped chunk {i} ({exc2})")
            done = min(start + batch_size, n)
            print(f"  [embed] {done}/{n} chunks", end="\r", flush=True)

        print()
        if vectors:
            return np.vstack(vectors).astype(np.float32), kept
        return np.zeros((0, self.dim), dtype=np.float32), kept
