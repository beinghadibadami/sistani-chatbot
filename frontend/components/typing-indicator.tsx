"use client"

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 p-4 bg-white dark:bg-slate-900 border border-primary/30 rounded-2xl rounded-bl-none w-fit">
      <div className="flex gap-1">
        <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }}></div>
        <div className="w-2 h-2 rounded-full bg-secondary animate-bounce" style={{ animationDelay: "150ms" }}></div>
        <div className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: "300ms" }}></div>
      </div>
      <span className="text-sm text-foreground/60 ml-2 animate-pulse-gentle">Generating response...</span>
    </div>
  )
}
