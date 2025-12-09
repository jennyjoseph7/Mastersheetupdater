"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Search, User, Bot, ThumbsUp, ThumbsDown, Phone, MessageSquare, Mail } from "lucide-react"
import type { ConversionLead } from "@/types/conversion"

interface ViewConversionModalProps {
  lead: ConversionLead
  isOpen: boolean
  onClose: () => void
}

interface Message {
  id: string
  sender: "user" | "bot"
  text: string
  timestamp: string
  rating?: "thumbs-up" | "thumbs-down"
}

const generateMockConversation = (lead: ConversionLead): Message[] => {
  const baseMessages = [
    {
      id: "1",
      sender: "bot" as const,
      text: `Hello ${lead.leadName.split(" ")[0]}! Thank you for your interest in ${lead.campaignName}. How can I assist you today?`,
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 30 * 60000).toISOString(),
    },
    {
      id: "2",
      sender: "user" as const,
      text: "Hi! I'm interested in learning more about this offer. Can you tell me the details?",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 28 * 60000).toISOString(),
    },
    {
      id: "3",
      sender: "bot" as const,
      text: "Of course! This campaign offers exclusive benefits including competitive pricing, flexible payment options, and comprehensive coverage. Would you like me to send you a detailed brochure?",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 25 * 60000).toISOString(),
      rating: "thumbs-up",
    },
    {
      id: "4",
      sender: "user" as const,
      text: "Yes, please. Also, what are the payment terms?",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 20 * 60000).toISOString(),
    },
    {
      id: "5",
      sender: "bot" as const,
      text: "We offer flexible payment plans with monthly, quarterly, and annual options. EMI facilities are also available with zero down payment for qualified customers.",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 18 * 60000).toISOString(),
    },
    {
      id: "6",
      sender: "user" as const,
      text: "That sounds great! I'd like to proceed with this.",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 15 * 60000).toISOString(),
    },
    {
      id: "7",
      sender: "bot" as const,
      text: "Wonderful! I'll connect you with our specialist who will help you complete the process. You should receive a call within the next hour.",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 10 * 60000).toISOString(),
      rating: "thumbs-up",
    },
    {
      id: "8",
      sender: "user" as const,
      text: "Perfect, thank you for your help!",
      timestamp: new Date(new Date(lead.conversionDate).getTime() - 5 * 60000).toISOString(),
    },
  ]

  return baseMessages
}

export function ViewConversionModal({ lead, isOpen, onClose }: ViewConversionModalProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [messages] = useState<Message[]>(generateMockConversation(lead))

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Live":
        return "bg-emerald-100 text-emerald-800 border-emerald-200"
      case "Completed":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "Paused":
        return "bg-gray-100 text-gray-800 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case "WhatsApp":
        return <MessageSquare className="h-4 w-4" />
      case "Email":
        return <Mail className="h-4 w-4" />
      case "Voice":
      case "SMS":
        return <Phone className="h-4 w-4" />
      default:
        return <MessageSquare className="h-4 w-4" />
    }
  }

  const filteredMessages = messages.filter((message) => message.text.toLowerCase().includes(searchTerm.toLowerCase()))

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {getChannelIcon(lead.channelType)}
            Conversion Details - {lead.leadName}
          </DialogTitle>
        </DialogHeader>

        {/* Header Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
          <div>
            <p className="text-sm font-medium">User ID</p>
            <p className="text-sm text-muted-foreground">{lead.userId}</p>
          </div>
          <div>
            <p className="text-sm font-medium">Campaign Status</p>
            <Badge className={getStatusColor(lead.campaignStatus)}>{lead.campaignStatus}</Badge>
          </div>
          <div>
            <p className="text-sm font-medium">Channel</p>
            <div className="flex items-center gap-2 mt-1">
              {getChannelIcon(lead.channelType)}
              <span className="text-sm text-muted-foreground">{lead.channelType}</span>
            </div>
          </div>
          <div>
            <p className="text-sm font-medium">Conversion Date</p>
            <p className="text-sm text-muted-foreground">{new Date(lead.conversionDate).toLocaleDateString()}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 p-4 bg-gradient-to-r from-primary/10 to-primary/5 rounded-lg border border-primary/20">
          <div>
            <p className="text-sm font-medium">Email</p>
            <p className="text-sm text-muted-foreground">{lead.email}</p>
          </div>
          <div>
            <p className="text-sm font-medium">Contact</p>
            <p className="text-sm text-muted-foreground">{lead.contactNumber}</p>
          </div>
          <div>
            <p className="text-sm font-medium">Campaign</p>
            <p className="text-sm text-muted-foreground">{lead.campaignName}</p>
          </div>
        </div>

        {/* Search within conversation */}
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search conversation..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>

        {/* Conversation */}
        <ScrollArea className="flex-1 max-h-96">
          <div className="space-y-4 p-4">
            {filteredMessages.length > 0 ? (
              filteredMessages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${message.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`flex gap-2 max-w-[80%] ${message.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                  >
                    <div className="flex-shrink-0">
                      {message.sender === "user" ? (
                        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                          <User className="w-4 h-4 text-primary-foreground" />
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                          <Bot className="w-4 h-4 text-muted-foreground" />
                        </div>
                      )}
                    </div>
                    <div
                      className={`rounded-lg p-3 ${
                        message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                      }`}
                    >
                      <p className="text-sm">{message.text}</p>
                      <div className="flex items-center justify-between mt-2 gap-2">
                        <p className="text-xs opacity-70">{new Date(message.timestamp).toLocaleTimeString()}</p>
                        {message.rating && (
                          <div className="ml-2">
                            {message.rating === "thumbs-up" ? (
                              <ThumbsUp className="w-3 h-3 text-green-500" />
                            ) : (
                              <ThumbsDown className="w-3 h-3 text-red-500" />
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-muted-foreground py-8">No messages found matching your search.</div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
