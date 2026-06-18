"""CLI entry point: `uv run rag-process` (or `python -m rag_processing.run`)."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse, chunk, and embed the PDF corpus into a committed index."
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[2] / "config.yaml"),
        help="Path to config.yaml (default: processing/config.yaml).",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    summary = run(config)
    print("\nDone:", summary)


if __name__ == "__main__":
    main()
