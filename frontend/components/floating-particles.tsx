"use client"

import { useEffect, useRef } from "react"

interface Particle {
  id: number
  x: number
  y: number
  size: number
  duration: number
  delay: number
}

export function FloatingParticles() {
  const containerRef = useRef<HTMLDivElement>(null)
  const particlesRef = useRef<Particle[]>([])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Generate particles
    for (let i = 0; i < 15; i++) {
      particlesRef.current.push({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 3 + 1,
        duration: Math.random() * 8 + 6,
        delay: Math.random() * 2,
      })
    }

    // Render particles
    particlesRef.current.forEach((particle) => {
      const particleEl = document.createElement("div")
      particleEl.className = "absolute rounded-full bg-gradient-to-r from-primary/40 to-secondary/40"
      particleEl.style.width = `${particle.size}px`
      particleEl.style.height = `${particle.size}px`
      particleEl.style.left = `${particle.x}%`
      particleEl.style.top = `${particle.y}%`
      particleEl.style.opacity = "0.3"
      particleEl.style.animation = `float ${particle.duration}s ease-in-out ${particle.delay}s infinite`
      particleEl.style.filter = "blur(0.5px)"
      container.appendChild(particleEl)
    })

    return () => {
      container.innerHTML = ""
    }
  }, [])

  return <div ref={containerRef} className="absolute inset-0 pointer-events-none overflow-hidden" />
}
