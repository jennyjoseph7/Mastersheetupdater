"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArrowDown } from "lucide-react"

interface FunnelStage {
  stage: string
  value: number
  percentage: string
  count: number
  dropoff?: number
}

const funnelData = {
  all: [
    { stage: "Sent/Called", value: 100, percentage: "100%", count: 30000 },
    { stage: "Delivered/Answered", value: 87, percentage: "87%", count: 26100, dropoff: 13 },
    { stage: "Read/Greeted", value: 62, percentage: "62%", count: 18600, dropoff: 25 },
    { stage: "Interacted", value: 34, percentage: "34%", count: 10200, dropoff: 28 },
    { stage: "Dropped-off", value: 24, percentage: "24%", count: 7200, dropoff: 10 },
    { stage: "Converted", value: 9, percentage: "9%", count: 2700, dropoff: 15 },
  ],
  whatsapp: [
    { stage: "Sent", value: 100, percentage: "100%", count: 12000 },
    { stage: "Delivered", value: 92, percentage: "92%", count: 11040, dropoff: 8 },
    { stage: "Read", value: 68, percentage: "68%", count: 8160, dropoff: 24 },
    { stage: "Interacted", value: 38, percentage: "38%", count: 4560, dropoff: 30 },
    { stage: "Dropped-off", value: 28, percentage: "28%", count: 3360, dropoff: 10 },
    { stage: "Converted", value: 11, percentage: "11%", count: 1320, dropoff: 17 },
  ],
  email: [
    { stage: "Sent", value: 100, percentage: "100%", count: 10000 },
    { stage: "Delivered", value: 95, percentage: "95%", count: 9500, dropoff: 5 },
    { stage: "Read", value: 45, percentage: "45%", count: 4500, dropoff: 50 },
    { stage: "Interacted", value: 22, percentage: "22%", count: 2200, dropoff: 23 },
    { stage: "Dropped-off", value: 15, percentage: "15%", count: 1500, dropoff: 7 },
    { stage: "Converted", value: 7, percentage: "7%", count: 700, dropoff: 8 },
  ],
  voice: [
    { stage: "Called", value: 100, percentage: "100%", count: 8000 },
    { stage: "Answered", value: 72, percentage: "72%", count: 5760, dropoff: 28 },
    { stage: "Greeted", value: 65, percentage: "65%", count: 5200, dropoff: 7 },
    { stage: "Interacted", value: 42, percentage: "42%", count: 3360, dropoff: 23 },
    { stage: "Dropped-off", value: 28, percentage: "28%", count: 2240, dropoff: 14 },
    { stage: "Converted", value: 8, percentage: "8%", count: 640, dropoff: 20 },
  ],
}

function FunnelStageCard({ stage, index, total }: { stage: FunnelStage; index: number; total: number }) {
  const widthPercentage = stage.value
  const calculatedWidth = 40 + (widthPercentage / 100) * 50 // reduced width range from 40-100 to 40-90

  return (
    <div className="relative">
      <div className="relative mx-auto" style={{ width: `${calculatedWidth}%` }}>
        <div className="bg-primary/90 rounded p-2 shadow-sm border border-primary/20">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-primary-foreground">{stage.stage}</h3>
            <span className="text-xs font-medium text-primary-foreground/80">{stage.count.toLocaleString()}</span>
          </div>
          <div className="text-lg font-bold text-primary-foreground">{stage.percentage}</div>
        </div>
      </div>

      {index < total - 1 && (
        <div className="flex justify-center">
          <ArrowDown className="h-4 w-4 text-muted-foreground/50" />
        </div>
      )}
    </div>
  )
}

export function EngagementFunnel() {
  const [activeTab, setActiveTab] = useState("all")

  const getCurrentData = () => {
    switch (activeTab) {
      case "whatsapp":
        return funnelData.whatsapp
      case "email":
        return funnelData.email
      case "voice":
        return funnelData.voice
      default:
        return funnelData.all
    }
  }

  const data = getCurrentData()

  return (
    <div className="w-full">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4 mb-3 bg-muted/50 p-1">
          <TabsTrigger value="all">All Channels</TabsTrigger>
          <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger>
          <TabsTrigger value="email">Email</TabsTrigger>
          <TabsTrigger value="voice">Voice</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-0">
          <div className="space-y-0 py-2">
            {data.map((stage, index) => (
              <FunnelStageCard key={`${activeTab}-${stage.stage}`} stage={stage} index={index} total={data.length} />
            ))}
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3">
            <div className="bg-card border rounded p-2">
              <p className="text-xs text-muted-foreground">Conversion Rate</p>
              <p className="text-lg font-bold text-emerald-600">{data[data.length - 1].percentage}</p>
            </div>
            <div className="bg-card border rounded p-2">
              <p className="text-xs text-muted-foreground">Total Reached</p>
              <p className="text-lg font-bold text-blue-600">{data[0].count.toLocaleString()}</p>
            </div>
            <div className="bg-card border rounded p-2">
              <p className="text-xs text-muted-foreground">Converted</p>
              <p className="text-lg font-bold text-purple-600">{data[data.length - 1].count.toLocaleString()}</p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
