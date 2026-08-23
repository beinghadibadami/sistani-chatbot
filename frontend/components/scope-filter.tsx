"use client"

import { useEffect, useRef, useState } from "react"
import { Check, Library } from "lucide-react"

import type { SourceInfo } from "@/lib/types"

/**
 * Restricts retrieval to chosen sources.
 *
 * Explicit scoping is preferable to inferring intent from wording: it is unambiguous, costs
 * nothing at query time, and expresses what the user actually wants. The backend applies it
 * as a real filter (SQL join for BM25, post-filter for the vector search).
 */
interface ScopeFilterProps {
  sources: SourceInfo[]
  scope: string[]
  onChange: (docIds: string[]) => void
}

export default function ScopeFilter({ sources, scope, onChange }: ScopeFilterProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onPointerDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onPointerDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  if (!sources.length) return null

  const toggle = (docId: string) => {
    onChange(scope.includes(docId) ? scope.filter((d) => d !== docId) : [...scope, docId])
  }

  const active = scope.length > 0

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label="Filter sources"
        title="Search within"
        className={`grid min-h-[44px] min-w-[44px] place-items-center gap-1.5 rounded-lg text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${
          active
            ? "bg-primary/12 text-primary"
            : "text-muted-foreground hover:bg-muted hover:text-foreground"
        }`}
      >
        <Library className="h-4 w-4" />
        {active && <span className="text-[0.6rem] tabular-nums">{scope.length}</span>}
      </button>

      {open && (
        <div className="animate-rise absolute right-0 top-full z-30 mt-2 w-[min(16rem,calc(100vw-1rem))] overflow-hidden rounded-xl border border-border bg-popover shadow-xl shadow-black/10">
          <div className="flex items-center justify-between border-b border-border/70 px-3 py-2">
            <span className="text-[0.7rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Search within
            </span>
            {active && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="text-[0.7rem] font-medium text-primary hover:underline"
              >
                Clear
              </button>
            )}
          </div>

          <ul className="max-h-72 overflow-y-auto p-1 scrollbar-thin">
            {sources.map((s) => {
              const checked = scope.includes(s.doc_id)
              return (
                <li key={s.doc_id}>
                  <button
                    type="button"
                    onClick={() => toggle(s.doc_id)}
                    className="flex w-full min-h-[44px] items-center gap-2.5 rounded-lg px-2 py-2.5 text-left transition-colors hover:bg-muted active:bg-muted"
                  >
                    <span
                      className={`grid h-4 w-4 shrink-0 place-items-center rounded border transition-colors ${
                        checked ? "border-primary bg-primary" : "border-border"
                      }`}
                    >
                      {checked && <Check className="h-3 w-3 text-primary-foreground" />}
                    </span>
                    <span className="min-w-0 flex-1 truncate font-serif text-[0.84rem] text-foreground">
                      {s.title}
                    </span>
                    <span className="shrink-0 text-[0.68rem] tabular-nums text-muted-foreground/70">
                      {s.chunks}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>

          <p className="border-t border-border/70 px-3 py-2 text-[0.7rem] leading-snug text-muted-foreground">
            {active
              ? "Only the selected texts will be searched."
              : "All texts are searched by default."}
          </p>
        </div>
      )}
    </div>
  )
}
