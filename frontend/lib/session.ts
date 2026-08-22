/**
 * Guest session identity and local chat persistence.
 *
 * No accounts: a random UUID in localStorage is enough to correlate a user's feedback over
 * time without collecting anything identifying. Conversations live only on the device, so
 * there is no server-side chat storage to secure or maintain.
 */

import type { Message } from "./types"

const SESSION_KEY = "sja.session-id"
const CHAT_KEY = "sja.chat"
const SCOPE_KEY = "sja.scope"
const CHAT_VERSION = 1
/** Cap persisted history so localStorage cannot grow without bound. */
const MAX_PERSISTED = 100

function safeLocalStorage(): Storage | null {
  // Private browsing and disabled-storage settings make access throw rather than return null.
  try {
    if (typeof window === "undefined") return null
    const probe = "__sja_probe__"
    window.localStorage.setItem(probe, "1")
    window.localStorage.removeItem(probe)
    return window.localStorage
  } catch {
    return null
  }
}

export function getSessionId(): string {
  const store = safeLocalStorage()
  if (!store) return "ephemeral-session"

  let id = store.getItem(SESSION_KEY)
  if (!id) {
    id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `sja-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`
    store.setItem(SESSION_KEY, id)
  }
  return id
}

interface PersistedChat {
  version: number
  messages: Message[]
}

export function loadChat(): Message[] | null {
  const store = safeLocalStorage()
  if (!store) return null
  try {
    const raw = store.getItem(CHAT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedChat
    if (parsed.version !== CHAT_VERSION || !Array.isArray(parsed.messages)) return null
    // A message persisted mid-stream would otherwise reload stuck in a streaming state.
    return parsed.messages.map((m) => ({ ...m, streaming: false }))
  } catch {
    return null
  }
}

export function saveChat(messages: Message[]): void {
  const store = safeLocalStorage()
  if (!store) return
  try {
    const trimmed = messages.slice(-MAX_PERSISTED)
    store.setItem(CHAT_KEY, JSON.stringify({ version: CHAT_VERSION, messages: trimmed }))
  } catch {
    // Quota exceeded: drop history rather than breaking the session.
    try {
      store.removeItem(CHAT_KEY)
    } catch {
      /* ignore */
    }
  }
}

export function clearChat(): void {
  safeLocalStorage()?.removeItem(CHAT_KEY)
}

export function loadScope(): string[] {
  const store = safeLocalStorage()
  if (!store) return []
  try {
    const raw = store.getItem(SCOPE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : []
  } catch {
    return []
  }
}

export function saveScope(docIds: string[]): void {
  const store = safeLocalStorage()
  if (!store) return
  try {
    store.setItem(SCOPE_KEY, JSON.stringify(docIds))
  } catch {
    /* ignore */
  }
}
