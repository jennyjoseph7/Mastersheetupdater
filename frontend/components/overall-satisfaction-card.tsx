"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface SatisfactionData {
  overallScore: number
  maxScore: number
  totalResponses: number
  satisfactionLevel: number
  satisfiedUsers: number
  ratingCategory: string
  positiveCount: number
  negativeCount: number
}

interface OverallSatisfactionCardProps {
  data: SatisfactionData
}

export function OverallSatisfactionCard({ data }: OverallSatisfactionCardProps) {
  const positiveRatio = (data.positiveCount / (data.positiveCount + data.negativeCount)) * 100

  return (
    <Card className="h-full shadow">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl font-semibold">Overall Satisfaction</CardTitle>
        <CardDescription className="text-muted-foreground">Comprehensive user satisfaction metrics</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Donut style progress indicator */}
        <div className="flex flex-col items-center space-y-4">
          <div className="relative w-32 h-32">
            <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
              {/* background */}
              <circle cx="60" cy="60" r="45" stroke="hsl(220,13%,91%)" strokeWidth="12" fill="none" />
              {/* positive arc */}
              <circle
                cx="60"
                cy="60"
                r="45"
                stroke="hsl(142,76%,36%)"
                strokeWidth="12"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 45}
                strokeDashoffset={2 * Math.PI * 45 * (1 - positiveRatio / 100)}
              />
            </svg>

            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-bold">{positiveRatio.toFixed(1)}%</span>
              <span className="text-xs text-muted-foreground">Positive feedback</span>
            </div>
          </div>
        </div>

        {/* Metrics grid */}
        <div className="space-y-4 pt-4 border-t">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Overall Score</span>
              <span className="font-semibold">
                {data.overallScore}/{data.maxScore}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Responses</span>
              <span className="font-semibold">{data.totalResponses.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Satisfaction Level</span>
              <span className="font-semibold">{data.satisfactionLevel}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Satisfied Users (4★+)</span>
              <span className="font-semibold">{data.satisfiedUsers}%</span>
            </div>
          </div>

          <div className="flex justify-between pt-2 text-sm">
            <span className="text-muted-foreground">Rating Category</span>
            <span className="font-semibold text-green-600">{data.ratingCategory}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
