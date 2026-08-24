"use client"

import { useEffect, useState } from "react"
import { Info, Bookmark, RotateCcw, X } from "lucide-react"

import ScopeFilter from "./scope-filter"
import type { SourceInfo } from "@/lib/types"

interface ChatHeaderProps {
  sources: SourceInfo[]
  scope: string[]
  onScopeChange: (docIds: string[]) => void
  onReset: () => void
  onOpenBookmarks: () => void
  hasMessages: boolean
}

export default function ChatHeader({
  sources,
  scope,
  onScopeChange,
  onReset,
  onOpenBookmarks,
  hasMessages,
}: ChatHeaderProps) {
  const [showDisclaimer, setShowDisclaimer] = useState(false)
  const [condensed, setCondensed] = useState(false)

  // Collapse the header once a conversation is underway so the answers get the space.
  useEffect(() => {
    setCondensed(hasMessages)
  }, [hasMessages])

  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur-xl">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <div
          className={`flex items-center justify-between gap-3 transition-all duration-500 ${
            condensed ? "py-3" : "py-6"
          }`}
        >
          <div className="flex min-w-0 items-center gap-3">
            <Seal condensed={condensed} />
            <div className="min-w-0">
              <h1
                className={`font-display font-semibold tracking-tight text-foreground transition-all duration-500 ${
                  condensed ? "text-base sm:text-lg" : "text-lg sm:text-2xl"
                }`}
              >
                Sistani Jurisprudence
              </h1>
              {!condensed && (
                <p className="mt-0.5 hidden sm:block font-serif text-sm text-muted-foreground animate-fade-in">
                  Answers grounded in cited rulings, not paraphrase
                </p>
              )}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <ScopeFilter sources={sources} scope={scope} onChange={onScopeChange} />

            <button
              type="button"
              onClick={onOpenBookmarks}
              aria-label="View saved rulings"
              title="Saved rulings"
              className="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <Bookmark className="h-4 w-4" />
            </button>

            <button
              type="button"
              onClick={() => setShowDisclaimer((v) => !v)}
              aria-label="About this assistant"
              aria-expanded={showDisclaimer}
              title="About"
              className="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <Info className="h-4 w-4" />
            </button>

            {hasMessages && (
              <button
                type="button"
                onClick={onReset}
                aria-label="Start a new conversation"
                title="New chat"
                className="grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {showDisclaimer && (
          <div className="animate-rise pb-4">
            <div className="relative rounded-lg border border-gold/35 bg-gold/[0.06]">
              <button
                type="button"
                onClick={() => setShowDisclaimer(false)}
                aria-label="Dismiss"
                className="absolute right-1 top-1 z-10 grid min-h-[44px] min-w-[44px] place-items-center rounded-lg text-muted-foreground transition-colors hover:text-foreground active:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>

              <div className="max-h-[70vh] overflow-y-auto overscroll-contain p-4 pr-9 scrollbar-thin">
                <h2 className="font-display text-base font-semibold text-foreground">
                  About this assistant
                </h2>
                <p className="mt-1.5 font-serif text-[0.9rem] leading-relaxed text-foreground/85">
                  Ask questions on Islamic rulings — prayer, fasting, hajj, purity, family
                  matters and daily practice — answered from the rulings of Grand Ayatollah
                  Sayyid Ali al-Sistani. You can ask in English, Hindi, Gujarati or Urdu, and
                  every answer cites the passages it drew on.
                </p>

                <p className="mt-2.5 font-serif text-[0.85rem] leading-relaxed text-foreground/70">
                  <span className="font-medium text-gold">Coming soon:</span> more sources from
                  the Ahlul Bayt (as) tradition — including Al-Kafi, Bihar al-Anwar and
                  Nahjul Balagha.
                </p>

                <h3 className="mt-3 font-display text-sm font-semibold text-foreground">
                  Please keep in mind
                </h3>
                <p className="mt-1 font-serif text-[0.9rem] leading-relaxed text-foreground/85">
                  This is an early version and may occasionally be incomplete or mistaken.
                  Expand the sources under each answer to read the original text. For any
                  consequential matter, verify against your Marja&apos;s official rulings or
                  consult a qualified scholar.
                </p>

                <div className="mt-3 border-t border-gold/25 pt-3">
                  <p className="font-serif text-[0.85rem] leading-relaxed text-foreground/75">
                    Questions, feedback or found a problem? Reach out at{" "}
                    <a
                      href="mailto:asteroid.dest101@gmail.com"
                      className="font-medium text-primary underline underline-offset-2 hover:text-primary/80"
                    >
                      asteroid.dest101@gmail.com
                    </a>
                  </p>
                  <p className="mt-2 font-serif text-[0.78rem] italic text-muted-foreground">
                    Built with care for the community
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="rule-gold" />
    </header>
  )
}

/** Eight-point star seal, echoing the backdrop tessellation. */
function Seal({ condensed }: { condensed: boolean }) {
  return (
    <span
      className={`relative grid shrink-0 place-items-center transition-all duration-500 ${
        condensed ? "h-7 w-7 sm:h-8 sm:w-8" : "h-9 w-9 sm:h-11 sm:w-11"
      }`}
    >
      <span className="absolute inset-0 rounded-lg bg-primary/10" />
      <svg viewBox="0 0 40 40" className="relative h-[62%] w-[62%]" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeWidth="1.6" className="text-primary">
          <rect x="9" y="9" width="22" height="22" />
          <rect x="9" y="9" width="22" height="22" transform="rotate(45 20 20)" />
        </g>
        <circle cx="20" cy="20" r="3" className="fill-gold" />
      </svg>
    </span>
  )
}
