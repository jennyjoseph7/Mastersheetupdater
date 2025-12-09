"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface UpdatedOverallSatisfactionCardProps {
  totalResponses: number
  responseRating: number
  maxRating: number
  positiveCount: number
  negativeCount: number
}

export function UpdatedOverallSatisfactionCard({
  totalResponses,
  responseRating,
  maxRating,
  positiveCount,
  negativeCount,
}: UpdatedOverallSatisfactionCardProps) {
  const ratingPercentage = (responseRating / maxRating) * 100

  return (
    <Card className="h-full shadow">
      <CardHeader className="pb-4">
        <CardTitle className="text-xl font-semibold">Overall Satisfaction</CardTitle>
        <CardDescription className="text-muted-foreground">User satisfaction metrics and ratings</CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Circular progress - matching Overall Score design */}
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
                strokeDashoffset={`${2 * Math.PI * 50 * (1 - ratingPercentage / 100)}`}
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold">{responseRating}</span>
              <span className="text-sm text-muted-foreground">of {maxRating}</span>
            </div>
          </div>
          <span className="text-sm text-muted-foreground">Overall Satisfaction Rating</span>
        </div>

        {/* Details section - matching Overall Score design */}
        <div className="space-y-3 pt-4 border-t">
          <div className="flex justify-between items-center">
            <span className="font-medium">Total Responses</span>
            <span className="text-sm text-muted-foreground">{totalResponses.toLocaleString()}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="font-medium">Response Rating</span>
            <span className="text-sm text-muted-foreground">
              {responseRating} / {maxRating}
            </span>
          </div>

          <div className="flex justify-between items-center text-sm">
            <span>Rating Percentage</span>
            <span className="text-muted-foreground">{ratingPercentage.toFixed(1)}%</span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${ratingPercentage}%` }}
            />
          </div>

          {/* Additional metrics */}
          <div className="grid grid-cols-2 gap-4 pt-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Positive</span>
              <span className="font-semibold text-green-600">{positiveCount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Negative</span>
              <span className="font-semibold text-red-600">{negativeCount}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
