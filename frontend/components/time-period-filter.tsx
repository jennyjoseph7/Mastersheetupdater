"use client"

import { useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface TimePeriodFilterProps {
  onPeriodChange?: (period: string) => void
  defaultValue?: string
}

export function TimePeriodFilter({ onPeriodChange, defaultValue = "this-week" }: TimePeriodFilterProps) {
  const [selectedPeriod, setSelectedPeriod] = useState(defaultValue)

  const handlePeriodChange = (period: string) => {
    setSelectedPeriod(period)
    onPeriodChange?.(period)
  }

  return (
    <Select value={selectedPeriod} onValueChange={handlePeriodChange}>
      <SelectTrigger className="w-[180px]">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="today">Today</SelectItem>
        <SelectItem value="this-week">This Week</SelectItem>
        <SelectItem value="this-month">This Month</SelectItem>
        <SelectItem value="this-year">This Year</SelectItem>
      </SelectContent>
    </Select>
  )
}
