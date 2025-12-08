"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Send } from "lucide-react"
import { cn } from "@/lib/utils"

interface TemplateCardProps {
  name: string
  preview: string
  tone: string
  variables: number
  selected: boolean
  approvalStatus: "none" | "pending" | "approved"
  onSelect: () => void
  onSubmitApproval: () => void
}

export function TemplateCard({
  name,
  preview,
  tone,
  variables,
  selected,
  approvalStatus,
  onSelect,
  onSubmitApproval,
}: TemplateCardProps) {
  const getApprovalBadge = () => {
    switch (approvalStatus) {
      case "pending":
        return (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-300">
            Pending
          </Badge>
        )
      case "approved":
        return <Badge className="bg-emerald-500 hover:bg-emerald-600">Approved</Badge>
      default:
        return null
    }
  }

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all hover:shadow-md min-w-[280px]",
        selected && "border-primary ring-2 ring-primary ring-offset-2",
      )}
      onClick={onSelect}
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h4 className="font-semibold text-sm mb-1">{name}</h4>
            <div className="text-xs text-muted-foreground max-h-[4.5rem] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
              {preview}
            </div>
          </div>
          {selected && (
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground ml-2">
              <Check className="h-3 w-3" />
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Badge variant="secondary" className="text-xs">
            {tone}
          </Badge>
          <span>{variables} variables</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          {approvalStatus !== "none" && getApprovalBadge()}
          {approvalStatus === "none" && (
            <Button
              size="sm"
              variant="outline"
              className="gap-1 text-xs h-7 bg-transparent w-full"
              onClick={(e) => {
                e.stopPropagation()
                onSubmitApproval()
              }}
            >
              <Send className="h-3 w-3" />
              Submit for Approval
            </Button>
          )}
          {approvalStatus === "pending" && (
            <Button size="sm" variant="outline" className="gap-1 text-xs h-7 bg-transparent" disabled>
              <Send className="h-3 w-3" />
              Submit for Approval
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
