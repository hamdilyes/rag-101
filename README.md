# rag-101

A Retrieval-Augmented-Generation app over a corpus of PDF files, with a chat UI
styled after **claude.ai**. Documents are processed locally with parallel
computing under configurable resource limits. Only the generated embeddings are
committed, never the source PDFs. Embeddings and reranking use **Qwen** models
from HuggingFace; any LLM API can be plugged in via the env file.

> Active development is on the **`dev`** branch. `main` stays clean with a brief
> README.

```
rag-101/
├── corpus/        # drop PDFs here (never committed)
├── data/index/    # committed embeddings (chunks.jsonl, embeddings.npy, meta.json)
├── processing/    # parallel parse -> chunk -> embed pipeline (Python / uv)
├── backend/       # FastAPI: retrieve -> rerank -> stream answer (Python / uv)
└── frontend/      # Next.js + Tailwind chat UI (claude.ai look, "Salam Ostad")
```

## How it fits together

1. **Process** the corpus once: `processing/` parses each PDF, chunks it, embeds
   the chunks with `Qwen/Qwen3-Embedding-0.6B`, and writes `data/index/`. The
   PDFs are git-ignored; the index is committed, so a teammate can run the app
   without ever receiving the documents.
2. **Serve**: `backend/` loads the index, embeds the query, runs cosine vector
   search, reranks the top candidates with `Qwen/Qwen3-Reranker-0.6B`, and
   streams an answer from the configured LLM (Claude `claude-opus-4-8` by
   default; any OpenAI-compatible endpoint works too).
3. **Chat**: `frontend/` is the claude.ai-style UI that streams the answer and
   shows the retrieved sources.

## Quick start

Prerequisites: [`uv`](https://docs.astral.sh/uv/) (Python) and Node.js 18+.

```bash
# 0. Configure
cp .env.example .env          # set ANTHROPIC_API_KEY (or your provider)

# 1. Add PDFs, then build the index (parallel; limits in processing/config.yaml)
#    -> writes data/index/
cd processing && uv sync && uv run rag-process && cd ..

# 2. Start the API
cd backend && uv sync && uv run rag-serve &   # http://localhost:8000
cd ..

# 3. Start the UI
cd frontend && npm install && npm run dev      # http://localhost:3000
```

Open http://localhost:3000 — you'll be greeted with **Salam Ostad**.

## What gets pushed

- ✅ `data/index/` — the embeddings, chunk text + metadata.
- ❌ `corpus/` — the raw PDFs (git-ignored).
- ❌ `.env`, model downloads (`.hf_cache/`), `node_modules/`, build output.

## Configuration

| Where | What |
| --- | --- |
| `.env` | LLM provider/key/model, retrieval knobs, model ids, paths. |
| `processing/config.yaml` | Parallel workers, RAM budget, batch size, chunking, embedding device. |

See the per-component READMEs in `processing/`, `backend/`, and `frontend/` for
details.

## Swapping the LLM

Default is Claude via the official Anthropic SDK. To use any other provider, set
in `.env`:

```ini
LLM_PROVIDER=openai
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1   # or Together / Groq / Mistral / local vLLM
LLM_MODEL=gpt-4o-mini
```
