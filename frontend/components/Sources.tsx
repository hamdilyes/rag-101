"use client";

import { useState } from "react";
import type { Source } from "@/lib/types";

export default function Sources({ sources }: { sources: Source[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs font-medium text-ink-faint hover:text-ink-soft"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className={`transition-transform ${open ? "rotate-90" : ""}`}
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
        {sources.length} source{sources.length > 1 ? "s" : ""}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((s, i) => (
            <div
              key={i}
              className="rounded-lg border border-border bg-sidebar/60 p-3 text-sm"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium text-ink">
                  {s.doc} <span className="text-ink-faint">· p.{s.page}</span>
                </span>
                <span className="text-xs text-ink-faint">
                  {s.score.toFixed(3)}
                </span>
              </div>
              <p className="text-ink-soft">{s.snippet}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
