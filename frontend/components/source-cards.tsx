"use client"

import { useState } from "react"
import { BookOpen, ChevronDown, FileText, HelpCircle, MapPin, Scroll, Users } from "lucide-react"

import type { Source } from "@/lib/types"

/**
 * Citations are the product here, not decoration: the pipeline resolves passages down to an
 * exact ruling, issue, or verse range, so each one is expandable to reveal the retrieved text.
 * Letting a user read the source is what separates a grounded answer from a plausible one.
 */

const DOC_META: Record<string, { label: string; Icon: typeof BookOpen }> = {
  quran: { label: "Quran", Icon: BookOpen },
  islamic_laws: { label: "Islamic Laws", Icon: Scroll },
  sistani_qna: { label: "Q&A", Icon: HelpCircle },
  hajj_rituals: { label: "Hajj", Icon: MapPin },
  summary_worship: { label: "Worship", Icon: FileText },
  women_rules: { label: "Women's Rules", Icon: Users },
  jurisprudence_easy: { label: "Jurisprudence", Icon: FileText },
}

interface SourceCardsProps {
  sources: Source[]
  /** Max sources to display. Backend retrieves more for LLM context quality,
   * but showing all of them can overwhelm. Default: 2 (highest-scored). */
  maxDisplay?: number
}

export default function SourceCards({ sources, maxDisplay = 2 }: SourceCardsProps) {
  const [open, setOpen] = useState<string | null>(null)

  if (!sources?.length) return null

  // The same passage can be retrieved by several routes; show each citation once.
  const seen = new Set<string>()
  const unique = sources.filter((s) => {
    if (seen.has(s.citation)) return false
    seen.add(s.citation)
    return true
  }).slice(0, maxDisplay)

  return (
    <div className="mt-3 space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Sources
        </span>
        <span className="h-px flex-1 bg-border/70" />
        <span className="text-[0.68rem] tabular-nums text-muted-foreground/70">
          {unique.length}
        </span>
      </div>

      <ul className="space-y-1.5">
        {unique.map((source, index) => {
          const meta = DOC_META[source.doc_id] ?? { label: source.doc_id, Icon: FileText }
          const Icon = meta.Icon
          // The work name is already conveyed by the icon + label, so only show the locator part.
          const detail = source.citation.split(" — ").slice(1).join(" · ")
          const isOpen = open === source.citation
          const canExpand = Boolean(source.text)

          return (
            <li
              key={source.citation}
              className="animate-rise overflow-hidden rounded-lg border border-border/70 bg-card/60"
              style={{ animationDelay: `${Math.min(index * 55, 220)}ms` }}
            >
              <button
                type="button"
                disabled={!canExpand}
                onClick={() => setOpen(isOpen ? null : source.citation)}
                aria-expanded={isOpen}
                className="group flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors hover:bg-primary/[0.045] disabled:cursor-default disabled:hover:bg-transparent"
              >
                <Icon className="mt-[0.15rem] h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />

                <span className="min-w-0 flex-1">
                  <span className="block text-[0.8rem] font-semibold leading-snug text-foreground">
                    {meta.label}
                  </span>
                  {detail && (
                    <span className="mt-0.5 block font-serif text-[0.82rem] leading-snug text-muted-foreground">
                      {detail}
                    </span>
                  )}
                </span>

                {source.source === "intent" && (
                  <span
                    title="Included because your question asked for this source type"
                    className="mt-[0.1rem] shrink-0 rounded border border-gold/45 px-1.5 py-0.5 text-[0.6rem] font-medium uppercase tracking-wider text-gold"
                  >
                    Scoped
                  </span>
                )}

                {canExpand && (
                  <ChevronDown
                    className={`mt-[0.15rem] h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform duration-300 ${
                      isOpen ? "rotate-180" : ""
                    }`}
                    aria-hidden="true"
                  />
                )}
              </button>

              {isOpen && source.text && (
                <div className="animate-fade-in border-t border-border/60 bg-muted/25 px-3 py-2.5">
                  <p
                    dir="auto"
                    className="max-h-64 overflow-y-auto whitespace-pre-wrap font-serif text-[0.86rem] leading-relaxed text-foreground/85 scrollbar-thin"
                  >
                    {source.text}
                  </p>
                  <p className="mt-2 border-t border-border/50 pt-1.5 text-[0.68rem] text-muted-foreground/80">
                    {source.citation}
                  </p>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
