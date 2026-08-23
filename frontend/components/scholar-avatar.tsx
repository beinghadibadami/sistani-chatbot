"use client"

/**
 * Minimalist scholar turban silhouette — no face, no identifiable features.
 *
 * A faceless turban/amamah (عمامة) silhouette rendered as a clean SVG. Used as the
 * assistant message avatar. Deliberately abstract: communicates "Islamic scholar"
 * without depicting any specific person, which respects adab while giving the
 * assistant a distinct visual identity beyond a generic bot icon.
 *
 * Design notes:
 * - Emerald/gold palette matches the app theme
 * - Subtle gradient gives depth without looking cartoony
 * - Circle container with a soft border matches the message layout rhythm
 * - Small enough (32-36px) to sit beside messages without dominating
 */

export default function ScholarAvatar({ size = 32 }: { size?: number }) {
  return (
    <span
      className="inline-grid shrink-0 place-items-center rounded-full bg-primary/8 ring-1 ring-primary/20"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="h-[70%] w-[70%]"
      >
        {/* Turban/amamah — layered folds wrapping around the head silhouette */}
        <defs>
          <linearGradient id="turban-grad" x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.95" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.7" />
          </linearGradient>
          <linearGradient id="turban-band" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--gold, #b8860b)" stopOpacity="0.9" />
            <stop offset="50%" stopColor="var(--gold, #b8860b)" stopOpacity="1" />
            <stop offset="100%" stopColor="var(--gold, #b8860b)" stopOpacity="0.9" />
          </linearGradient>
        </defs>

        <g className="text-primary">
          {/* Head/shoulder silhouette — abstract, no facial features */}
          <ellipse cx="20" cy="34" rx="9" ry="5" fill="currentColor" opacity="0.25" />

          {/* Neck */}
          <rect x="17" y="28" width="6" height="5" rx="3" fill="currentColor" opacity="0.3" />

          {/* Main turban dome — wrapped layers */}
          <path
            d="M10 20 C10 12, 14 7, 20 7 C26 7, 30 12, 30 20 C30 24, 27 27, 20 27 C13 27, 10 24, 10 20Z"
            fill="url(#turban-grad)"
          />

          {/* Turban fold lines — gives the wrapped-cloth look */}
          <path
            d="M12 18 Q16 15 20 16 Q24 17 28 15"
            stroke="currentColor"
            strokeWidth="0.6"
            strokeOpacity="0.4"
            fill="none"
          />
          <path
            d="M11.5 21 Q15 19 20 19.5 Q25 20 28.5 18"
            stroke="currentColor"
            strokeWidth="0.5"
            strokeOpacity="0.3"
            fill="none"
          />
          <path
            d="M13 24 Q17 22.5 20 23 Q23 23.5 27 22"
            stroke="currentColor"
            strokeWidth="0.5"
            strokeOpacity="0.25"
            fill="none"
          />

          {/* Gold band across the turban — traditional amamah detail */}
          <path
            d="M11 19.5 Q15.5 17.5 20 18 Q24.5 18.5 29 17"
            stroke="url(#turban-band)"
            strokeWidth="1.2"
            strokeLinecap="round"
            fill="none"
          />

          {/* Turban tail hanging on the left side */}
          <path
            d="M12 21 C10 23, 9 26, 10 28"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeOpacity="0.5"
            fill="none"
          />

          {/* Top knot/peak */}
          <ellipse cx="20" cy="8.5" rx="4" ry="2.5" fill="currentColor" opacity="0.6" />
        </g>
      </svg>
    </span>
  )
}
