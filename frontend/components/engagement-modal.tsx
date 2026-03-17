"use client";

import { useState, useEffect, useMemo } from "react";
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
import { Button } from "@/components/ui/button";
import { 
  User, 
  Bot, 
  MessageSquare, 
  Download, 
  Calendar, 
  Clock, 
  PhoneIncoming, // Added for Recording
  BarChart3,     // Added for Sentiment
  Smile          // Added for Emotions
} from "lucide-react";
import { fetchUserSessions, epochToIST } from "@/utils/api";
import { cn } from "@/lib/utils";

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
  // --- New Fields Added (Optional) ---
  disposition_detail?: string;
  sentiment_score?: number;
  emotion_analysis?: Record<string, string | number>;
  call_recording?: string;
  // -----------------------------------
  created: number;
  updated: number;
  start_time: number;
  end_time?: number;
  duration?: number;
  history: Message[];
}

interface EngagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  campaignId: string;
  personName?: string;
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

  useEffect(() => {
    if (sessions.length > 0 && selectedSessionIndex >= sessions.length) {
      setSelectedSessionIndex(0);
    }
  }, [sessions.length, selectedSessionIndex]);

  const selectedSession = sessions[selectedSessionIndex] || null;

  const sortedMessages = useMemo(() => {
    if (!selectedSession?.history) return [];
    return [...selectedSession.history].sort((a, b) => a.timestamp - b.timestamp);
  }, [selectedSession]);

  const handleDownload = () => {
    if (!selectedSession) return;
    const transcript = sortedMessages
      .map(m => `[${epochToIST(m.timestamp)}] ${m.role.toUpperCase()}: ${m.message}`)
      .join("\n\n");
    
    const blob = new Blob([transcript], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcript-${personName || userId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent
        className="max-h-[90vh] flex flex-col p-0 overflow-hidden bg-background border-none shadow-2xl"
        style={{ width: "95vw", maxWidth: "1400px" }}
      >
        {/* Modal Header */}
        <DialogHeader className="px-6 py-4 border-b flex flex-row items-center justify-between space-y-0 shrink-0">
          <DialogTitle className="flex items-center gap-2 text-xl font-semibold">
            <MessageSquare className="h-5 w-5 text-primary" />
            Engagement History
            {personName && (
              <span className="text-muted-foreground font-normal ml-1">
                — {personName}
              </span>
            )}
          </DialogTitle>
          <div className="flex items-center gap-3 pr-8">
            {/* Added: Recording Button (Only shows if link exists) */}
            {selectedSession?.call_recording && (
              <Button variant="ghost" size="sm" asChild className="text-primary hover:bg-primary/5">
                <a href={selectedSession.call_recording} target="_blank" rel="noreferrer">
                  <PhoneIncoming className="h-4 w-4 mr-2" />
                  Recording
                </a>
              </Button>
            )}
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDownload} 
              disabled={!selectedSession || sortedMessages.length === 0}
              className="h-9 px-4 border-slate-200 hover:bg-slate-50 transition-colors"
            >
              <Download className="h-4 w-4 mr-2" />
              Download Transcript
            </Button>
          </div>
        </DialogHeader>

        <div className="flex-1 flex overflow-hidden h-[calc(90vh-70px)]">
          {isLoading ? (
            <div className="flex-1 p-6 space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-full w-full" />
            </div>
          ) : error ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground gap-2">
              <p className="text-destructive font-medium">Failed to load engagement history</p>
              <p className="text-sm">{error.message}</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground py-20">
              <MessageSquare className="h-12 w-12 mb-4 opacity-20" />
              <p>No engagement history found for this user.</p>
            </div>
          ) : (
            <>
              {/* Sidebar Navigation */}
              <aside className="w-80 border-r bg-slate-50/50 flex flex-col shrink-0">
                <div className="px-4 py-3 border-b bg-white/50">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">
                    All Sessions ({sessions.length})
                  </h3>
                </div>
                <ScrollArea className="flex-1">
                  <div className="p-3 space-y-2">
                    {sessions.map((session, index) => (
                      <button
                        key={session.session_id}
                        onClick={() => setSelectedSessionIndex(index)}
                        className={cn(
                          "w-full text-left p-4 rounded-xl transition-all border group relative",
                          selectedSessionIndex === index
                            ? "bg-white border-primary shadow-sm ring-1 ring-primary/5"
                            : "bg-transparent border-transparent hover:bg-slate-100/80"
                        )}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className={cn(
                            "text-sm font-bold capitalize truncate pr-2",
                            selectedSessionIndex === index ? "text-primary" : "text-slate-700"
                          )}>
                            {session.channel?.replace(/_/g, " ") || "WhatsApp Chat"}
                          </span>
                          <span className="text-[10px] font-medium text-slate-400 shrink-0">
                            {session.duration ? `${Math.floor(session.duration)}s` : "N/A"}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-slate-500">
                          <div className="flex items-center">
                            <Calendar className="h-3 w-3 mr-1 opacity-70" />
                            {new Date(session.start_time * 1000).toLocaleDateString()}
                          </div>
                          <div className="flex items-center">
                            <Clock className="h-3 w-3 mr-1 opacity-70" />
                            {new Date(session.start_time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </ScrollArea>
              </aside>

              {/* Main Chat Detail Area */}
              <main className="flex-1 flex flex-col bg-white overflow-hidden relative">
                {selectedSession && (
                  <>
                    {/* UPDATED: Sticky Session Metrics Bar with new Stats */}
                    <div className="grid grid-cols-4 gap-8 px-8 py-5 border-b bg-white shrink-0">
                      
                      {/* 1. Disposition (Prioritizes detailed view if available) */}
                      <MetricItem 
                        label="Disposition" 
                        value={selectedSession.disposition_detail || selectedSession.disposition} 
                        isBadge={!selectedSession.disposition_detail} 
                      />

                      {/* 2. Duration (Preserved) */}
                      <MetricItem 
                        label="Duration" 
                        value={selectedSession.duration 
                          ? `${Math.floor(selectedSession.duration / 60)}m ${selectedSession.duration % 60}s` 
                          : "N/A"} 
                      />

                      {/* 3. Sentiment Score (New) */}
                      <div className="space-y-1.5">
                        <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">Sentiment</p>
                        {selectedSession.sentiment_score !== undefined ? (
                           <Badge variant="outline" className="flex w-fit gap-1 items-center bg-slate-50 font-mono py-1">
                             <BarChart3 className="h-3 w-3 text-slate-400" />
                             {selectedSession.sentiment_score}
                           </Badge>
                        ) : (
                           <p className="text-sm font-semibold text-slate-700 text-xs">N/A</p>
                        )}
                      </div>

                      {/* 4. Emotion Analysis (New - takes up remaining space) */}
                      <div className="space-y-1.5">
                        <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">Emotions</p>
                        <div className="flex flex-wrap gap-2">
                          {selectedSession.emotion_analysis ? (
                             Object.entries(selectedSession.emotion_analysis).map(([key, val]) => (
                               <Badge key={key} variant="secondary" className="capitalize text-[10px] font-medium bg-indigo-50 text-indigo-700 border-indigo-100 py-0.5 px-2">
                                 <Smile className="h-2.5 w-2.5 mr-1" />
                                 {key}: {val}
                               </Badge>
                             ))
                          ) : (
                             <p className="text-sm text-slate-400 italic text-xs">No analysis</p>
                          )}
                        </div>
                      </div>

                    </div>

                    {/* Scrollable Chat Area */}
                    <ScrollArea className="flex-1 h-full w-full bg-slate-50/30">
                      <div className="p-8 space-y-8 max-w-4xl mx-auto min-h-full">
                        {sortedMessages.length === 0 ? (
                          <div className="flex flex-col items-center justify-center h-64 text-slate-400 italic">
                            No messages found in this session.
                          </div>
                        ) : (
                          sortedMessages.map((message, index) => {
                            const isUser = message.role === "user";
                            return (
                              <div
                                key={`${message.index}-${index}`}
                                className={cn(
                                  "flex gap-4",
                                  isUser ? "flex-row-reverse" : "flex-row"
                                )}
                              >
                                {/* Avatar Icons */}
                                <div className={cn(
                                  "h-9 w-9 rounded-full flex items-center justify-center shrink-0 border shadow-sm",
                                  isUser ? "bg-indigo-600 text-white border-indigo-700" : "bg-white text-slate-500 border-slate-200"
                                )}>
                                  {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                                </div>

                                {/* Message Bubbles */}
                                <div className={cn(
                                  "flex flex-col max-w-[75%] gap-1.5",
                                  isUser ? "items-end" : "items-start"
                                )}>
                                  <div
                                    className={cn(
                                      "px-5 py-3.5 rounded-2xl text-[14px] leading-relaxed shadow-sm border",
                                      isUser 
                                        ? "bg-indigo-600 text-white border-indigo-700 rounded-tr-none" 
                                        : "bg-white text-slate-700 border-slate-100 rounded-tl-none"
                                    )}
                                  >
                                    <p className="whitespace-pre-wrap">{message.message}</p>
                                  </div>
                                  <span className="text-[10px] font-medium text-slate-400 px-1">
                                    {epochToIST(message.timestamp)}
                                  </span>
                                </div>
                              </div>
                            );
                          })
                        )}
                        {/* Buffer at the bottom */}
                        <div className="h-4" />
                      </div>
                    </ScrollArea>
                  </>
                )}
              </main>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Helper component for session metrics
function MetricItem({ label, value, isBadge, isMono }: { label: string, value?: string, isBadge?: boolean, isMono?: boolean }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">{label}</p>
      {isBadge ? (
        <Badge variant="secondary" className="bg-slate-100 text-slate-700 border-none px-2.5 py-0.5 hover:bg-slate-200 capitalize text-[11px]">
          {value || "N/A"}
        </Badge>
      ) : (
        <p className={cn(
          "text-sm font-semibold text-slate-700 truncate",
          isMono && "font-mono text-xs text-slate-500"
        )}>
          {value || "N/A"}
        </p>
      )}
    </div>
  );
}