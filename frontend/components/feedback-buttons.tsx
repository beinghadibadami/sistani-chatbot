"use client"

import { useState } from "react"
import { ThumbsDown, ThumbsUp } from "lucide-react"

import type { Rating } from "@/lib/types"

/**
 * Answer rating.
 *
 * A negative rating opens an optional comment box, because "this was wrong" is far more
 * actionable when paired with why. The submitted record includes the citations that were
 * retrieved, which is what makes bad answers diagnosable rather than merely counted.
 */
interface FeedbackButtonsProps {
  rating?: Rating
  onSubmit: (rating: Rating, comment?: string) => void
}

export default function FeedbackButtons({ rating, onSubmit }: FeedbackButtonsProps) {
  const [pendingNegative, setPendingNegative] = useState(false)
  const [comment, setComment] = useState("")

  if (rating) {
    return (
      <p className="mt-2 text-[0.72rem] text-muted-foreground">
        {rating === 1 ? "Thank you for the feedback." : "Thank you — this helps us improve."}
      </p>
    )
  }

  if (pendingNegative) {
    return (
      <div className="animate-rise mt-2 rounded-lg border border-border/70 bg-card/60 p-2.5">
        <label
          htmlFor="feedback-comment"
          className="block text-[0.72rem] font-medium text-muted-foreground"
        >
          What was wrong? (optional)
        </label>
        <textarea
          id="feedback-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={2}
          maxLength={2000}
          placeholder="Incorrect ruling, wrong source, missing detail…"
          className="mt-1.5 w-full resize-none rounded-md border border-border bg-input px-2.5 py-1.5 font-serif text-[0.85rem] text-foreground placeholder:text-muted-foreground/70 focus:outline-none focus:ring-2 focus:ring-ring/40"
        />
        <div className="mt-2 flex items-center gap-2">
          <button
            type="button"
            onClick={() => onSubmit(-1, comment.trim() || undefined)}
            className="rounded-md bg-primary px-2.5 py-1 text-[0.75rem] font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Submit
          </button>
          <button
            type="button"
            onClick={() => {
              setPendingNegative(false)
              setComment("")
            }}
            className="rounded-md px-2 py-1 text-[0.75rem] font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-2 flex items-center gap-1">
      <span className="mr-1 text-[0.72rem] text-muted-foreground/80">Helpful?</span>
      <button
        type="button"
        onClick={() => onSubmit(1)}
        aria-label="Helpful"
        className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        type="button"
        onClick={() => setPendingNegative(true)}
        aria-label="Not helpful"
        className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}
