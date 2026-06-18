"""Parallel orchestration of the parse -> chunk -> embed pipeline.

Design
------
* Parse + chunk run in a process pool (CPU-bound, embarrassingly parallel per
  file). Each worker loads the tokenizer exactly once via an initializer.
* The worker count is derived from the RAM budget in config.yaml, and the
  orchestrator throttles dispatch when measured RSS nears the ceiling.
* Embedding runs once in the main process: the model is loaded a single time
  and chunks are encoded in batches, which keeps peak RAM/VRAM predictable.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

import numpy as np

from .chunk import Chunk, chunk_pages, get_tokenizer
from .config import Config, current_ram_gb
from .embed import Embedder
from .parse import parse_pdf

# --- per-worker globals (set by the initializer) ----------------------------
_WORKER = {}


def _init_worker(model_name: str, min_chars: int, chunk_size: int, chunk_overlap: int):
    _WORKER["tokenizer"] = get_tokenizer(model_name)
    _WORKER["min_chars"] = min_chars
    _WORKER["chunk_size"] = chunk_size
    _WORKER["chunk_overlap"] = chunk_overlap


def _process_file(path_str: str) -> list[dict]:
    """Parse + chunk one PDF. Returns plain dicts so results pickle cheaply."""
    pages = parse_pdf(path_str, min_chars=_WORKER["min_chars"])
    chunks = chunk_pages(
        pages,
        _WORKER["tokenizer"],
        chunk_size=_WORKER["chunk_size"],
        chunk_overlap=_WORKER["chunk_overlap"],
    )
    return [{"doc": c.doc, "page": c.page, "text": c.text} for c in chunks]


def discover_pdfs(corpus_dir: Path) -> list[Path]:
    return sorted(p for p in corpus_dir.rglob("*.pdf") if p.is_file())


def run(config: Config) -> dict:
    corpus_dir = config.corpus_dir
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = discover_pdfs(corpus_dir)
    if not pdfs:
        print(f"No PDFs found in {corpus_dir}. Add files and re-run.")
        return {"documents": 0, "chunks": 0}

    print(
        f"Found {len(pdfs)} PDF(s). "
        f"Using {config.resources.max_workers} worker(s), "
        f"RAM budget {config.resources.max_ram_gb} GB."
    )

    # ---- Stage 1: parse + chunk in parallel --------------------------------
    all_chunks: list[Chunk] = []
    start = time.time()
    with ProcessPoolExecutor(
        max_workers=config.resources.max_workers,
        initializer=_init_worker,
        initargs=(
            config.embedding_model,
            config.min_chars,
            config.chunk_size,
            config.chunk_overlap,
        ),
    ) as pool:
        futures: dict = {}
        pending = list(pdfs)

        def _dispatch_one():
            path = pending.pop(0)
            futures[pool.submit(_process_file, str(path))] = path.name

        # Prime up to max_workers tasks, then refill as each completes — this
        # is the throttle point where we respect the RAM ceiling.
        for _ in range(min(config.resources.max_workers, len(pending))):
            _dispatch_one()

        done = 0
        while futures:
            finished, _ = wait(futures, return_when=FIRST_COMPLETED)
            for fut in finished:
                name = futures.pop(fut)
                try:
                    rows = fut.result()
                    all_chunks.extend(Chunk(**r) for r in rows)
                    done += 1
                    print(f"  [{done}/{len(pdfs)}] {name}: {len(rows)} chunks")
                except Exception as exc:  # keep going on a bad file
                    print(f"  !! {name}: failed ({exc})")

                # Refill, backing off while we are over the RAM budget.
                if pending:
                    while (
                        current_ram_gb() > config.resources.max_ram_gb and futures
                    ):
                        time.sleep(0.2)
                    if pending:
                        _dispatch_one()

    parse_secs = time.time() - start
    print(f"Parsed + chunked {len(all_chunks)} chunks in {parse_secs:.1f}s.")

    if not all_chunks:
        print("No chunks produced (all documents empty or below min_chars).")
        return {"documents": len(pdfs), "chunks": 0}

    # ---- Stage 2: embed (single model load, batched) -----------------------
    print(f"Loading embedding model {config.embedding_model} ...")
    try:
        embedder = Embedder(
            config.embedding_model,
            device=config.device,
            normalize=config.normalize,
            cache_dir=str(config.hf_cache_dir),
        )
    except Exception as exc:
        # Model can't load (no download / not installed). Nothing to embed —
        # exit cleanly with a clear message instead of a traceback.
        print(
            f"ERROR: could not load embedding model '{config.embedding_model}': {exc}\n"
            "Check your internet connection / HuggingFace access and try again. "
            "Parsing + chunking succeeded; no index was written."
        )
        return {"documents": len(pdfs), "chunks": len(all_chunks), "embedded": 0, "error": str(exc)}

    print(f"Embedding on device={embedder.device}, dim={embedder.dim} ...")
    texts = [c.text for c in all_chunks]
    embeddings, kept = embedder.encode_documents(
        texts, batch_size=config.resources.embed_batch_size
    )
    kept_chunks = [all_chunks[i] for i in kept]
    skipped = len(all_chunks) - len(kept_chunks)
    if skipped:
        print(f"Skipped {skipped} chunk(s) that could not be embedded.")

    # ---- Write the committed index -----------------------------------------
    _write_index(output_dir, kept_chunks, embeddings, embedder, config)
    print(f"Wrote index to {output_dir}")
    return {
        "documents": len(pdfs),
        "chunks": len(all_chunks),
        "embedded": len(kept_chunks),
        "skipped": skipped,
        "dim": embedder.dim,
    }


def _write_index(
    output_dir: Path,
    chunks: list[Chunk],
    embeddings: np.ndarray,
    embedder: Embedder,
    config: Config,
):
    # chunks.jsonl (row-aligned with embeddings.npy)
    with (output_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            f.write(
                json.dumps(
                    {"id": i, "doc": c.doc, "page": c.page, "text": c.text},
                    ensure_ascii=False,
                )
                + "\n"
            )

    np.save(output_dir / "embeddings.npy", embeddings)

    meta = {
        "model": config.embedding_model,
        "dim": int(embedder.dim),
        "count": len(chunks),
        "normalized": config.normalize,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
    }
    with (output_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
