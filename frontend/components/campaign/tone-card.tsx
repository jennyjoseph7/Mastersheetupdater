"use client"

import type React from "react"

import { Card, CardContent } from "@/components/ui/card"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface ToneCardProps {
  icon: React.ReactNode
  title: string
  selected: boolean
  onSelect: () => void
}

export function ToneCard({ icon, title, selected, onSelect }: ToneCardProps) {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md",
        selected && "border-primary ring-2 ring-primary ring-offset-2",
      )}
      onClick={onSelect}
    >
      <CardContent className="flex flex-col items-center justify-center p-6 relative">
        {selected && (
          <div className="absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <Check className="h-4 w-4" />
          </div>
        )}
        <div className="mb-3 text-primary">{icon}</div>
        <h3 className="font-medium text-sm text-center">{title}</h3>
      </CardContent>
    </Card>
  )
}
