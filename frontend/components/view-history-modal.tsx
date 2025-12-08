"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Search, User, Bot, ThumbsUp, ThumbsDown, Phone, MessageSquare, Database } from "lucide-react"
import type { Audience } from "./audience-list"

interface ViewHistoryModalProps {
  audience: Audience
  isOpen: boolean
  onClose: () => void
}

interface AudienceRecord {
  id: string
  timestamp: string
  interaction: string
  channel: string
  outcome: string
  duration: string
}

const generateMockRecords = (audience: Audience): AudienceRecord[] => {
  return [
    {
      id: "REC001",
      timestamp: "2025-01-10 14:30:25",
      interaction: "Product Inquiry",
      channel: audience.interactionType === "chat" ? "Chat" : "Call",
      outcome: audience.status,
      duration: `${Math.floor(audience.totalDuration)} min`,
    },
    {
      id: "REC002",
      timestamp: "2025-01-09 10:15:42",
      interaction: "Support Request",
      channel: "Email",
      outcome: "Resolved",
      duration: "N/A",
    },
    {
      id: "REC003",
      timestamp: "2025-01-08 16:45:18",
      interaction: "Pricing Query",
      channel: audience.interactionType === "chat" ? "Chat" : "Call",
      outcome: "Follow-up Scheduled",
      duration: "8 min",
    },
    {
      id: "REC004",
      timestamp: "2025-01-07 11:20:33",
      interaction: "Feature Demo",
      channel: "Video Call",
      outcome: "Interested",
      duration: "25 min",
    },
    {
      id: "REC005",
      timestamp: "2025-01-06 09:30:15",
      interaction: "Initial Contact",
      channel: "Web Form",
      outcome: "Lead Created",
      duration: "N/A",
    },
  ]
}

export function ViewHistoryModal({ audience, isOpen, onClose }: ViewHistoryModalProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [records] = useState<AudienceRecord[]>(generateMockRecords(audience))

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Converted":
        return "bg-green-100 text-green-800 border-green-200"
      case "Qualified":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "Lead":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "Losing":
        return "bg-orange-100 text-orange-800 border-orange-200"
      case "Lost":
        return "bg-red-100 text-red-800 border-red-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "Positive":
        return "bg-green-100 text-green-800 border-green-200"
      case "Negative":
        return "bg-red-100 text-red-800 border-red-200"
      case "Neutral":
        return "bg-gray-100 text-gray-800 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const filteredMessages =
    audience.messages?.filter((message) => message.text.toLowerCase().includes(searchTerm.toLowerCase())) || []

  const filteredRecords = records.filter(
    (record) =>
      record.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.interaction.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.channel.toLowerCase().includes(searchTerm.toLowerCase()) ||
      record.outcome.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {audience.interactionType === "chat" ? (
              <MessageSquare className="h-5 w-5" />
            ) : (
              <Phone className="h-5 w-5" />
            )}
            Interaction History - {audience.name}
          </DialogTitle>
        </DialogHeader>

        {/* Header Info */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
          <div>
            <p className="text-sm font-medium">User ID</p>
            <p className="text-sm text-muted-foreground">{audience.userId}</p>
          </div>
          <div>
            <p className="text-sm font-medium">Status</p>
            <Badge className={getStatusColor(audience.status)}>{audience.status}</Badge>
          </div>
          <div>
            <p className="text-sm font-medium">Duration</p>
            <p className="text-sm text-muted-foreground">{audience.totalDuration} min</p>
          </div>
          <div>
            <p className="text-sm font-medium">Sentiment</p>
            <Badge className={getSentimentColor(audience.sentiment)}>{audience.sentiment}</Badge>
          </div>
        </div>

        <Tabs defaultValue="history" className="flex-1">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="history">
              <MessageSquare className="h-4 w-4 mr-2" />
              Interaction History
            </TabsTrigger>
            <TabsTrigger value="datatable">
              <Database className="h-4 w-4 mr-2" />
              Data Records
            </TabsTrigger>
          </TabsList>

          {/* Search within transcript */}
          <div className="relative mt-4">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8"
            />
          </div>

          <TabsContent value="history" className="mt-4">
            <ScrollArea className="flex-1 max-h-96">
              {audience.interactionType === "chat" && audience.messages ? (
                <div className="space-y-4 p-4">
                  {filteredMessages.map((message) => (
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
                          <div className="flex items-center justify-between mt-2">
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
                  ))}
                </div>
              ) : (
                <div className="p-4">
                  <h4 className="font-medium mb-2">Call Transcript Summary</h4>
                  <div className="bg-muted/50 rounded-lg p-4">
                    <p className="text-sm leading-relaxed">
                      {audience.callTranscript || "No transcript available for this call."}
                    </p>
                  </div>
                </div>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="datatable" className="mt-4">
            <ScrollArea className="flex-1 max-h-96">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Record ID</TableHead>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>Interaction Type</TableHead>
                      <TableHead>Channel</TableHead>
                      <TableHead>Outcome</TableHead>
                      <TableHead>Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredRecords.length > 0 ? (
                      filteredRecords.map((record) => (
                        <TableRow key={record.id}>
                          <TableCell className="font-medium">{record.id}</TableCell>
                          <TableCell className="text-sm">{record.timestamp}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{record.interaction}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">{record.channel}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge className={getStatusColor(record.outcome)}>{record.outcome}</Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">{record.duration}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                          No records found matching your search.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
