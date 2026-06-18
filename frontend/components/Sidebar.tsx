"use client";

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  onNewChat: () => void;
}

export default function Sidebar({ open, onToggle, onNewChat }: SidebarProps) {
  return (
    <aside
      className={`flex h-full flex-col bg-sidebar border-r border-border transition-all duration-200 ${
        open ? "w-64" : "w-[60px]"
      }`}
    >
      <div className="flex items-center justify-between px-3 py-4">
        {open && (
          <span className="font-serif text-lg text-ink">RAG-101</span>
        )}
        <button
          onClick={onToggle}
          aria-label="Toggle sidebar"
          className="rounded-lg p-2 text-ink-soft hover:bg-border/60"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </div>

      <div className="px-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg border border-border bg-raised px-3 py-2 text-sm text-ink hover:border-clay/40 hover:text-clay"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          {open && <span>New chat</span>}
        </button>
      </div>

      {/* Single-chat app: no recents list. The space pushes the user area down. */}
      <div className="flex-1" />

      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-clay text-xs font-medium text-white">
            O
          </div>
          {open && <span className="text-sm text-ink-soft">Ostad</span>}
        </div>
      </div>
    </aside>
  );
}
