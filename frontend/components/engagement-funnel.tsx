"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface FunnelStage {
  stage: string;
  value: number;
  percentage: string;
  count: number;
  dropoff?: number;
}

const defaultFunnelData = {
  all: [
    { stage: "Sent/Called", value: 100, percentage: "100%", count: 30000 },
    {
      stage: "Delivered/Answered",
      value: 87,
      percentage: "87%",
      count: 26100,
      dropoff: 13,
    },
    {
      stage: "Read/Greeted",
      value: 62,
      percentage: "62%",
      count: 18600,
      dropoff: 25,
    },
    {
      stage: "Interacted",
      value: 34,
      percentage: "34%",
      count: 10200,
      dropoff: 28,
    },
    {
      stage: "Dropped-off",
      value: 24,
      percentage: "24%",
      count: 7200,
      dropoff: 10,
    },
    {
      stage: "Converted",
      value: 9,
      percentage: "9%",
      count: 2700,
      dropoff: 15,
    },
  ],
  whatsapp: [
    { stage: "Sent", value: 100, percentage: "100%", count: 12000 },
    {
      stage: "Delivered",
      value: 92,
      percentage: "92%",
      count: 11040,
      dropoff: 8,
    },
    { stage: "Read", value: 68, percentage: "68%", count: 8160, dropoff: 24 },
    {
      stage: "Interacted",
      value: 38,
      percentage: "38%",
      count: 4560,
      dropoff: 30,
    },
    {
      stage: "Dropped-off",
      value: 28,
      percentage: "28%",
      count: 3360,
      dropoff: 10,
    },
    {
      stage: "Converted",
      value: 11,
      percentage: "11%",
      count: 1320,
      dropoff: 17,
    },
  ],
  email: [
    { stage: "Sent", value: 100, percentage: "100%", count: 10000 },
    {
      stage: "Delivered",
      value: 95,
      percentage: "95%",
      count: 9500,
      dropoff: 5,
    },
    { stage: "Read", value: 45, percentage: "45%", count: 4500, dropoff: 50 },
    {
      stage: "Interacted",
      value: 22,
      percentage: "22%",
      count: 2200,
      dropoff: 23,
    },
    {
      stage: "Dropped-off",
      value: 15,
      percentage: "15%",
      count: 1500,
      dropoff: 7,
    },
    { stage: "Converted", value: 7, percentage: "7%", count: 700, dropoff: 8 },
  ],
  voice: [
    { stage: "Called", value: 100, percentage: "100%", count: 8000 },
    {
      stage: "Answered",
      value: 72,
      percentage: "72%",
      count: 5760,
      dropoff: 28,
    },
    { stage: "Greeted", value: 65, percentage: "65%", count: 5200, dropoff: 7 },
    {
      stage: "Interacted",
      value: 42,
      percentage: "42%",
      count: 3360,
      dropoff: 23,
    },
    {
      stage: "Dropped-off",
      value: 28,
      percentage: "28%",
      count: 2240,
      dropoff: 14,
    },
    { stage: "Converted", value: 8, percentage: "8%", count: 640, dropoff: 20 },
  ],
};

interface EngagementFunnelProps {
  customData?: {
    all?: FunnelStage[];
    whatsapp?: FunnelStage[];
    email?: FunnelStage[];
    voice?: FunnelStage[];
  };
  availableChannels?: string[]; // Array of channel keys that have data
}

function FunnelStageCard({
  stage,
  index,
  total,
  topWidth,
  bottomWidth,
  leftOffset,
}: {
  stage: FunnelStage;
  index: number;
  total: number;
  topWidth: number;
  bottomWidth: number;
  leftOffset: number;
}) {
  // Calculate gradient color - purple gradient that gets darker as we go down
  const hue = 260;
  const baseSaturation = 70;
  const baseLightness = 55;

  // Darker gradient as we go down the funnel
  const saturation = baseSaturation + index * 1.5;
  const lightnessStart = baseLightness - index * 2.5;
  const lightnessEnd = baseLightness - index * 3;

  const gradientStart = `hsl(${hue}, ${saturation}%, ${lightnessStart}%)`;
  const gradientEnd = `hsl(${hue}, ${saturation + 3}%, ${lightnessEnd}%)`;

  // Calculate taper percentage for clip-path
  // This creates the trapezoid shape where bottom is narrower than top
  // The bottom width should match the next stage's top width
  // Container width is topWidth%, and we want bottom edge to be bottomWidth%
  // So bottom edge should span (bottomWidth / topWidth * 100)% of the container
  const bottomEdgePercent = (bottomWidth / topWidth) * 100;
  const bottomLeftOffset = (100 - bottomEdgePercent) / 2;
  const bottomRightOffset = 100 - bottomLeftOffset;

  return (
    <div className="relative w-full flex items-center gap-4 mb-0 min-h-[60px]">
      {/* Funnel segment container - positioned with calculated left offset for seamless connection */}
      <div className="relative flex-1" style={{ position: "relative" }}>
        <div
          className="relative"
          style={{
            width: `${topWidth}%`,
            height: "60px",
            marginLeft: `${leftOffset}%`,
          }}
        >
          {/* Create trapezoid shape using CSS clip-path */}
          {/* Top edge spans full container width, bottom edge is narrower */}
          {/* The bottom edge width (bottomWidth) matches the next stage's top width */}
          <div
            className="relative h-full flex items-center justify-center px-4"
            style={{
              clipPath: `polygon(
                0% 0%,
                100% 0%,
                ${bottomRightOffset}% 100%,
                ${bottomLeftOffset}% 100%
              )`,
              background: `linear-gradient(to bottom, ${gradientStart}, ${gradientEnd})`,
            }}
          >
            <h3 className="text-sm font-semibold text-white text-center">
              {stage.stage}
            </h3>
          </div>
        </div>
      </div>

      {/* Percentage display on the right */}
      <div className="flex-shrink-0 w-20 text-right">
        <span className="text-sm font-semibold text-foreground whitespace-nowrap">
          {stage.percentage}
        </span>
      </div>
    </div>
  );
}

export function EngagementFunnel({
  customData,
  availableChannels,
}: EngagementFunnelProps = {}) {
  const funnelData = customData || defaultFunnelData;

  // Determine available channels from data if not provided
  const channels =
    availableChannels ||
    (() => {
      const channels: string[] = ["all"];
      if (funnelData.whatsapp && funnelData.whatsapp.length > 0)
        channels.push("whatsapp");
      if (funnelData.email && funnelData.email.length > 0)
        channels.push("email");
      if (funnelData.voice && funnelData.voice.length > 0)
        channels.push("voice");
      return channels;
    })();

  // Set initial active tab to first available channel
  const [activeTab, setActiveTab] = useState(channels[0] || "all");

  const getCurrentData = () => {
    switch (activeTab) {
      case "whatsapp":
        return funnelData.whatsapp || [];
      case "email":
        return funnelData.email || [];
      case "voice":
        return funnelData.voice || [];
      default:
        return funnelData.all || [];
    }
  };

  const data = getCurrentData();

  if (data.length === 0) {
    return (
      <div className="w-full text-center text-muted-foreground py-8">
        No engagement data available
      </div>
    );
  }

  const channelLabels: Record<string, string> = {
    all: "All Channels",
    whatsapp: "WhatsApp",
    email: "Email",
    voice: "Voice",
  };

  // Map channel count to grid classes
  const gridColsClass: Record<number, string> = {
    1: "grid-cols-1",
    2: "grid-cols-2",
    3: "grid-cols-3",
    4: "grid-cols-4",
  };

  const gridClass = gridColsClass[channels.length] || "grid-cols-4";

  return (
    <div className="w-full">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className={`grid w-full ${gridClass} mb-3 bg-muted/50 p-1`}>
          {channels.map((channel) => (
            <TabsTrigger key={channel} value={channel}>
              {channelLabels[channel] || channel}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={activeTab} className="mt-0">
          <div className="py-4 w-full max-w-5xl mx-auto relative">
            {(() => {
              // Pre-calculate all widths and offsets for seamless connection
              const maxWidth = 90;
              const minWidth = 20;

              // First pass: calculate bottom widths for all stages
              const stageData: Array<{
                stage: FunnelStage;
                bottomWidth: number;
                topWidth: number;
                index: number;
              }> = data.map((stage, index) => {
                const widthPercentage = stage.value;
                const bottomWidth =
                  minWidth + (widthPercentage / 100) * (maxWidth - minWidth);
                return { stage, bottomWidth, topWidth: 0, index };
              });

              // Second pass: calculate top widths - each stage's top width equals previous stage's bottom width
              stageData.forEach((item, index) => {
                if (index === 0) {
                  item.topWidth = maxWidth;
                } else {
                  // Top width of current stage = bottom width of previous stage
                  item.topWidth = stageData[index - 1].bottomWidth;
                }
              });

              // Calculate left offsets to ensure seamless connection
              // Each stage's bottom width equals the next stage's top width
              // We need to align the bottom edge of each stage with the top edge of the next
              const offsets: number[] = [];
              stageData.forEach((item, index) => {
                if (index === 0) {
                  // First stage: center it
                  offsets[index] = (100 - item.topWidth) / 2;
                } else {
                  // Calculate where previous stage's bottom edge starts
                  const prevItem = stageData[index - 1];
                  // Previous stage's bottom edge left position = container offset + half the width difference
                  const prevBottomLeft =
                    offsets[index - 1] +
                    (prevItem.topWidth - prevItem.bottomWidth) / 2;
                  // Current stage's top edge should start at the same position
                  // (since topWidth[i] = bottomWidth[i-1], they have the same width and align perfectly)
                  offsets[index] = prevBottomLeft;
                }
              });

              return stageData.map((item, index) => (
                <FunnelStageCard
                  key={`${activeTab}-${item.stage.stage}`}
                  stage={item.stage}
                  index={index}
                  total={data.length}
                  topWidth={item.topWidth}
                  bottomWidth={item.bottomWidth}
                  leftOffset={offsets[index]}
                />
              ));
            })()}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
