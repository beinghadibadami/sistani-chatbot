"use client"

import { useEffect, useRef } from "react"
import MessageBubble from "./message-bubble"
import TypingIndicator from "./typing-indicator"
import SourcePills from "./source-pills"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: string[]
  timestamp: Date
}

interface ChatMessagesProps {
  messages: Message[]
  loading: boolean
}

export default function ChatMessages({ messages, loading }: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 space-y-4 scrollbar-thin">
      <div className="max-w-4xl mx-auto space-y-4">
        {messages.map((message, index) => (
          <div key={message.id} className="animate-slide-in" style={{ animationDelay: `${index * 50}ms` }}>
            <MessageBubble role={message.role} content={message.content} />
            {/* {message.role === "assistant" && message.sources && message.sources.length > 0 && (
              <SourcePills sources={message.sources} />
            )} */}
          </div>
        ))}

        {loading && (
          <div className="animate-slide-in">
            <TypingIndicator />
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
