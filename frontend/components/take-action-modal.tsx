"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { UnansweredQuery } from "./unanswered-query-list"

interface TakeActionModalProps {
  query: UnansweredQuery | null
  isOpen: boolean
  onClose: () => void
  onAction: (queryId: string, actionType: "resolved" | "escalated", notes: string) => void
}

export function TakeActionModal({ query, isOpen, onClose, onAction }: TakeActionModalProps) {
  const [actionType, setActionType] = useState<"resolved" | "escalated">("resolved")
  const [notes, setNotes] = useState("")

  if (!query) return null

  const handleSubmit = () => {
    onAction(query.id, actionType, notes)
    setNotes("") // Clear notes after submission
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Take Action on Query</DialogTitle>
          <DialogDescription>Review the query and decide on the appropriate action.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <span className="text-sm font-medium col-span-1">Query:</span>
            <p className="col-span-3 text-sm text-muted-foreground">{query.queryText}</p>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <span className="text-sm font-medium col-span-1">Session ID:</span>
            <p className="col-span-3 text-sm text-muted-foreground">{query.sessionId}</p>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <span className="text-sm font-medium col-span-1">Timestamp:</span>
            <p className="col-span-3 text-sm text-muted-foreground">{new Date(query.timestamp).toLocaleString()}</p>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <span className="text-sm font-medium col-span-1">Action:</span>
            <Select
              value={actionType}
              onValueChange={(value: "resolved" | "escalated") => setActionType(value)}
              className="col-span-3"
            >
              <SelectTrigger>
                <SelectValue placeholder="Select action" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="resolved">Mark as Resolved</SelectItem>
                <SelectItem value="escalated">Escalate to Human</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-4 items-start gap-4">
            <span className="text-sm font-medium col-span-1 pt-2">Notes:</span>
            <Textarea
              placeholder="Add any relevant notes here..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="col-span-3"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>Submit Action</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
