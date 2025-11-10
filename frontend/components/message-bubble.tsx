"use client"

import ReactMarkdown from "react-markdown"

interface MessageBubbleProps {
  role: "user" | "assistant"
  content: string
}

export default function MessageBubble({ role, content }: MessageBubbleProps) {
  const isUser = role === "user"

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl px-4 py-3 rounded-2xl shadow-sm transition-all duration-300 hover:shadow-lg ${
          isUser
            ? "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground rounded-br-none"
            : "bg-white dark:bg-slate-900 border border-primary/30 text-foreground rounded-bl-none shadow-md hover:border-primary/50"
        }`}
      >
        <div className="prose dark:prose-invert prose-sm max-w-none">
          <ReactMarkdown
            components={{
              p: ({ node, ...props }) => <p className="mb-2 last:mb-0 leading-relaxed" {...props} />,
              strong: ({ node, ...props }) => (
                <strong className="font-semibold text-primary dark:text-accent" {...props} />
              ),
              em: ({ node, ...props }) => <em className="italic opacity-80" {...props} />,
              a: ({ node, ...props }) => <a className="text-primary hover:underline" {...props} />,
              ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1 mb-2" {...props} />,
              ol: ({ node, ...props }) => <ol className="list-decimal list-inside space-y-1 mb-2" {...props} />,
              li: ({ node, ...props }) => <li className="text-sm" {...props} />,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
