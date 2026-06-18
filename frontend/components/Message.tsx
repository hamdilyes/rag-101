"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/lib/types";
import Sources from "./Sources";

export default function Message({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl bg-clay-soft px-4 py-2.5 text-[15px] leading-7 text-ink">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-clay font-serif text-sm text-white">
        ✻
      </div>
      <div className="min-w-0 flex-1">
        <div className="prose-rag">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
          {message.streaming && (
            <span className="caret ml-0.5 inline-block h-4 w-[2px] -translate-y-[1px] bg-ink align-middle" />
          )}
        </div>
        {message.sources && <Sources sources={message.sources} />}
      </div>
    </div>
  );
}
