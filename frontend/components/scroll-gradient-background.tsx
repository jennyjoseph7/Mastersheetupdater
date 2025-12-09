"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"

export function ScrollGradientBackground() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const { resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    const handleScroll = () => {
      const windowHeight = window.innerHeight
      const documentHeight = document.documentElement.scrollHeight
      const scrollTop = window.scrollY
      const maxScroll = documentHeight - windowHeight

      const progress = maxScroll > 0 ? Math.min(scrollTop / maxScroll, 1) : 0
      setScrollProgress(progress)
    }

    window.addEventListener("scroll", handleScroll, { passive: true })
    handleScroll()

    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  const currentTheme = mounted ? resolvedTheme : "light"

  const overlayOpacity = 0.15 + scrollProgress * 0.7

  if (!mounted) return null

  return (
    <>
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          background:
            currentTheme === "dark"
              ? "radial-gradient(ellipse at top, hsl(var(--background)) 0%, hsl(237, 84%, 20%) 100%)"
              : "radial-gradient(ellipse at top, hsl(var(--background)) 0%, hsl(224, 71%, 85%) 100%)",
        }}
      />
      <div
        className="fixed inset-0 pointer-events-none transition-opacity duration-300 ease-out z-0"
        style={{
          background:
            currentTheme === "dark"
              ? "linear-gradient(to bottom, transparent 0%, rgba(15, 15, 35, 0.9) 100%)"
              : "linear-gradient(to bottom, transparent 0%, rgba(79, 70, 229, 0.15) 100%)",
          opacity: overlayOpacity,
        }}
      />
    </>
  )
}
