"use client"

import { useState } from "react"
import { ArrowUpRight, BookOpen, Droplets, Heart, Moon, Plane, Scale, Scroll, Users } from "lucide-react"

/**
 * Opening screen with topic categories and starter questions.
 *
 * Designed for an Indian (Gujarati/Hindi-speaking) Shia audience:
 * - Uses familiar Indian transliterations (namaz, roza, wazu)
 * - Topics reflect what this community actually asks about
 * - Language hint reassures users they can type in Gujarati/Hindi
 */

const TOPICS: {
  id: string
  label: string
  icon: React.ReactNode
  questions: { text: string; hint?: string }[]
}[] = [
  {
    id: "namaz",
    label: "Namaz",
    icon: <Moon className="h-4 w-4" />,
    questions: [
      { text: "What breaks namaz (things that invalidate prayer)?" },
      { text: "How to pray qasr namaz while travelling?" },
      { text: "What is the correct method of wazu?" },
    ],
  },
  {
    id: "roza",
    label: "Roza & Ramadan",
    icon: <Moon className="h-4 w-4" />,
    questions: [
      { text: "What invalidates a roza during Ramadan?" },
      { text: "What is the kaffara for missing a fast?" },
      { text: "Can I brush my teeth while fasting?" },
    ],
  },
  {
    id: "taharat",
    label: "Taharat (Purity)",
    icon: <Droplets className="h-4 w-4" />,
    questions: [
      { text: "What are the ten najis (impure) things?" },
      { text: "When is ghusl compulsory?" },
      { text: "How to do tayammum when water is not available?" },
    ],
  },
  {
    id: "nikah",
    label: "Nikah & Family",
    icon: <Heart className="h-4 w-4" />,
    questions: [
      { text: "What are the conditions for a valid nikah?" },
      { text: "Is mutah (temporary marriage) allowed?" },
      { text: "How is inheritance divided between husband and wife?" },
    ],
  },
  {
    id: "hajj",
    label: "Hajj & Umrah",
    icon: <Plane className="h-4 w-4" />,
    questions: [
      { text: "When does Hajj become compulsory on a person?" },
      { text: "What are the prohibitions during ihram?" },
      { text: "Can someone perform Hajj on behalf of another?" },
    ],
  },
  {
    id: "khums",
    label: "Khums & Zakat",
    icon: <Scale className="h-4 w-4" />,
    questions: [
      { text: "How is khums calculated on savings?" },
      { text: "What is the difference between khums and zakat?" },
      { text: "Is zakat compulsory on gold jewellery?" },
    ],
  },
  {
    id: "quran",
    label: "Quran & Dua",
    icon: <BookOpen className="h-4 w-4" />,
    questions: [
      { text: "Which verses talk about Friday congregational prayer?" },
      { text: "What does Surah Al-Fatihah mean?" },
      { text: "Is it allowed to recite Quran without wazu?" },
    ],
  },
  {
    id: "women",
    label: "Women's Rules",
    icon: <Users className="h-4 w-4" />,
    questions: [
      { text: "What are the signs of menstruation (haydh)?" },
      { text: "Can a woman pray during istihadha?" },
      { text: "What prayers does a woman need to make up after periods?" },
    ],
  },
]

interface EmptyStateProps {
  onPick: (question: string) => void
}

export default function EmptyState({ onPick }: EmptyStateProps) {
  const [activeTopic, setActiveTopic] = useState<string | null>(null)

  const active = TOPICS.find((t) => t.id === activeTopic)

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-1 py-6 sm:py-10">
      {/* Greeting */}
      <p
        dir="rtl"
        lang="ar"
        className="font-arabic text-2xl leading-loose text-primary sm:text-[1.75rem]"
      >
        بسم الله الرحمن الرحيم
      </p>

      <div className="rule-gold mt-4 w-40" />

      <h2 className="mt-4 text-center font-display text-xl font-medium tracking-tight text-foreground sm:text-2xl">
        Ask about any Islamic ruling
      </h2>
      <p className="mt-2 max-w-md text-center font-serif text-sm leading-relaxed text-muted-foreground">
        Answers based on the rulings of Ayatullah al-Sistani, with exact citations.
        <br />
        <span className="mt-1 inline-block text-primary/80">
          Gujarati ya Hindi mein bhi sawaal puch sakte ho ✓
        </span>
      </p>

      {/* Topic pills */}
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {TOPICS.map((topic) => (
          <button
            key={topic.id}
            type="button"
            onClick={() => setActiveTopic(activeTopic === topic.id ? null : topic.id)}
            className={`inline-flex min-h-[36px] items-center gap-1.5 rounded-full border px-3 py-1.5 text-[0.8rem] font-medium transition-all ${
              activeTopic === topic.id
                ? "border-primary/60 bg-primary/10 text-primary"
                : "border-border/70 bg-card/50 text-muted-foreground hover:border-primary/40 hover:text-foreground"
            }`}
          >
            {topic.icon}
            {topic.label}
          </button>
        ))}
      </div>

      {/* Questions for active topic */}
      {active && (
        <div className="mt-4 w-full animate-rise">
          <ul className="space-y-1.5">
            {active.questions.map((q, i) => (
              <li key={q.text}>
                <button
                  type="button"
                  onClick={() => onPick(q.text)}
                  className="group flex w-full min-h-[44px] items-center gap-2.5 rounded-xl border border-border/60 bg-card/40 px-3.5 py-2.5 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card hover:shadow-sm active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <span className="flex-1 font-serif text-sm leading-snug text-foreground">
                    {q.text}
                  </span>
                  <ArrowUpRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Default starters when no topic is selected */}
      {!active && (
        <div className="mt-6 w-full">
          <p className="mb-2.5 text-center text-[0.7rem] font-medium uppercase tracking-[0.12em] text-muted-foreground/70">
            Popular questions
          </p>
          <ul className="grid gap-2 sm:grid-cols-2">
            {[
              { text: "What are the conditions for Friday namaz?", hint: "Namaz" },
              { text: "How is the estate divided between husband and wife?", hint: "Inheritance" },
              { text: "What invalidates a roza during Ramadan?", hint: "Roza" },
              { text: "What are the ten najis things?", hint: "Taharat" },
              { text: "When does ihram become compulsory for Hajj?", hint: "Hajj" },
              { text: "How is khums calculated on yearly savings?", hint: "Khums" },
            ].map((s, i) => (
              <li key={s.text} className="animate-rise" style={{ animationDelay: `${i * 50}ms` }}>
                <button
                  type="button"
                  onClick={() => onPick(s.text)}
                  className="group flex h-full w-full min-h-[44px] flex-col items-start gap-1 rounded-xl border border-border/60 bg-card/40 px-3.5 py-2.5 text-left transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:bg-card hover:shadow-sm active:translate-y-0 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                >
                  <span className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-gold">
                    {s.hint}
                  </span>
                  <span className="font-serif text-[0.85rem] leading-snug text-foreground">
                    {s.text}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
