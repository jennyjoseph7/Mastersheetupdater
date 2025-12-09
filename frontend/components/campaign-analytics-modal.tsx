"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Users, MessageSquare, Mail, Phone, User, Bot, ThumbsUp, ThumbsDown } from "lucide-react"
import type { Campaign } from "@/types/campaign"
import { cn } from "@/lib/utils"

interface CampaignAnalyticsModalProps {
  campaign: Campaign | null
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

interface Conversation {
  id: string
  personName: string
  email: string
  contactNumber: string
  channel: "WhatsApp" | "Email" | "Voice" | "SMS"
  messages: Message[]
  conversionDate: string
}

// Generate mock conversations based on campaign channels
const generateMockConversations = (campaign: Campaign): Conversation[] => {
  const conversations: Conversation[] = []
  const names = ["Rajesh Kumar", "Priya Sharma", "Amit Patel", "Sneha Reddy", "Vikram Singh", "Anjali Mehta"]
  const channels = campaign.channelsUsed || ["WhatsApp", "Email", "SMS"]
  
  channels.forEach((channel, channelIndex) => {
    // Create 2-3 conversations per channel
    const conversationsPerChannel = 2 + (channelIndex % 2)
    
    for (let i = 0; i < conversationsPerChannel; i++) {
      const personIndex = (channelIndex * conversationsPerChannel + i) % names.length
      const personName = names[personIndex]
      const baseDate = new Date(campaign.createdOn)
      baseDate.setDate(baseDate.getDate() + channelIndex * 2 + i)
      
      const messages: Message[] = [
        {
          id: `msg-${channel}-${i}-1`,
          sender: "bot",
          text: `Hello ${personName.split(" ")[0]}! Thank you for your interest in ${campaign.name}. How can I assist you today?`,
          timestamp: new Date(baseDate.getTime() - 30 * 60000).toISOString(),
        },
        {
          id: `msg-${channel}-${i}-2`,
          sender: "user",
          text: channel === "WhatsApp" 
            ? "Hi! I'm interested in learning more about this offer. Can you tell me the details?"
            : channel === "Email"
            ? "I received your email about the campaign. Could you provide more information?"
            : channel === "Voice"
            ? "Hello, I'm calling regarding the campaign I saw. Can you help me?"
            : "I got your SMS. Please send me more details.",
          timestamp: new Date(baseDate.getTime() - 28 * 60000).toISOString(),
        },
        {
          id: `msg-${channel}-${i}-3`,
          sender: "bot",
          text: "Of course! This campaign offers exclusive benefits including competitive pricing, flexible payment options, and comprehensive coverage. Would you like me to send you a detailed brochure?",
          timestamp: new Date(baseDate.getTime() - 25 * 60000).toISOString(),
          rating: "thumbs-up",
        },
        {
          id: `msg-${channel}-${i}-4`,
          sender: "user",
          text: "Yes, please. Also, what are the payment terms?",
          timestamp: new Date(baseDate.getTime() - 20 * 60000).toISOString(),
        },
        {
          id: `msg-${channel}-${i}-5`,
          sender: "bot",
          text: "We offer flexible payment plans with monthly, quarterly, and annual options. EMI facilities are also available with zero down payment for qualified customers.",
          timestamp: new Date(baseDate.getTime() - 18 * 60000).toISOString(),
        },
        {
          id: `msg-${channel}-${i}-6`,
          sender: "user",
          text: "That sounds great! I'd like to proceed with this.",
          timestamp: new Date(baseDate.getTime() - 15 * 60000).toISOString(),
        },
        {
          id: `msg-${channel}-${i}-7`,
          sender: "bot",
          text: "Wonderful! I'll connect you with our specialist who will help you complete the process. You should receive a call within the next hour.",
          timestamp: new Date(baseDate.getTime() - 10 * 60000).toISOString(),
          rating: "thumbs-up",
        },
      ]
      
      conversations.push({
        id: `conv-${channel}-${i}`,
        personName,
        email: `${personName.toLowerCase().replace(" ", ".")}@example.com`,
        contactNumber: `+91 98765${10000 + channelIndex * 10 + i}`,
        channel: channel as "WhatsApp" | "Email" | "Voice" | "SMS",
        messages,
        conversionDate: baseDate.toISOString(),
      })
    }
  })
  
  return conversations
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

const getChannelColor = (channel: string) => {
  switch (channel) {
    case "WhatsApp":
      return "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400"
    case "Email":
      return "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400"
    case "SMS":
      return "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400"
    case "Voice":
      return "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400"
    default:
      return "bg-gray-100 text-gray-700"
  }
}

export function CampaignAnalyticsModal({ campaign, isOpen, onClose }: CampaignAnalyticsModalProps) {
  if (!campaign) return null

  const conversations = generateMockConversations(campaign)
  
  // Group conversations by channel
  const conversationsByChannel = conversations.reduce((acc, conv) => {
    if (!acc[conv.channel]) {
      acc[conv.channel] = []
    }
    acc[conv.channel].push(conv)
    return acc
  }, {} as Record<string, Conversation[]>)

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">{campaign.name} - Conversations</DialogTitle>
        </DialogHeader>

        <div className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                People's Conversations by Channel
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                View all conversations with people who converted, organized by their communication channels
              </p>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue={campaign.channelsUsed?.[0] || "WhatsApp"} className="w-full">
                <TabsList 
                  className="grid w-full mb-6" 
                  style={{ 
                    gridTemplateColumns: `repeat(${Math.min(campaign.channelsUsed?.length || 1, 4)}, minmax(0, 1fr))` 
                  }}
                >
                  {campaign.channelsUsed?.map((channel) => (
                    <TabsTrigger key={channel} value={channel} className="flex items-center gap-2">
                      {getChannelIcon(channel)}
                      {channel}
                      <Badge variant="secondary" className="ml-1">
                        {conversationsByChannel[channel]?.length || 0}
                      </Badge>
                    </TabsTrigger>
                  ))}
                </TabsList>

                {campaign.channelsUsed?.map((channel) => (
                  <TabsContent key={channel} value={channel} className="mt-0">
                    <div className="space-y-4">
                      {conversationsByChannel[channel]?.map((conversation) => (
                        <Card key={conversation.id} className="border-l-4 border-l-primary">
                          <CardHeader className="pb-3">
                            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                              <div className="flex items-start gap-3 flex-1 min-w-0">
                                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                  <User className="h-5 w-5 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <CardTitle className="text-lg truncate">{conversation.personName}</CardTitle>
                                  <div className="flex flex-wrap items-center gap-2 mt-1">
                                    <Badge className={getChannelColor(channel)}>
                                      <span className="flex items-center gap-1">
                                        {getChannelIcon(channel)}
                                        {channel}
                                      </span>
                                    </Badge>
                                    <span className="text-xs text-muted-foreground whitespace-nowrap">
                                      {new Date(conversation.conversionDate).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <div className="flex flex-col gap-1 mt-2 sm:hidden">
                                    <p className="text-sm text-muted-foreground truncate">{conversation.email}</p>
                                    <p className="text-sm text-muted-foreground">{conversation.contactNumber}</p>
                                  </div>
                                </div>
                              </div>
                              <div className="hidden sm:flex flex-col gap-1 text-right flex-shrink-0 ml-4">
                                <p className="text-sm text-muted-foreground break-all">{conversation.email}</p>
                                <p className="text-sm text-muted-foreground whitespace-nowrap">{conversation.contactNumber}</p>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <ScrollArea className="h-[300px] pr-4">
                              <div className="space-y-3">
                                {conversation.messages.map((message) => (
                                  <div
                                    key={message.id}
                                    className={cn(
                                      "flex items-start gap-3",
                                      message.sender === "user" ? "justify-end" : "justify-start"
                                    )}
                                  >
                                    <div
                                      className={cn(
                                        "flex gap-2 max-w-[80%]",
                                        message.sender === "user" ? "flex-row-reverse" : "flex-row"
                                      )}
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
                                        className={cn(
                                          "rounded-lg p-3 text-sm",
                                          message.sender === "user"
                                            ? "bg-primary text-primary-foreground"
                                            : "bg-muted"
                                        )}
                                      >
                                        <p>{message.text}</p>
                                        <div className="flex items-center justify-between mt-2 gap-2">
                                          <p className="text-xs opacity-70">
                                            {new Date(message.timestamp).toLocaleTimeString()}
                                          </p>
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
                            </ScrollArea>
                          </CardContent>
                        </Card>
                      ))}
                      {(!conversationsByChannel[channel] || conversationsByChannel[channel].length === 0) && (
                        <div className="text-center text-muted-foreground py-8">
                          No conversations found for {channel}
                        </div>
                      )}
                    </div>
                  </TabsContent>
                ))}
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default CampaignAnalyticsModal
