"use client";

import { useState, useEffect, Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

// Imports
import { fetchAudienceTasks, getDealershipId } from "@/utils/api";
import { api } from "@/lib/api";

// UI Components
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";
import {
  MessageSquare,
  Mail,
  Phone,
  Check,
  Rocket,
  X,
  RefreshCw,
  Upload,
  Download,
  MessageSquareText,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
  RotateCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AILoader } from "@/components/ui/ai-loader";

// Import your advanced Dialog
import { AddDataSourceDialog } from "@/components/audience/add-data-source-dialog";

// --- HELPERS ---
const channels = [
  { id: "whatsapp", name: "WhatsApp", icon: <MessageSquare className="h-4 w-4" />, costPerUnit: 2.5655 },
  { id: "email", name: "Email", icon: <Mail className="h-4 w-4" />, costPerUnit: 0.195 },
  { id: "voice", name: "Voice Call", icon: <Phone className="h-4 w-4" />, costPerUnit: 8.56 },
  { id: "rcs", name: "RCS", icon: <MessageSquareText className="h-4 w-4" />, costPerUnit: 0.9525 },
  { id: "sms", name: "SMS", icon: <MessageSquareText className="h-4 w-4" />, costPerUnit: 0.12 },
];

const fromEpoch = (epoch: number) => {
  if (!epoch) return "";
  const d = new Date(epoch * 1000);
  return d.toISOString().split("T")[0];
};

const reverseMapChannels = (backend: string[]) => {
  const map: Record<string, string> = {
    whatsapp_chat: "whatsapp",
    email: "email",
    voice_phone: "voice",
    rcs_message: "rcs",
    sms_message: "sms",
  };
  return backend.map((c) => map[c] || c);
};

// --- SYNC UTILS ---
async function getTaskStatus(taskId: string) {
  return await api(`/gryd/status/${taskId}`, "GET");
}

async function getTaskResult(taskId: string) {
  return await api(`/gryd/result/${taskId}`, "GET");
}

async function updateAudienceTask(id: string, updateData: any) {
  return await api(`/gryd/db/object/audience_task/${id}`, "PATCH", updateData);
}

// --- MAIN COMPONENT ---

function ResumeCampaignContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const campaignId = searchParams.get("id");
  const typeParam = searchParams.get("type");

  const { isDealershipSetupComplete } = useAuth();

  // Core States
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [createdCampaignId, setCreatedCampaignId] = useState<string | null>(null);
  const [campaignType, setCampaignType] = useState<string>("");

  // Campaign Data (Hydrated)
  const [campaignName, setCampaignName] = useState("");
  const [campaignDescription, setCampaignDescription] = useState("");
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [duration, setDuration] = useState({ start: "", end: "" });
  const [selectedObjectiveId, setSelectedObjectiveId] = useState("");
  const [selectedObjectiveTitle, setSelectedObjectiveTitle] = useState("");

  // Audience State
  const [targetAudience, setTargetAudience] = useState<string[]>([]);
  const [selectedAudienceDetails, setSelectedAudienceDetails] = useState<any>(null);
  const [audienceTasks, setAudienceTasks] = useState<any[]>([]);
  const [isLoadingAudience, setIsLoadingAudience] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);

  // Launch States
  const [isLaunchSuccessOpen, setIsLaunchSuccessOpen] = useState(false);
  const [launchStatus, setLaunchStatus] = useState("");
  const [isLaunchError, setIsLaunchError] = useState(false);

  // --- 1. HYDRATION ---
  useEffect(() => {
    if (!campaignId || !typeParam) return;
    const fetchDraft = async () => {
      try {
        setIsLoading(true);
        const endpoint = typeParam === "presales" 
            ? `/gryd/db/object/pre_sales_campaign/${campaignId}` 
            : `/gryd/db/object/post_sales_campaign/${campaignId}`;

        const res = await api(endpoint, "GET");
        const data = res?.data || res;

        setCreatedCampaignId(campaignId);
        setCampaignType(typeParam);
        setCampaignName(data.campaign_name || "");
        setCampaignDescription(data.campaign_description || "");
        setDuration({ start: fromEpoch(data.start_date), end: fromEpoch(data.end_date) });
        setSelectedChannels(reverseMapChannels(data.channels || []));
        
        // Storing IDs for the AddDataSourceDialog prefill
        setSelectedObjectiveId(data.campaign_objective_id || "");
        setSelectedObjectiveTitle(data.campaign_objective_id || "Campaign Objective");
      } catch (err) {
        router.push("/campaign/create");
      } finally {
        setIsLoading(false);
      }
    };
    fetchDraft();
  }, [campaignId, typeParam]);

  // --- 2. AUDIENCE FETCHING & AUTO-SELECT ---
  const loadAudienceData = async (currentPage = 1) => {
    setIsLoadingAudience(true);
    try {
      const res: any = await fetchAudienceTasks(currentPage, 10, "all", campaignId || "");
      const items = res.items || res.data || (Array.isArray(res) ? res : []);
      setAudienceTasks(items);
      setTotalPages(Math.ceil((res.total || 0) / 10));

      // Auto-select list matching this campaign
      const preassigned = items.find((t: any) => t.campaign_id === campaignId);
      if (preassigned) {
        setTargetAudience([preassigned.task_id]);
        setSelectedAudienceDetails(preassigned);
      }
    } finally {
      setIsLoadingAudience(false);
    }
  };

  useEffect(() => {
    if (!isLoading) loadAudienceData(page);
  }, [isLoading, page]);

  // --- 3. REFRESH STATUS LOGIC (Synced with Audience/page.tsx) ---
  const handleRefreshTask = async () => {
    if (!targetAudience[0] || !selectedAudienceDetails) return;
    setIsRefreshing(true);
    try {
      const taskId = targetAudience[0];
      const dbId = selectedAudienceDetails.audience_task_id || selectedAudienceDetails.id || selectedAudienceDetails._id;
      
      const statusData = await getTaskStatus(taskId);
      
      let backendStatusString = "pending";
      let isSuccess = false;

      // Logic derived from your Audience page snippet
      if ((statusData.error && statusData.error.length > 0) || statusData.status === "error" || statusData.state === "FAILURE") {
         backendStatusString = "error";
      } else if (statusData.status === "success" || statusData.state === "SUCCESS") {
         backendStatusString = "connected"; 
         isSuccess = true;
      } else {
         backendStatusString = (statusData.status || statusData.state || "processing").toLowerCase();
      }

      let finalSize = selectedAudienceDetails.process_size;
      if (isSuccess) {
          const resultData = await getTaskResult(taskId);
          const result = resultData.result || resultData;
          finalSize = result.processed ?? result.total ?? finalSize;

          // PATCH the DB
          await updateAudienceTask(dbId, { 
            csv_status: backendStatusString, 
            process_size: finalSize,
            audience_size: finalSize
          });
      }

      await loadAudienceData(page);
    } catch (e) {
      console.error("Refresh Logic Failed", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  // --- 4. CALCULATIONS ---
  const getAudienceSize = () => parseInt(selectedAudienceDetails?.process_size || 0);
  const calculateCredits = () => getAudienceSize() * selectedChannels.reduce((sum, id) => sum + (channels.find(c => c.id === id)?.costPerUnit || 0), 0);

  const handleLaunch = async () => {
    if (!createdCampaignId || !targetAudience[0]) return;
    setIsLaunchSuccessOpen(true);
    setIsLaunchError(false);
    setLaunchStatus("Triggering campaign engine...");
    try {
      const endpoint = campaignType === "presales" ? `/gryd/db/object/pre_sales_campaign/${createdCampaignId}` : `/gryd/db/object/post_sales_campaign/${createdCampaignId}`;
      await api(endpoint, "PATCH", { 
        number_targeted: getAudienceSize(), 
        budget_allocated: calculateCredits(), 
        campaign_status: "Active", 
        campaign_user_source_id: targetAudience[0] 
      });
      const service =
        process.env.NEXT_PUBLIC_AUTOCRM_CAMPAIGN_TRIGGER_SERVICE_NAME ||
        "autocrm-campaign";
      await api(`/gryd/task/${service}/trigger_campaign`, "POST", {
        args: [],
        kwargs: {
          campaign_type:
            campaignType === "presales" ? "pre-sales" : "post-sales",
          campaign_id: createdCampaignId,
          disposition: "queued",
        },
      });
      setLaunchStatus("Campaign Launched Successfully!");
    } catch (err) {
      setIsLaunchError(true);
    }
  };

  if (isLoading) return <div className="flex h-screen items-center justify-center"><AILoader /></div>;

  return (
    <ProtectedRoute>
      {/* HEADER - 100% UI MATCH */}
      <div className="sticky top-0 z-30 w-full bg-white border-b px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.back()}><ArrowLeft className="h-5 w-5" /></Button>
          <h1 className="text-xl font-bold">Resume Campaign</h1>
        </div>
        <div className="text-sm text-muted-foreground">Step 2/2 — Audience & Review</div>
      </div>

      <div className="pb-24 w-full px-4 py-8 md:px-6 lg:px-8 bg-background min-h-screen">
        <div className="mx-auto max-w-5xl space-y-8">
          
          {/* TARGET AUDIENCE SECTION */}
          <Card className="shadow-sm border">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">Target Audience</CardTitle>
              <CardDescription>Select or upload your target audience</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label className="text-sm font-semibold">Select Audience</Label>
                  {targetAudience[0] && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={handleRefreshTask} 
                      disabled={isRefreshing} 
                      className="h-7 text-xs gap-1 text-primary"
                    >
                      <RotateCw className={cn("h-3 w-3", isRefreshing && "animate-spin")} /> Refresh Status
                    </Button>
                  )}
                </div>
                <Select
                  onValueChange={(val) => {
                    setTargetAudience([val]);
                    const task = audienceTasks.find(t => t.task_id === val);
                    if (task) setSelectedAudienceDetails(task);
                  }}
                  value={targetAudience[0] || ""}
                >
                  <SelectTrigger className="h-12"><SelectValue placeholder="Choose audience segment" /></SelectTrigger>
                  <SelectContent>
                    {audienceTasks.map((t) => (
                      <SelectItem key={t.task_id} value={t.task_id}>
                        <div className="flex items-center gap-2">
                           <span>{t.source_name || "Untitled"} ({t.process_size || 0} users)</span>
                           <Badge variant="outline" className="text-[10px] uppercase font-bold border-blue-200 bg-blue-50 text-blue-700">
                             {t.csv_status || 'connected'}
                           </Badge>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="relative py-2"><div className="absolute inset-0 flex items-center"><span className="w-full border-t" /></div><div className="relative flex justify-center text-xs uppercase"><span className="bg-white px-2 text-muted-foreground">OR</span></div></div>

              <div className="flex gap-4">
                <Button variant="outline" className="h-12 flex-1 border-dashed border-2 hover:border-primary" onClick={() => setIsUploadDialogOpen(true)}><Upload className="mr-2 h-4 w-4" /> Upload New Audience</Button>
                <Button variant="ghost" className="h-12 flex-1"><Download className="mr-2 h-4 w-4" /> Download Template</Button>
              </div>
            </CardContent>
          </Card>

          {/* REVIEW & CONFIRM SECTION - 100% UI MATCH */}
          <Card className="shadow-sm border">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">Review & Confirm</CardTitle>
              <CardDescription>Verify all details before launching.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              
              <div className="space-y-4">
                <div className="bg-slate-50/50 rounded-lg p-6 space-y-4 text-sm border max-w-md">
                   {[
                     { label: "Title:", val: campaignName },
                     { label: "Objective:", val: selectedObjectiveTitle },
                     { label: "Start:", val: duration.start },
                     { label: "End:", val: duration.end }
                   ].map(item => (
                     <div key={item.label} className="flex justify-between items-center gap-8">
                        <span className="text-muted-foreground whitespace-nowrap">{item.label}</span>
                        <span className="font-semibold text-right">{item.val}</span>
                     </div>
                   ))}
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="font-semibold text-sm">Selected Channels</h3>
                <div className="flex gap-2">
                  {selectedChannels.map(c => (
                    <Badge key={c} className="bg-[#F3E8FF] text-[#7E22CE] hover:bg-[#E9D5FF] capitalize border-none px-4 py-1">{c}</Badge>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="font-semibold text-sm">Cost Analysis</h3>
                <div className="space-y-3">
                  {selectedChannels.map(id => {
                    const ch = channels.find(c => c.id === id);
                    const size = getAudienceSize();
                    return (
                      <div key={id} className="border rounded-xl p-5 bg-white">
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-bold text-base capitalize">{id}</span>
                          <span className="font-bold text-base">{(size * (ch?.costPerUnit || 0)).toLocaleString()} credits</span>
                        </div>
                        <div className="flex justify-between items-center text-xs text-muted-foreground">
                          <span>Audience: <span className="text-slate-900 font-medium">{selectedAudienceDetails?.source_name || "No Audience Selected"}</span></span>
                          <div className="flex gap-4">
                             <span>Size: {size}</span>
                             <span>Credits per message: {ch?.costPerUnit}</span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div className="p-5 bg-slate-50 border rounded-xl flex justify-between items-center">
                    <span className="font-bold text-lg">Total Credits Required</span>
                    <span className="font-bold text-lg">{calculateCredits().toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </CardContent>
            
            <CardFooter className="flex justify-end gap-3 pt-6 pb-6 border-t bg-slate-50/30">
               <Button variant="outline" className="bg-white" onClick={() => router.push("/")}>Discard Changes</Button>
               <Button className="bg-[#3D0C8A] hover:bg-[#2d0966] text-white px-10" onClick={handleLaunch}>Launch Now</Button>
            </CardFooter>
          </Card>

          <Button variant="ghost" onClick={() => router.back()} className="text-muted-foreground hover:bg-transparent p-0"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Setup</Button>
        </div>
      </div>

      {/* MODAL - PREFILLED WITH CAMPAIGN DATA */}
      <AddDataSourceDialog 
        isOpen={isUploadDialogOpen} 
        onClose={() => setIsUploadDialogOpen(false)} 
        prefilledData={{ 
          category: campaignType === "presales" ? "pre-sales" : "post-sales", 
          objectiveId: selectedObjectiveId,
          campaignId: createdCampaignId || undefined 
        }} 
        onSave={() => loadAudienceData(page)} 
      />

      <Dialog open={isLaunchSuccessOpen} onOpenChange={setIsLaunchSuccessOpen}>
        <DialogContent className="sm:max-w-md text-center">
            <div className={cn("mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full", isLaunchError ? "bg-red-100" : "bg-green-100")}>
              {isLaunchError ? <X className="text-red-600" /> : <Check className="text-green-600" />}
            </div>
            <DialogTitle>{isLaunchError ? "Error" : "Success"}</DialogTitle>
            <DialogDescription>{launchStatus}</DialogDescription>
            <Button className="mt-4" onClick={() => router.push("/")} disabled={!launchStatus.includes("Successfully")}>Go to Dashboard</Button>
        </DialogContent>
      </Dialog>
    </ProtectedRoute>
  );
}

export default function ResumeCampaignPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ResumeCampaignContent />
    </Suspense>
  );
}