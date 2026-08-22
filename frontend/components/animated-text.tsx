"use client"

import { type ReactNode, useEffect, useState } from "react"

interface AnimatedTextProps {
  children: ReactNode
  className?: string
  delay?: number
  duration?: number
}

export function AnimatedText({ children, className = "", delay = 0, duration = 0.6 }: AnimatedTextProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true)
    }, delay)

    return () => clearTimeout(timer)
  }, [delay])

  return (
    <div
      className={`${className} transition-all ${isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"}`}
      style={{
        transitionDuration: `${duration}s`,
      }}
    >
      {children}
    </div>
  )
}
