import type React from "react"

interface LiveStatusCardProps {
  title: string
  value: string
  description: string
  icon: React.ReactNode
  trend?: string
  trendDirection?: "up" | "down" | "neutral"
}

export function LiveStatusCard({
  title,
  value,
  description,
  icon,
  trend,
  trendDirection = "neutral",
}: LiveStatusCardProps) {
  return (
    <div className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-primary/5 via-primary/3 to-primary/5 p-6 shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">{icon}</div>
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="text-3xl font-bold text-primary">{value}</p>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        {trend && (
          <div className="flex items-center space-x-1">
            <div className="flex h-2 w-2 animate-pulse rounded-full bg-emerald-500"></div>
            <span className="text-xs font-medium text-emerald-600">Live</span>
          </div>
        )}
      </div>

      {/* Animated background elements */}
      <div className="absolute -right-4 -top-4 h-24 w-24 rounded-full bg-primary/5 blur-xl"></div>
      <div className="absolute -bottom-6 -left-6 h-32 w-32 rounded-full bg-primary/3 blur-2xl"></div>
    </div>
  )
}
