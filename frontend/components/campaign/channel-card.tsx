"use client"

import type React from "react"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface ChannelCardProps {
  icon: React.ReactNode
  name: string
  status: "not-connected" | "connected" | "creative-only"
  selected: boolean
  onSelect: () => void
}

export function ChannelCard({ icon, name, status, selected, onSelect }: ChannelCardProps) {
  const getStatusBadge = () => {
    switch (status) {
      case "not-connected":
        return (
          <Badge variant="destructive" className="text-xs">
            Not Connected
          </Badge>
        )
      case "connected":
        return <Badge className="bg-emerald-500 hover:bg-emerald-600 text-xs">Connected</Badge>
      case "creative-only":
        return (
          <Badge variant="outline" className="text-xs">
            Creative Only
          </Badge>
        )
    }
  }

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
        <div
          className={cn(
            "mb-3 p-3 rounded-full transition-colors",
            selected ? "bg-primary/10 text-primary" : "bg-muted/50 text-muted-foreground",
          )}
        >
          {icon}
        </div>
        <h3 className={cn("font-semibold text-sm mb-2 transition-colors", selected && "text-primary")}>{name}</h3>
        {getStatusBadge()}
      </CardContent>
    </Card>
  )
}
