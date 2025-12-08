"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LineChart } from "@/components/charts/line-chart"
import { ResponsiveChartContainer } from "@/components/responsive-chart-container"

interface FilterableChartProps {
  title: string
  description: string
  weeklyData: Array<{ name: string; value: number }>
  monthlyData: Array<{ name: string; value: number }>
  yearlyData: Array<{ name: string; value: number }>
  yAxisLabel: string
}

export function FilterableChart({
  title,
  description,
  weeklyData,
  monthlyData,
  yearlyData,
  yAxisLabel,
}: FilterableChartProps) {
  const [timeFilter, setTimeFilter] = useState("monthly")

  const getDataForFilter = () => {
    switch (timeFilter) {
      case "weekly":
        return weeklyData
      case "yearly":
        return yearlyData
      default:
        return monthlyData
    }
  }

  const getXAxisLabel = () => {
    switch (timeFilter) {
      case "weekly":
        return "Week"
      case "yearly":
        return "Year"
      default:
        return "Month"
    }
  }

  return (
    <Card className="shadow">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <Select value={timeFilter} onValueChange={setTimeFilter}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="weekly">Weekly</SelectItem>
              <SelectItem value="monthly">Monthly</SelectItem>
              <SelectItem value="yearly">Yearly</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveChartContainer>
          <LineChart data={getDataForFilter()} xAxisLabel={getXAxisLabel()} yAxisLabel={yAxisLabel} />
        </ResponsiveChartContainer>
      </CardContent>
    </Card>
  )
}
