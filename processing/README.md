# Processing pipeline

Parses the PDF corpus, chunks it, embeds the chunks with **Qwen3-Embedding**, and
writes a committed index to `../data/index/`. The raw PDFs never leave your
machine; only the embeddings are pushed.

## Setup

Uses [`uv`](https://docs.astral.sh/uv/). From this folder:

```bash
uv sync
```

This installs PyMuPDF, sentence-transformers, torch, etc. The Qwen embedding
model downloads from HuggingFace on first run into `../.hf_cache` (git-ignored).

## Run

1. Put PDFs in `../corpus/`.
2. Tune resource limits in `config.yaml` (workers, RAM budget, batch size).
3. Run:

```bash
uv run rag-process
```

## Parallel computing & resource limits

All limits live in `config.yaml` under `resources:`:

| Key | Meaning |
| --- | --- |
| `max_workers` | Worker processes for parse + chunk (`auto` derives from CPU and RAM). |
| `max_ram_gb` | Soft RAM ceiling. Worker count is capped to `max_ram_gb / per_worker_ram_gb`, and dispatch backs off when measured RSS nears the ceiling. |
| `per_worker_ram_gb` | Estimated RAM per worker, used to derive the worker count. |
| `embed_batch_size` | Batch size for the embedding stage. |

**How parallelism is applied:** parse + chunk run across worker processes (one
file at a time per worker, each worker loads the tokenizer once). Embedding then
runs once in the main process with a single model load and batched encoding, so
peak memory stays predictable rather than multiplying the model across workers.

Set `embedding.device: cuda` in `config.yaml` to embed on GPU.

## Output (`../data/index/`)

| File | Contents |
| --- | --- |
| `chunks.jsonl` | One line per chunk: `{id, doc, page, text}`. |
| `embeddings.npy` | `float32` matrix, row-aligned with `chunks.jsonl`. |
| `meta.json` | Model name, dimension, count, normalization, chunk settings. |
