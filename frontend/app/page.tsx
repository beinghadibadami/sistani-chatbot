"use client"

import { useCallback, useEffect, useRef, useState } from "react"

import ChatHeader from "@/components/chat-header"
import ChatInput from "@/components/chat-input"
import ChatMessages from "@/components/chat-messages"
import DevModelSwitcher from "@/components/dev-model-switcher"
import GeometricBackdrop from "@/components/geometric-backdrop"
import { fetchModels, fetchSources, sendFeedback, streamChat } from "@/lib/api"
import {
  clearChat,
  getSessionId,
  loadChat,
  loadScope,
  saveChat,
  saveScope,
} from "@/lib/session"
import type { Message, ProviderInfo, Rating, Source, SourceInfo } from "@/lib/types"

const HISTORY_TURNS = 6

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [scope, setScope] = useState<string[]>([])
  const [seed, setSeed] = useState<string | undefined>()
  const [hydrated, setHydrated] = useState(false)
  // Dev model switcher state — only meaningful when NEXT_PUBLIC_DEV_MODE=true
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [selectedProvider, setSelectedProvider] = useState<string>("groq")
  const [lastTtft, setLastTtft] = useState<number | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  const sessionIdRef = useRef<string>("")

  // Restore local state after mount; localStorage is unavailable during SSR.
  useEffect(() => {
    sessionIdRef.current = getSessionId()
    const saved = loadChat()
    if (saved?.length) setMessages(saved)
    setScope(loadScope())
    setHydrated(true)
    fetchSources().then(setSources)
    // Only fetch models list in dev mode (the switcher is hidden in prod anyway).
    if (process.env.NEXT_PUBLIC_DEV_MODE === "true") {
      fetchModels().then(({ providers: ps, current }) => {
        setProviders(ps)
        setSelectedProvider(current)
      })
    }
  }, [])

  useEffect(() => {
    if (hydrated) saveChat(messages)
  }, [messages, hydrated])

  useEffect(() => () => abortRef.current?.abort(), [])

  const patch = useCallback((id: string, changes: Partial<Message>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...changes } : m)))
  }, [])

  const handleScopeChange = (docIds: string[]) => {
    setScope(docIds)
    saveScope(docIds)
  }

  const handleReset = () => {
    abortRef.current?.abort()
    setMessages([])
    clearChat()
    setLoading(false)
  }

  const handleStop = () => {
    abortRef.current?.abort()
    setLoading(false)
    // Keep whatever text arrived; just mark it finished so actions become available.
    setMessages((prev) =>
      prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)),
    )
  }

  const send = async (text: string) => {
    const question = text.trim()
    if (!question || loading) return

    setSeed(undefined)

    const userMessage: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question,
      timestamp: Date.now(),
    }
    const assistantId = `a-${Date.now()}`

    // History is built from state as it was before this turn.
    const history = messages
      .filter((m) => !m.error)
      .slice(-HISTORY_TURNS)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    let answer = ""
    let started = false
    let collected: Source[] = []
    const ttftStart = Date.now()
    let ttftRecorded = false

    // Replay the most recent turn's passages so a follow-up retains its subject.
    const priorSources =
      [...messages].reverse().find((m) => m.role === "assistant" && m.sources?.length)
        ?.sources ?? []

    try {
      await streamChat(
        { question, history, topK: 5, docIds: scope, priorSources, provider: selectedProvider },
        {
          onSources: (incoming) => {
            collected = incoming
            // Create the assistant bubble as soon as sources arrive so the user sees
            // something immediately (~0ms after the first SSE event) rather than waiting
            // up to ~4s for the first text token. At TTFT the bubble shows sources only;
            // text fills in as it streams. The thinking indicator disappears at this point.
            if (!started) {
              started = true
              setMessages((prev) => [
                ...prev,
                {
                  id: assistantId,
                  role: "assistant" as const,
                  content: "",
                  sources: incoming,
                  timestamp: Date.now(),
                  streaming: true,
                },
              ])
            } else {
              patch(assistantId, { sources: incoming })
            }
          },
          onDelta: (piece) => {
            answer += piece
            if (!ttftRecorded) {
              setLastTtft(Date.now() - ttftStart)
              ttftRecorded = true
            }
            if (!started) {
              // Fallback: sources event was missed, create bubble on first text
              started = true
              setMessages((prev) => [
                ...prev,
                {
                  id: assistantId,
                  role: "assistant" as const,
                  content: answer,
                  sources: collected,
                  timestamp: Date.now(),
                  streaming: true,
                },
              ])
            } else {
              patch(assistantId, { content: answer })
            }
          },
          onFollowups: (followups) => {
            patch(assistantId, { followups })
          },
          onDeclined: () => {
            // Sources were shown before the model decided the request was off-topic;
            // retract them since the answer never actually drew on them.
            collected = []
            patch(assistantId, { sources: [] })
          },
          onError: (detail) => {
            throw new Error(detail)
          },
        },
        controller.signal,
      )

      if (!started) {
        // Stream completed without producing any text.
        setMessages((prev) => [
          ...prev,
          {
            id: assistantId,
            role: "assistant",
            content: "I could not produce an answer for that. Please try rephrasing.",
            timestamp: Date.now(),
            error: true,
          },
        ])
      } else {
        patch(assistantId, { streaming: false, sources: collected })
      }
    } catch (error) {
      if ((error as Error).name === "AbortError") return
      console.error("Chat failed:", error)
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== assistantId),
        {
          id: `e-${Date.now()}`,
          role: "assistant",
          content:
            "I could not reach the service. If it has been idle it may be waking up — please try again in a moment.",
          timestamp: Date.now(),
          error: true,
        },
      ])
    } finally {
      setLoading(false)
      abortRef.current = null
    }
  }

  const handleRate = async (messageId: string, rating: Rating, comment?: string) => {
    // Record the choice immediately; feedback delivery is telemetry and must not gate the UI.
    patch(messageId, { rating })

    const index = messages.findIndex((m) => m.id === messageId)
    const answer = messages[index]
    const question = [...messages.slice(0, index)].reverse().find((m) => m.role === "user")

    if (!answer || !question) return

    await sendFeedback({
      sessionId: sessionIdRef.current,
      question: question.content,
      answer: answer.content,
      rating,
      comment,
      citations: answer.sources ?? [],
    })
  }

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden">
      <GeometricBackdrop />

      <div className="relative z-10 flex h-full flex-col">
        <ChatHeader
          sources={sources}
          scope={scope}
          onScopeChange={handleScopeChange}
          onReset={handleReset}
          hasMessages={messages.length > 0}
        />

        {/* Dev model switcher — hidden in production via NEXT_PUBLIC_DEV_MODE guard */}
        {process.env.NEXT_PUBLIC_DEV_MODE === "true" && providers.length > 0 && (
          <div className="border-b border-dashed border-amber-400/40 bg-amber-50/50 px-4 py-1.5 dark:bg-amber-950/20">
            <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
              <DevModelSwitcher
                providers={providers}
                selected={selectedProvider}
                onChange={setSelectedProvider}
                lastTtft={lastTtft}
              />
              <span className="text-[0.65rem] text-amber-700/70 dark:text-amber-400/50">
                Provider override requires{" "}
                <code className="rounded bg-amber-200/60 px-1 py-0.5 text-[0.6rem]">
                  ALLOW_PROVIDER_OVERRIDE=1
                </code>{" "}
                on the backend
              </span>
            </div>
          </div>
        )}

        <ChatMessages
          messages={messages}
          loading={loading}
          onPickQuestion={(q) => send(q)}
          onRate={handleRate}
        />

        <ChatInput onSendMessage={send} onStop={handleStop} disabled={loading} seed={seed} />
      </div>
    </div>
  )
}
