"use client"

/**
 * Static SVG backdrop: an eight-point girih star tessellation, the motif that recurs across
 * Islamic architectural ornament.
 *
 * This replaces the previous WebGL aurora deliberately. That effect was both generic and
 * costly (a continuously animating fragment shader), whereas this is a single tiled SVG
 * pattern - no canvas, no render loop, and it stays sharp at any zoom. Two very slow drifting
 * radial washes supply depth without demanding attention.
 */
export default function GeometricBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* Base wash */}
      <div className="absolute inset-0 bg-background" />

      {/* Girih tiling */}
      <svg className="absolute inset-0 h-full w-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="girih" width="120" height="120" patternUnits="userSpaceOnUse">
            <g
              fill="none"
              stroke="currentColor"
              strokeWidth="0.9"
              className="text-primary"
              opacity="0.13"
            >
              {/* Eight-point star: two overlaid squares, one rotated 45deg. */}
              <rect x="30" y="30" width="60" height="60" />
              <rect x="30" y="30" width="60" height="60" transform="rotate(45 60 60)" />
              {/* Interlacing lines to the tile edges */}
              <path d="M60 0 L60 30 M60 90 L60 120 M0 60 L30 60 M90 60 L120 60" />
              {/* Corner quarter-stars complete the tessellation across tile seams. */}
              <path d="M0 0 L18 0 L0 18 Z M120 0 L102 0 L120 18 Z M0 120 L18 120 L0 102 Z M120 120 L102 120 L120 102 Z" />
              <circle cx="60" cy="60" r="9" />
            </g>
          </pattern>

          <radialGradient id="wash-emerald" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.20" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="wash-gold" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.14" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
          </radialGradient>
        </defs>

        <rect width="100%" height="100%" fill="url(#girih)" />

        {/* Slow washes: motion is barely perceptible by design. */}
        <g className="animate-drift text-primary">
          <ellipse cx="18%" cy="12%" rx="46%" ry="34%" fill="url(#wash-emerald)" />
        </g>
        <g className="animate-drift text-gold" style={{ animationDelay: "-11s" }}>
          <ellipse cx="84%" cy="82%" rx="42%" ry="32%" fill="url(#wash-gold)" />
        </g>
      </svg>

      {/* Vignette keeps the pattern from competing with the text column. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 50% 40%, transparent 30%, color-mix(in oklch, var(--background) 82%, transparent) 78%)",
        }}
      />
    </div>
  )
}
