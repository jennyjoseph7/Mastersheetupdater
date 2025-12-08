"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Users, TrendingUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface AudienceCardProps {
  id: string
  name: string
  description: string
  memberCount: number
  icon: string
  gradient: string
  isSelected: boolean
  onClick: () => void
}

export function AudienceCard({
  name,
  description,
  memberCount,
  icon,
  gradient,
  isSelected,
  onClick,
}: AudienceCardProps) {
  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-105",
        isSelected && "ring-2 ring-primary shadow-xl scale-105",
      )}
      onClick={onClick}
    >
      <CardContent className="p-6">
        <div className={cn("w-12 h-12 rounded-lg mb-4 flex items-center justify-center", gradient)}>
          <span className="text-2xl">{icon}</span>
        </div>
        <h3 className="text-lg font-semibold mb-2">{name}</h3>
        <p className="text-sm text-muted-foreground mb-4">{description}</p>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">{memberCount.toLocaleString()}</span>
            <span className="text-muted-foreground">members</span>
          </div>
          {isSelected && (
            <div className="flex items-center gap-1 text-xs text-primary font-medium">
              <TrendingUp className="h-3 w-3" />
              Active
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
