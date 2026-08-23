"use client"

import Image from "next/image"

/**
 * Assistant avatar using the project's avatar.png.
 * Shown at the left of every assistant message.
 */
export default function ScholarAvatar({ size = 34 }: { size?: number }) {
  return (
    <span
      className="inline-grid shrink-0 place-items-center overflow-hidden rounded-full bg-primary/8 ring-1 ring-primary/20"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <Image
        src="/avatar.png"
        alt=""
        width={size}
        height={size}
        className="h-full w-full object-cover"
        priority
      />
    </span>
  )
}
