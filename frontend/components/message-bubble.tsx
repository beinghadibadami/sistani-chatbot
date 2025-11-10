"use client"

import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

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
            remarkPlugins={[remarkGfm]}
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
              table: ({ node, ...props }) => (
                <div className="overflow-x-auto my-2">
                  <table className="min-w-full text-sm border border-border rounded-md" {...props} />
                </div>
              ),
              thead: ({ node, ...props }) => <thead className="bg-muted/40" {...props} />,
              tbody: ({ node, ...props }) => <tbody {...props} />,
              tr: ({ node, ...props }) => <tr className="border-b last:border-0" {...props} />,
              th: ({ node, ...props }) => (
                <th className="text-left px-3 py-2 font-semibold border-r last:border-r-0" {...props} />
              ),
              td: ({ node, ...props }) => <td className="px-3 py-2 align-top border-r last:border-r-0" {...props} />,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  )
}
