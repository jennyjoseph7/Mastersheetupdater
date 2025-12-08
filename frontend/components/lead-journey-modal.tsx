"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface LeadJourneyModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  lead: {
    userId: string
    name: string
    email: string
    contact: string
    campaignName: string
    channel: string
  } | null
}

const sampleConversation = [
  {
    id: 1,
    sender: "user",
    message: "Hi, I'm interested in your insurance plans",
    timestamp: "12:21:04",
  },
  {
    id: 2,
    sender: "bot",
    message:
      "Hello! I'd be happy to help you find the right insurance plan. What type of coverage are you looking for?",
    timestamp: "12:21:04",
  },
  {
    id: 3,
    sender: "user",
    message: "I need health insurance for my family",
    timestamp: "12:21:45",
  },
  {
    id: 4,
    sender: "bot",
    message: "Great! We have several family health insurance plans. How many family members would you like to cover?",
    timestamp: "12:21:46",
  },
  {
    id: 5,
    sender: "user",
    message: "Four members - me, my spouse, and two children",
    timestamp: "12:22:15",
  },
  {
    id: 6,
    sender: "bot",
    message:
      "Perfect! I can offer you our Family Health Plus plan which covers up to 6 family members. It includes comprehensive coverage with cashless hospitalization at 5000+ network hospitals. Would you like to know more about the benefits?",
    timestamp: "12:22:16",
  },
  {
    id: 7,
    sender: "user",
    message: "Yes, please tell me about the premium and coverage details",
    timestamp: "12:23:00",
  },
  {
    id: 8,
    sender: "bot",
    message:
      "For a family of 4, the annual premium is ₹25,000 with a sum insured of ₹10 lakhs. This includes pre and post hospitalization, day care procedures, and annual health check-ups. We also offer a 10% discount for online purchases.",
    timestamp: "12:23:02",
  },
]

export function LeadJourneyModal({ open, onOpenChange, lead }: LeadJourneyModalProps) {
  const [searchQuery, setSearchQuery] = useState("")

  if (!lead) return null

  const filteredMessages = sampleConversation.filter((msg) =>
    msg.message.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[85vh] p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl flex items-center gap-2">
              <span className="text-muted-foreground">💬</span>
              Interaction History - {lead.name}
            </DialogTitle>
            <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="grid grid-cols-4 gap-6 px-6 py-4 border-b bg-muted/30">
          <div>
            <p className="text-sm text-muted-foreground mb-1">User ID</p>
            <p className="font-semibold">{lead.userId}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Status</p>
            <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Converted</Badge>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Duration</p>
            <p className="font-semibold">15 min 30 sec</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Sentiment</p>
            <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">Positive</Badge>
          </div>
        </div>

        <div className="px-6 pt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search within transcript..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="px-6 py-4 space-y-4 overflow-y-auto max-h-[calc(85vh-280px)]">
          {filteredMessages.map((message) => (
            <div key={message.id} className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[70%] ${message.sender === "user" ? "order-2" : "order-1"}`}>
                <div
                  className={`rounded-2xl px-4 py-3 ${
                    message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                  }`}
                >
                  <p className="text-sm leading-relaxed">{message.message}</p>
                </div>
                <p className="text-xs text-muted-foreground mt-1 px-2">{message.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
