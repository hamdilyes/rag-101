"""Chunking: split page text into overlapping, token-bounded chunks.

Token counts use the embedding model's tokenizer when available so chunks line
up with what the model actually consumes; otherwise we approximate at ~4
characters per token. Chunking is paragraph-aware: we pack whole paragraphs
until the token budget is hit, then start a new chunk with a token overlap.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parse import Page


@dataclass
class Chunk:
    doc: str
    page: int
    text: str


class _ApproxTokenizer:
    """Fallback tokenizer: ~4 chars per token, good enough for budgeting."""

    @staticmethod
    def encode(text: str) -> list[int]:
        return list(range(max(1, len(text) // 4)))

    @staticmethod
    def count(text: str) -> int:
        return max(1, len(text) // 4)


def get_tokenizer(model_name: str | None):
    if not model_name:
        return _ApproxTokenizer()
    try:
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(model_name)

        class _HFTok:
            def count(self, text: str) -> int:
                return len(tok.encode(text, add_special_tokens=False))

        return _HFTok()
    except Exception:
        return _ApproxTokenizer()


def chunk_pages(
    pages: list[Page],
    tokenizer,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for body in _split_text(page.text, tokenizer, chunk_size, chunk_overlap):
            chunks.append(Chunk(doc=page.doc, page=page.page, text=body))
    return chunks


def _split_text(text: str, tokenizer, chunk_size: int, chunk_overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = tokenizer.count(para)

        # A single paragraph larger than the budget is hard-split by sentences.
        if para_tokens > chunk_size:
            if current:
                chunks.append("\n\n".join(current))
                current, current_tokens = [], 0
            chunks.extend(_split_long(para, tokenizer, chunk_size, chunk_overlap))
            continue

        if current_tokens + para_tokens > chunk_size and current:
            chunks.append("\n\n".join(current))
            current, current_tokens = _carry_overlap(current, tokenizer, chunk_overlap)

        current.append(para)
        current_tokens += para_tokens

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _carry_overlap(paras: list[str], tokenizer, chunk_overlap: int):
    """Seed the next chunk with trailing paragraphs up to chunk_overlap tokens."""
    carried: list[str] = []
    tokens = 0
    for para in reversed(paras):
        t = tokenizer.count(para)
        if tokens + t > chunk_overlap:
            break
        carried.insert(0, para)
        tokens += t
    return carried, tokens


def _split_long(text: str, tokenizer, chunk_size: int, chunk_overlap: int) -> list[str]:
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    tokens = 0
    for sent in sentences:
        st = tokenizer.count(sent)
        if tokens + st > chunk_size and current:
            chunks.append(" ".join(current))
            # overlap by sentences
            carried, tokens = [], 0
            for s in reversed(current):
                t = tokenizer.count(s)
                if tokens + t > chunk_overlap:
                    break
                carried.insert(0, s)
                tokens += t
            current = carried
        current.append(sent)
        tokens += st
    if current:
        chunks.append(" ".join(current))
    return chunks
