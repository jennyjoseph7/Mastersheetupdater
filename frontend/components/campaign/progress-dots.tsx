"use client"

import { cn } from "@/lib/utils"

interface ProgressDotsProps {
  total: number
  current: number
  className?: string
}

export function ProgressDots({ total, current, className }: ProgressDotsProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      {Array.from({ length: total }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "h-2 rounded-full transition-all duration-300",
            index === current - 1 ? "w-8 bg-primary" : "w-2 bg-muted",
          )}
        />
      ))}
    </div>
  )
}
