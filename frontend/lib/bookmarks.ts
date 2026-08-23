/**
 * Saved rulings — localStorage persistence.
 *
 * A user can bookmark any assistant answer to reference it later. Stored locally
 * on device, no server involved — similar to browser bookmarks but for rulings.
 */

export interface SavedRuling {
  id: string
  question: string
  answer: string
  citations: string[]
  savedAt: number
}

const STORAGE_KEY = "sja.bookmarks"
const MAX_BOOKMARKS = 50

function getStore(): Storage | null {
  try {
    if (typeof window === "undefined") return null
    return window.localStorage
  } catch {
    return null
  }
}

export function loadBookmarks(): SavedRuling[] {
  const store = getStore()
  if (!store) return []
  try {
    const raw = store.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function saveBookmark(ruling: Omit<SavedRuling, "savedAt">): void {
  const store = getStore()
  if (!store) return
  try {
    const existing = loadBookmarks()
    // Don't duplicate
    if (existing.some((r) => r.id === ruling.id)) return
    const updated = [{ ...ruling, savedAt: Date.now() }, ...existing].slice(0, MAX_BOOKMARKS)
    store.setItem(STORAGE_KEY, JSON.stringify(updated))
  } catch {
    // Quota exceeded — silently fail
  }
}

export function removeBookmark(id: string): void {
  const store = getStore()
  if (!store) return
  try {
    const existing = loadBookmarks()
    store.setItem(STORAGE_KEY, JSON.stringify(existing.filter((r) => r.id !== id)))
  } catch {}
}

export function isBookmarked(id: string): boolean {
  return loadBookmarks().some((r) => r.id === id)
}
