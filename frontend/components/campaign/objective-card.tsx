"use client"

import type React from "react"

import { Card, CardContent } from "@/components/ui/card"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface ObjectiveCardProps {
  icon: React.ReactNode
  title: string
  selected: boolean
  onSelect: () => void
}

export function ObjectiveCard({ icon, title, selected, onSelect }: ObjectiveCardProps) {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-300 hover:shadow-lg hover:scale-[1.03] hover:border-primary/50",
        selected && "border-primary ring-2 ring-primary ring-offset-2 shadow-lg bg-primary/5",
      )}
      onClick={onSelect}
    >
      <CardContent className="flex flex-col items-center justify-center p-6 relative">
        {selected && (
          <div className="absolute top-2 right-2 flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md">
            <Check className="h-5 w-5" />
          </div>
        )}
        <div className={cn("mb-3 transition-colors", selected ? "text-primary" : "text-muted-foreground")}>{icon}</div>
        <h3 className={cn("font-semibold text-sm text-center transition-colors", selected && "text-primary")}>
          {title}
        </h3>
      </CardContent>
    </Card>
  )
}
