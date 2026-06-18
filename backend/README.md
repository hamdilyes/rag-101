# Backend (RAG API)

FastAPI server that loads the committed embeddings index, embeds the query with
**`BAAI/bge-small-en-v1.5`**, runs cosine vector search, optionally reranks with
a cross-encoder (off by default), and streams an answer from a provider-agnostic
LLM (OpenAI-compatible by default).

## Setup

```bash
uv sync
```

Configuration is read from the repo-root `.env` (copy `../.env.example`). Set at
least `ANTHROPIC_API_KEY` (or switch `LLM_PROVIDER=openai` and set
`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`).

## Run

The processing pipeline must have produced `../data/index/` first.

```bash
uv run rag-serve
# -> http://localhost:8000
```

## API

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Index/model status. |
| `POST` | `/api/chat` | SSE stream of the answer. Body: `{ "message": str, "history": [...] }`. |

`/api/chat` emits `data: {json}\n\n` frames, each with a `type`:
`sources` (retrieved chunks), `delta` (text), `error`, `done`.

## Swapping the LLM

`LLM_PROVIDER=openai` (default) targets any OpenAI-compatible
`/chat/completions` endpoint — point `LLM_BASE_URL` at OpenAI, Together, Groq,
Mistral, or a local vLLM/llama.cpp server, set `LLM_API_KEY` and `LLM_MODEL`.
`LLM_PROVIDER=anthropic` is also supported (uses the Anthropic SDK).

The reranker is off by default (`RERANK_ENABLED=false`). If enabled and the
cross-encoder fails to load, the server logs a warning and falls back to
vector-only ranking. The query embedding model must match the model used to
build the index (`EMBEDDING_MODEL`).
