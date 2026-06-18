"""FastAPI RAG server.

Endpoints
---------
GET  /api/health  -> index/model status.
POST /api/chat    -> Server-Sent-Events stream. Body:
        { "message": str, "history": [{"role","content"}, ...] }
     Emits `data: {json}\n\n` frames with a "type" field:
        {"type":"sources", "sources":[...]}   (once, first)
        {"type":"delta",   "text":"..."}      (many)
        {"type":"done"}                        (once, last)
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .config import settings
from .llm import stream_answer
from .retriever import RetrievedChunk, Retriever
from .store import VectorStore

# Singletons populated during the lifespan startup phase.
_state: dict = {"store": None, "retriever": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = VectorStore(settings.index_dir)
    _state["store"] = store
    if store.ready:
        # Loading the embedder here surfaces model-download/load errors at boot.
        _state["retriever"] = Retriever(settings, store)
        print(
            f"[startup] index ready: {len(store.chunks)} chunks, "
            f"model={store.meta.get('model')}, dim={store.meta.get('dim')}"
        )
    else:
        print(
            f"[startup] no index at {settings.index_dir}. "
            "Run the processing pipeline first."
        )
    yield
    _state.clear()


app = FastAPI(title="RAG-101 backend", lifespan=lifespan)

# CORS for local dev (the Next.js dev server proxies, but allow direct calls too).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


SYSTEM_PROMPT = (
    "You are a helpful research assistant answering questions about a private "
    "corpus of documents. Answer using ONLY the provided context. Cite the "
    "sources you use inline using the format [<document> p.<page>]. If the "
    "answer is not contained in the context, say you could not find it in the "
    "documents rather than guessing. Be concise and precise."
)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/api/health")
def health() -> dict:
    store: VectorStore | None = _state["store"]
    return {
        "ready": bool(store and store.ready),
        "chunks": len(store.chunks) if store else 0,
        "embedding_model": settings.embedding_model,
        "reranker_model": settings.reranker_model if settings.rerank_enabled else None,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


def _build_user_turn(message: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            f"{message}\n\n(No context was retrieved from the documents.)"
        )
    blocks = []
    for c in chunks:
        blocks.append(f"[{c.doc} p.{c.page}]\n{c.text}")
    context = "\n\n---\n\n".join(blocks)
    return f"Context:\n\n{context}\n\n---\n\nQuestion: {message}"


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    retriever: Retriever | None = _state["retriever"]

    async def gen() -> AsyncIterator[str]:
        chunks: list[RetrievedChunk] = []
        if retriever is not None:
            chunks = retriever.retrieve(req.message)

        # 1) sources event
        yield _sse(
            {
                "type": "sources",
                "sources": [
                    {
                        "doc": c.doc,
                        "page": c.page,
                        "score": round(c.score, 4),
                        "snippet": (c.text[:280] + "…") if len(c.text) > 280 else c.text,
                    }
                    for c in chunks
                ],
            }
        )

        # 2) delta events
        history = [
            m for m in req.history if m.get("role") in {"user", "assistant"}
        ]
        messages = [*history, {"role": "user", "content": _build_user_turn(req.message, chunks)}]
        try:
            async for text in stream_answer(settings, SYSTEM_PROMPT, messages):
                yield _sse({"type": "delta", "text": text})
        except RuntimeError as exc:
            # Our own clear config errors (e.g. missing API key) are worth showing.
            yield _sse({"type": "error", "message": str(exc)})
        except Exception as exc:
            # Provider outage / timeout / network: keep the real cause in the logs,
            # show the user a friendly message.
            print(f"[chat] LLM call failed: {exc!r}")
            yield _sse(
                {
                    "type": "error",
                    "message": "Our LLM is currently offline. Please try again in a moment.",
                }
            )

        # 3) done event
        yield _sse({"type": "done"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def main() -> None:
    import uvicorn

    uvicorn.run(
        "rag_backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
