"use client"

import { useState } from "react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

const data = [
  {
    channel: "WhatsApp",
    "Insurance Renewal": 150,
    "Policy Inquiry": 180,
    "Premium Payment": 120,
    total: 450,
  },
  {
    channel: "Email",
    "Insurance Renewal": 90,
    "Policy Inquiry": 130,
    "Premium Payment": 90,
    total: 310,
  },
  {
    channel: "Voice",
    "Insurance Renewal": 110,
    "Policy Inquiry": 90,
    "Premium Payment": 80,
    total: 280,
  },
]

const COLORS = {
  "Insurance Renewal": "hsl(142, 76%, 36%)", // Green
  "Policy Inquiry": "hsl(221, 83%, 53%)", // Blue
  "Premium Payment": "hsl(262, 83%, 58%)", // Purple
}

const INTENT_KEYS = ["Insurance Renewal", "Policy Inquiry", "Premium Payment"]

export function ConversationIntentChart() {
  const [selectedIntent, setSelectedIntent] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<"grouped" | "stacked">("grouped")

  const totals = data.reduce(
    (acc, item) => {
      acc.total += item.total
      INTENT_KEYS.forEach((key) => {
        acc[key] = (acc[key] || 0) + item[key as keyof typeof item]
      })
      return acc
    },
    { total: 0 } as Record<string, number>,
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex gap-3 flex-wrap">
          {INTENT_KEYS.map((intent) => {
            const count = totals[intent] || 0
            const percentage = ((count / totals.total) * 100).toFixed(1)
            return (
              <div
                key={intent}
                className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
                onClick={() => setSelectedIntent(selectedIntent === intent ? null : intent)}
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{
                    backgroundColor: COLORS[intent as keyof typeof COLORS],
                    opacity: selectedIntent && selectedIntent !== intent ? 0.3 : 1,
                  }}
                />
                <div className="flex flex-col">
                  <span className="text-xs font-medium">{intent}</span>
                  <span className="text-xs text-muted-foreground">
                    {count} ({percentage}%)
                  </span>
                </div>
              </div>
            )
          })}
        </div>

        <div className="flex gap-2">
          <Button
            variant={viewMode === "grouped" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("grouped")}
          >
            Grouped
          </Button>
          <Button
            variant={viewMode === "stacked" ? "default" : "outline"}
            size="sm"
            onClick={() => setViewMode("stacked")}
          >
            Stacked
          </Button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={data} barGap={8} barCategoryGap={viewMode === "grouped" ? "20%" : "10%"}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" opacity={0.3} />
          <XAxis
            dataKey="channel"
            className="text-xs"
            tick={{ fill: "hsl(var(--muted-foreground))" }}
            axisLine={{ stroke: "hsl(var(--border))" }}
          />
          <YAxis
            className="text-xs"
            tick={{ fill: "hsl(var(--muted-foreground))" }}
            axisLine={{ stroke: "hsl(var(--border))" }}
          />
          <Tooltip
            cursor={{ fill: "hsl(var(--muted))", opacity: 0.1 }}
            contentStyle={{
              backgroundColor: "hsl(var(--background))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "var(--radius)",
              boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
            }}
            labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
          />
          <Legend
            wrapperStyle={{ paddingTop: "20px" }}
            iconType="circle"
            onClick={(e) => {
              const intent = e.value
              setSelectedIntent(selectedIntent === intent ? null : intent)
            }}
          />
          {INTENT_KEYS.map((intent) => (
            <Bar
              key={intent}
              dataKey={intent}
              stackId={viewMode === "stacked" ? "a" : undefined}
              fill={COLORS[intent as keyof typeof COLORS]}
              radius={viewMode === "stacked" ? undefined : [4, 4, 0, 0]}
              opacity={selectedIntent && selectedIntent !== intent ? 0.2 : 1}
              animationDuration={800}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      <div className="grid grid-cols-3 gap-4">
        {data.map((channel) => (
          <div key={channel.channel} className="p-4 rounded-lg border bg-card">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-sm">{channel.channel}</h4>
              <Badge variant="secondary" className="text-xs">
                {channel.total}
              </Badge>
            </div>
            <div className="space-y-2">
              {INTENT_KEYS.map((intent) => {
                const value = channel[intent as keyof typeof channel] as number
                const percentage = ((value / channel.total) * 100).toFixed(0)
                return (
                  <div key={intent} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{intent}</span>
                    <span className="font-medium">{percentage}%</span>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
