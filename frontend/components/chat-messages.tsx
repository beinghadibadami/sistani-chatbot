"use client"

import { useEffect, useRef, useState } from "react"

import EmptyState from "./empty-state"
import FeedbackButtons from "./feedback-buttons"
import FollowupChips from "./followup-chips"
import MessageActions from "./message-actions"
import MessageBubble from "./message-bubble"
import SourceCards from "./source-cards"
import ThinkingIndicator from "./thinking-indicator"
import { isBookmarked, removeBookmark, saveBookmark } from "@/lib/bookmarks"
import type { Message, Rating } from "@/lib/types"

interface ChatMessagesProps {
  messages: Message[]
  loading: boolean
  onPickQuestion: (question: string) => void
  onRate: (messageId: string, rating: Rating, comment?: string) => void
}

export default function ChatMessages({
  messages,
  loading,
  onPickQuestion,
  onRate,
}: ChatMessagesProps) {
  const endRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const pinnedRef = useRef(true)
  const last = messages[messages.length - 1]
  // Track bookmarked message IDs to reactively update the UI
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set())

  // Load bookmark state on mount
  useEffect(() => {
    const ids = new Set(
      messages
        .filter((m) => m.role === "assistant" && isBookmarked(m.id))
        .map((m) => m.id)
    )
    setBookmarkedIds(ids)
  }, [messages.length])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const onScroll = () => {
      const distance = el.scrollHeight - el.scrollTop - el.clientHeight
      pinnedRef.current = distance < 120
    }
    el.addEventListener("scroll", onScroll, { passive: true })
    return () => el.removeEventListener("scroll", onScroll)
  }, [])

  useEffect(() => {
    if (!pinnedRef.current) return
    endRef.current?.scrollIntoView({ behavior: last?.streaming ? "auto" : "smooth" })
  }, [messages.length, last?.content, last?.streaming, loading])

  const handleBookmark = (msg: Message) => {
    const alreadyBookmarked = bookmarkedIds.has(msg.id)
    if (alreadyBookmarked) {
      removeBookmark(msg.id)
      setBookmarkedIds((prev) => { const next = new Set(prev); next.delete(msg.id); return next })
    } else {
      // Find the user question that preceded this answer
      const idx = messages.findIndex((m) => m.id === msg.id)
      const question = [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")
      saveBookmark({
        id: msg.id,
        question: question?.content ?? "",
        answer: msg.content,
        citations: (msg.sources ?? []).map((s) => s.citation),
      })
      setBookmarkedIds((prev) => new Set(prev).add(msg.id))
    }
  }

  const isEmpty = messages.length === 0

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
        {isEmpty ? (
          <EmptyState onPick={onPickQuestion} />
        ) : (
          <div className="space-y-7">
            {messages.map((message, idx) => (
              <div key={message.id} className="animate-rise">
                <MessageBubble
                  role={message.role}
                  content={message.content}
                  streaming={message.streaming}
                  error={message.error}
                />

                {message.role === "assistant" && !message.streaming && !message.error && (
                  <>
                    {message.sources && message.sources.length > 0 && (
                      <div className="ml-[46px] sm:ml-[46px]">
                        <SourceCards sources={message.sources} />
                      </div>
                    )}

                    <div className="ml-[46px] sm:ml-[46px]">
                      <MessageActions
                        content={message.content}
                        question={
                          [...messages.slice(0, idx)].reverse().find((m) => m.role === "user")?.content
                        }
                        citations={(message.sources ?? []).map((s) => s.citation)}
                        messageId={message.id}
                        isBookmarked={bookmarkedIds.has(message.id)}
                        onBookmark={() => handleBookmark(message)}
                      />

                      <FeedbackButtons
                        rating={message.rating}
                        onSubmit={(rating, comment) => onRate(message.id, rating, comment)}
                      />

                      {message.followups && message.followups.length > 0 && (
                        <FollowupChips
                          followups={message.followups}
                          onPick={onPickQuestion}
                          disabled={loading}
                        />
                      )}
                    </div>
                  </>
                )}
              </div>
            ))}

            {loading && !last?.streaming && <ThinkingIndicator />}
          </div>
        )}

        <div ref={endRef} className="h-2" />
      </div>
    </div>
  )
}
