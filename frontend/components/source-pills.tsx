"use client"

interface SourcePillsProps {
  sources: string[]
}

export default function SourcePills({ sources }: SourcePillsProps) {
  return (
    <div className="flex flex-wrap gap-2 mt-3 ml-0">
      <span className="text-xs font-semibold text-foreground/60 uppercase tracking-wide">Sources:</span>
      {sources.map((source, index) => (
        <div
          key={index}
          className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/30 animate-fade-in hover:bg-primary/20 hover:border-primary/50 transition-all duration-300"
          style={{ animationDelay: `${index * 100}ms` }}
        >
          📄 {source.split("/").pop() || source}
        </div>
      ))}
    </div>
  )
}
