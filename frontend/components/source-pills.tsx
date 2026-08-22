"use client"

import { BookOpen, Scroll, FileText, HelpCircle, MapPin, Users } from "lucide-react"

export interface Source {
  citation: string
  doc_id: string
  chapter?: string | null
  section?: string | null
  locator?: string | null
  score?: number
  source?: string
}

// Short display labels, since the full citation already names the work.
const DOC_META: Record<string, { label: string; Icon: typeof BookOpen }> = {
  quran: { label: "Quran", Icon: BookOpen },
  islamic_laws: { label: "Islamic Laws", Icon: Scroll },
  sistani_qna: { label: "Q&A", Icon: HelpCircle },
  hajj_rituals: { label: "Hajj", Icon: MapPin },
  summary_worship: { label: "Worship", Icon: FileText },
  women_rules: { label: "Women's Rules", Icon: Users },
  jurisprudence_easy: { label: "Jurisprudence", Icon: FileText },
}

interface SourcePillsProps {
  sources: Source[]
}

export default function SourcePills({ sources }: SourcePillsProps) {
  if (!sources?.length) return null

  // The same work can be cited more than once; show each distinct citation once.
  const seen = new Set<string>()
  const unique = sources.filter((s) => {
    if (seen.has(s.citation)) return false
    seen.add(s.citation)
    return true
  })

  return (
    <div className="flex flex-wrap items-center gap-2 mt-3">
      <span className="text-xs font-semibold text-foreground/60 uppercase tracking-wide">Sources</span>
      {unique.map((source, index) => {
        const meta = DOC_META[source.doc_id] ?? { label: source.doc_id, Icon: FileText }
        const Icon = meta.Icon
        // Drop the work title from the visible text; the icon and label convey it.
        const detail = source.citation.split(" — ").slice(1).join(" · ")
        return (
          <span
            key={`${source.citation}-${index}`}
            title={source.citation}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/30 animate-fade-in hover:bg-primary/20 hover:border-primary/50 transition-all duration-300"
            style={{ animationDelay: `${index * 80}ms` }}
          >
            <Icon className="h-3 w-3 shrink-0" aria-hidden="true" />
            <span className="font-semibold">{meta.label}</span>
            {detail && <span className="opacity-80">{detail}</span>}
          </span>
        )
      })}
    </div>
  )
}
