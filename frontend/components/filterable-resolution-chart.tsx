"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { LineChart } from "@/components/charts/line-chart"
import { ResponsiveChartContainer } from "@/components/responsive-chart-container"

interface FilterableResolutionChartProps {
  title: string
  description: string
}

export function FilterableResolutionChart({ title, description }: FilterableResolutionChartProps) {
  const [timeFilter, setTimeFilter] = useState("this-week")

  const getDataForFilter = () => {
    switch (timeFilter) {
      case "today":
        return [
          { name: "9 AM", value: 78 },
          { name: "12 PM", value: 82 },
          { name: "3 PM", value: 85 },
          { name: "6 PM", value: 80 },
        ]
      case "this-week":
        return [
          { name: "Mon", value: 75 },
          { name: "Tue", value: 78 },
          { name: "Wed", value: 82 },
          { name: "Thu", value: 85 },
          { name: "Fri", value: 84 },
          { name: "Sat", value: 80 },
          { name: "Sun", value: 83 },
        ]
      case "this-month":
        return [
          { name: "Week 1", value: 65 },
          { name: "Week 2", value: 68 },
          { name: "Week 3", value: 72 },
          { name: "Week 4", value: 78 },
        ]
      case "this-year":
        return [
          { name: "Jan", value: 65 },
          { name: "Feb", value: 68 },
          { name: "Mar", value: 72 },
          { name: "Apr", value: 78 },
          { name: "May", value: 84 },
          { name: "Jun", value: 82 },
          { name: "Jul", value: 85 },
          { name: "Aug", value: 87 },
          { name: "Sep", value: 89 },
          { name: "Oct", value: 86 },
          { name: "Nov", value: 88 },
          { name: "Dec", value: 90 },
        ]
      default:
        return [
          { name: "Mon", value: 75 },
          { name: "Tue", value: 78 },
          { name: "Wed", value: 82 },
          { name: "Thu", value: 85 },
          { name: "Fri", value: 84 },
          { name: "Sat", value: 80 },
          { name: "Sun", value: 83 },
        ]
    }
  }

  const getXAxisLabel = () => {
    switch (timeFilter) {
      case "today":
        return "Hour"
      case "this-week":
        return "Day"
      case "this-month":
        return "Week"
      case "this-year":
        return "Month"
      default:
        return "Day"
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
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="this-week">This Week</SelectItem>
              <SelectItem value="this-month">This Month</SelectItem>
              <SelectItem value="this-year">This Year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveChartContainer>
          <LineChart data={getDataForFilter()} xAxisLabel={getXAxisLabel()} yAxisLabel="Resolution Rate (%)" />
        </ResponsiveChartContainer>
      </CardContent>
    </Card>
  )
}
