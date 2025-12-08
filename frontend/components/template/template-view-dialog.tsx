"use client"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Mail, MessageSquare, Calendar, FileText } from "lucide-react"
import type { Template } from "@/app/template/page"

interface TemplateViewDialogProps {
  template: Template
  isOpen: boolean
  onClose: () => void
}

export function TemplateViewDialog({ template, isOpen, onClose }: TemplateViewDialogProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date)
  }

  const getStatusBadge = (status: Template["status"]) => {
    switch (status) {
      case "Approved":
        return (
          <Badge className="bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400">
            Approved
          </Badge>
        )
      case "Pending":
        return (
          <Badge className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-400">
            Pending
          </Badge>
        )
      case "Rejected":
        return (
          <Badge className="bg-red-100 text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400">
            Rejected
          </Badge>
        )
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Template Details
          </DialogTitle>
          <DialogDescription>View template information and approval status</DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Template Info */}
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Template Name</p>
              <p className="text-lg font-semibold">{template.name}</p>
            </div>

            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Template ID</p>
              <p className="font-mono text-sm">{template.id}</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Channel</p>
                <div className="flex items-center gap-2">
                  {template.channel === "WhatsApp" ? (
                    <MessageSquare className="h-4 w-4 text-green-600" />
                  ) : (
                    <Mail className="h-4 w-4 text-blue-600" />
                  )}
                  <span>{template.channel}</span>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-muted-foreground mb-1">Status</p>
                {getStatusBadge(template.status)}
              </div>
            </div>

            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Campaign Name</p>
              <p>{template.campaignName}</p>
            </div>

            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Last Updated</p>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4" />
                {formatDate(template.lastUpdated)}
              </div>
            </div>
          </div>

          {/* Rejection Reason */}
          {template.status === "Rejected" && template.rejectionReason && (
            <>
              <Separator />
              <div className="rounded-lg bg-red-50 dark:bg-red-900/10 p-4 border border-red-200 dark:border-red-900/20">
                <p className="text-sm font-medium text-red-900 dark:text-red-400 mb-2">Rejection Reason</p>
                <p className="text-sm text-red-700 dark:text-red-300">{template.rejectionReason}</p>
              </div>
            </>
          )}

          {/* Template Preview Placeholder */}
          <Separator />
          <div>
            <p className="text-sm font-medium text-muted-foreground mb-3">Template Preview</p>
            <div className="rounded-lg border bg-muted/50 p-6 text-center">
              <p className="text-sm text-muted-foreground">Template preview will be displayed here</p>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
