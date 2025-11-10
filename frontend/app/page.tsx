"use client"

import { useState, useRef, useEffect } from "react"
import ChatHeader from "@/components/chat-header"
import ChatMessages from "@/components/chat-messages"
import ChatInput from "@/components/chat-input"
import Aurora from "@/components/aurora"
import { FloatingParticles } from "@/components/floating-particles"

export default function Home() {
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"
  type Message = {
    id: string
    role: "assistant" | "user"
    content: string
    sources?: string[]
    timestamp: Date
  }
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content:
        "السلام عليكم ورحمة الله وبركاته\n\nWelcome to the Sistani Jurisprudence Assistant. I am here to help answer your Islamic jurisprudence questions based on the rulings of Ayatullah al-Sistani. Feel free to ask about Islamic law, worship, and daily practices.",
      timestamp: new Date(),
    },
  ])
  const [loading, setLoading] = useState(false)
  const [input, setInput] = useState("")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const response = await fetch(`${BACKEND_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, top_k: 3 }),
      })

      if (!response.ok) throw new Error("API Error")
      const data = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Error:", error)
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          role: "assistant",
          content: "Sorry, I encountered an error. Please try again or check the connection to the API.",
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative flex flex-col h-screen bg-background overflow-hidden">
      <div className="absolute inset-0 z-0">
        <Aurora colorStops={["#10b981", "#34d399", "#059669"]} amplitude={0.8} blend={0.4} speed={1.2} />
        <FloatingParticles />
      </div>

      <div className="relative z-10 flex flex-col h-full">
        <ChatHeader />
        <ChatMessages messages={messages} loading={loading} />
        <div ref={messagesEndRef} />
        <ChatInput onSendMessage={handleSendMessage} disabled={loading} />
      </div>
    </div>
  )
}
