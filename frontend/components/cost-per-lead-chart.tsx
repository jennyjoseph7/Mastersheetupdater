"use client"

import { useState } from "react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList } from "recharts"
import { TrendingDown, TrendingUp, DollarSign } from "lucide-react"
import { Badge } from "@/components/ui/badge"

const data = [
  { channel: "WhatsApp", cost: 12, leads: 450, totalSpend: 5400, trend: -8 },
  { channel: "Email", cost: 8, leads: 620, totalSpend: 4960, trend: -12 },
  { channel: "Voice", cost: 27, leads: 180, totalSpend: 4860, trend: 5 },
]

const COLORS = {
  WhatsApp: "hsl(142, 76%, 36%)",
  Email: "hsl(217, 91%, 60%)",
  Voice: "hsl(262, 83%, 58%)",
}

export function CostPerLeadChart() {
  const [hoveredBar, setHoveredBar] = useState<string | null>(null)

  const avgCost = data.reduce((sum, item) => sum + item.cost, 0) / data.length
  const bestChannel = data.reduce((min, item) => (item.cost < min.cost ? item : min))
  const totalLeads = data.reduce((sum, item) => sum + item.leads, 0)

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-muted/50 rounded-lg p-4 space-y-1">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <DollarSign className="h-4 w-4" />
            Average Cost
          </div>
          <div className="text-2xl font-bold">${avgCost.toFixed(2)}</div>
        </div>

        <div className="bg-muted/50 rounded-lg p-4 space-y-1">
          <div className="text-sm text-muted-foreground">Best Channel</div>
          <div className="text-2xl font-bold">{bestChannel.channel}</div>
          <div className="text-xs text-emerald-600 dark:text-emerald-400">${bestChannel.cost} per lead</div>
        </div>

        <div className="bg-muted/50 rounded-lg p-4 space-y-1">
          <div className="text-sm text-muted-foreground">Total Leads</div>
          <div className="text-2xl font-bold">{totalLeads.toLocaleString()}</div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" opacity={0.3} />
          <XAxis dataKey="channel" className="text-xs" tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }} />
          <YAxis
            className="text-xs"
            tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
            label={{
              value: "Cost ($)",
              angle: -90,
              position: "insideLeft",
              style: { fontSize: "12px", fill: "hsl(var(--foreground))" },
            }}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted))", opacity: 0.2 }}
            contentStyle={{
              backgroundColor: "hsl(var(--background))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "var(--radius)",
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            }}
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const data = payload[0].payload
                return (
                  <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
                    <p className="font-semibold text-sm mb-2">{data.channel}</p>
                    <div className="space-y-1 text-xs">
                      <div className="flex justify-between gap-4">
                        <span className="text-muted-foreground">Cost per Lead:</span>
                        <span className="font-bold">${data.cost}</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-muted-foreground">Total Leads:</span>
                        <span className="font-medium">{data.leads}</span>
                      </div>
                      <div className="flex justify-between gap-4">
                        <span className="text-muted-foreground">Total Spend:</span>
                        <span className="font-medium">${data.totalSpend.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between gap-4 items-center pt-1">
                        <span className="text-muted-foreground">Trend:</span>
                        <span
                          className={`font-medium flex items-center gap-1 ${data.trend < 0 ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}
                        >
                          {data.trend < 0 ? <TrendingDown className="h-3 w-3" /> : <TrendingUp className="h-3 w-3" />}
                          {Math.abs(data.trend)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )
              }
              return null
            }}
          />
          <Bar
            dataKey="cost"
            radius={[8, 8, 0, 0]}
            onMouseEnter={(data) => setHoveredBar(data.channel)}
            onMouseLeave={() => setHoveredBar(null)}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[entry.channel as keyof typeof COLORS]}
                opacity={hoveredBar === null || hoveredBar === entry.channel ? 1 : 0.4}
                style={{ transition: "opacity 0.2s ease" }}
              />
            ))}
            <LabelList
              dataKey="cost"
              position="top"
              formatter={(value: number) => `$${value}`}
              style={{ fill: "hsl(var(--foreground))", fontSize: "12px", fontWeight: "600" }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Channel Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {data.map((item) => (
          <div
            key={item.channel}
            className="border rounded-lg p-4 space-y-3 hover:border-foreground/20 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: COLORS[item.channel as keyof typeof COLORS] }}
                />
                <span className="font-semibold text-sm">{item.channel}</span>
              </div>
              <Badge variant={item.trend < 0 ? "default" : "secondary"} className="text-xs">
                {item.trend < 0 ? <TrendingDown className="h-3 w-3 mr-1" /> : <TrendingUp className="h-3 w-3 mr-1" />}
                {Math.abs(item.trend)}%
              </Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Cost per Lead</span>
                <span className="font-bold">${item.cost}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Leads</span>
                <span className="font-medium">{item.leads}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Total Spend</span>
                <span className="font-medium">${item.totalSpend.toLocaleString()}</span>
              </div>
            </div>

            <div className="pt-2 border-t">
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">vs Average</span>
                <span
                  className={
                    item.cost < avgCost
                      ? "text-emerald-600 dark:text-emerald-400 font-medium"
                      : "text-red-600 dark:text-red-400 font-medium"
                  }
                >
                  {item.cost < avgCost ? "-" : "+"}
                  {Math.abs(((item.cost - avgCost) / avgCost) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
