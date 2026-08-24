"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

import ScholarAvatar from "./scholar-avatar"

interface MessageBubbleProps {
  role: "user" | "assistant"
  content: string
  streaming?: boolean
  error?: boolean
}

export default function MessageBubble({ role, content, streaming, error }: MessageBubbleProps) {
  const isUser = role === "user"

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div
          dir="auto"
          className="max-w-[85%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 font-sans text-[0.95rem] leading-relaxed text-primary-foreground shadow-sm"
        >
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="group relative">
      {/* Avatar above text on mobile, beside on desktop */}
      <div className="mb-2 sm:hidden">
        <ScholarAvatar />
      </div>

      <div className="flex gap-3">
        {/* Avatar beside text on desktop only */}
        <div className="mt-1 hidden shrink-0 sm:block">
          <ScholarAvatar />
        </div>

        {/* Answer content — full width on mobile, constrained on desktop */}
        <div className="min-w-0 flex-1">
          <div
            dir="auto"
            className={`prose-answer ${error ? "text-destructive" : "text-foreground"}`}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ node, ...props }) => (
                  <div className="overflow-x-auto -mx-1 px-1 my-2">
                    <table {...props} />
                  </div>
                ),
                a: ({ node, ...props }) => (
                  <a {...props} target="_blank" rel="noopener noreferrer" />
                ),
              }}
            >
              {content}
            </ReactMarkdown>

            {streaming && (
              <span
                aria-hidden="true"
                className="animate-caret ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[0.15em] bg-primary"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
