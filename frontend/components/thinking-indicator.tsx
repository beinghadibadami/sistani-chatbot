"use client"

import { useEffect, useState } from "react"

import { COLD_START_HINT_MS } from "@/lib/api"

/**
 * Pre-first-token state.
 *
 * The free hosting tier sleeps after inactivity, so a first request can take 30-60s to wake
 * the service. Showing the same silent spinner throughout makes a waking service look like a
 * broken one, so the copy escalates over time and says what is actually happening.
 */
const STAGES = [
  { after: 0, label: "Searching the sources" },
  { after: 1400, label: "Reading the retrieved passages" },
  { after: COLD_START_HINT_MS, label: "Waking the service — this can take up to a minute" },
  { after: 20000, label: "Still waking up, thank you for your patience" },
]

export default function ThinkingIndicator() {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const started = Date.now()
    const timer = setInterval(() => setElapsed(Date.now() - started), 400)
    return () => clearInterval(timer)
  }, [])

  const stage = [...STAGES].reverse().find((s) => elapsed >= s.after) ?? STAGES[0]
  const isSlow = elapsed >= COLD_START_HINT_MS

  return (
    <div className="border-l-2 border-gold/40 pl-4 sm:pl-5" aria-live="polite">
      <div className="flex items-center gap-2.5">
        <span className="flex gap-1" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-primary"
              style={{ animation: `dot 1.3s ease-in-out ${i * 0.16}s infinite` }}
            />
          ))}
        </span>
        <span
          className={`font-serif text-[0.88rem] ${
            isSlow ? "text-muted-foreground" : "shimmer-text"
          }`}
        >
          {stage.label}
        </span>
      </div>
    </div>
  )
}
