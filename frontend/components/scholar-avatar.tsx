"use client"

import Image from "next/image"

/**
 * Assistant avatar using the project's avatar.png.
 * Shown at the left of every assistant message.
 * 40px on mobile, 50px on desktop (sm: breakpoint).
 */
export default function ScholarAvatar() {
  return (
    <span
      className="inline-grid shrink-0 place-items-center overflow-hidden rounded-full ring-1 ring-primary/25 h-10 w-10 sm:h-[50px] sm:w-[50px]"
      aria-hidden="true"
    >
      <Image
        src="/avatar.png"
        alt=""
        width={100}
        height={100}
        className="h-full w-full object-cover"
        priority
      />
    </span>
  )
}
