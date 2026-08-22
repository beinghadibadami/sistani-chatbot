"use client"

interface GradientTextProps {
  children: string
  className?: string
}

export function GradientText({ children, className = "" }: GradientTextProps) {
  return (
    <span
      className={`bg-gradient-to-r from-emerald-400 via-green-400 to-emerald-600 bg-clip-text text-transparent ${className}`}
      style={{
        backgroundSize: "200% 200%",
        animation: "gradientShift 8s ease infinite",
      }}
    >
      {children}
    </span>
  )
}
