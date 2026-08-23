/**
 * Backend client: SSE chat streaming, source list, model list, feedback.
 */

import type { ProviderInfo, Rating, Source, SourceInfo } from "./types"
export const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

/**
 * Render's free tier sleeps after inactivity; first request can take 30-60s.
 * Surfacing that as "waking up" rather than a stalled spinner is the difference between
 * looking slow and looking broken.
 */
export const COLD_START_HINT_MS = 4000

export interface StreamHandlers {
  onSources?: (sources: Source[], retrievalQuery: string | null) => void
  onDelta?: (text: string) => void
  onFollowups?: (followups: string[]) => void
  /**
   * Fired when the model declined the request as off-topic. Retrieval always runs
   * before generation decides this, so sources sent in the earlier "sources" event
   * must be retracted — they were never actually used in the answer.
   */
  onDeclined?: () => void
  onError?: (detail: string) => void
}

/** Cap replayed passages so the prompt cannot grow without bound. */
const MAX_PRIOR_SOURCES = 5

export async function streamChat(
  params: {
    question: string
    history: { role: string; content: string }[]
    topK?: number
    docIds?: string[]
    priorSources?: Source[]
    /** Provider override — only honoured by the backend when ALLOW_PROVIDER_OVERRIDE is set. */
    provider?: string
  },
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const prior = (params.priorSources ?? [])
    .filter((s) => s.text)
    .slice(0, MAX_PRIOR_SOURCES)
    .map((s) => ({
      citation: s.citation,
      text: s.text as string,
      doc_id: s.doc_id,
      chapter: s.chapter ?? null,
      section: s.section ?? null,
      locator: s.locator ?? null,
    }))

  const response = await fetch(`${BACKEND_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: params.question,
      history: params.history,
      top_k: params.topK ?? 5,
      doc_ids: params.docIds?.length ? params.docIds : null,
      prior_sources: prior.length ? prior : null,
      provider: params.provider ?? null,
    }),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`Request failed (${response.status})`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split("\n\n")
    buffer = frames.pop() ?? ""

    for (const frame of frames) {
      const lines = frame.split("\n")
      const event = lines.find((l) => l.startsWith("event:"))?.slice(6).trim()
      const data = lines.find((l) => l.startsWith("data:"))?.slice(5).trim()
      if (!event || !data) continue

      let payload: any
      try {
        payload = JSON.parse(data)
      } catch {
        continue
      }

      switch (event) {
        case "sources":
          // All retrieved sources are passed through — the display component caps what
          // the user sees, while the full set remains available for prior_sources replay.
          handlers.onSources?.(payload.sources ?? [], payload.retrieval_query ?? null)
          break
        case "delta":
          handlers.onDelta?.(payload.text ?? "")
          break
        case "followups":
          handlers.onFollowups?.(payload.followups ?? [])
          break
        case "declined":
          handlers.onDeclined?.()
          break
        case "error":
          handlers.onError?.(payload.detail ?? "Unknown error")
          break
      }
    }
  }
}

export async function fetchModels(): Promise<{ providers: ProviderInfo[]; current: string }> {
  try {
    const res = await fetch(`${BACKEND_URL}/models`)
    if (!res.ok) return { providers: [], current: "groq" }
    return res.json()
  } catch {
    return { providers: [], current: "groq" }
  }
}

export async function fetchSources(): Promise<SourceInfo[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/sources`)
    if (!res.ok) return []
    const data = await res.json()
    return data.sources ?? []
  } catch {
    return []
  }
}

export async function sendFeedback(payload: {
  sessionId: string
  question: string
  answer: string
  rating: Rating
  comment?: string
  citations?: Source[]
}): Promise<boolean> {
  try {
    const res = await fetch(`${BACKEND_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: payload.sessionId,
        question: payload.question,
        answer: payload.answer,
        rating: payload.rating,
        comment: payload.comment || null,
        citations: (payload.citations ?? []).map(({ text, ...rest }) => rest),
        retrieval: {},
      }),
    })
    return res.ok
  } catch {
    return false
  }
}
