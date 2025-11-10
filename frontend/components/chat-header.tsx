"use client"

export default function ChatHeader() {
  return (
    <header className="border-b border-border/30 bg-white/35 dark:bg-slate-50/50 backdrop-blur-sm sticky top-0 z-10">
      <div className="max-w-4xl mx-auto px-4 py-6 sm:px-6">
        <div className="flex items-center justify-center mb-4 animate-fade-in">
          {/* <div className="text-4xl mr-3"></div> */}
          <h1
            className="text-3xl sm:text-4xl font-bold bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent"
            style={{ backgroundSize: "200% 200%", animation: "gradientShift 8s ease infinite" }}
      
          >
            Sistani Jurisprudence
          </h1>
        </div>

        {/* Subtitle */}
        <p className="text-center text-foreground/70 text-sm sm:text-base leading-relaxed">
          Ask questions about Islamic jurisprudence based on the scholarly rulings of Ayatullah al-Sistani
        </p>
        <p className="mt-2 text-center text-xs sm:text-sm text-foreground/60">
          Disclaimer: Answers are AI-generated. While we strive for accuracy, errors may occur. Please always refer to
          listed sources, the official website of your Marja&apos;, or consult a scholar.
        </p>

        {/* Decorative geometric lines - subtle Islamic pattern */}
        <div className="mt-4 flex justify-center gap-2 opacity-30">
          <div className="w-1 h-6 bg-primary rounded-full"></div>
          <div className="w-1 h-8 bg-secondary rounded-full"></div>
          <div className="w-1 h-6 bg-accent rounded-full"></div>
          <div className="w-1 h-8 bg-primary rounded-full"></div>
          <div className="w-1 h-6 bg-secondary rounded-full"></div>
        </div>
      </div>
    </header>
  )
}
