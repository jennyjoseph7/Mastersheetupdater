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
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { UnansweredQuery } from "./unanswered-query-list"

interface EnhancedTakeActionModalProps {
  query: UnansweredQuery | null
  isOpen: boolean
  onClose: () => void
  onAction: (queryId: string, actionType: string, actionData: any) => void
}

export function EnhancedTakeActionModal({ query, isOpen, onClose, onAction }: EnhancedTakeActionModalProps) {
  const [selectedState, setSelectedState] = useState<string>("")
  const [notes, setNotes] = useState("")
  const [correctAnswer, setCorrectAnswer] = useState("")
  const [faqQuestion, setFaqQuestion] = useState("")
  const [faqAnswer, setFaqAnswer] = useState("")
  const [faqCategory, setFaqCategory] = useState("")
  const [incorrectAnswerAction, setIncorrectAnswerAction] = useState("")

  if (!query) return null

  const handleSubmit = () => {
    let actionData: any = { notes }

    switch (selectedState) {
      case "garbage":
        actionData = { ...actionData, reason: "Query marked as garbage/spam" }
        break
      case "incorrect-answer":
        if (incorrectAnswerAction === "correct-answer") {
          actionData = { ...actionData, correctAnswer, action: "provide-correct-answer" }
        } else if (incorrectAnswerAction === "escalate") {
          actionData = { ...actionData, action: "escalate-ticket" }
        }
        break
      case "faq-added":
        actionData = {
          ...actionData,
          faq: {
            question: faqQuestion,
            answer: faqAnswer,
            category: faqCategory,
          },
        }
        break
      case "not-supported":
        actionData = { ...actionData, reason: "Feature/query currently not supported" }
        break
    }

    onAction(query.id, selectedState, actionData)
    resetForm()
    onClose()
  }

  const resetForm = () => {
    setSelectedState("")
    setNotes("")
    setCorrectAnswer("")
    setFaqQuestion("")
    setFaqAnswer("")
    setFaqCategory("")
    setIncorrectAnswerAction("")
  }

  const isFormValid = () => {
    if (!selectedState) return false

    switch (selectedState) {
      case "incorrect-answer":
        if (!incorrectAnswerAction) return false
        if (incorrectAnswerAction === "correct-answer" && !correctAnswer.trim()) return false
        break
      case "faq-added":
        if (!faqQuestion.trim() || !faqAnswer.trim() || !faqCategory) return false
        break
    }

    return true
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Take Action on Query</DialogTitle>
          <DialogDescription>Review the query and select the appropriate action.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Query Information */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Query</Label>
            <div className="p-3 bg-muted rounded-md">
              <p className="text-sm">{query.queryText}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <Label className="text-muted-foreground">Session ID</Label>
              <p className="font-medium">{query.sessionId}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Timestamp</Label>
              <p className="font-medium">{new Date(query.timestamp).toLocaleString()}</p>
            </div>
          </div>

          {/* State Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">Select State</Label>
            <RadioGroup value={selectedState} onValueChange={setSelectedState}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="garbage" id="garbage" />
                <Label htmlFor="garbage">Garbage</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="incorrect-answer" id="incorrect-answer" />
                <Label htmlFor="incorrect-answer">Incorrect Answer</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="faq-added" id="faq-added" />
                <Label htmlFor="faq-added">Add FAQ</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="not-supported" id="not-supported" />
                <Label htmlFor="not-supported">Currently Not Supported</Label>
              </div>
            </RadioGroup>
          </div>

          {/* Conditional Fields Based on Selected State */}
          {selectedState === "incorrect-answer" && (
            <div className="space-y-4 p-4 border rounded-md bg-yellow-50">
              <Label className="text-sm font-medium">Action for Incorrect Answer</Label>
              <RadioGroup value={incorrectAnswerAction} onValueChange={setIncorrectAnswerAction}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="correct-answer" id="correct-answer" />
                  <Label htmlFor="correct-answer">Provide Correct Answer</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="escalate" id="escalate" />
                  <Label htmlFor="escalate">Raise a Ticket (Escalate)</Label>
                </div>
              </RadioGroup>

              {incorrectAnswerAction === "correct-answer" && (
                <div className="space-y-2">
                  <Label htmlFor="correct-answer-text">Correct Answer</Label>
                  <Textarea
                    id="correct-answer-text"
                    placeholder="Provide the correct answer for this query..."
                    value={correctAnswer}
                    onChange={(e) => setCorrectAnswer(e.target.value)}
                    rows={3}
                  />
                </div>
              )}
            </div>
          )}

          {selectedState === "faq-added" && (
            <div className="space-y-4 p-4 border rounded-md bg-blue-50">
              <Label className="text-sm font-medium">FAQ Details</Label>

              <div className="space-y-2">
                <Label htmlFor="faq-question">FAQ Question</Label>
                <Input
                  id="faq-question"
                  placeholder="Enter the FAQ question..."
                  value={faqQuestion}
                  onChange={(e) => setFaqQuestion(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="faq-answer">FAQ Answer</Label>
                <Textarea
                  id="faq-answer"
                  placeholder="Enter the FAQ answer..."
                  value={faqAnswer}
                  onChange={(e) => setFaqAnswer(e.target.value)}
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="faq-category">FAQ Category</Label>
                <Select value={faqCategory} onValueChange={setFaqCategory}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="policy">Policy</SelectItem>
                    <SelectItem value="claims">Claims</SelectItem>
                    <SelectItem value="payments">Payments</SelectItem>
                    <SelectItem value="coverage">Coverage</SelectItem>
                    <SelectItem value="account">Account Management</SelectItem>
                    <SelectItem value="general">General</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {selectedState === "not-supported" && (
            <div className="p-4 border rounded-md bg-purple-50">
              <p className="text-sm text-muted-foreground">
                This query will be marked as "Currently Not Supported". The system will learn to handle similar queries
                in future updates.
              </p>
            </div>
          )}

          {selectedState === "garbage" && (
            <div className="p-4 border rounded-md bg-gray-50">
              <p className="text-sm text-muted-foreground">
                This query will be marked as garbage/spam and will be used to improve spam detection.
              </p>
            </div>
          )}

          {/* Notes Section */}
          <div className="space-y-2">
            <Label htmlFor="notes">Additional Notes (Optional)</Label>
            <Textarea
              id="notes"
              placeholder="Add any additional notes or context..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => {
              resetForm()
              onClose()
            }}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isFormValid()}>
            Submit Action
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
