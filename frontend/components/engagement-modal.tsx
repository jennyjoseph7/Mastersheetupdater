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
  Play,        
  Volume2,    
  X,           
  BarChart3,     
  Smile,
  FileText,
  Copy,
  Check,
  Phone,
  Mail,
  ArrowRight
} from "lucide-react";
import { fetchUserSessions, epochToIST } from "@/utils/api";
import { cn } from "@/lib/utils";

// --- Interfaces ---

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
  disposition_detail?: string;
  sentiment_score?: number;
  emotion_analysis?: Record<string, string | number>;
  call_recording?: string;
  summary?: string;
  created: number;
  updated: number;
  start_time: number;
  end_time?: number;
  duration?: number;
  history: Message[];
}

function getActionLabel(action: string): string {
  const normalized = action.toLowerCase();
  const labelMap: Record<string, string> = {
    voice_phone: "Voice Call",
    voice: "Voice Call",
    voice_phone_outbound: "Outbound Call",
    voice_phone_inbound: "Inbound Call",
    whatsapp: "WhatsApp",
    whatsapp_chat: "WhatsApp Chat",
    whatsapp_chat_outbound: "Outbound WhatsApp",
    whatsapp_chat_inbound: "Inbound WhatsApp",
    email: "Email",
    email_outbound: "Outbound Email",
    email_inbound: "Inbound Email",
    sms: "SMS",
    sms_outbound: "Outbound SMS",
    sms_inbound: "Inbound SMS",
    rcs: "RCS",
    rcs_outbound: "Outbound RCS",
    rcs_inbound: "Inbound RCS",
  };
  return labelMap[normalized] || action.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

function getActionIcon(action: string) {
  const normalized = action.toLowerCase();
  if (normalized.includes("voice") || normalized.includes("phone")) {
    return <Phone className="h-4 w-4" />;
  }
  if (normalized.includes("whatsapp") || normalized.includes("chat") || normalized.includes("sms") || normalized.includes("rcs") || normalized.includes("message")) {
    return <MessageSquare className="h-4 w-4" />;
  }
  if (normalized.includes("email") || normalized.includes("mail")) {
    return <Mail className="h-4 w-4" />;
  }
  return <Clock className="h-4 w-4" />;
}

function getStatusStyles(status: string) {
  const normalized = status.toLowerCase();
  switch (normalized) {
    case "engaged":
    case "contacted":
    case "converted":
      return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-800";
    case "reached":
      return "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/30 dark:text-purple-400 dark:border-purple-800";
    case "queued":
    case "active":
      return "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/30 dark:text-blue-400 dark:border-blue-800";
    case "failed":
    case "busy":
      return "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800";
    case "unknown":
    default:
      return "bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-900/50 dark:text-slate-400 dark:border-slate-800";
  }
}

export function LeadTimelineVisual({ timeline }: { timeline: string }) {
  if (!timeline) return null;

  const steps = timeline.split("->").map(step => {
    const trimmed = step.trim();
    const match = trimmed.match(/^([^(]+)(?:\(([^)]+)\))?$/);
    if (match) {
      return {
        action: match[1].trim(),
        status: match[2] ? match[2].trim() : "",
      };
    }
    return {
      action: trimmed,
      status: "",
    };
  });

  return (
    <div className="flex flex-col gap-2 p-3 bg-slate-50/50 dark:bg-slate-900/10 border border-slate-200/60 dark:border-slate-800/60 rounded-xl">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
        <Clock className="h-3.5 w-3.5" />
        Lead Journey Timeline
      </div>
      <div className="flex flex-wrap items-center gap-2.5">
        {steps.map((step, idx) => {
          const actionLabel = getActionLabel(step.action);
          const statusStyles = getStatusStyles(step.status);
          
          return (
            <div key={idx} className="flex items-center gap-2.5">
              <div className="flex items-center gap-2.5 bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800 shadow-sm rounded-lg px-3.5 py-2 transition-all hover:border-slate-200 hover:shadow">
                <div className="text-indigo-600 dark:text-indigo-400 shrink-0 bg-indigo-50 dark:bg-indigo-950/30 p-1.5 rounded-md">
                  {getActionIcon(step.action)}
                </div>
                <div className="flex flex-col leading-none">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    {actionLabel}
                  </span>
                  {step.status && (
                    <span className={`text-[9px] px-1.5 py-0.5 rounded border font-medium mt-1 uppercase tracking-wider ${statusStyles}`}>
                      {step.status}
                    </span>
                  )}
                </div>
              </div>
              {idx < steps.length - 1 && (
                <ArrowRight className="h-4 w-4 text-slate-300 dark:text-slate-700 shrink-0 animate-pulse" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface EngagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  campaignId: string;
  personName?: string;
  leadTimeline?: string;
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
  leadTimeline,
}: EngagementModalProps) {
  const [copied, setCopied] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false); // Controls the inline player
  
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

  // Reset player when changing sessions
  useEffect(() => {
    setShowPlayer(false);
  }, [selectedSessionIndex]);

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

  // --- Handlers ---

  const handleCopySummary = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
            <MessageSquare className="h-5 w-5 text-indigo-600" />
            Engagement History
            {personName && (
              <span className="text-slate-400 font-normal ml-1">— {personName}</span>
            )}
          </DialogTitle>

          <div className="flex items-center gap-4 pr-10">
            {/* Inline Audio Player Logic */}
            {selectedSession?.call_recording && (
              <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-900 px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-800 transition-all">
                {!showPlayer ? (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-7 gap-2 text-indigo-600 hover:bg-indigo-50 hover:text-indigo-700"
                    onClick={() => setShowPlayer(true)}
                  >
                    <Play className="h-3.5 w-3.5 fill-current" />
                    <span className="text-xs font-bold">Play Recording</span>
                  </Button>
                ) : (
                  <div className="flex items-center gap-3 animate-in fade-in slide-in-from-right-2">
                    <div className="flex items-center gap-2 text-slate-400">
                      <Volume2 className="h-3.5 w-3.5" />
                      <audio 
                        src={selectedSession.call_recording} 
                        controls 
                        autoPlay 
                        className="h-7 w-48 md:w-64 accent-indigo-600"
                      />
                    </div>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6 rounded-full hover:bg-slate-200"
                      onClick={() => setShowPlayer(false)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
            )}

            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDownload} 
              disabled={!selectedSession || sortedMessages.length === 0}
              className="h-9 px-4 border-slate-200 hover:bg-slate-50 transition-colors"
            >
              <Download className="h-4 w-4 mr-2 text-slate-500" />
              Download Transcript
            </Button>
          </div>
        </DialogHeader>

        {leadTimeline && (
          <div className="px-6 py-3 border-b bg-slate-50/50 dark:bg-slate-900/10 shrink-0">
            <LeadTimelineVisual timeline={leadTimeline} />
          </div>
        )}

        <div className="flex-1 flex overflow-hidden min-h-0">
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
                            ? "bg-white border-indigo-600 shadow-sm ring-1 ring-indigo-600/5"
                            : "bg-transparent border-transparent hover:bg-slate-100/80"
                        )}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className={cn(
                            "text-sm font-bold capitalize truncate pr-2",
                            selectedSessionIndex === index ? "text-indigo-600" : "text-slate-700"
                          )}>
                            {session.channel?.replace(/_/g, " ") || "Voice Phone"}
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
                    {/* Sticky Session Metrics Bar */}
                    <div className="grid grid-cols-4 gap-8 px-8 py-5 border-b bg-white shrink-0">
                      <MetricItem 
                        label="Disposition" 
                        value={selectedSession.disposition_detail || selectedSession.disposition} 
                        isBadge={!selectedSession.disposition_detail} 
                      />

                      <MetricItem 
                        label="Duration" 
                        value={selectedSession.duration 
                          ? `${Math.floor(selectedSession.duration / 60)}m ${selectedSession.duration % 60}s` 
                          : "N/A"} 
                      />

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

                    {/* AI Summary Section */}
                    {selectedSession.summary && (
                      <div className="px-8 py-4 bg-slate-50/80 border-b border-slate-100 shrink-0">
                        <div className="max-w-4xl mx-auto flex items-start gap-4">
                          <div className="p-2 bg-white rounded-lg border border-slate-200 shadow-sm shrink-0">
                            <FileText className="h-4 w-4 text-indigo-600" />
                          </div>
                          <div className="flex-1 space-y-1">
                            <div className="flex items-center justify-between">
                              <h4 className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">Call Summary</h4>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-6 px-2 text-[10px] text-slate-400 hover:text-indigo-600"
                                onClick={() => handleCopySummary(selectedSession.summary!)}
                              >
                                {copied ? <Check className="h-3 w-3 mr-1" /> : <Copy className="h-3 w-3 mr-1" />}
                                {copied ? "Copied" : "Copy"}
                              </Button>
                            </div>
                            <p className="text-sm text-slate-600 leading-relaxed italic">
                              "{selectedSession.summary}"
                            </p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Scrollable Chat Area */}
                    <ScrollArea className="flex-1 h-full w-full bg-slate-50/30">
                      <div className="p-8 space-y-8 max-w-4xl mx-auto min-h-full mb-[15rem]">
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
                                <div className={cn(
                                  "h-9 w-9 rounded-full flex items-center justify-center shrink-0 border shadow-sm",
                                  isUser ? "bg-indigo-600 text-white border-indigo-700" : "bg-white text-slate-500 border-slate-200"
                                )}>
                                  {isUser ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                                </div>

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