"use client"

import { useState } from "react"
import { Bookmark, Trash2, X } from "lucide-react"

import { type SavedRuling, loadBookmarks, removeBookmark } from "@/lib/bookmarks"

/**
 * Slide-out panel showing all bookmarked rulings.
 * Accessible from the header. Stored purely in localStorage.
 */

interface SavedRulingsProps {
  open: boolean
  onClose: () => void
  onAsk: (question: string) => void
}

export default function SavedRulings({ open, onClose, onAsk }: SavedRulingsProps) {
  const [rulings, setRulings] = useState<SavedRuling[]>(() => loadBookmarks())

  const handleRemove = (id: string) => {
    removeBookmark(id)
    setRulings((prev) => prev.filter((r) => r.id !== id))
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-label="Saved rulings">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 flex h-full w-full max-w-md flex-col overflow-hidden bg-background shadow-2xl animate-rise">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/70 px-4 py-3">
          <div className="flex items-center gap-2">
            <Bookmark className="h-4 w-4 text-gold fill-gold" />
            <h2 className="font-display text-lg font-semibold text-foreground">Saved Rulings</h2>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[0.65rem] font-medium tabular-nums text-muted-foreground">
              {rulings.length}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3 scrollbar-thin">
          {rulings.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Bookmark className="h-8 w-8 text-muted-foreground/40" />
              <p className="mt-3 font-serif text-sm text-muted-foreground">
                No saved rulings yet.
                <br />
                Tap the bookmark icon on any answer to save it here.
              </p>
            </div>
          ) : (
            <ul className="space-y-3">
              {rulings.map((ruling) => (
                <li
                  key={ruling.id}
                  className="rounded-xl border border-border/70 bg-card/50 p-3 transition-colors hover:bg-card"
                >
                  <div className="flex items-start justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        onAsk(ruling.question)
                        onClose()
                      }}
                      className="flex-1 text-left"
                    >
                      <p className="text-[0.78rem] font-semibold text-primary leading-snug">
                        {ruling.question}
                      </p>
                      <p className="mt-1.5 line-clamp-3 font-serif text-[0.82rem] leading-relaxed text-foreground/80">
                        {ruling.answer.replace(/[*#_`]/g, "").slice(0, 200)}
                        {ruling.answer.length > 200 ? "…" : ""}
                      </p>
                      {ruling.citations.length > 0 && (
                        <p className="mt-1.5 text-[0.68rem] text-muted-foreground">
                          📚 {ruling.citations.slice(0, 2).join(" · ")}
                        </p>
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => handleRemove(ruling.id)}
                      aria-label="Remove bookmark"
                      className="shrink-0 grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive active:bg-destructive/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <p className="mt-2 text-[0.62rem] text-muted-foreground/60">
                    {new Date(ruling.savedAt).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
