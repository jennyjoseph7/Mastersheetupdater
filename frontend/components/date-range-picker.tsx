"use client"

import { useState } from "react"
import { Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"

interface DateRangePickerProps {
  onDateRangeChange?: (range: { from: Date; to: Date }) => void
}

export function DateRangePicker({ onDateRangeChange }: DateRangePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedRange, setSelectedRange] = useState("Week")
  const [dateRange, setDateRange] = useState({
    from: new Date(2025, 6, 21), // July 21, 2025 (Monday)
    to: new Date(2025, 6, 27), // July 27, 2025 (Sunday)
  })

  const presetRanges = ["Day", "Week", "Month", "Year", "Overall"]

  const formatDateRange = (from: Date, to: Date) => {
    const formatDate = (date: Date) => {
      return date.toLocaleDateString("en-US", {
        month: "2-digit",
        day: "2-digit",
        year: "numeric",
      })
    }
    return `${formatDate(from)} - ${formatDate(to)}`
  }

  const handlePresetClick = (preset: string) => {
    setSelectedRange(preset)
    const today = new Date()
    let from: Date, to: Date

    switch (preset) {
      case "Day":
        from = to = new Date(today)
        break
      case "Week":
        // Assuming week starts on Monday
        const firstDayOfWeek = new Date(today)
        firstDayOfWeek.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1)) // Adjust for Monday start
        from = firstDayOfWeek
        to = new Date(firstDayOfWeek)
        to.setDate(firstDayOfWeek.getDate() + 6)
        break
      case "Month":
        from = new Date(today.getFullYear(), today.getMonth(), 1)
        to = new Date(today.getFullYear(), today.getMonth() + 1, 0)
        break
      case "Year":
        from = new Date(today.getFullYear(), 0, 1)
        to = new Date(today.getFullYear(), 11, 31)
        break
      case "Overall":
        from = new Date(2020, 0, 1) // Arbitrary start date for "Overall"
        to = new Date(today)
        break
      default:
        from = new Date(2025, 6, 21) // Default to current week if something goes wrong
        to = new Date(2025, 6, 27)
    }

    setDateRange({ from, to })
    onDateRangeChange?.({ from, to })
    setIsOpen(false) // Close popover after selection
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn("w-[200px] justify-start text-left font-normal", !dateRange && "text-muted-foreground")}
        >
          <Calendar className="mr-2 h-4 w-4" />
          {selectedRange}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-40 p-0" align="end">
        {/* Preset sidebar */}
        <div className="w-full bg-muted/50">
          <div className="p-2 space-y-1">
            {presetRanges.map((preset) => (
              <Button
                key={preset}
                variant={selectedRange === preset ? "default" : "ghost"}
                className={cn(
                  "w-full justify-start text-sm font-normal",
                  selectedRange === preset && "bg-primary text-primary-foreground",
                )}
                onClick={() => handlePresetClick(preset)}
              >
                {preset}
              </Button>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
