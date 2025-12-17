"use client"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  Mail, 
  MessageSquare, 
  Calendar, 
  FileText, 
  Globe, 
  Smartphone, 
  MapPin, 
  Store, 
  Target 
} from "lucide-react"
import type { Template } from "@/app/template/page"
import { epochToIST, capitalize } from "@/utils/api"

interface TemplateViewDialogProps {
  template: Template
  isOpen: boolean
  onClose: () => void
}

export function TemplateViewDialog({ template, isOpen, onClose }: TemplateViewDialogProps) {
  
  const getStatusBadge = (statusArray: string | string[]) => {
    // Handle specific array structure if it comes as ["Approved", ...] or just "Approved"
    const status = Array.isArray(statusArray) ? statusArray[0] : statusArray;
    const normalizedStatus = capitalize(status || "");

    switch (normalizedStatus) {
      case "Approved":
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-green-200">Approved</Badge>
      case "Pending":
        return <Badge className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100 border-yellow-200">Pending</Badge>
      case "Rejected":
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-100 border-red-200">Rejected</Badge>
      default:
        return <Badge variant="outline">{normalizedStatus}</Badge>
    }
  }

  // Parses text to highlight variables like {{variable}} or {'variable'}
  const renderMessageWithVariables = (text: string) => {
    if (!text) return <span className="text-muted-foreground italic">No message content</span>;
    
    // Regex to match {{variable}} or {'variable'}
    const regex = /(\{\{.*?\}\}|\{\'[^']+\'\})/g;
    const parts = text.split(regex);

    return (
      <p className="whitespace-pre-wrap text-sm text-[#111b21] leading-relaxed break-words">
        {parts.map((part, i) => {
          if (part.match(regex)) {
            const cleanVar = part.replace(/[\{\}\']/g, '').trim();
            return (
              <span key={i} title={`Variable: ${cleanVar}`} className="bg-blue-100 text-blue-800 px-1 rounded-[4px] font-medium text-xs mx-0.5 align-middle inline-block h-5 leading-5 border border-blue-200">
                {part}
              </span>
            );
          }
          return part;
        })}
      </p>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col p-0 gap-0 sm:max-w-max">
        
        {/* Header */}
        <div className="p-6 pb-4 border-b bg-background z-10">
           <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <FileText className="h-5 w-5 text-primary" />
              Template Details
            </DialogTitle>
            <DialogDescription>
              {template.template_name}
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Content Container */}
        <div className="flex-1 overflow-hidden flex flex-col lg:flex-row ">
            
            {/* LEFT COLUMN: Metadata (Scrollable) */}
            <ScrollArea className="flex-1 p-6 max-h-[calc(90vh-80px)]">
              <div className="space-y-8 pr-4">
                
                {/* Core Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-6">
                  
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</p>
                    <div>{getStatusBadge(template.status)}</div>
                  </div>

                  <div className="space-y-1">
                     <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Channel</p>
                     <div className="flex items-center gap-2 text-sm font-medium">
                        {template.channel === "WhatsApp" ? (
                          <MessageSquare className="h-4 w-4 text-green-600" />
                        ) : (
                          <Mail className="h-4 w-4 text-blue-600" />
                        )}
                        <span>{template.channel}</span>
                     </div>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Template ID</p>
                    <p className="text-sm font-mono text-muted-foreground break-all">{template.template_id}</p>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Language</p>
                    <div className="flex items-center gap-2 text-sm">
                      <Globe className="h-4 w-4 text-muted-foreground" />
                      <span>{capitalize(template.language)}</span>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Provider</p>
                    <p className="text-sm font-medium">{capitalize(template.provider_name)}</p>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Last Updated</p>
                    <div className="flex items-center gap-2 text-sm">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      {/* Handle both number (epoch) and string dates if necessary */}
                      <span>{typeof template.updated === 'number' ? epochToIST(template.updated) : template.updated}</span>
                    </div>
                  </div>

                  {/* Dynamic Fields from JSON */}
                  {template.dealer_name && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Dealer</p>
                      <div className="flex items-center gap-2 text-sm">
                        <Store className="h-4 w-4 text-muted-foreground" />
                        <span>{template.dealer_name}</span>
                      </div>
                    </div>
                  )}

                  {template.region_name && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Region</p>
                      <div className="flex items-center gap-2 text-sm">
                        <MapPin className="h-4 w-4 text-muted-foreground" />
                        <span>{template.region_name}</span>
                      </div>
                    </div>
                  )}
                  
                  {template.campaignName && (
                     <div className="space-y-1">
                       <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Campaign Type</p>
                       <p className="text-sm">{template.campaignName}</p>
                     </div>
                  )}
                </div>

                {/* Campaign Objectives */}
                {template.campaign_objective && Array.isArray(template.campaign_objective) && (
                  <div>
                     <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-2">
                        <Target className="h-3.5 w-3.5" /> Campaign Objectives
                     </p>
                     <div className="flex flex-wrap gap-2">
                        {template.campaign_objective.map((obj: string, i: number) => (
                           <Badge key={i} variant="secondary" className="font-normal text-xs">{obj}</Badge>
                        ))}
                     </div>
                  </div>
                )}

                {/* Rejection Reason Block */}
                {(JSON.stringify(template.status).toLowerCase().includes("rejected") || template.status === "Rejected") && template.rejectionReason && (
                  <div className="rounded-lg bg-red-50 p-4 border border-red-200 animate-in fade-in slide-in-from-top-2">
                    <p className="text-sm font-bold text-red-900 mb-1 flex items-center gap-2">
                       Rejection Reason
                    </p>
                    <p className="text-sm text-red-800">{template.rejectionReason}</p>
                  </div>
                )}
                
                {/* Template Variables Raw View */}
                {template.template_variables && template.template_variables.length > 0 && (
                   <div className="pt-4 border-t">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">Detected Variables</p>
                      <div className="grid grid-cols-2 gap-2">
                         {template.template_variables.map((v: string, i: number) => (
                            <div key={i} className="text-xs font-mono bg-muted/50 p-1.5 rounded border">
                               {`{${v}}`}
                            </div>
                         ))}
                      </div>
                   </div>
                )}
              </div>
            </ScrollArea>

            {/* RIGHT COLUMN: Phone Preview */}
            <div className="flex-none w-full lg:w-[380px] bg-muted/20 border-l p-6 flex flex-col items-center justify-center bg-slate-50">
              <div className="mb-4 flex items-center gap-2 text-sm font-medium text-muted-foreground uppercase tracking-widest">
                <Smartphone className="h-4 w-4" /> Live Preview
              </div>
              
              {/* Phone Device Frame */}
              <div className="relative w-[300px] h-[600px] bg-slate-900 rounded-[3rem] shadow-2xl border-[10px] border-slate-900 overflow-hidden flex flex-col ring-1 ring-black/10">
                
                {/* Status Bar Mockup */}
                <div className="bg-[#075e54] text-white/90 text-[10px] px-6 pt-3 pb-1 flex justify-between items-center z-10">
                   <span className="font-medium">9:41</span>
                   <div className="flex gap-1.5 opacity-90">
                      <div className="w-3 h-3 bg-current rounded-full opacity-20"></div>
                      <div className="w-3 h-3 bg-current rounded-full opacity-50"></div>
                      <div className="w-3 h-3 bg-current rounded-full"></div>
                   </div>
                </div>
                
                {/* WhatsApp Chat Header */}
                <div className="bg-[#075e54] p-3 flex items-center gap-3 shadow-sm z-10 pb-3">
                   <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center text-white font-bold text-sm shrink-0">
                     D
                   </div>
                   <div className="flex flex-col overflow-hidden">
                      <span className="text-white text-sm font-semibold truncate leading-tight">DaveAi</span>
                      <span className="text-white/80 text-[10px] flex items-center gap-1 mt-0.5">
                         Official Business Account <CheckCircle2 className="h-2 w-2 fill-white text-[#075e54]" />
                      </span>
                   </div>
                </div>

                {/* Chat Background & Content */}
                <div className="flex-1 bg-[#efe7dd] p-3 overflow-y-auto flex flex-col relative">
                  
                  {/* WhatsApp Doodle Background Pattern opacity */}
                  <div className="absolute inset-0 opacity-[0.06] pointer-events-none" 
                       style={{backgroundImage: "url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png')", backgroundSize: "400px"}} 
                  />

                  {/* Date Divider */}
                  <div className="self-center bg-[#fff] text-[#5e6c75] text-[10px] px-3 py-1.5 rounded-lg shadow-[0_1px_0.5px_rgba(0,0,0,0.13)] mb-4 mt-2 font-medium z-10">
                     TODAY
                  </div>

                  {/* Message Bubble */}
                  <div className="bg-white rounded-lg p-2 max-w-[92%] shadow-[0_1px_0.5px_rgba(0,0,0,0.13)] self-start relative rounded-tl-none z-10 group">
                    {/* Tail SVG */}
                    <svg viewBox="0 0 8 13" height="13" width="8" className="absolute -left-2 top-0 text-white fill-current">
                       <path opacity="0.13" d="M5.188 1H0v11.193l6.467-8.625C7.526 2.156 6.958 1 5.188 1z"></path>
                       <path d="M5.188 0H0v11.193l6.467-8.625C7.526 1.156 6.958 0 5.188 0z"></path>
                    </svg>

                    {/* Message Text */}
                    <div className="px-1 pt-1 pb-4">
                       {renderMessageWithVariables(template.template_message || "")}
                    </div>
                    
                    {/* Timestamp */}
                    <div className="absolute bottom-1 right-2 text-[9px] text-[rgba(17,27,33,0.5)] flex items-center gap-1">
                       {/* Handle epoch time safely */}
                       {(() => {
                          const date = typeof template.updated === 'number' ? new Date(template.updated * 1000) : new Date();
                          return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', hour12: true});
                       })()}
                    </div>
                  </div>

                  {/* Buttons (if any) */}
                  {template.buttons && template.buttons.length > 0 && (
                    <div className="mt-2 w-full max-w-[92%] self-start flex flex-col gap-2 z-10">
                       {template.buttons.map((btn, idx) => (
                          <div key={idx} className="bg-white rounded-[10px] py-2.5 px-3 text-center text-[#00a884] text-sm font-medium shadow-[0_1px_0.5px_rgba(0,0,0,0.13)] active:bg-[#f0f2f5] cursor-pointer transition-colors flex items-center justify-center gap-2 hover:bg-gray-50">
                             {btn.type === 'QUICK_REPLY' && <MessageSquare className="h-3.5 w-3.5" />}
                             {btn.text}
                          </div>
                       ))}
                    </div>
                  )}

                </div>
                
                {/* Chat Footer Mockup */}
                 <div className="bg-[#f0f2f5] p-2 px-3 flex items-center gap-3 border-t border-slate-200">
                    <div className="w-6 h-6 rounded-full bg-slate-300 text-white flex items-center justify-center text-[10px]">+</div>
                    <div className="flex-1 h-8 bg-white rounded-lg border-none"></div>
                    <div className="w-6 h-6 rounded-full bg-[#00a884] flex items-center justify-center">
                       <div className="w-3 h-3 border-l-2 border-b-2 border-white -rotate-45 translate-x-0.5"></div>
                    </div>
                 </div>

              </div>
              <p className="mt-6 text-xs text-muted-foreground text-center px-8">
                 Preview is an approximation. Actual rendering may vary by device.
              </p>
            </div>

        </div>
      </DialogContent>
    </Dialog>
  )
}

function CheckCircle2({className}: {className?: string}) {
   return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
         <path fillRule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.75-5.25z" clipRule="evenodd" />
      </svg>
   )
}