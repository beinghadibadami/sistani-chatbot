"use client"

import { CornerDownRight } from "lucide-react"

/**
 * Follow-up suggestions produced by the model in the same completion as the answer (separated
 * by a sentinel), so they cost a handful of output tokens rather than a second round trip.
 */
interface FollowupChipsProps {
  followups: string[]
  onPick: (question: string) => void
  disabled?: boolean
}

export default function FollowupChips({ followups, onPick, disabled }: FollowupChipsProps) {
  if (!followups?.length) return null

  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {followups.map((q, i) => (
        <button
          key={`${q}-${i}`}
          type="button"
          disabled={disabled}
          onClick={() => onPick(q)}
          className="animate-rise inline-flex items-center gap-1.5 rounded-full border border-border/80 bg-card/60 px-3 py-1.5 font-serif text-[0.82rem] text-foreground/90 transition-all hover:border-primary/45 hover:bg-primary/[0.06] hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          style={{ animationDelay: `${i * 70}ms` }}
        >
          <CornerDownRight className="h-3 w-3 shrink-0 text-muted-foreground" aria-hidden="true" />
          {q}
        </button>
      ))}
    </div>
  )
}
