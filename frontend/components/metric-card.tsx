import { ArrowDown, ArrowUp } from "lucide-react"

interface MetricCardProps {
  title: string
  value: string
  description: string
  trend?: string
  trendDirection?: "up" | "down" | "neutral"
}

export function MetricCard({ title, value, description, trend, trendDirection = "neutral" }: MetricCardProps) {
  return (
    <div className="rounded-lg border bg-card p-3 shadow-sm">
      <div className="flex justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        {trend && (
          <div className="flex items-center gap-1 text-xs">
            {trendDirection === "up" && <ArrowUp className="h-3 w-3 text-emerald-500" />}
            {trendDirection === "down" && <ArrowDown className="h-3 w-3 text-rose-500" />}
            <span
              className={
                trendDirection === "up"
                  ? "text-emerald-500"
                  : trendDirection === "down"
                    ? "text-rose-500"
                    : "text-muted-foreground"
              }
            >
              {trend}
            </span>
          </div>
        )}
      </div>
      <div className="mt-1">
        <p className="text-2xl font-bold text-primary">{value}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
