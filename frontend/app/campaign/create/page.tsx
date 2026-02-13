"use client";

import { useState, useEffect, Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";

// Imports
import { fetchAudienceTasks ,getDealershipId} from "@/utils/api";
import { api } from "@/lib/api";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ObjectiveCard } from "@/components/campaign/objective-card";
import { PreviouslyUsedCampaigns } from "@/components/campaign/previously-used-campaigns";
import { AddDataSourceDialog } from "@/components/audience/add-data-source-dialog";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";
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
  FileText,
  Calendar,
  CreditCard,
  CalendarClock,
  ArrowLeft,
  Download,
  MessageSquareText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AILoader } from "@/components/ui/ai-loader";
import { Separator } from "@/components/ui/separator";

// --- HELPERS & CONSTANTS ---

const getObjectiveIcon = (objectiveId: string, title: string) => {
  const id = objectiveId?.toLowerCase() || "";
  const titleLower = title?.toLowerCase() || "";

  if (
    id.includes("car") ||
    id.includes("launch") ||
    titleLower.includes("car") ||
    titleLower.includes("launch")
  )
    return <Car className="h-6 w-6" />;
  if (
    id.includes("festive") ||
    id.includes("sale") ||
    titleLower.includes("festive") ||
    titleLower.includes("sale")
  )
    return <PartyPopper className="h-6 w-6" />;
  if (
    id.includes("stock") ||
    id.includes("clearance") ||
    titleLower.includes("stock") ||
    titleLower.includes("clearance")
  )
    return <Tag className="h-6 w-6" />;
  if (
    id.includes("test") ||
    id.includes("drive") ||
    titleLower.includes("test") ||
    titleLower.includes("drive")
  )
    return <TrendingUp className="h-6 w-6" />;
  if (
    id.includes("service") ||
    titleLower.includes("service") ||
    titleLower.includes("maintenance")
  )
    return <Wrench className="h-6 w-6" />;
  if (id.includes("warranty") || titleLower.includes("warranty"))
    return <ShieldCheck className="h-6 w-6" />;
  if (id.includes("insurance") || titleLower.includes("insurance"))
    return <FileText className="h-6 w-6" />;
  if (id === "custom" || titleLower.includes("custom"))
    return <Edit3 className="h-6 w-6" />;
  return <Target className="h-6 w-6" />;
};

const ShieldCheck = (props: any) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" />
    <path d="m9 12 2 2 4-4" />
  </svg>
);

// Updated Channel Definitions with calculated cost factors
const channels = [
  {
    id: "whatsapp",
    name: "WhatsApp",
    icon: <MessageSquare className="h-6 w-6" />,
    costPerUnit: 2.5655,
  },
  {
    id: "email",
    name: "Email",
    icon: <Mail className="h-6 w-6" />,
    costPerUnit: 0.195,
  },
  {
    id: "voice",
    icon: <Phone className="h-6 w-6" />,
    costPerUnit: 8.56,
  },
  {
    id: "rcs",
    icon: <MessageSquareText className="h-6 w-6" />,
    costPerUnit: 0.9525,
  },
  {
    id: "sms",
    name: "SMS",
    icon: <MessageSquareText className="h-6 w-6" />, // Reusing icon for example
    costPerUnit: 0.12, // Example cost
  },
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

const toEpoch = (dateStr: string) =>
  dateStr ? Math.floor(new Date(dateStr).getTime() / 1000) : 0;

const mapChannels = (selectedIds: string[]) => {
  const map: Record<string, string> = {
    whatsapp: "whatsapp_chat",
    email: "email",
    voice: "voice_phone",
    rcs: "rcs_message",
    sms: "sms_message",
  };
  return selectedIds.map((c) => map[c] || c);
};

const mapLanguage = (code: string) => {
  const map: Record<string, string> = {
    en: "english",
    hi: "hindi",
    mr: "marathi",
    ta: "tamil",
    te: "telugu",
    kn: "kannada",
    bn: "bengali",
    gu: "gujarati",
  };
  return map[code] || "english";
};

// --- MAIN COMPONENT ---

function CampaignCreateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isDealershipSetupComplete } = useAuth();

  // Redirect if dealership setup is not complete
  useEffect(() => {
    if (isDealershipSetupComplete === false) {
      router.push("/dealership/update-details");
    }
  }, [isDealershipSetupComplete, router]);

  if (isDealershipSetupComplete === false) {
    return (
      <ProtectedRoute>
        <div className="flex items-center justify-center min-h-screen bg-slate-50/50">
          <div className="text-center space-y-4 max-w-md mx-auto p-6">
            <Alert className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <AlertDescription className="space-y-4">
                <div>
                  <p className="font-semibold text-lg mb-2 text-amber-900 dark:text-amber-100">
                    Profile Verification Required
                  </p>
                  <p className="text-sm text-amber-800 dark:text-amber-200">
                    To run a campaign, please verify and complete your dealership profile.
                  </p>
                </div>
                <Button
                  onClick={() => router.push("/dealership/update-details")}
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                >
                  Complete Setup
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </AlertDescription>
            </Alert>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  // Steps & Data
  const [creationStep, setCreationStep] = useState<"details" | "audience">(
    "details"
  );
  const [createdCampaignId, setCreatedCampaignId] = useState<string | null>(
    null
  );
  const [campaignType, setCampaignType] = useState<
    "presales" | "postsales" | ""
  >("");

  // Objectives
  const [selectedObjective, setSelectedObjective] = useState("");
  const [selectedObjectiveData, setSelectedObjectiveData] = useState<any>(null);
  const [customObjective, setCustomObjective] = useState("");
  const [preSalesObjectives, setPreSalesObjectives] = useState<any[]>([]);
  const [fetchedPostSalesObjectives, setFetchedPostSalesObjectives] = useState<
    any[]
  >([]);

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
  const [urgencyHook, setUrgencyHook] = useState("");

  // Audience Data
  const [targetAudience, setTargetAudience] = useState<string[]>([]);
  const [selectedAudienceDetails, setSelectedAudienceDetails] = useState<any>(
    null
  ); 
  const [audienceTasks, setAudienceTasks] = useState<any[]>([]);
  const [isLoadingAudience, setIsLoadingAudience] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);

  // Pagination State
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const ITEMS_PER_PAGE = 5;

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

  // --- Computed State for Scheduling ---
  const isScheduledCampaign = useMemo(() => {
    if (!duration.start) return false;
    const d = new Date();
    const offset = d.getTimezoneOffset();
    const localToday = new Date(d.getTime() - offset * 60 * 1000)
      .toISOString()
      .split("T")[0];
    return duration.start > localToday;
  }, [duration.start]);

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
    setSelectedAudienceDetails(null);
  }, [campaignType]);

  // --- AUDIENCE FETCHING FIX ---
  const loadAudienceData = async (currentPage = 1) => {
    setIsLoadingAudience(true);
    const fetchcount = 10; // ITEMS_PER_PAGE;
    try {
      // Calling updated API with pagination parameters
      const res: any = await fetchAudienceTasks(currentPage, fetchcount);
      console.log("Fetched Audience Response:", res);
      // FIX: Robust check for items and total_number based on response structure
      let items = [];
      let total = 0;

      if (res.items && Array.isArray(res.items)) {
         // Case 1: Helper returns mapped object { items: [], total_number: N }
         items = res.items;
         total = res.total || 0; 
      } else if (res.data && Array.isArray(res.data)) {
         // Case 2: Raw API response { data: [], total_number: N }
         items = res.data;
         total = res.total || 0;
      } else if (Array.isArray(res)) {
         // Case 3: Just an array (fallback, no total)
         items = res;
         
      }
      
      setAudienceTasks(items);
      setTotalPages(Math.ceil(total / fetchcount));
      
    } catch (e) {
      console.error("Failed to fetch audience", e);
    } finally {
      setIsLoadingAudience(false);
    }
  };

  useEffect(() => {
    if (creationStep === "audience") {
      loadAudienceData(page);
    }
  }, [creationStep, page]);

  // Fetch Objectives
  useEffect(() => {
    const fetchObjectives = async () => {
      setIsLoadingObjectives(true);
      try {
        const typeParam =
          campaignType === "presales" ? "pre-sales" : "post-sales";
        const response = await api(
          `/gryd/db/objects/campaign_objective?campaign_type=${typeParam}`,
          "GET"
        );
        const data = Array.isArray(response) ? response : response.data || [];

        const mapped = data.map((obj: any, idx: number) => {
          const id = obj.campaign_objective_id || obj.id || `obj-${idx}`;
          const title =
            obj.campaign_objective_name || obj.title || obj.name || "Objective";
          return {
            id: id,
            title: title,
            campaignSubType: obj.campaign_sub_type || "other",
            icon: getObjectiveIcon(id, title),
            fullData: obj,
          };
        });

        mapped.push({
          id: "custom",
          title: "Custom Objective",
          campaignSubType: "Flexible",
          icon: <Edit3 className="h-6 w-6" />,
          fullData: null,
        });

        if (campaignType === "presales") setPreSalesObjectives(mapped);
        else setFetchedPostSalesObjectives(mapped);
      } catch (e) {
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
      const objectivesList =
        campaignType === "presales"
          ? preSalesObjectives
          : fetchedPostSalesObjectives;
      const objectiveText =
        selectedObjective === "custom"
          ? customObjective
          : objectivesList.find((o) => o.id === selectedObjective)?.title || "";

      let enhancedText = objectiveText;
      if (carModel && selectedObjective.includes("launch"))
        enhancedText += ` for ${carModel}`;

      const customObjects: Record<string, any> = {};
      selectedObjectiveData?.custom_campaign_attributes?.forEach(
        (attr: any) => {
          if (attr.attribute_name && attr.attribute_value)
            customObjects[attr.attribute_name] = attr.attribute_value;
        }
      );
      if (carModel) customObjects["Car Model"] = carModel;
      if (launchDate) customObjects["Launch Date"] = launchDate;

      const payload = {
        args: [
          campaignType === "presales" ? "pre-sale" : "post-sale",
          enhancedText,
        ],
        kwargs: {
          dealership_idea: {
            languages: [
              languageOptions.find((l) => l.value === language)?.label ||
                "English",
            ],
            campaign_offer: campaignDescription,
            custom_objects: customObjects,
          },
        },
        _timeout: 120,
      };

      const data = await api(
        "/gryd/api/autocrm-short-run-agent/generate_campaign_idea",
        "POST",
        payload
      );

      const today = new Date();
      const nextWeek = new Date(today);
      nextWeek.setDate(today.getDate() + 7);
      const formatDate = (d: Date) => {
        const offset = d.getTimezoneOffset();
        const local = new Date(d.getTime() - offset * 60 * 1000);
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
      setUrgencyHook(data.urgency_hook);
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

  const getAudienceSize = () => {
    // If we have selected details specifically preserved, use that
    if (
      selectedAudienceDetails &&
      targetAudience.includes(selectedAudienceDetails.task_id)
    ) {
      return parseInt(selectedAudienceDetails.process_size || 0);
    }

    // Fallback to finding in current list (might fail if paginated away)
    return audienceTasks
      .filter((task) => targetAudience.includes(task.task_id))
      .reduce((sum, task) => sum + parseInt(task.process_size || 0), 0);
  };

  const getAudienceName = () => {
    // Priority: Saved Details -> Search in current list -> Fallback
    if (
      selectedAudienceDetails &&
      targetAudience.includes(selectedAudienceDetails.task_id)
    ) {
      return (
        selectedAudienceDetails.source_name ||
        selectedAudienceDetails.audience_name ||
        "Untitled Audience"
      );
    }

    const selectedTasks = audienceTasks.filter((task) =>
      targetAudience.includes(task.task_id)
    );
    if (selectedTasks.length === 0) return "No Audience Selected";
    if (selectedTasks.length === 1)
      return (
        selectedTasks[0].source_name ||
        selectedTasks[0].audience_name ||
        "Untitled Audience"
      );
    return "Multiple Audiences Selected";
  };

  const calculateCredits = () => {
    const totalAudience = getAudienceSize();

    return selectedChannels.reduce((sum, channelId) => {
      const channelDef = channels.find((c) => c.id === channelId);
      return sum + totalAudience * (channelDef?.costPerUnit || 0);
    }, 0);
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
      campaign_status: "Drafted",
      start_date: toEpoch(duration.start),
      end_date: toEpoch(duration.end),
      channels: mapChannels(selectedChannels),
      languages: [mapLanguage(language)],
      campaign_offer: campaignData?.campaignOffer || campaignDescription,
      urgency_hook: urgencyHook || "",
      ctas: [callToAction],
      number_targeted: 0,
      budget_allocated: 0,
      campaign_objective_id:
        selectedObjective === "custom"
          ? customObjective
          : selectedObjectiveData?.title || selectedObjective,
      campaign_sub_type: selectedObjectiveData?.campaignSubType || "other",
      campaign_user_source: "file",
    };

    try {
      let endpoint = "";
      let finalPayload = {};
      const dealershipId = getDealershipId();

      if (!dealershipId) {
        alert("Dealership ID not found. Please re-login.");
        setIsPostingCampaign(false);
        return;
      }
      if (campaignType === "presales") {
        endpoint = "/gryd/db/object/pre_sales_campaign";
        finalPayload = {
          ...commonPayload,
          campaign_type: "pre-sales",
          // workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
          dealership_id: dealershipId,
        };
      } else {
        endpoint = "/gryd/db/object/post_sales_campaign";
        finalPayload = {
          ...commonPayload,
          campaign_type: "post-sales",
          // workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
          dealership_id: dealershipId,
        };
      }

      const res = await api(endpoint, "POST", finalPayload);
      const newId = res?.data?.id || res?.id || res?.campaign_id;
      if (!newId) throw new Error("ID not returned");

      setCreatedCampaignId(newId);
      setCreationStep("audience");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error("Proceed failed", err);
      alert("Failed to save draft.");
    } finally {
      setIsPostingCampaign(false);
    }
  };

  const handleLaunch = async () => {
    if (!createdCampaignId) {
      alert("Error: Campaign ID missing.");
      return;
    }

    setIsLaunchSuccessOpen(true);
    setIsLaunchError(false);
    setLaunchStatus(
      isScheduledCampaign
        ? "Scheduling campaign..."
        : "Finalizing audience data..."
    );

    try {
      const totalReach = getAudienceSize();
      const budget = calculateCredits();

      const statusToSet = isScheduledCampaign ? "Planned" : "Active";

      const patchEndpoint =
        campaignType === "presales"
          ? `/gryd/db/object/pre_sales_campaign/${createdCampaignId}`
          : `/gryd/db/object/post_sales_campaign/${createdCampaignId}`;

      await api(patchEndpoint, "PATCH", {
        number_targeted: totalReach,
        budget_allocated: budget,
        campaign_status: statusToSet,
      });

      if (!isScheduledCampaign) {
        setLaunchStatus("Triggering campaign engine...");
        const taskType =
          campaignType === "presales" ? "pre-sales" : "post-sales";

        await api("/gryd/task/autocrm-campaign/trigger_campaign", "POST", {
          args: [],
          kwargs: { campaign_type: taskType, campaign_id: createdCampaignId },
        });
      }

      setLaunchStatus(
        isScheduledCampaign
          ? "Campaign Scheduled Successfully!"
          : "Campaign Launched Successfully!"
      );
      setTimeout(() => localStorage.removeItem("campaignFormData"), 1000);
    } catch (err) {
      console.error("Launch error", err);
      setIsLaunchError(true);
      setLaunchStatus("Failed to process request. Please retry.");
    }
  };

  const objectives =
    campaignType === "presales"
      ? preSalesObjectives
      : fetchedPostSalesObjectives;

  return (
    <ProtectedRoute>
      {/* TOP HEADER */}
      <div className="sticky top-0 z-30 w-full bg-background border-b px-8 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-4">
          {creationStep === "audience" ? (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setCreationStep("details")}
              className="mr-2"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.back()}
              className="mr-2"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
          )}
          <h1 className="text-xl font-bold text-foreground">Create Campaign</h1>
        </div>
        <div className="text-sm font-medium text-muted-foreground">
          {creationStep === "details"
            ? "Step 1/2 — Campaign Setup"
            : "Step 2/2 — Audience & Review"}
        </div>
      </div>

      <div className="pb-24 w-full px-4 py-8 md:px-6 lg:px-8 bg-background min-h-screen">
        {/* LAUNCH STATUS MODAL */}
        <Dialog
          open={isLaunchSuccessOpen}
          onOpenChange={(o) => {
            if (!o && !isLaunchError && !launchStatus.includes("Successfully"))
              return;
            setIsLaunchSuccessOpen(o);
          }}
        >
          <DialogContent
            className="sm:max-w-md text-center"
            onInteractOutside={(e) => {
              if (!isLaunchError && !launchStatus.includes("Successfully"))
                e.preventDefault();
            }}
          >
            {/* ... Modal Content ... */}
            <DialogHeader>
              <div
                className={cn(
                  "mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full transition-colors",
                  isLaunchError ? "bg-red-100" : "bg-green-100"
                )}
              >
                {isLaunchError ? (
                  <AlertCircle className="h-6 w-6 text-red-600" />
                ) : isScheduledCampaign ? (
                  <CalendarClock className="h-6 w-6 text-green-600" />
                ) : (
                  <Rocket className="h-6 w-6 text-green-600" />
                )}
              </div>
              <DialogTitle className="text-center">
                {isLaunchError
                  ? "Error"
                  : isScheduledCampaign
                  ? "Scheduling Campaign"
                  : "Launching Campaign"}
              </DialogTitle>
              <DialogDescription className="text-center">
                {isLaunchError ? "Something went wrong." : launchStatus}
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-center py-4">
              {isLaunchError ? (
                <X className="h-10 w-10 text-red-500 animate-in zoom-in" />
              ) : launchStatus.includes("Successfully") ? (
                <Check className="h-10 w-10 text-green-500 animate-in zoom-in" />
              ) : (
                <RefreshCw className="h-10 w-10 text-primary animate-spin" />
              )}
            </div>
            <DialogFooter className="sm:justify-center">
              {isLaunchError ? (
                <Button
                  variant="outline"
                  onClick={() => setIsLaunchSuccessOpen(false)}
                >
                  Close & Retry
                </Button>
              ) : (
                <Button
                  disabled={!launchStatus.includes("Successfully")}
                  onClick={() => router.push("/")}
                >
                  Go to Dashboard
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* REVIEW DETAILS DIALOG */}
        <Dialog
          open={isObjectiveDetailsOpen}
          onOpenChange={setIsObjectiveDetailsOpen}
        >
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            {/* ... Objective Details Content ... */}
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit3 className="h-5 w-5 text-primary" /> Review Campaign
                Details
              </DialogTitle>
              <DialogDescription>
                Confirm objective details and fill in required attributes.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
              {selectedObjectiveData && (
                <div className="rounded-lg border bg-card text-card-foreground shadow-sm">
                  <div className="p-6 space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Info className="h-4 w-4 text-primary" />
                      <h3 className="font-semibold leading-none tracking-tight">
                        Campaign Information
                      </h3>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                          Campaign Name
                        </Label>
                        <div className="font-medium text-base">
                          {selectedObjectiveData.campaign_objective_name ||
                            selectedObjectiveData.title}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                          Type / Sub-Type
                        </Label>
                        <div className="font-medium text-base flex items-center gap-2">
                          <Badge variant="outline" className="capitalize">
                            {campaignType}
                          </Badge>
                          <span>/</span>
                          <span>
                            {selectedObjectiveData.campaign_sub_type || "other"}
                          </span>
                        </div>
                      </div>
                      <div className="space-y-1 md:col-span-2">
                        <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                          Description
                        </Label>
                        <div className="text-sm text-foreground/80 leading-relaxed bg-muted/30 p-3 rounded-md">
                          {selectedObjectiveData.campaign_objective_description ||
                            "No description available."}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b">
                  <Edit3 className="h-4 w-4 text-primary" />
                  <h3 className="font-semibold leading-none tracking-tight">
                    Required Attributes
                  </h3>
                </div>
                {(selectedObjective === "new-car-launch" ||
                  selectedObjective.includes("launch")) && (
                  <div className="grid grid-cols-2 gap-4 bg-muted/30 p-4 rounded-md">
                    <div className="space-y-2">
                      <Label>
                        Car Model <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        value={carModel}
                        onChange={(e) => setCarModel(e.target.value)}
                        placeholder="e.g. Grand Vitara"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>
                        Launch Date <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        type="date"
                        value={launchDate}
                        onChange={(e) => setLaunchDate(e.target.value)}
                      />
                    </div>
                  </div>
                )}
                {selectedObjectiveData?.custom_campaign_attributes?.map(
                  (attr: any, idx: number) => (
                    <div key={idx} className="space-y-2">
                      <Label>{attr.attribute_name}</Label>
                      <Input
                        placeholder={`Enter ${attr.attribute_name}`}
                        value={attr.attribute_value || ""}
                        onChange={(e) => {
                          const u = [
                            ...selectedObjectiveData.custom_campaign_attributes,
                          ];
                          u[idx].attribute_value = e.target.value;
                          setSelectedObjectiveData({
                            ...selectedObjectiveData,
                            custom_campaign_attributes: u,
                          });
                        }}
                      />
                    </div>
                  )
                )}
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsObjectiveDetailsOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  setIsObjectiveDetailsOpen(false);
                  handleGenerateCampaign();
                }}
              >
                <Sparkles className="mr-2 h-4 w-4" /> Generate Campaign
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <AddDataSourceDialog
          isOpen={isUploadDialogOpen}
          onClose={() => setIsUploadDialogOpen(false)}
          prefilledData={{
            category: campaignType === "presales" ? "pre-sales" : "post-sales",
            objectiveId: selectedObjective,
            campaignId: createdCampaignId || undefined,
          }}
          onSave={(dataSource) => {
            loadAudienceData(1); // Reload page 1 on upload
            if (dataSource.connectionDetails?.taskId) {
              setTargetAudience((prev) => [
                ...prev,
                dataSource.connectionDetails.taskId,
              ]);
            }
          }}
        />

        <div className="mx-auto max-w-5xl space-y-8">
          {/* --- STEP 1: CAMPAIGN SETUP --- */}
          {creationStep === "details" && (
            <>
              {/* CAMPAIGN TYPE SELECTION */}
              <div className="space-y-4">
                <h2 className="text-2xl font-bold flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground">
                    1
                  </span>
                  Select Campaign Type
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <Card
                    className={cn(
                      "cursor-pointer border-2 p-8 flex flex-col items-center transition-all relative overflow-hidden",
                      campaignType === "presales"
                        ? "border-primary bg-primary/5 shadow-md scale-[1.02]"
                        : "hover:border-primary/50 hover:scale-[1.01]"
                    )}
                    onClick={() => setCampaignType("presales")}
                  >
                    <div
                      className={cn(
                        "p-4 rounded-full mb-6 transition-colors",
                        campaignType === "presales"
                          ? "bg-primary/20"
                          : "bg-primary/10"
                      )}
                    >
                      <Target className="h-16 w-16 text-primary" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2">Pre-Sales</h3>
                    <p className="text-center text-muted-foreground">
                      Generate leads and acquire new customers
                    </p>
                    {campaignType === "presales" && (
                      <div className="absolute top-4 right-4">
                        <Check className="h-6 w-6 text-primary animate-in zoom-in" />
                      </div>
                    )}
                  </Card>
                  <Card
                    className={cn(
                      "cursor-pointer border-2 p-8 flex flex-col items-center transition-all relative overflow-hidden",
                      campaignType === "postsales"
                        ? "border-primary bg-primary/5 shadow-md scale-[1.02]"
                        : "hover:border-primary/50 hover:scale-[1.01]"
                    )}
                    onClick={() => setCampaignType("postsales")}
                  >
                    <div
                      className={cn(
                        "p-4 rounded-full mb-6 transition-colors",
                        campaignType === "postsales"
                          ? "bg-primary/20"
                          : "bg-primary/10"
                      )}
                    >
                      <Users className="h-16 w-16 text-primary" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2">Post-Sales</h3>
                    <p className="text-center text-muted-foreground">
                      Engage existing customers and drive service
                    </p>
                    {campaignType === "postsales" && (
                      <div className="absolute top-4 right-4">
                        <Check className="h-6 w-6 text-primary animate-in zoom-in" />
                      </div>
                    )}
                  </Card>
                </div>
              </div>

              {/* PROGRESSIVE SECTIONS */}
              {campaignType && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
                  {/* OBJECTIVES */}
                  <div className="space-y-4">
                    <h2 className="text-2xl font-bold flex items-center gap-2">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground">
                        2
                      </span>
                      Select Objective
                    </h2>
                    <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                      <CardContent className="pt-6">
                        <Tabs value={activeTab} onValueChange={setActiveTab}>
                          <TabsList className="mb-4 w-full justify-start h-auto p-1">
                            <TabsTrigger value="setup" className="px-6 py-2">
                              Objectives
                            </TabsTrigger>
                            <TabsTrigger value="previous" className="px-6 py-2">
                              Previously Used
                            </TabsTrigger>
                          </TabsList>
                          <TabsContent value="setup" className="space-y-4">
                            {isLoadingObjectives ? (
                              <div className="flex items-center justify-center py-12">
                                <RefreshCw className="h-8 w-8 animate-spin text-primary mr-2" />
                                <span className="text-muted-foreground text-lg">
                                  Loading objectives...
                                </span>
                              </div>
                            ) : (
                              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                                {objectives.map((obj) => (
                                  <ObjectiveCard
                                    key={obj.id}
                                    {...obj}
                                    selected={selectedObjective === obj.id}
                                    onSelect={() => {
                                      setSelectedObjective(obj.id);
                                      setSelectedObjectiveData(
                                        obj.fullData || null
                                      );
                                      setCampaignData(null);
                                      setCreatedCampaignId(null);
                                      if (obj.id !== "custom")
                                        setIsObjectiveDetailsOpen(true);
                                    }}
                                  />
                                ))}
                              </div>
                            )}
                            {selectedObjective === "custom" && (
                              <div className="mt-4 flex gap-2">
                                <Input
                                  placeholder="Describe your custom objective..."
                                  value={customObjective}
                                  onChange={(e) =>
                                    setCustomObjective(e.target.value)
                                  }
                                  className="h-12"
                                />
                                <Button
                                  onClick={handleGenerateCampaign}
                                  className="h-12 px-6"
                                >
                                  Generate
                                </Button>
                              </div>
                            )}
                          </TabsContent>
                          <TabsContent value="previous">
                            <PreviouslyUsedCampaigns
                              campaignType={campaignType}
                              onReuseCampaign={() => {}}
                            />
                          </TabsContent>
                        </Tabs>
                      </CardContent>
                    </Card>
                  </div>

                  {isGenerating && (
                    <Card className="py-12">
                      <AILoader />
                    </Card>
                  )}

                  {/* DETAILS */}
                  {!isGenerating && campaignData && (
                    <div className="space-y-8 animate-in fade-in duration-500">
                      <div className="space-y-4">
                        <h2 className="text-2xl font-bold flex items-center gap-2">
                          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground">
                            3
                          </span>
                          Review & Configure
                        </h2>

                        <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                          <CardHeader>
                            <CardTitle>Campaign Attributes</CardTitle>
                            <CardDescription>
                              Review generated content
                            </CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                              <div className="space-y-2">
                                <Label>Campaign Name</Label>
                                <Input
                                  value={campaignName}
                                  onChange={(e) =>
                                    setCampaignName(e.target.value)
                                  }
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Campaign Title</Label>
                                <Input
                                  value={campaignTitle}
                                  onChange={(e) =>
                                    setCampaignTitle(e.target.value)
                                  }
                                />
                              </div>
                            </div>
                            <div className="space-y-2">
                              <Label>Description / Offer</Label>
                              <Textarea
                                rows={3}
                                value={campaignDescription}
                                onChange={(e) =>
                                  setCampaignDescription(e.target.value)
                                }
                              />
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                              <div className="space-y-2">
                                <Label>Start Date</Label>
                                <Input
                                  type="date"
                                  value={duration.start}
                                  onChange={(e) =>
                                    setDuration({
                                      ...duration,
                                      start: e.target.value,
                                    })
                                  }
                                />
                                {isScheduledCampaign && (
                                  <p className="text-xs text-amber-600 font-medium flex items-center gap-1 mt-1">
                                    <CalendarClock className="h-3 w-3" /> Future
                                    start date: Campaign will be scheduled.
                                  </p>
                                )}
                              </div>
                              <div className="space-y-2">
                                <Label>End Date</Label>
                                <Input
                                  type="date"
                                  value={duration.end}
                                  onChange={(e) =>
                                    setDuration({
                                      ...duration,
                                      end: e.target.value,
                                    })
                                  }
                                />
                              </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                              <div className="space-y-2">
                                <Label>Tone</Label>
                                <Input
                                  value={tone}
                                  onChange={(e) => setTone(e.target.value)}
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Call to Action</Label>
                                <Input
                                  value={callToAction}
                                  onChange={(e) =>
                                    setCallToAction(e.target.value)
                                  }
                                />
                              </div>
                              <div className="space-y-2">
                                <Label>Urgency Hook</Label>
                                <Input
                                  value={urgencyHook}
                                  onChange={(e) => setUrgencyHook(e.target.value)}
                                />
                              </div>
                            </div>
                          </CardContent>
                        </Card>

                        <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                          <CardHeader>
                            <CardTitle>Channels</CardTitle>
                            <CardDescription>
                              Channels auto-optimized for this campaign
                            </CardDescription>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                              {channels.map((ch) => (
                                <Card
                                  key={ch.id}
                                  className={cn(
                                    "border-2 transition-all cursor-pointer",
                                    selectedChannels.includes(ch.id)
                                      ? "border-primary bg-primary/5 shadow-sm"
                                      : "opacity-50"
                                  )}
                                  onClick={() => {
                                    if (selectedChannels.includes(ch.id)) {
                                      setSelectedChannels(
                                        selectedChannels.filter(
                                          (c) => c !== ch.id
                                        )
                                      );
                                    } else {
                                      setSelectedChannels([
                                        ...selectedChannels,
                                        ch.id,
                                      ]);
                                    }
                                  }}
                                >
                                  <CardContent className="flex flex-col items-center p-4">
                                    <div
                                      className={cn(
                                        "mb-2",
                                        selectedChannels.includes(ch.id)
                                          ? "text-primary"
                                          : "text-muted-foreground"
                                      )}
                                    >
                                      {ch.icon}
                                    </div>
                                    <span className="font-semibold">
                                      {ch.name}
                                    </span>
                                    {selectedChannels.includes(ch.id) && (
                                      <Badge className="mt-2 bg-green-600">
                                        Active
                                      </Badge>
                                    )}
                                  </CardContent>
                                </Card>
                              ))}
                            </div>
                          </CardContent>
                        </Card>

                        <div className="flex justify-end pt-4 pb-12">
                          <Button
                            size="lg"
                            onClick={handleProceed}
                            disabled={isPostingCampaign}
                            className="gap-2 px-8 text-lg h-14 shadow-lg hover:shadow-xl transition-all animate-pulse hover:scale-105 bg-primary hover:bg-primary-700 hover:animate-none"
                          >
                            {isPostingCampaign ? (
                              <>
                                <RefreshCw className="animate-spin h-5 w-5 mr-2" />{" "}
                                Saving Draft...
                              </>
                            ) : (
                              <>
                                Proceed to Audience Selection{" "}
                                <ArrowRight className="w-5 h-5 ml-2" />
                              </>
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* --- STEP 2: AUDIENCE & REVIEW --- */}
          {creationStep === "audience" && (
            <div className="space-y-8 animate-in fade-in slide-in-from-right-8 duration-500">
              {/* AUDIENCE CARD */}
              <Card className="shadow-lg bg-white border">
                <CardHeader className="border-b pb-4">
                  <CardTitle className="text-xl">Target Audience</CardTitle>
                  <CardDescription>
                    Select or upload your target audience
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-6 space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="audience-select" className="font-semibold">
                      Select Audience
                    </Label>
                    <Select
                      onValueChange={(val) => {
                        setTargetAudience([val]);
                        const task = audienceTasks.find(
                          (t) => t.task_id === val
                        );
                        if (task) setSelectedAudienceDetails(task);
                      }}
                      value={targetAudience[0] || ""}
                    >
                      <SelectTrigger
                        id="audience-select"
                        className="h-12 text-base"
                      >
                        <SelectValue placeholder="Choose audience segment" />
                      </SelectTrigger>
                      <SelectContent>
                        {isLoadingAudience ? (
                          <div className="p-4 text-center text-sm text-muted-foreground">
                            Loading...
                          </div>
                        ) : audienceTasks.length > 0 ? (
                          <>
                            {audienceTasks.map((task) => (
                              <SelectItem
                                key={task.task_id}
                                value={task.task_id}
                              >
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">
                                    {task.source_name ||
                                      task.audience_name ||
                                      "Untitled List"}
                                  </span>
                                  <Badge variant="outline" className="text-xs">
                                    {parseInt(
                                      task.process_size || 0
                                    ).toLocaleString()}{" "}
                                    Records
                                  </Badge>
                                </div>
                              </SelectItem>
                            ))}
                            {/* Pagination Controls */}
                            <div
                              className="flex items-center justify-between p-2 border-t mt-2 bg-slate-50"
                              onKeyDown={(e) => e.stopPropagation()}
                            >
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={page <= 1}
                                onClick={(e) => {
                                  e.preventDefault();
                                  setPage((p) => p - 1);
                                }}
                                className="h-8 w-8 p-0"
                              >
                                <ChevronLeft className="h-4 w-4" />
                              </Button>
                              <span className="text-xs text-muted-foreground font-medium">
                                Page {page} of {totalPages || 1}
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={page >= totalPages}
                                onClick={(e) => {
                                  e.preventDefault();
                                  setPage((p) => p + 1);
                                }}
                                className="h-8 w-8 p-0"
                              >
                                <ChevronRight className="h-4 w-4" />
                              </Button>
                            </div>
                          </>
                        ) : (
                          <div className="p-2 text-sm text-muted-foreground">
                            No lists found.
                          </div>
                        )}
                      </SelectContent>
                    </Select>

                    {/* Show selected details slightly below if something is picked */}
                    {targetAudience.length > 0 && (
                      <div className="mt-2 p-3 bg-secondary/10 rounded-md flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">
                          Selected Segment ID: {targetAudience[0]}
                        </span>
                        <Badge className="bg-primary">Selected</Badge>
                      </div>
                    )}
                  </div>

                  <div className="relative py-2">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-white px-2 text-muted-foreground">
                        OR
                      </span>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-4">
                    <Button
                      variant="outline"
                      className="h-12 flex-1 border-dashed border-2 hover:border-primary hover:bg-primary/5"
                      onClick={() => setIsUploadDialogOpen(true)}
                    >
                      <Upload className="mr-2 h-4 w-4" /> Upload New Audience
                    </Button>
                    <Button variant="ghost" className="h-12 flex-1">
                      <Download className="mr-2 h-4 w-4" /> Download Template
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* REVIEW CARD */}
              <Card className="shadow-lg border bg-white">
                <CardHeader className="pb-4 border-b">
                  <CardTitle className="text-xl">Review Campaign</CardTitle>
                  <CardDescription>
                    Review your campaign before launching
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-8 pt-6">
                  {/* Campaign Details Section */}
                  <div className="space-y-4">
                    <h3 className="font-semibold text-base">
                      Campaign Details
                    </h3>
                    <div className="bg-slate-50 rounded-lg p-4 space-y-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-muted-foreground">
                          Campaign Title:
                        </span>
                        <span className="font-medium">{campaignName}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-muted-foreground">
                          Objective:
                        </span>
                        <span className="font-medium">
                          {selectedObjectiveData?.title || "Custom Objective"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-muted-foreground">
                          Start Date:
                        </span>
                        <span className="font-medium">{duration.start}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-muted-foreground">End Date:</span>
                        <span className="font-medium">{duration.end}</span>
                      </div>
                    </div>
                  </div>

                  {/* Selected Channels */}
                  <div className="space-y-4">
                    <h3 className="font-semibold text-base">
                      Selected Channels
                    </h3>
                    <div className="flex gap-2">
                      {selectedChannels.map((c) => (
                        <Badge
                          key={c}
                          variant="secondary"
                          className="px-3 py-1 bg-purple-100 text-purple-700 hover:bg-purple-200 capitalize"
                        >
                          {c}
                        </Badge>
                      ))}
                      {selectedChannels.length === 0 && (
                        <span className="text-sm text-muted-foreground">
                          No channels selected
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Credits Breakdown */}
                  <div className="space-y-4">
                    <h3 className="font-semibold text-base">
                      Credits Breakdown
                    </h3>
                    <div className="border rounded-lg divide-y">
                      {selectedChannels.map((channelId) => {
                        const channelDef = channels.find(
                          (c) => c.id === channelId
                        );
                        const audienceSize = getAudienceSize();
                        const totalChannelCredits =
                          audienceSize * (channelDef?.costPerUnit || 0);

                        return (
                          <div key={channelId} className="p-4 space-y-2">
                            <div className="flex justify-between font-medium">
                              <span className="capitalize">{channelId}</span>
                              <span>
                                {totalChannelCredits.toLocaleString()} credits
                              </span>
                            </div>
                            <div className="flex justify-between text-xs text-muted-foreground">
                              <div className="flex gap-4">
                                <span>
                                  Audience:{" "}
                                  <span className="text-foreground">
                                    {getAudienceName()}
                                  </span>
                                </span>
                              </div>
                              <div className="flex gap-4">
                                <span>
                                  Size: {audienceSize.toLocaleString()}
                                </span>
                                <span>
                                  Credits per message: {channelDef?.costPerUnit}
                                </span>
                              </div>
                            </div>
                          </div>
                        );
                      })}

                      {/* Total Row */}
                      <div className="p-4 bg-slate-50 flex justify-between items-center font-bold text-lg rounded-b-lg">
                        <span>Total Credits</span>
                        <span>{calculateCredits().toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>

                {/* Bottom Action Bar */}
                <CardFooter className="flex justify-end gap-3 pt-6 pb-6 border-t bg-slate-50/50 rounded-b-lg">
                  <Button
                    variant="outline"
                    className="bg-white"
                    onClick={() => {
                      // Logic to save draft
                      setCreationStep("details");
                      setCreatedCampaignId(null);
                    }}
                  >
                    Save as Draft
                  </Button>
                  <Button
                    className="bg-[#3D0C8A] hover:bg-[#2d0966] text-white px-8"
                    onClick={handleLaunch}
                  >
                    {isScheduledCampaign ? (
                      <>
                        <CalendarClock className="mr-2 h-4 w-4" /> Schedule
                        Campaign
                      </>
                    ) : (
                      <>
                        <Rocket className="mr-2 h-4 w-4" /> Launch Campaign
                      </>
                    )}
                  </Button>
                </CardFooter>
              </Card>

              <div className="flex justify-start pt-4 pb-12">
                <Button
                  variant="ghost"
                  onClick={() => setCreationStep("details")}
                  className="text-muted-foreground hover:text-foreground pl-0 hover:bg-transparent"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" /> Back to Setup
                </Button>
              </div>
            </div>
          )}
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