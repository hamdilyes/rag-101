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

    def encode_documents(self, texts: list[str], batch_size: int = 16) -> np.ndarray:
        """Embed corpus chunks. Documents get no instruction prefix (Qwen3)."""
        embs = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
        return embs.astype(np.float32)
