"use client"

import { cn } from "@/lib/utils"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ThumbsDown, ThumbsUp } from "lucide-react"
import type { UserSession } from "./user-session-list" // Import the interface

interface ConversationHistoryProps {
  session: UserSession
}

export function ConversationHistory({ session }: ConversationHistoryProps) {
  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle>Conversation History for Session: {session.id}</CardTitle>
        <p className="text-sm text-muted-foreground">
          User: {session.userId} | Duration: {session.duration}
        </p>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <ScrollArea className="h-[calc(100vh-300px)] pr-4">
          {" "}
          {/* Adjust height as needed */}
          <div className="space-y-4">
            {session.messages.map((message) => (
              <div
                key={message.id}
                className={cn("flex items-start gap-3", message.sender === "user" ? "justify-end" : "justify-start")}
              >
                <div
                  className={cn(
                    "max-w-[70%] rounded-lg p-3 text-sm",
                    message.sender === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                  )}
                >
                  <p>{message.text}</p>
                  <p className="mt-1 text-xs opacity-70">{new Date(message.timestamp).toLocaleTimeString()}</p>
                  {message.sender === "user" && message.rating && (
                    <div className="mt-2 flex items-center gap-1">
                      {message.rating === "thumbs-up" ? (
                        <ThumbsUp className="h-4 w-4 text-green-300" />
                      ) : (
                        <ThumbsDown className="h-4 w-4 text-red-300" />
                      )}
                      <span className="text-xs opacity-70">Feedback</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
