"""PDF parsing: extract text per page using PyMuPDF (fitz)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Page:
    doc: str          # source file name
    page: int         # 1-based page number
    text: str


def parse_pdf(path: str | Path, min_chars: int = 50) -> list[Page]:
    """Return one Page per PDF page whose text passes the min_chars filter.

    Imported lazily so worker processes only pay the import cost once spawned.
    """
    import fitz  # PyMuPDF

    path = Path(path)
    pages: list[Page] = []
    with fitz.open(path) as pdf:
        for i in range(pdf.page_count):
            # Per-page guard: a single broken page is skipped, not fatal.
            try:
                text = _normalize(pdf[i].get_text("text"))
            except Exception:
                continue
            if len(text) >= min_chars:
                pages.append(Page(doc=path.name, page=i + 1, text=text))
    return pages


def _normalize(text: str) -> str:
    # Collapse runaway whitespace while keeping paragraph breaks readable.
    lines = [ln.strip() for ln in text.splitlines()]
    out: list[str] = []
    blank = False
    for ln in lines:
        if ln:
            out.append(ln)
            blank = False
        elif not blank:
            out.append("")
            blank = True
    return "\n".join(out).strip()
