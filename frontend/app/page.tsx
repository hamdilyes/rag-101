"use client";

import { useEffect, useRef, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChatInput from "@/components/ChatInput";
import Message from "@/components/Message";
import { streamChat } from "@/lib/chat";
import type { ChatMessage } from "@/lib/types";

// Render an error inside the assistant message, in the same bubble as a normal
// answer. If text already streamed before the failure, keep it and append.
function appendError(existing: string, message: string): string {
  return existing.trim() ? `${existing}\n\n${message}` : message;
}

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const hasChat = messages.length > 0;

  function newChat() {
    // Erase the current (only) chat and stop any in-flight stream.
    abortRef.current?.abort();
    setMessages([]);
    setBusy(false);
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (busy) return;
    setBusy(true);

    const history = messages;
    const userMsg: ChatMessage = { role: "user", content: text };
    const assistantMsg: ChatMessage = { role: "assistant", content: "", streaming: true };
    setMessages((m) => [...m, userMsg, assistantMsg]);

    const idx = history.length + 1; // index of the assistant message
    const controller = new AbortController();
    abortRef.current = controller;

    // Guarded update: if "New chat" cleared the conversation mid-stream, the
    // target message no longer exists — skip the write instead of crashing.
    const patch = (fn: (cur: ChatMessage) => ChatMessage) =>
      setMessages((m) => {
        if (!m[idx]) return m;
        const copy = [...m];
        copy[idx] = fn(copy[idx]);
        return copy;
      });

    await streamChat(
      text,
      history,
      {
        onSources: (sources) => patch((cur) => ({ ...cur, sources })),
        onDelta: (delta) => patch((cur) => ({ ...cur, content: cur.content + delta })),
        onError: (msg) =>
          patch((cur) => ({ ...cur, content: appendError(cur.content, msg), streaming: false })),
        onDone: () => patch((cur) => ({ ...cur, streaming: false })),
      },
      controller.signal,
    ).catch((e) => {
      if (e instanceof Error && e.name === "AbortError") return; // chat was reset
      patch((cur) => ({
        ...cur,
        content: appendError(cur.content, "Our LLM is currently offline. Please try again in a moment."),
        streaming: false,
      }));
    });

    if (abortRef.current === controller) abortRef.current = null;
    setBusy(false);
  }

  return (
    <div className="flex h-screen">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((o) => !o)}
        onNewChat={newChat}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        {!hasChat ? (
          // ---- Empty state: centered greeting + input ----
          <div className="flex flex-1 flex-col items-center justify-center px-4">
            <div className="w-full max-w-chat">
              <h1 className="mb-8 flex items-center justify-center gap-3 font-serif text-4xl text-ink">
                <span className="text-clay">✻</span>
                Salam Ostad
              </h1>
              <ChatInput onSend={send} disabled={busy} />
            </div>
          </div>
        ) : (
          // ---- Conversation ----
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto">
              <div className="mx-auto w-full max-w-chat space-y-8 px-4 py-8">
                {messages.map((m, i) => (
                  <Message key={i} message={m} />
                ))}
              </div>
            </div>
            <div className="border-t border-border bg-canvas">
              <div className="mx-auto w-full max-w-chat px-4 py-4">
                <ChatInput onSend={send} disabled={busy} />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
