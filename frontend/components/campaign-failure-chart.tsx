"use client"

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

const failureData = [
  {
    channel: "WhatsApp",
    "Message not delivered": 450,
  },
  {
    channel: "Email",
    Spam: 380,
  },
  {
    channel: "Voice",
    "Not reachable": 290,
    "Didn't pick up": 180,
    Rejected: 240,
  },
]

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div
        className="bg-background border border-border rounded-md p-3 shadow-lg"
        style={{
          backgroundColor: "hsl(var(--background))",
          border: "1px solid hsl(var(--border))",
        }}
      >
        <p className="font-semibold mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: entry.color }} />
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-semibold">{entry.value}</span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export function CampaignFailureChart() {
  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={failureData}>
        <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
        <XAxis dataKey="channel" className="text-xs" tick={{ fontSize: 12 }} />
        <YAxis
          className="text-xs"
          tick={{ fontSize: 12 }}
          label={{
            value: "Number of Failures",
            angle: -90,
            position: "insideLeft",
            style: { fontSize: "12px", textAnchor: "middle" },
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ fontSize: "12px" }} iconType="rect" />
        <Bar dataKey="Message not delivered" stackId="a" fill="hsl(260, 98%, 31%)" radius={[0, 0, 0, 0]} />
        <Bar dataKey="Spam" stackId="a" fill="hsl(280, 85%, 45%)" radius={[0, 0, 0, 0]} />
        <Bar dataKey="Not reachable" stackId="a" fill="hsl(260, 75%, 50%)" radius={[0, 0, 0, 0]} />
        <Bar dataKey="Didn't pick up" stackId="a" fill="hsl(270, 70%, 60%)" radius={[0, 0, 0, 0]} />
        <Bar dataKey="Rejected" stackId="a" fill="hsl(280, 65%, 70%)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
