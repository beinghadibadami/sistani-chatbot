"use client"

import { useState } from "react"
import { Bookmark, BookmarkCheck, Check, Copy, Share2 } from "lucide-react"

/**
 * Action buttons below assistant messages: Copy, Share (WhatsApp), Bookmark.
 * Visible always on mobile, hover-reveal on desktop.
 */

interface MessageActionsProps {
  content: string
  question?: string
  citations?: string[]
  messageId: string
  isBookmarked: boolean
  onBookmark: () => void
}

export default function MessageActions({
  content,
  question,
  citations,
  messageId,
  isBookmarked,
  onBookmark,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false)

  const copyText = () => {
    const parts: string[] = []
    if (question) parts.push(`Q: ${question}`)
    parts.push(content)
    if (citations?.length) {
      parts.push(`\nSources: ${citations.join(", ")}`)
    }
    navigator.clipboard.writeText(parts.join("\n\n")).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    }).catch(() => {})
  }

  const shareWhatsApp = () => {
    const parts: string[] = []
    if (question) parts.push(`*Q: ${question}*`)
    const trimmed = content.length > 1400 ? content.slice(0, 1400) + "…" : content
    parts.push(trimmed)
    if (citations?.length) {
      parts.push(`\n📚 ${citations.slice(0, 3).join(" | ")}`)
    }
    parts.push("\n🔗 al-sistani-chat.onrender.com")
    parts.push("_— Sistani Jurisprudence Assistant_")

    const text = encodeURIComponent(parts.join("\n\n"))
    window.open(`https://wa.me/?text=${text}`, "_blank", "noopener")
  }

  return (
    <div className="mt-2 flex items-center gap-0.5">
      {/* Copy */}
      <button
        type="button"
        onClick={copyText}
        aria-label={copied ? "Copied" : "Copy answer"}
        className="inline-flex min-h-[44px] items-center gap-1.5 rounded-md px-2.5 py-2 text-[0.75rem] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        {copied ? (
          <>
            <Check className="h-4 w-4 text-primary" />
            <span className="hidden sm:inline">Copied</span>
          </>
        ) : (
          <>
            <Copy className="h-4 w-4" />
            <span className="hidden sm:inline">Copy</span>
          </>
        )}
      </button>

      {/* Share via WhatsApp */}
      <button
        type="button"
        onClick={shareWhatsApp}
        aria-label="Share on WhatsApp"
        className="inline-flex min-h-[44px] items-center gap-1.5 rounded-md px-2.5 py-2 text-[0.75rem] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground active:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <Share2 className="h-4 w-4" />
        <span className="hidden sm:inline">Share</span>
      </button>

      {/* Bookmark */}
      <button
        type="button"
        onClick={onBookmark}
        aria-label={isBookmarked ? "Remove bookmark" : "Save this ruling"}
        className={`inline-flex min-h-[44px] items-center gap-1.5 rounded-md px-2.5 py-2 text-[0.75rem] font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${
          isBookmarked
            ? "text-gold hover:bg-muted active:bg-muted"
            : "text-muted-foreground hover:bg-muted hover:text-foreground active:bg-muted"
        }`}
      >
        {isBookmarked ? (
          <>
            <Bookmark className="h-4 w-4 fill-current" />
            <span className="hidden sm:inline">Saved</span>
          </>
        ) : (
          <>
            <Bookmark className="h-4 w-4" />
            <span className="hidden sm:inline">Save</span>
          </>
        )}
      </button>
    </div>
  )
}
