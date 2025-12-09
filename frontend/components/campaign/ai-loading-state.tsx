"use client"

import { Sparkles, Wand2 } from "lucide-react"
import { Card } from "@/components/ui/card"

interface AILoadingStateProps {
  message?: string
}

export function AILoadingState({ message = "AI is generating your content..." }: AILoadingStateProps) {
  return (
    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
      <div className="flex items-center gap-4 p-6">
        <div className="relative">
          <div className="absolute inset-0 animate-ping rounded-full bg-primary/20" />
          <div className="relative flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Wand2 className="h-6 w-6 text-primary animate-pulse" />
          </div>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="h-4 w-4 text-primary animate-pulse" />
            <h4 className="font-semibold text-sm">AI Generation in Progress</h4>
          </div>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
      </div>
    </Card>
  )
}
