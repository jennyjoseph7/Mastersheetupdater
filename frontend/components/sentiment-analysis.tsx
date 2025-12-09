"use client"

import { useState } from "react"
import { Smile, Meh, Frown, TrendingUp, MessageSquare } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface SentimentData {
  positive: number
  neutral: number
  negative: number
  totalInteractions: number
}

const sentimentData: Record<string, SentimentData> = {
  all: { positive: 58, neutral: 32, negative: 10, totalInteractions: 18600 },
  whatsapp: { positive: 62, neutral: 28, negative: 10, totalInteractions: 8160 },
  email: { positive: 48, neutral: 40, negative: 12, totalInteractions: 4500 },
  voice: { positive: 65, neutral: 25, negative: 10, totalInteractions: 5200 },
}

export function SentimentAnalysis() {
  const [activeTab, setActiveTab] = useState("all")
  const data = sentimentData[activeTab]

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
          <div className="space-y-3">
            <Card className="p-3 bg-gradient-to-br from-emerald-50 to-emerald-100/50 dark:from-emerald-950/30 dark:to-emerald-900/20 border-emerald-200 dark:border-emerald-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
                    <Smile className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">Positive</p>
                    <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-400">{data.positive}%</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    {Math.round((data.positive / 100) * data.totalInteractions).toLocaleString()} interactions
                  </p>
                </div>
              </div>
              <div className="mt-2 bg-emerald-200/40 dark:bg-emerald-900/30 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-emerald-600 dark:bg-emerald-400 rounded-full transition-all"
                  style={{ width: `${data.positive}%` }}
                />
              </div>
            </Card>

            <Card className="p-3 bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-950/30 dark:to-gray-900/20 border-gray-200 dark:border-gray-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-gray-500/20 flex items-center justify-center">
                    <Meh className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">Neutral</p>
                    <p className="text-2xl font-bold text-gray-700 dark:text-gray-400">{data.neutral}%</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    {Math.round((data.neutral / 100) * data.totalInteractions).toLocaleString()} interactions
                  </p>
                </div>
              </div>
              <div className="mt-2 bg-gray-200/40 dark:bg-gray-900/30 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-gray-600 dark:bg-gray-400 rounded-full transition-all"
                  style={{ width: `${data.neutral}%` }}
                />
              </div>
            </Card>

            <Card className="p-3 bg-gradient-to-br from-red-50 to-red-100/50 dark:from-red-950/30 dark:to-red-900/20 border-red-200 dark:border-red-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-red-500/20 flex items-center justify-center">
                    <Frown className="h-5 w-5 text-red-600 dark:text-red-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium">Negative</p>
                    <p className="text-2xl font-bold text-red-700 dark:text-red-400">{data.negative}%</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    {Math.round((data.negative / 100) * data.totalInteractions).toLocaleString()} interactions
                  </p>
                </div>
              </div>
              <div className="mt-2 bg-red-200/40 dark:bg-red-900/30 rounded-full h-1.5 overflow-hidden">
                <div
                  className="h-full bg-red-600 dark:bg-red-400 rounded-full transition-all"
                  style={{ width: `${data.negative}%` }}
                />
              </div>
            </Card>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="bg-card border rounded p-2">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">Total Analyzed</p>
                </div>
                <p className="text-lg font-bold text-primary mt-1">{data.totalInteractions.toLocaleString()}</p>
              </div>
              <div className="bg-card border rounded p-2">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-600" />
                  <p className="text-xs text-muted-foreground">Satisfaction</p>
                </div>
                <p className="text-lg font-bold text-emerald-600 mt-1">{data.positive}%</p>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
