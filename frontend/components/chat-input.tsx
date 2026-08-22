"use client"

import type React from "react"
import { useEffect, useRef, useState } from "react"
import { ArrowUp, Square } from "lucide-react"

interface ChatInputProps {
  onSendMessage: (message: string) => void
  onStop: () => void
  disabled?: boolean
  /** Prefilled text, e.g. from a starter or follow-up chip. */
  seed?: string
}

const MAX_ROWS_PX = 168

export default function ChatInput({ onSendMessage, onStop, disabled, seed }: ChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Grow with content up to a ceiling, then scroll internally.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, MAX_ROWS_PX)}px`
  }, [input])

  useEffect(() => {
    if (seed) {
      setInput(seed)
      textareaRef.current?.focus()
    }
  }, [seed])

  const submit = () => {
    const text = input.trim()
    if (!text || disabled) return
    onSendMessage(text)
    setInput("")
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    submit()
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends; Shift+Enter inserts a newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="sticky bottom-0 z-20 border-t border-border/60 bg-background/85 backdrop-blur-xl">
      <form onSubmit={handleSubmit} className="mx-auto max-w-3xl px-4 pb-3 pt-3 sm:px-6 sm:pb-4">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-input px-3 py-2 shadow-sm transition-colors focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-ring/25">
          <textarea
            ref={textareaRef}
            dir="auto"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about rulings, worship, or a specific verse…"
            aria-label="Your question"
            className="max-h-[168px] flex-1 resize-none bg-transparent py-1.5 font-serif text-[0.95rem] leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/70 scrollbar-thin"
          />

          {disabled ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop generating"
              className="mb-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-muted text-foreground transition-colors hover:bg-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <Square className="h-3 w-3 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="Send question"
              className="mb-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-30 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <ArrowUp className="h-4 w-4" />
            </button>
          )}
        </div>

        <p className="mt-1.5 px-1 text-center text-[0.68rem] text-muted-foreground/70">
          AI-generated · verify consequential matters against the cited sources
        </p>
      </form>
    </div>
  )
}
