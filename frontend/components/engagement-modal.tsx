"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { User, Bot, MessageSquare } from "lucide-react";
import { fetchUserSessions, epochToIST } from "@/utils/api";

interface EngagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  campaignId: string;
  personName?: string;
}

interface Message {
  role: string;
  index: number;
  message: string;
  timestamp: number;
}

interface Session {
  session_id: string;
  user_id: string;
  person_name?: string;
  phone_number?: string;
  status: string;
  channel: string;
  disposition?: string;
  created: number;
  updated: number;
  start_time: number;
  end_time?: number;
  duration?: number;
  history: Message[];
}

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateIfStale: false,
  revalidateOnReconnect: false,
  errorRetryCount: 0,
  shouldRetryOnError: false,
};

export function EngagementModal({
  isOpen,
  onClose,
  userId,
  campaignId,
  personName,
}: EngagementModalProps) {
  const {
    data: sessionsData,
    isLoading,
    error,
  } = useSWR<{ items: Session[]; total: number }>(
    isOpen && userId && campaignId
      ? `user-sessions-${userId}-${campaignId}`
      : null,
    () => fetchUserSessions(userId, campaignId),
    SWR_OPTIONS
  );

  const sessions = sessionsData?.items ?? [];
  const [selectedSessionIndex, setSelectedSessionIndex] = useState(0);

  // Reset to first session when sessions change
  useEffect(() => {
    if (sessions.length > 0 && selectedSessionIndex >= sessions.length) {
      setSelectedSessionIndex(0);
    }
  }, [sessions.length, selectedSessionIndex]);

  const selectedSession =
    sessions.length > 0 ? sessions[selectedSessionIndex] : null;
  const messages = selectedSession?.history ?? [];

  // Sort messages by timestamp
  const sortedMessages = [...messages].sort(
    (a, b) => a.timestamp - b.timestamp
  );

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent
        className="max-h-[90vh] flex flex-col p-0"
        style={{ width: "95vw", maxWidth: "95vw" }}
      >
        <DialogHeader className="px-6 pt-6 pb-4">
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Engagement History
            {personName && (
              <span className="text-muted-foreground font-normal">
                - {personName}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 flex flex-col min-h-0 px-6 pb-6">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : error ? (
            <div className="text-center text-muted-foreground py-8">
              Failed to load engagement history. {error.message}
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No engagement history found for this user.
            </div>
          ) : (
            <>
              {/* Show tabs if multiple sessions exist */}
              {sessions.length > 1 && (
                <Tabs
                  value={selectedSessionIndex.toString()}
                  onValueChange={(value) =>
                    setSelectedSessionIndex(parseInt(value))
                  }
                  className="mb-4"
                >
                  <TabsList
                    className="inline-flex h-auto w-full bg-transparent p-0 gap-2"
                    style={{
                      gridTemplateColumns: `repeat(${sessions.length}, minmax(0, 1fr))`,
                    }}
                  >
                    {sessions.map((session, index) => (
                      <TabsTrigger
                        key={session.session_id}
                        value={index.toString()}
                        className="flex-1 h-auto py-2.5 px-4 rounded-lg border border-border/50 bg-background/50 data-[state=active]:bg-background data-[state=active]:border-border data-[state=active]:shadow-sm transition-all duration-200 hover:bg-background/80"
                      >
                        <div className="flex flex-col items-center gap-0.5">
                          <span className="text-xs font-medium capitalize leading-tight">
                            {session.channel?.replace(/_/g, " ") || "Session"}
                          </span>
                          <span className="text-[10px] text-muted-foreground/80 font-normal">
                            {session.duration
                              ? `${Math.floor(session.duration / 60)}m`
                              : "N/A"}
                          </span>
                        </div>
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              )}

              {selectedSession && (
                <>
                  {/* Session Info */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg mb-4 flex-shrink-0">
                    <div>
                      <p className="text-sm font-medium">Session ID</p>
                      <p className="text-sm text-muted-foreground font-mono">
                        {selectedSession.session_id?.substring(0, 12)}...
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Channel</p>
                      <Badge variant="secondary" className="capitalize">
                        {selectedSession.channel?.replace(/_/g, " ") || "N/A"}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Disposition</p>
                      <Badge
                        variant={
                          selectedSession.disposition === "converted" ||
                          selectedSession.disposition === "engaged"
                            ? "default"
                            : selectedSession.disposition === "failed"
                            ? "destructive"
                            : "secondary"
                        }
                      >
                        {selectedSession.disposition || "N/A"}
                      </Badge>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Duration</p>
                      <p className="text-sm text-muted-foreground">
                        {selectedSession.duration
                          ? `${Math.floor(selectedSession.duration / 60)}m ${
                              selectedSession.duration % 60
                            }s`
                          : "N/A"}
                      </p>
                    </div>
                  </div>

                  {/* Chat Conversation */}
                  <div
                    className="border rounded-lg overflow-hidden"
                    style={{ height: "calc(90vh - 250px)", minHeight: "500px" }}
                  >
                    <ScrollArea className="h-full w-full">
                      <div className="space-y-4 p-4 pr-6">
                        {sortedMessages.length === 0 ? (
                          <div className="text-center text-muted-foreground py-8">
                            No messages found in this session.
                          </div>
                        ) : (
                          sortedMessages.map((message, index) => {
                            const isUser = message.role === "user";
                            return (
                              <div
                                key={`${message.index}-${index}`}
                                className={`flex gap-3 ${
                                  isUser ? "justify-end" : "justify-start"
                                }`}
                              >
                                <div
                                  className={`flex gap-2 max-w-[75%] ${
                                    isUser ? "flex-row-reverse" : "flex-row"
                                  }`}
                                >
                                  <div className="flex-shrink-0">
                                    {isUser ? (
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
                                    className={`rounded-lg p-3 break-words ${
                                      isUser
                                        ? "bg-primary text-primary-foreground"
                                        : "bg-muted"
                                    }`}
                                    style={{
                                      wordBreak: "break-word",
                                      overflowWrap: "anywhere",
                                    }}
                                  >
                                    <p className="text-sm whitespace-pre-wrap break-words">
                                      {message.message}
                                    </p>
                                    <p className="text-xs opacity-70 mt-2">
                                      {epochToIST(message.timestamp)}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                    </ScrollArea>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
