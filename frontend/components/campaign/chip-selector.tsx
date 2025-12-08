"use client"

import { Badge } from "@/components/ui/badge"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"

interface ChipSelectorProps {
  options: string[]
  selected: string[]
  onToggle: (option: string) => void
}

export function ChipSelector({ options, selected, onToggle }: ChipSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => {
        const isSelected = selected.includes(option)
        return (
          <Badge
            key={option}
            variant={isSelected ? "default" : "outline"}
            className={cn(
              "cursor-pointer px-3 py-1.5 text-sm transition-all hover:shadow-sm",
              isSelected && "bg-primary hover:bg-primary/90",
            )}
            onClick={() => onToggle(option)}
          >
            {option}
            {isSelected && (
              <button
                className="ml-1.5 inline-flex items-center justify-center hover:bg-primary-foreground/20 rounded-full p-0.5"
                onClick={(e) => {
                  e.stopPropagation()
                  onToggle(option)
                }}
                aria-label="Remove"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </Badge>
        )
      })}
    </div>
  )
}
