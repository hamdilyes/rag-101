"use client";

import { useEffect, useRef, useState } from "react";
import Sidebar from "@/components/Sidebar";
import ChatInput from "@/components/ChatInput";
import Message from "@/components/Message";
import { streamChat } from "@/lib/chat";
import type { ChatMessage } from "@/lib/types";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const hasChat = messages.length > 0;

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

    await streamChat(
      text,
      history,
      {
        onSources: (sources) =>
          setMessages((m) => {
            const copy = [...m];
            copy[idx] = { ...copy[idx], sources };
            return copy;
          }),
        onDelta: (delta) =>
          setMessages((m) => {
            const copy = [...m];
            copy[idx] = { ...copy[idx], content: copy[idx].content + delta };
            return copy;
          }),
        onError: (msg) =>
          setMessages((m) => {
            const copy = [...m];
            copy[idx] = {
              ...copy[idx],
              content:
                copy[idx].content + `\n\n_Error: ${msg}_`,
              streaming: false,
            };
            return copy;
          }),
        onDone: () =>
          setMessages((m) => {
            const copy = [...m];
            copy[idx] = { ...copy[idx], streaming: false };
            return copy;
          }),
      },
    ).catch((e) => {
      setMessages((m) => {
        const copy = [...m];
        copy[idx] = {
          ...copy[idx],
          content: copy[idx].content + `\n\n_Error: ${String(e)}_`,
          streaming: false,
        };
        return copy;
      });
    });

    setBusy(false);
  }

  return (
    <div className="flex h-screen">
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((o) => !o)}
        onNewChat={() => setMessages([])}
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
              <p className="mt-4 text-center text-sm text-ink-faint">
                Ask anything about your document corpus.
              </p>
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
