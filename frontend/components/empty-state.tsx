"use client"

import { ArrowUpRight } from "lucide-react"

/**
 * Opening screen. Starter questions solve the blank-page problem and simultaneously
 * communicate scope — each one is drawn from a different source in the library, so the
 * breadth of the corpus is shown rather than described.
 */
const STARTERS: { question: string; hint: string }[] = [
  { question: "What are the conditions for Friday prayer?", hint: "Worship" },
  { question: "How is the estate divided between a husband and wife?", hint: "Inheritance" },
  { question: "What invalidates a fast during Ramadan?", hint: "Fasting" },
  { question: "What are the ten impurities (najasat)?", hint: "Purity" },
  { question: "When does ihram become obligatory for Hajj?", hint: "Hajj" },
  { question: "What is taqlid and why is it necessary?", hint: "Foundations" },
]

interface EmptyStateProps {
  onPick: (question: string) => void
}

export default function EmptyState({ onPick }: EmptyStateProps) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-1 py-8 sm:py-14">
      <p
        dir="rtl"
        lang="ar"
        className="font-arabic text-2xl leading-loose text-primary sm:text-[1.75rem]"
      >
        السلام عليكم ورحمة الله وبركاته
      </p>

      <div className="rule-gold mt-5 w-40" />

      <h2 className="mt-5 text-center font-display text-2xl font-medium tracking-tight text-foreground sm:text-3xl">
        Ask a question of the sources
      </h2>
      <p className="mt-2.5 max-w-lg text-center font-serif text-[0.95rem] leading-relaxed text-muted-foreground">
        Every answer is retrieved from a library of eight works — the Quran, al-Sistani&apos;s
        rulings, and jurisprudence manuals — and cited down to the exact ruling or verse.
      </p>

      <ul className="mt-8 grid w-full gap-2 sm:grid-cols-2">
        {STARTERS.map((s, i) => (
          <li key={s.question} className="animate-rise" style={{ animationDelay: `${i * 60}ms` }}>
            <button
              type="button"
              onClick={() => onPick(s.question)}
              className="group flex h-full w-full flex-col items-start gap-1.5 rounded-xl border border-border/70 bg-card/50 px-3.5 py-3 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <span className="text-[0.64rem] font-semibold uppercase tracking-[0.14em] text-gold">
                {s.hint}
              </span>
              <span className="flex items-start gap-1.5 font-serif text-[0.9rem] leading-snug text-foreground">
                {s.question}
                <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
