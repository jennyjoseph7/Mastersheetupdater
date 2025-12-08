"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface SurveyResponseData {
  question: string
  responses: {
    option: string
    count: number
    percentage: number
    color: string
  }[]
}

interface SurveyResponseChartProps {
  data: SurveyResponseData[]
}

export function SurveyResponseChart({ data }: SurveyResponseChartProps) {
  return (
    <div className="space-y-6">
      {data.map((survey, index) => (
        <Card key={index}>
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">{survey.question}</CardTitle>
            <CardDescription>Survey responses breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {survey.responses.map((response, responseIndex) => (
                <div key={responseIndex} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">{response.option}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">{response.count} responses</span>
                      <span className="text-sm font-semibold">{response.percentage}%</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full transition-all duration-500 ease-out"
                      style={{
                        width: `${response.percentage}%`,
                        backgroundColor: response.color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground">
                Total responses: {survey.responses.reduce((sum, r) => sum + r.count, 0)}
              </p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
