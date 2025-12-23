"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

// Imports
import { fetchAudienceTasks } from "@/utils/api";
import { api } from "@/lib/api";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ObjectiveCard } from "@/components/campaign/objective-card";
import { PreviouslyUsedCampaigns } from "@/components/campaign/previously-used-campaigns";
import { AddDataSourceDialog } from "@/components/audience/add-data-source-dialog";
import { ProtectedRoute } from "@/components/protected-route";
import {
  MessageSquare,
  Mail,
  Phone,
  Sparkles,
  PartyPopper,
  Tag,
  Car,
  Wrench,
  Sun,
  Edit3,
  Check,
  Target,
  Users,
  Rocket,
  X,
  TrendingUp,
  Heart,
  Gift,
  AlertCircle,
  RefreshCw,
  Image as ImageIcon,
  Info,
  ArrowRight,
  Upload,
  Database,
  FileText
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AILoader } from "@/components/ui/ai-loader";

// --- HELPERS & CONSTANTS ---

const getObjectiveIcon = (objectiveId: string, title: string) => {
  const id = objectiveId?.toLowerCase() || "";
  const titleLower = title?.toLowerCase() || "";

  if (id.includes("car") || id.includes("launch") || titleLower.includes("car") || titleLower.includes("launch")) return <Car className="h-6 w-6" />;
  if (id.includes("festive") || id.includes("sale") || titleLower.includes("festive") || titleLower.includes("sale")) return <PartyPopper className="h-6 w-6" />;
  if (id.includes("stock") || id.includes("clearance") || titleLower.includes("stock") || titleLower.includes("clearance")) return <Tag className="h-6 w-6" />;
  if (id.includes("test") || id.includes("drive") || titleLower.includes("test") || titleLower.includes("drive")) return <TrendingUp className="h-6 w-6" />;
  if (id.includes("service") || titleLower.includes("service") || titleLower.includes("maintenance")) return <Wrench className="h-6 w-6" />;
  if (id.includes("warranty") || titleLower.includes("warranty")) return <ShieldCheck className="h-6 w-6" />;
  if (id.includes("insurance") || titleLower.includes("insurance")) return <FileText className="h-6 w-6" />;
  if (id === "custom" || titleLower.includes("custom")) return <Edit3 className="h-6 w-6" />;
  return <Target className="h-6 w-6" />;
};

const ShieldCheck = (props: any) => (
  <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    <path d="m9 12 2 2 4-4" />
  </svg>
)

const channels = [
  { id: "whatsapp", name: "WhatsApp", icon: <MessageSquare className="h-6 w-6" /> },
  { id: "email", name: "Email", icon: <Mail className="h-6 w-6" /> },
  { id: "voice", name: "Voice", icon: <Phone className="h-6 w-6" /> },
];

const languageOptions = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi" },
  { value: "mr", label: "Marathi" },
  { value: "ta", label: "Tamil" },
  { value: "te", label: "Telugu" },
  { value: "kn", label: "Kannada" },
  { value: "bn", label: "Bengali" },
  { value: "gu", label: "Gujarati" },
];

const toEpoch = (dateStr: string) => dateStr ? Math.floor(new Date(dateStr).getTime() / 1000) : 0;

const mapChannels = (selectedIds: string[]) => {
  const map: Record<string, string> = { whatsapp: "whatsapp_chat", email: "email", voice: "voice_phone" };
  return selectedIds.map((c) => map[c] || c);
};

const mapLanguage = (code: string) => {
  const map: Record<string, string> = { en: "english", hi: "hindi", mr: "marathi", ta: "tamil", te: "telugu", kn: "kannada", bn: "bengali", gu: "gujarati" };
  return map[code] || "english";
};

// --- MAIN COMPONENT ---

function CampaignCreateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Steps & Data
  const [creationStep, setCreationStep] = useState<"details" | "audience">("details");
  const [createdCampaignId, setCreatedCampaignId] = useState<string | null>(null);
  const [campaignType, setCampaignType] = useState<"presales" | "postsales" | "">("");
  
  // Objectives
  const [selectedObjective, setSelectedObjective] = useState("");
  const [selectedObjectiveData, setSelectedObjectiveData] = useState<any>(null);
  const [customObjective, setCustomObjective] = useState("");
  const [preSalesObjectives, setPreSalesObjectives] = useState<any[]>([]);
  const [fetchedPostSalesObjectives, setFetchedPostSalesObjectives] = useState<any[]>([]);
  
  // Campaign Details
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPostingCampaign, setIsPostingCampaign] = useState(false);
  const [campaignData, setCampaignData] = useState<any>(null);
  const [campaignName, setCampaignName] = useState("");
  const [campaignDescription, setCampaignDescription] = useState("");
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [duration, setDuration] = useState({ start: "", end: "" });
  const [campaignTitle, setCampaignTitle] = useState("");
  const [tone, setTone] = useState("");
  const [callToAction, setCallToAction] = useState("");
  const [language, setLanguage] = useState("en");
  
  // Audience Data
  const [targetAudience, setTargetAudience] = useState<string[]>([]);
  const [audienceTasks, setAudienceTasks] = useState<any[]>([]);
  const [isLoadingAudience, setIsLoadingAudience] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);

  // Custom Attributes
  const [carModel, setCarModel] = useState("");
  const [launchDate, setLaunchDate] = useState("");
  
  // UI States
  const [activeTab, setActiveTab] = useState("setup");
  const [isLoadingObjectives, setIsLoadingObjectives] = useState(false);
  const [isObjectiveDetailsOpen, setIsObjectiveDetailsOpen] = useState(false);
  const [isLaunchSuccessOpen, setIsLaunchSuccessOpen] = useState(false);
  const [launchStatus, setLaunchStatus] = useState("");
  const [isLaunchError, setIsLaunchError] = useState(false);

  // --- Initialization ---

  useEffect(() => {
    const isNew = searchParams.get("new");
    if (isNew === "true") {
      localStorage.removeItem("campaignFormData");
      setCampaignType("");
      setCreatedCampaignId(null);
      setCreationStep("details");
      router.replace("/campaign/create", { scroll: false });
    }
  }, [searchParams, router]);

  useEffect(() => {
    setSelectedObjective("");
    setCustomObjective("");
    setCampaignData(null);
    setCreatedCampaignId(null);
    setCreationStep("details");
    setTargetAudience([]);
    setAudienceTasks([]);
  }, [campaignType]);

  // Fetch Audience Tasks
  const loadAudienceData = async () => {
    setIsLoadingAudience(true);
    try {
        const res = await fetchAudienceTasks();
        setAudienceTasks(res.items || []);
    } catch (e) {
        console.error("Failed to fetch audience", e);
    } finally {
        setIsLoadingAudience(false);
    }
  };

  useEffect(() => {
    if (creationStep === "audience") {
        loadAudienceData();
    }
  }, [creationStep]);

  // Fetch Objectives
  useEffect(() => {
    const fetchObjectives = async () => {
      setIsLoadingObjectives(true);
      try {
        const typeParam = campaignType === "presales" ? "pre-sales" : "post-sales";
        const response = await api(`/gryd/db/objects/campaign_objective?campaign_type=${typeParam}`, "GET");
        const data = Array.isArray(response) ? response : response.data || [];
        
        const mapped = data.map((obj: any, idx: number) => {
            const id = obj.campaign_objective_id || obj.id || `obj-${idx}`;
            const title = obj.campaign_objective_name || obj.title || obj.name || "Objective";
            return {
                id: id,
                title: title,
                campaignSubType: obj.campaign_sub_type || "General",
                icon: getObjectiveIcon(id, title),
                fullData: obj
            };
        });

        mapped.push({ 
            id: "custom", 
            title: "Custom Objective", 
            campaignSubType: "Flexible",
            icon: <Edit3 className="h-6 w-6"/>, 
            fullData: null 
        });

        if (campaignType === "presales") setPreSalesObjectives(mapped);
        else setFetchedPostSalesObjectives(mapped);

      } catch(e) { 
        console.error("Error fetching objectives:", e); 
      } finally {
        setIsLoadingObjectives(false);
      }
    };

    if (campaignType) fetchObjectives();
  }, [campaignType]);

  // --- Logic ---

  const handleGenerateCampaign = async () => {
    setIsGenerating(true);
    try {
      const objectivesList = campaignType === "presales" ? preSalesObjectives : fetchedPostSalesObjectives;
      const objectiveText = selectedObjective === "custom" ? customObjective : objectivesList.find(o => o.id === selectedObjective)?.title || "";
      
      let enhancedText = objectiveText;
      if (carModel && selectedObjective.includes("launch")) enhancedText += ` for ${carModel}`;

      const customObjects: Record<string, any> = {};
      selectedObjectiveData?.custom_attributes?.forEach((attr: any) => {
         if (attr.attribute_name && attr.attribute_value) customObjects[attr.attribute_name] = attr.attribute_value;
      });
      if (carModel) customObjects["Car Model"] = carModel;
      if (launchDate) customObjects["Launch Date"] = launchDate;

      const payload = {
        args: [campaignType === "presales" ? "pre-sale" : "post-sale", enhancedText],
        kwargs: {
          dealership_idea: {
            languages: [languageOptions.find((l) => l.value === language)?.label || "English"],
            campaign_offer: campaignDescription,
            custom_objects: customObjects,
          },
        },
      };

      const data = await api("/gryd/api/autocrm-agent/generate_campaign_idea", "POST", payload);
      
      const today = new Date();
      const nextWeek = new Date(today);
      nextWeek.setDate(today.getDate() + 7);
      const formatDate = (d: Date) => {
         const offset = d.getTimezoneOffset();
         const local = new Date(d.getTime() - (offset * 60 * 1000));
         return local.toISOString().split("T")[0];
      };

      setCampaignData({
        name: data.campaign_name,
        description: data.campaign_description,
        campaignTitle: data.campaign_tagline,
        tone: data.campaign_tone,
        callToAction: data.ctas?.[0] || "Learn More",
        language: data.languages?.[0] || "English",
        campaignOffer: data.campaign_offer,
        urgencyHook: data.urgency_hook,
      });

      setCampaignName(data.campaign_name);
      setCampaignDescription(data.campaign_description);
      setCampaignTitle(data.campaign_tagline);
      setTone(data.campaign_tone);
      setCallToAction(data.ctas?.[0] || "Learn More");
      setLanguage(data.languages?.[0] || "en");
      setDuration({ start: formatDate(today), end: formatDate(nextWeek) });
      setSelectedChannels(["voice", "whatsapp", "email"]); 

    } catch (error) {
      console.error(error);
      alert("Failed to generate campaign. Check console.");
    } finally {
      setIsGenerating(false);
    }
  };

  const calculateCredits = () => {
    const totalAudience = audienceTasks
      .filter((task) => targetAudience.includes(task.task_id))
      .reduce((sum, task) => sum + (parseInt(task.process_size || 0)), 0);

    const whatsappCredits = selectedChannels.includes("whatsapp") ? totalAudience * 5 : 0;
    const emailCredits = selectedChannels.includes("email") ? totalAudience * 1 : 0;
    const voiceCredits = selectedChannels.includes("voice") ? totalAudience * 10 : 0;

    return whatsappCredits + emailCredits + voiceCredits;
  };

  const getTotalReach = () => {
    return audienceTasks
      .filter((task) => targetAudience.includes(task.task_id))
      .reduce((sum, task) => sum + (parseInt(task.process_size || 0)), 0);
  };

  const handleProceed = async () => {
    if (!campaignName || !duration.start || !duration.end) {
        alert("Please fill in Campaign Name and Duration.");
        return;
    }
    
    setIsPostingCampaign(true);

    const commonPayload = {
        campaign_name: campaignName,
        campaign_description: campaignDescription,
        campaign_status: "Draft",
        start_date: toEpoch(duration.start),
        end_date: toEpoch(duration.end),
        channels: mapChannels(selectedChannels),
        languages: [mapLanguage(language)],
        campaign_offer: campaignData?.campaignOffer || campaignDescription,
        urgency_hook: [campaignData?.urgencyHook || ""],
        ctas: [callToAction],
        number_targeted: 0,
        budget_allocated: 0, 
        campaign_objective_id: selectedObjective === "custom" ? customObjective : selectedObjectiveData?.title || selectedObjective,
        campaign_sub_type: selectedObjectiveData?.campaignSubType || "General",
        created: Math.floor(Date.now() / 1000),
        updated: Math.floor(Date.now() / 1000),
        campaign_user_source: "file",
    };
console.log("Common Payload:", commonPayload);
    try {
        let endpoint = "";
        let finalPayload = {};

        if (campaignType === "presales") {
            endpoint = "/gryd/db/object/pre_sales_campaign";
            finalPayload = {
                ...commonPayload,
                campaign_type: "pre-sales",
                dealership_id: "nexa-delhi-south-nexa-dealer-group-north-india",
                region_id: "north-india",
                dealer_name: "NEXA Delhi South",
                supported_brands: ["NEXA"],
            };
        } else {
            endpoint = "/gryd/db/object/post_sales_campaign";
            finalPayload = {
                ...commonPayload,
                campaign_type: "post-sales",
                workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
                dealership_id: "nexa-delhi-south-nexa-dealer-group-north-india",
                campaign_objective_type: ["lead volume"],
            };
        }

        const res = await api(endpoint, "POST", finalPayload);
        const newId = res?.data?.id || res?.id || res?.campaign_id;
        if (!newId) throw new Error("ID not returned");

        setCreatedCampaignId(newId);
        setCreationStep("audience");
        setTimeout(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }), 100);

    } catch (err) {
        console.error("Proceed failed", err);
        alert("Failed to save draft.");
    } finally {
        setIsPostingCampaign(false);
    }
  };

  const handleLaunch = async () => {
      if (!createdCampaignId) { alert("Error: Campaign ID missing."); return; }
      setIsLaunchSuccessOpen(true);
      setIsLaunchError(false);
      setLaunchStatus("Finalizing audience data...");

      try {
        const totalReach = getTotalReach();
        const budget = calculateCredits();
        
        const patchEndpoint = campaignType === "presales" 
            ? `/gryd/db/object/pre_sales_campaign/${createdCampaignId}`
            : `/gryd/db/object/post_sales_campaign/${createdCampaignId}`;

        await api(patchEndpoint, "PATCH", {
            number_targeted: totalReach,
            budget_allocated: budget,
            campaign_status: "Active"
        });

        setLaunchStatus("Triggering campaign engine...");
        const taskType = campaignType === "presales" ? "pre-sales" : "post-sales";
        
        await api("/gryd/task/autocrm-campaign/trigger_campaign", "POST", {
            args: [],
            kwargs: { campaign_type: taskType, campaign_id: createdCampaignId }
        });

        setLaunchStatus("Campaign launched successfully!");
        setTimeout(() => localStorage.removeItem("campaignFormData"), 1000);

      } catch (err) {
          console.error("Launch error", err);
          setIsLaunchError(true);
          setLaunchStatus("Failed to launch. Please retry.");
      }
  };

  const objectives = campaignType === "presales" ? preSalesObjectives : fetchedPostSalesObjectives;

  return (
    <ProtectedRoute>
      <div className="pb-24">
        {/* LAUNCH STATUS MODAL */}
        <Dialog open={isLaunchSuccessOpen} onOpenChange={(o) => { if(!o && !isLaunchError && launchStatus !== "Campaign launched successfully!") return; setIsLaunchSuccessOpen(o); }}>
          <DialogContent className="sm:max-w-md text-center" onInteractOutside={(e) => { if (!isLaunchError && launchStatus !== "Campaign launched successfully!") e.preventDefault(); }}>
            <DialogHeader>
              <div className={cn("mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full transition-colors", isLaunchError ? "bg-red-100" : "bg-green-100")}>
                {isLaunchError ? <AlertCircle className="h-6 w-6 text-red-600"/> : <Rocket className="h-6 w-6 text-green-600"/>}
              </div>
              <DialogTitle className="text-center">{isLaunchError ? "Error" : "Launching Campaign"}</DialogTitle>
              <DialogDescription className="text-center">{isLaunchError ? "Something went wrong." : launchStatus}</DialogDescription>
            </DialogHeader>
            <div className="flex justify-center py-4">
                {isLaunchError ? <X className="h-10 w-10 text-red-500 animate-in zoom-in"/> : launchStatus.includes("success") ? <Check className="h-10 w-10 text-green-500 animate-in zoom-in"/> : <RefreshCw className="h-10 w-10 text-primary animate-spin"/>}
            </div>
            <DialogFooter className="sm:justify-center">
              {isLaunchError ? <Button variant="outline" onClick={() => setIsLaunchSuccessOpen(false)}>Close & Retry</Button> : <Button disabled={!launchStatus.includes("success")} onClick={() => router.push("/")}>Go to Dashboard</Button>}
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* REVIEW DETAILS DIALOG */}
        <Dialog open={isObjectiveDetailsOpen} onOpenChange={setIsObjectiveDetailsOpen}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                         <Edit3 className="h-5 w-5 text-primary" /> Review Campaign Details
                    </DialogTitle>
                    <DialogDescription>Confirm objective details and fill in required attributes.</DialogDescription>
                </DialogHeader>
                <div className="space-y-6 py-4">
                    {/* CAMPAIGN INFO */}
                    {selectedObjectiveData && (
                        <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
                            <div className="p-6 space-y-4">
                                <div className="flex items-center gap-2 mb-2">
                                    <Info className="h-4 w-4 text-primary" />
                                    <h3 className="font-semibold leading-none tracking-tight">Campaign Information</h3>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-1">
                                        <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Campaign Name</Label>
                                        <div className="font-medium text-base">{selectedObjectiveData.campaign_objective_name || selectedObjectiveData.title}</div>
                                    </div>
                                    <div className="space-y-1">
                                        <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Type / Sub-Type</Label>
                                        <div className="font-medium text-base flex items-center gap-2">
                                            <Badge variant="outline" className="capitalize">{campaignType}</Badge>
                                            <span>/</span>
                                            <span>{selectedObjectiveData.campaign_sub_type || "General"}</span>
                                        </div>
                                    </div>
                                    <div className="space-y-1 md:col-span-2">
                                        <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Description</Label>
                                        <div className="text-sm text-foreground/80 leading-relaxed bg-muted/30 p-3 rounded-md">
                                            {selectedObjectiveData.campaign_objective_description || "No description available."}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                    {/* ATTRIBUTES */}
                    <div className="space-y-4">
                         <div className="flex items-center gap-2 pb-2 border-b">
                             <Edit3 className="h-4 w-4 text-primary" />
                             <h3 className="font-semibold leading-none tracking-tight">Required Attributes</h3>
                         </div>
                         {(selectedObjective === "new-car-launch" || selectedObjective.includes("launch")) && (
                             <div className="grid grid-cols-2 gap-4 bg-muted/30 p-4 rounded-md">
                                <div className="space-y-2"><Label>Car Model <span className="text-destructive">*</span></Label><Input value={carModel} onChange={e=>setCarModel(e.target.value)} placeholder="e.g. Grand Vitara"/></div>
                                <div className="space-y-2"><Label>Launch Date <span className="text-destructive">*</span></Label><Input type="date" value={launchDate} onChange={e=>setLaunchDate(e.target.value)} /></div>
                             </div>
                        )}
                        {selectedObjectiveData?.custom_attributes?.map((attr: any, idx: number) => (
                            <div key={idx} className="space-y-2">
                                 <Label>{attr.attribute_name}</Label>
                                 <Input placeholder={`Enter ${attr.attribute_name}`} value={attr.attribute_value || ""} onChange={(e) => { const u = [...selectedObjectiveData.custom_attributes]; u[idx].attribute_value = e.target.value; setSelectedObjectiveData({...selectedObjectiveData, custom_attributes: u}); }} />
                            </div>
                        ))}
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={() => setIsObjectiveDetailsOpen(false)}>Cancel</Button>
                    <Button onClick={() => { setIsObjectiveDetailsOpen(false); handleGenerateCampaign(); }}><Sparkles className="mr-2 h-4 w-4"/> Generate Campaign</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
        
        {/* ADD DATA SOURCE DIALOG - Passed with Prefilled Data */}
        <AddDataSourceDialog 
            isOpen={isUploadDialogOpen} 
            onClose={() => setIsUploadDialogOpen(false)} 
            prefilledData={{
                category: campaignType === "presales" ? "pre_sales" : "post_sales",
                objectiveId: selectedObjective,
                campaignId: createdCampaignId || undefined
            }}
            onSave={(dataSource) => {
                loadAudienceData(); // Refresh list 
                // Auto-select the newly created audience task
                if (dataSource.connectionDetails?.taskId) {
                    setTargetAudience(prev => [...prev, dataSource.connectionDetails.taskId]);
                }
            }}
        />

        <div className="w-full px-4 py-8 md:px-6 lg:px-8">
          <div className="mx-auto max-w-5xl space-y-8">
            
            {/* STEP 0: CAMPAIGN TYPE SELECTION */}
            {!campaignType && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4">
                <div className="text-center space-y-3">
                    <h1 className="text-4xl font-bold tracking-tight">Create Campaign</h1>
                    <p className="text-lg text-muted-foreground">Choose your campaign type to get started</p>
                </div>
                <Card className="shadow-xl border-2">
                    <CardContent className="p-8">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <Card className="cursor-pointer border-2 hover:border-primary p-8 flex flex-col items-center transition-all hover:scale-[1.02]" onClick={() => setCampaignType("presales")}>
                                <div className="p-4 rounded-full bg-primary/10 mb-6"><Target className="h-16 w-16 text-primary" /></div>
                                <h3 className="text-2xl font-bold mb-2">Pre-Sales</h3>
                                <p className="text-center text-muted-foreground">Generate leads and acquire new customers</p>
                            </Card>
                            <Card className="cursor-pointer border-2 hover:border-primary p-8 flex flex-col items-center transition-all hover:scale-[1.02]" onClick={() => setCampaignType("postsales")}>
                                <div className="p-4 rounded-full bg-primary/10 mb-6"><Users className="h-16 w-16 text-primary" /></div>
                                <h3 className="text-2xl font-bold mb-2">Post-Sales</h3>
                                <p className="text-center text-muted-foreground">Engage existing customers and drive service</p>
                            </Card>
                        </div>
                    </CardContent>
                </Card>
              </div>
            )}

            {/* CAMPAIGN MANAGER */}
            {campaignType && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
                 <div className="flex justify-between items-center">
                    <div><h1 className="text-3xl font-bold">Campaign Manager</h1><p className="text-muted-foreground capitalize">{campaignType} Campaign</p></div>
                    <Button variant="outline" onClick={() => setCampaignType("")} className="gap-2"><X className="h-4 w-4"/> Change Type</Button>
                 </div>

                 {/* OBJECTIVES */}
                 <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                    <CardHeader><CardTitle className="text-2xl flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary"/> Campaign Objective</CardTitle></CardHeader>
                    <CardContent>
                        <Tabs value={activeTab} onValueChange={setActiveTab}>
                            <TabsList className="mb-4 w-full justify-start h-auto p-1"><TabsTrigger value="setup" className="px-6 py-2">Objectives</TabsTrigger><TabsTrigger value="previous" className="px-6 py-2">Previously Used</TabsTrigger></TabsList>
                            <TabsContent value="setup" className="space-y-4">
                                {isLoadingObjectives ? (
                                    <div className="flex items-center justify-center py-12">
                                        <RefreshCw className="h-8 w-8 animate-spin text-primary mr-2" />
                                        <span className="text-muted-foreground text-lg">Loading objectives...</span>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                                        {objectives.map((obj) => (
                                            <ObjectiveCard key={obj.id} {...obj} selected={selectedObjective === obj.id} onSelect={() => {
                                                setSelectedObjective(obj.id);
                                                setSelectedObjectiveData(obj.fullData || null);
                                                setCampaignData(null); setCreatedCampaignId(null); setCreationStep("details");
                                                if(obj.id !== 'custom') setIsObjectiveDetailsOpen(true);
                                            }}/>
                                        ))}
                                    </div>
                                )}
                                {selectedObjective === "custom" && <div className="mt-4 flex gap-2"><Input placeholder="Describe your custom objective..." value={customObjective} onChange={e=>setCustomObjective(e.target.value)} className="h-12"/><Button onClick={handleGenerateCampaign} className="h-12 px-6">Generate</Button></div>}
                            </TabsContent>
                            <TabsContent value="previous"><PreviouslyUsedCampaigns campaignType={campaignType} onReuseCampaign={()=>{}}/></TabsContent>
                        </Tabs>
                    </CardContent>
                 </Card>
                
                 {isGenerating && <Card className="py-12"><AILoader /></Card>}

                 {!isGenerating && campaignData && (
                     <div className="space-y-6 animate-in fade-in duration-500">
                        {/* DETAILS FORM */}
                        <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                            <CardHeader><CardTitle>Campaign Attributes</CardTitle><CardDescription>Review generated content</CardDescription></CardHeader>
                            <CardContent className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2"><Label>Campaign Name</Label><Input value={campaignName} onChange={e=>setCampaignName(e.target.value)}/></div>
                                    <div className="space-y-2"><Label>Campaign Title</Label><Input value={campaignTitle} onChange={e=>setCampaignTitle(e.target.value)}/></div>
                                </div>
                                <div className="space-y-2"><Label>Description / Offer</Label><Textarea rows={3} value={campaignDescription} onChange={e=>setCampaignDescription(e.target.value)}/></div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2"><Label>Start Date</Label><Input type="date" value={duration.start} onChange={e=>setDuration({...duration, start:e.target.value})}/></div>
                                    <div className="space-y-2"><Label>End Date</Label><Input type="date" value={duration.end} onChange={e=>setDuration({...duration, end:e.target.value})}/></div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="space-y-2"><Label>Tone</Label><Input value={tone} onChange={e => setTone(e.target.value)} /></div>
                                    <div className="space-y-2"><Label>Call to Action</Label><Input value={callToAction} onChange={e => setCallToAction(e.target.value)} /></div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                            <CardHeader><CardTitle>Channels</CardTitle><CardDescription>Channels auto-optimized for this campaign</CardDescription></CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-3 gap-4">
                                    {channels.map((ch) => (
                                        <Card key={ch.id} className={cn("border-2 transition-all", selectedChannels.includes(ch.id) ? "border-primary bg-primary/5 shadow-sm" : "opacity-50")}>
                                            <CardContent className="flex flex-col items-center p-4">
                                                <div className={cn("mb-2", selectedChannels.includes(ch.id) ? "text-primary" : "text-muted-foreground")}>{ch.icon}</div>
                                                <span className="font-semibold">{ch.name}</span>
                                                {selectedChannels.includes(ch.id) && <Badge className="mt-2 bg-green-600">Active</Badge>}
                                            </CardContent>
                                        </Card>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>
                        
                        {creationStep === "details" && (
                            <div className="flex justify-end pt-4 pb-12">
                                <Button size="lg" onClick={handleProceed} disabled={isPostingCampaign} className="gap-2 px-8 text-lg h-14 shadow-lg hover:shadow-xl transition-all">
                                    {isPostingCampaign ? <><RefreshCw className="animate-spin h-5 w-5 mr-2"/> Saving Draft...</> : <>Proceed to Audience Selection <ArrowRight className="w-5 h-5 ml-2"/></>}
                                </Button>
                            </div>
                        )}

                        {/* STEP 2: DYNAMIC AUDIENCE SELECTION */}
                        {creationStep === "audience" && (
                             <div className="space-y-6 animate-in fade-in slide-in-from-bottom-8 duration-700">
                                <Card className="shadow-xl border-2 border-l-4 border-l-emerald-500 border-emerald-100">
                                    <CardHeader className="flex flex-row items-center justify-between">
                                        <div>
                                            <CardTitle className="text-2xl text-emerald-800 flex items-center gap-2"><Users className="h-6 w-6"/> Select Target Audience</CardTitle>
                                            <CardDescription>Select from existing lists or upload a new CSV</CardDescription>
                                        </div>
                                        <Button onClick={() => setIsUploadDialogOpen(true)} className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white shadow-md">
                                            <Upload className="h-4 w-4" /> Upload New List
                                        </Button>
                                    </CardHeader>
                                    <CardContent>
                                        {isLoadingAudience ? (
                                            <div className="flex justify-center py-12">
                                                <div className="text-center">
                                                    <RefreshCw className="animate-spin h-8 w-8 text-emerald-600 mx-auto mb-2"/>
                                                    <p className="text-muted-foreground">Fetching audience lists...</p>
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
                                                {audienceTasks.length === 0 ? (
                                                    <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg bg-slate-50 dark:bg-slate-900/50">
                                                        <Database className="h-12 w-12 mx-auto mb-3 opacity-20"/>
                                                        <h3 className="font-semibold text-lg">No audience lists found</h3>
                                                        <p className="mb-4">Upload a CSV file to get started.</p>
                                                        <Button variant="outline" onClick={() => setIsUploadDialogOpen(true)}>Upload CSV</Button>
                                                    </div>
                                                ) : (
                                                    audienceTasks.map((task) => (
                                                        <div key={task.task_id} 
                                                            className={cn("cursor-pointer border-2 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between hover:shadow-md transition-all", 
                                                                targetAudience.includes(task.task_id) ? "border-emerald-500 bg-emerald-50" : "border-muted bg-card hover:border-emerald-200"
                                                            )}
                                                            onClick={() => setTargetAudience(prev => prev.includes(task.task_id) ? prev.filter(p => p !== task.task_id) : [...prev, task.task_id])}
                                                        >
                                                            <div className="flex items-start gap-4 mb-3 sm:mb-0">
                                                                <div className={cn("h-10 w-10 rounded-full flex items-center justify-center shrink-0 transition-colors", targetAudience.includes(task.task_id) ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-500")}>
                                                                    <FileText className="h-5 w-5" />
                                                                </div>
                                                                <div>
                                                                    <p className="font-bold text-lg leading-tight text-foreground">{task.source_name || task.audience_name || "Untitled List"}</p>
                                                                    <div className="flex flex-wrap gap-2 mt-2">
                                                                        {task.tags && Array.isArray(task.tags) && task.tags.map((tag: string, i: number) => (
                                                                            <Badge key={i} variant="secondary" className="text-xs px-2 py-0.5 bg-slate-200 text-slate-700 hover:bg-slate-300">{tag}</Badge>
                                                                        ))}
                                                                    </div>
                                                                    <p className="text-xs text-muted-foreground mt-1 font-mono">ID: {task.task_id}</p>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-4 justify-between sm:justify-end w-full sm:w-auto mt-2 sm:mt-0 pl-14 sm:pl-0">
                                                                <div className="text-right mr-4">
                                                                    <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Records</p>
                                                                    <p className="font-bold text-xl">{parseInt(task.process_size || 0).toLocaleString()}</p>
                                                                </div>
                                                                {targetAudience.includes(task.task_id) ? 
                                                                    <Badge className="bg-emerald-600 hover:bg-emerald-700 h-8 px-3 text-sm">Selected</Badge> : 
                                                                    <Badge variant="outline" className="h-8 px-3 text-sm">Select</Badge>
                                                                }
                                                            </div>
                                                        </div>
                                                    ))
                                                )}
                                            </div>
                                        )}
                                        
                                        <div className="mt-6 p-6 bg-slate-50 dark:bg-slate-900 rounded-xl border flex flex-col sm:flex-row justify-between items-center gap-4">
                                            <div>
                                                <p className="text-sm text-muted-foreground uppercase font-bold tracking-wider">Total Reach</p>
                                                <p className="text-3xl font-bold text-emerald-700">{getTotalReach().toLocaleString()}</p>
                                            </div>
                                            <div className="text-right">
                                                 <p className="text-sm text-muted-foreground uppercase font-bold tracking-wider">Est. Cost (Credits)</p>
                                                 <p className="text-2xl font-bold text-foreground">{calculateCredits().toLocaleString()}</p>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>

                                <div className="flex justify-between pt-4 pb-12">
                                    <Button variant="ghost" onClick={() => { setCreationStep("details"); setCreatedCampaignId(null); }} className="text-muted-foreground hover:text-foreground">
                                        Back to Details
                                    </Button>
                                    <Button size="lg" onClick={handleLaunch} className="gap-2 px-10 bg-emerald-600 hover:bg-emerald-700 h-14 text-lg shadow-xl shadow-emerald-200 dark:shadow-none transition-all hover:scale-105">
                                        <Rocket className="h-5 w-5"/> Launch Campaign Now
                                    </Button>
                                </div>
                             </div>
                        )}
                     </div>
                 )}
              </div>
            )}
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

export default function CampaignCreatePage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <CampaignCreateContent />
    </Suspense>
  );
}