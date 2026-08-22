export interface Source {
  citation: string
  doc_id: string
  chapter?: string | null
  section?: string | null
  locator?: string | null
  score?: number
  /** Which retriever surfaced this chunk: dense | bm25 | both | intent */
  source?: string
  /** The retrieved passage itself, shown when a citation is expanded. */
  text?: string
}

export type Rating = 1 | -1

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: Source[]
  followups?: string[]
  timestamp: number
  /** True while tokens are still arriving for this message. */
  streaming?: boolean
  /** Set once the user rates the answer, so the choice survives a reload. */
  rating?: Rating
  error?: boolean
}

export interface ProviderInfo {
  id: string
  model: string
  label: string
  notes: string
}

export interface SourceInfo {
  doc_id: string
  title: string
  chunks: number
}
