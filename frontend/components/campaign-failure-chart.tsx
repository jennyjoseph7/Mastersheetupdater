"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const CHANNEL_COLORS: Record<string, string> = {
  whatsapp_chat: "#25D366",
  whatsapp: "#25D366",
  WhatsApp: "#25D366",
  email: "#EA4335",
  Email: "#EA4335",
  voice: "#4285F4",
  Voice: "#4285F4",
  sms: "#FACC15",
  SMS: "#FACC15",
  default: "#6366f1",
};

// Default data for demonstration/fallback
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
];

interface CampaignFailureChartProps {
  customData?: Array<Record<string, any>>;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-popover text-popover-foreground border rounded-md p-3 shadow-lg outline-none">
        <p className="font-semibold mb-2">{label}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-muted-foreground">{entry.name}:</span>
            <span className="font-semibold">{entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export function CampaignFailureChart({
  customData,
}: CampaignFailureChartProps = {}) {
  // --- Data Transformation Logic ---
  const { chartData, failureReasons } = useMemo(() => {
    // 1. Determine which data to use
    const rawData =
      customData && customData.length > 0 ? customData : defaultFailureData;

    // 2. Check if data is in API "Long" format (contains 'message' and 'count' keys)
    //    Example: [{ channel: 'wa', message: 'Error', count: 5 }]
    const isApiFormat = rawData.some(
      (item) => "message" in item && "count" in item
    );

    let processedData = rawData;

    if (isApiFormat) {
      // Pivot the data: Group by channel, use messages as keys
      const grouped: Record<string, any> = {};

      rawData.forEach((item) => {
        // Use channelName if available (for better display), else channel
        const channelKey = item.channelName || item.channel;

        if (!grouped[channelKey]) {
          grouped[channelKey] = { channel: channelKey };
        }
        // Assign the count to the specific error message key
        // Example: { channel: 'WhatsApp', 'Message not delivered': 6 }
        grouped[channelKey][item.message] = item.count;
      });

      processedData = Object.values(grouped);
    }

    // 3. Extract all unique failure reason keys for the Bar stacks
    const reasons = new Set<string>();
    processedData.forEach((item) => {
      Object.keys(item).forEach((key) => {
        // Exclude internal keys
        if (
          key !== "channel" &&
          key !== "channelName" &&
          key !== "fill" &&
          key !== "id"
        ) {
          reasons.add(key);
        }
      });
    });

    return {
      chartData: processedData,
      failureReasons: Array.from(reasons),
    };
  }, [customData]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="w-full text-center text-muted-foreground py-8">
        No failure data available
      </div>
    );
  }

  // Define colors for known error types
  const colorMap: Record<string, string> = {
    "Message not delivered": "hsl(260, 98%, 31%)", // Deep Purple
    Spam: "hsl(280, 85%, 45%)", // Purple
    "Not reachable": "hsl(260, 75%, 50%)", // Light Purple
    "Didn't pick up": "hsl(270, 70%, 60%)", // Lighter Purple
    Rejected: "hsl(280, 65%, 70%)", // Lavender
  };

  // Generate consistent colors for unknown failure reasons
  const getColor = (reason: string, index: number) => {
    if (colorMap[reason]) return colorMap[reason];
    // Fallback: Generate a distinct color based on index
    // Using a spectrum from blue to red
    return `hsl(${220 + (index * 40) % 100}, 70%, 50%)`;
  };

  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={300}>
      <BarChart
        data={chartData}
        margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
      >
        <CartesianGrid
          strokeDasharray="3 3"
          vertical={false}
          stroke="hsl(var(--muted))"
          opacity={0.3}
        />
        <XAxis
          dataKey="channel"
          tickLine={false}
          axisLine={false}
          tick={(props) => {
            const { x, y, payload } = props;
            const channelName = payload.value || "";
            // Try to match color loosely (e.g. 'whatsapp' or 'whatsapp_chat')
            const channelKey = Object.keys(CHANNEL_COLORS).find((k) =>
              channelName.toLowerCase().includes(k.replace("_chat", ""))
            );
            const fillColor =
              CHANNEL_COLORS[channelName] ||
              CHANNEL_COLORS[channelKey || "default"] ||
              CHANNEL_COLORS.default;

            return (
              <g transform={`translate(${x},${y})`}>
                <text
                  x={0}
                  y={0}
                  dy={16}
                  textAnchor="middle"
                  fill={fillColor}
                  fontSize={12}
                  fontWeight={600}
                >
                  {channelName}
                </text>
              </g>
            );
          }}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          fontSize={12}
          stroke="hsl(var(--muted-foreground))"
          allowDecimals={false}
        />
        <Tooltip cursor={{ fill: "transparent" }} content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ paddingTop: "20px" }}
          iconType="circle"
          formatter={(value) => (
            <span className="text-xs text-muted-foreground font-medium">
              {value}
            </span>
          )}
        />
        {failureReasons.map((reason, index) => (
          <Bar
            key={reason}
            dataKey={reason}
            name={reason}
            stackId="a"
            fill={getColor(reason, index)}
            radius={[4, 4, 0, 0]} // Radius only applies to top-most bar in stack visually
            maxBarSize={50}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}