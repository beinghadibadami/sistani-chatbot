"use client"

/**
 * Dev-only model switcher — completely absent from production builds.
 *
 * Rendered only when NEXT_PUBLIC_DEV_MODE=true is in the environment. In production
 * that variable is simply not set, so the component renders null without any bundle
 * cost. This is the standard Next.js pattern for dev-only UI.
 *
 * The selected provider is passed per-request so you can flip mid-conversation and
 * compare answers on the same question. It is stored in sessionStorage (not
 * localStorage) so it resets on every browser tab — intentional, prevents accidentally
 * leaving a dev setting active across sessions.
 */

import { useEffect, useState } from "react"
import { FlaskConical, Zap } from "lucide-react"

import type { ProviderInfo } from "@/lib/types"

interface DevModelSwitcherProps {
  providers: ProviderInfo[]
  selected: string
  onChange: (provider: string) => void
  /** Show latency from the last completed request */
  lastTtft?: number | null
}

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  groq: <Zap className="h-3 w-3" />,
  gemini: <FlaskConical className="h-3 w-3" />,
}

export default function DevModelSwitcher({
  providers,
  selected,
  onChange,
  lastTtft,
}: DevModelSwitcherProps) {
  if (process.env.NEXT_PUBLIC_DEV_MODE !== "true") return null
  if (!providers.length) return null

  return (
    <div
      role="group"
      aria-label="Dev: model selector"
      className="flex items-center gap-1.5 rounded-lg border border-dashed border-amber-400/60 bg-amber-50/70 px-2 py-1 dark:border-amber-500/40 dark:bg-amber-950/30"
    >
      {/* DEV badge */}
      <span className="shrink-0 rounded bg-amber-400/80 px-1.5 py-0.5 text-[0.58rem] font-bold uppercase tracking-wider text-amber-950">
        DEV
      </span>

      {/* Provider buttons */}
      {providers.map((p) => {
        const active = selected === p.id
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onChange(p.id)}
            title={`${p.label} — ${p.notes}`}
            aria-pressed={active}
            className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[0.7rem] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-amber-500 ${
              active
                ? "bg-amber-400/90 text-amber-950"
                : "text-amber-800 hover:bg-amber-200/70 dark:text-amber-300 dark:hover:bg-amber-800/40"
            }`}
          >
            {PROVIDER_ICONS[p.id] ?? null}
            {p.label.split("·")[0].trim()}
          </button>
        )
      })}

      {/* Last TTFT */}
      {lastTtft != null && (
        <span
          aria-live="polite"
          className="ml-1 shrink-0 text-[0.62rem] tabular-nums text-amber-700/80 dark:text-amber-400/70"
        >
          {lastTtft >= 1000
            ? `${(lastTtft / 1000).toFixed(1)}s`
            : `${Math.round(lastTtft)}ms`}{" "}
          TTFT
        </span>
      )}
    </div>
  )
}
