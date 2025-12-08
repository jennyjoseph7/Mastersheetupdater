"use client"

import { Loader2 } from "lucide-react"

interface StepLoaderProps {
  message: string
  submessage?: string
}

export function StepLoader({ message, submessage }: StepLoaderProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="relative">
        <div className="absolute inset-0 rounded-full bg-primary/10 blur-md animate-pulse" />
        <Loader2 className="h-12 w-12 text-primary animate-spin relative" />
      </div>
      <p className="mt-6 text-lg font-semibold text-foreground">{message}</p>
      {submessage && <p className="mt-2 text-sm text-muted-foreground">{submessage}</p>}
    </div>
  )
}
