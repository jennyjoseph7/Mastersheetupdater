"use client"

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

const defaultFailureData = [
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

interface CampaignFailureChartProps {
  customData?: Array<Record<string, any>>;
}

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

export function CampaignFailureChart({ customData }: CampaignFailureChartProps = {}) {
  const failureData = customData || defaultFailureData;

  if (!failureData || failureData.length === 0) {
    return (
      <div className="w-full text-center text-muted-foreground py-8">
        No failure data available
      </div>
    );
  }

  // Extract all unique failure reason keys from the data
  const failureReasons = new Set<string>();
  failureData.forEach((item) => {
    Object.keys(item).forEach((key) => {
      if (key !== "channel") {
        failureReasons.add(key);
      }
    });
  });

  const failureReasonArray = Array.from(failureReasons);
  const colorMap: Record<string, string> = {
    "Message not delivered": "hsl(260, 98%, 31%)",
    "Spam": "hsl(280, 85%, 45%)",
    "Not reachable": "hsl(260, 75%, 50%)",
    "Didn't pick up": "hsl(270, 70%, 60%)",
    "Rejected": "hsl(280, 65%, 70%)",
  };

  // Generate colors for unknown failure reasons
  const getColor = (reason: string, index: number) => {
    return colorMap[reason] || `hsl(${260 + index * 20}, 70%, ${50 + index * 5}%)`;
  };

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
        {failureReasonArray.map((reason, index) => (
          <Bar
            key={reason}
            dataKey={reason}
            stackId="a"
            fill={getColor(reason, index)}
            radius={index === failureReasonArray.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
