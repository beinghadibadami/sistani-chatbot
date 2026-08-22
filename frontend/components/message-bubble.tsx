"use client"

import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Check, Copy } from "lucide-react"

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
      {/* Assistant answers are unbubbled: a gold margin rule reads as a manuscript gloss
          rather than a chat balloon, and gives long answers a full measure to breathe. */}
      <div className="relative border-l-2 border-gold/40 pl-4 sm:pl-5">
        <div
          dir="auto"
          className={`prose-answer ${error ? "text-destructive" : "text-foreground"}`}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Open any model-provided link safely.
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

        {!streaming && !error && content.trim().length > 0 && (
          <CopyButton text={content} />
        )}
      </div>
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* clipboard unavailable (insecure context or denied permission) */
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      aria-label={copied ? "Copied" : "Copy answer"}
      className="mt-2 inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-[0.72rem] font-medium text-muted-foreground opacity-0 transition-all hover:bg-muted hover:text-foreground focus-visible:opacity-100 group-hover:opacity-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-primary" />
          Copied
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          Copy
        </>
      )}
    </button>
  )
}
