"use client"

import { useEffect, useRef } from "react"

import EmptyState from "./empty-state"
import FeedbackButtons from "./feedback-buttons"
import FollowupChips from "./followup-chips"
import MessageBubble from "./message-bubble"
import SourceCards from "./source-cards"
import ThinkingIndicator from "./thinking-indicator"
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

  // Only auto-scroll while the user is already near the bottom, so scrolling up to read an
  // earlier answer is not fought by incoming tokens.
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

  const isEmpty = messages.length === 0

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6">
        {isEmpty ? (
          <EmptyState onPick={onPickQuestion} />
        ) : (
          <div className="space-y-7">
            {messages.map((message) => (
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
                      <SourceCards sources={message.sources} />
                    )}

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
                  </>
                )}
              </div>
            ))}

            {/* Shown only until the first token lands; after that the caret conveys progress. */}
            {loading && !last?.streaming && <ThinkingIndicator />}
          </div>
        )}

        <div ref={endRef} className="h-2" />
      </div>
    </div>
  )
}
