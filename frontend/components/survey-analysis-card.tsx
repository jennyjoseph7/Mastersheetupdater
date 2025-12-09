"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface SurveyMetric {
  id: string
  name: string
  score: number
  maxScore: number
  description: string
}

interface SurveyAnalysisCardProps {
  metrics: SurveyMetric[]
}

export function SurveyAnalysisCard({ metrics }: SurveyAnalysisCardProps) {
  const [selectedMetric, setSelectedMetric] = useState(metrics[0]?.id || "")

  const currentMetric = metrics.find((m) => m.id === selectedMetric) || metrics[0]
  const percentage = (currentMetric.score / currentMetric.maxScore) * 100

  return (
    <Card className="h-full shadow">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl font-semibold">Survey Response Analysis</CardTitle>
        <CardDescription className="text-muted-foreground">Insights from post-session user surveys</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Circular progress */}
        <div className="flex flex-col items-center space-y-4">
          <div className="relative w-32 h-32">
            <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 120 120">
              {/* Background circle */}
              <circle cx="60" cy="60" r="50" stroke="hsl(220, 13%, 91%)" strokeWidth="8" fill="none" />
              {/* Progress circle */}
              <circle
                cx="60"
                cy="60"
                r="50"
                stroke="hsl(260, 98%, 31%)"
                strokeWidth="8"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={`${2 * Math.PI * 50}`}
                strokeDashoffset={`${2 * Math.PI * 50 * (1 - percentage / 100)}`}
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold">{currentMetric.score}</span>
              <span className="text-sm text-muted-foreground">of {currentMetric.maxScore}</span>
            </div>
          </div>
          <span className="text-sm text-muted-foreground">Selected Metric</span>
        </div>

        {/* Metric selector */}
        <div className="space-y-4">
          <Select value={selectedMetric} onValueChange={setSelectedMetric}>
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {metrics.map((metric) => (
                <SelectItem key={metric.id} value={metric.id}>
                  {metric.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Metric details */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-medium">{currentMetric.name}</span>
              <span className="text-sm text-muted-foreground">{currentMetric.description}</span>
            </div>

            <div className="flex justify-between items-center text-sm">
              <span>
                {currentMetric.score} / {currentMetric.maxScore}
              </span>
              <span className="text-muted-foreground">{percentage.toFixed(1)}%</span>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-1000 ease-out"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
