"use client";

import { useState, useEffect, Suspense, useMemo, useRef } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";

// Imports
import {
  fetchAudienceTasks,
  getDealershipId,
  executeTaskWithPolling,
  cloneLeadsTask,
  assignAudienceTask,
  updateAudienceTask,
} from "@/utils/api";
import { api, dealershipUpdateDetails } from "@/lib/api";

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
  Search,
  Download,
  MessageSquareText,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AILoader } from "@/components/ui/ai-loader";
import { Separator } from "@/components/ui/separator";

// --- HELPERS & CONSTANTS ---
const STELLANTIS_AGENT_MAP: Record<string, string> = {};
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
    name: "Voice Call",
    icon: <Phone className="h-6 w-6" />,
    costPerUnit: 8.56,
  },
  {
    id: "rcs",
    name: "RCS",
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
  { value: "ml", label: "Malayalam" },
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
    ml: "malayalam",
  };
  return map[code] || "english";
};

// --- MAIN COMPONENT ---

function CampaignCreateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isDealershipSetupComplete } = useAuth();
  // Voice Configuration States
  const [voiceStartLanguage, setVoiceStartLanguage] = useState("en");
  const [voiceAgentId, setVoiceAgentId] = useState("");
  const pathname = usePathname();
  const [totalNumber, setTotalNumber] = useState(0);
  const [isLastPage, setIsLastPage] = useState(false);

  const [activeTab, setActiveTab] = useState("generic"); // Default to Generic
  const [genericObjectives, setGenericObjectives] = useState<any[]>([]);
  const [customObjectives, setCustomObjectives] = useState<any[]>([]);
  const [previousObjectives, setPreviousObjectives] = useState<any[]>([]);

  const prefillFromExistingCampaign = (data: any) => {
    // 1. Format today's date (DD-MM-YYYY)
    const today = new Date();
    const dateSuffix = today
      .toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
      .replace(/\//g, "-");

    // 2. Basic Details - Appending the date
    const baseName = data.campaign_name || "PreviousUsed";
    const basetitle =
      data.campaign_tagline || data.campaign_title || "Previous Campaign";
    setCampaignName(`${baseName} - ${dateSuffix}`);

    setCampaignDescription(data.campaign_description || "");
    setCampaignTitle(
      data.campaign_tagline ||
        data.campaign_title ||
        `${basetitle} - ${dateSuffix}`,
    );
    setTone(data.campaign_tone || "");
    setUrgencyHook(data.urgency_hook || "");

    // 3. CTAs and Languages
    if (data.ctas && data.ctas.length > 0) setCallToAction(data.ctas[0]);

    if (data.languages && data.languages.length > 0) {
      const langLabel = data.languages[0].toLowerCase();
      const langEntry = languageOptions.find(
        (l) => l.label.toLowerCase() === langLabel,
      );
      setLanguage(langEntry ? langEntry.value : "en");
    }

    // 4. Channels Mapping
    if (data.channels) {
      const channelMap: Record<string, string> = {
        whatsapp_chat: "whatsapp",
        email: "email",
        voice_phone: "voice",
        rcs_message: "rcs",
        sms_message: "sms",
      };
      setSelectedChannels(data.channels.map((c: string) => channelMap[c] || c));
    }

    // 5. Voice Config
    if (data.voice_start_language)
      setVoiceStartLanguage(data.voice_start_language);
    if (data.voice_agent_id) setVoiceAgentId(data.voice_agent_id);

    // 6. Reset Dates to "Starting Today"
    const nextWeek = new Date(today);
    nextWeek.setDate(today.getDate() + 7);
    const formatDate = (d: Date) => {
      const offset = d.getTimezoneOffset();
      const local = new Date(d.getTime() - offset * 60 * 1000);
      return local.toISOString().split("T")[0];
    };

    setDuration({
      start: formatDate(today),
      end: formatDate(nextWeek),
    });

    // Trigger Section Visibility
    setCampaignData({
      isExisting: true,
      campaignOffer: data.campaign_offer || data.campaign_description,
    });
  };

  // Pagination & Search
  const currentPage = Number(searchParams.get("page")) || 1;
  const searchQuery = searchParams.get("q") || "";
  // Auto-fill voice agent ID for stellantis-india

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
                    To run a campaign, please verify and complete your
                    dealership profile.
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
    "details",
  );
  const [createdCampaignId, setCreatedCampaignId] = useState<string | null>(
    null,
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

  const detailsRef = useRef<HTMLDivElement | null>(null);

  // Campaign Details
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatusMsg, setGenerationStatusMsg] = useState("");
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
  const [selectedAudienceDetails, setSelectedAudienceDetails] =
    useState<any>(null);
  const [audienceTasks, setAudienceTasks] = useState<any[]>([]);
  const [isLoadingAudience, setIsLoadingAudience] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  // const [audienceSourceType, setAudienceSourceType] = useState<"upload" | "previous" | "fresh" | null>(null);

  // Filter fetched audiences based on presence of campaign_id
  // const usedAudiences = audienceTasks.filter((t) => !!t.campaign_id);
  // const freshAudiences = audienceTasks.filter((t) => !t.campaign_id);
  // Pagination State
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const ITEMS_PER_PAGE = 5;

  // Custom Attributes
  const [carModel, setCarModel] = useState("");
  const [launchDate, setLaunchDate] = useState("");

  // UI States
  // const [activeTab, setActiveTab] = useState("setup");
  const [isLoadingObjectives, setIsLoadingObjectives] = useState(false);
  const [isObjectiveDetailsOpen, setIsObjectiveDetailsOpen] = useState(false);
  const [isLaunchSuccessOpen, setIsLaunchSuccessOpen] = useState(false);
  const [launchStatus, setLaunchStatus] = useState("");
  const [isLaunchError, setIsLaunchError] = useState(false);
  const [launchStep, setLaunchStep] = useState(0);
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

  const [hasWhatsappTemplates, setHasWhatsappTemplates] =
    useState<boolean>(true);

  useEffect(() => {
    const checkWhatsappTemplates = async () => {
      const objectiveName =
        selectedObjectiveData?.campaign_objective_name ||
        selectedObjectiveData?.title ||
        selectedObjective;
      if (!objectiveName || objectiveName === "custom") {
        setHasWhatsappTemplates(true);
        return;
      }
      try {
        const dealershipId = getDealershipId() || "";
        const endpoint = `/gryd/db/objects/template?campaign_objective_name=${encodeURIComponent(objectiveName)}&dealership_id=${encodeURIComponent(dealershipId)}`;
        const res = await api(endpoint, "GET");
        const templates = res.data || [];
        const hasTemplates = templates.some(
          (t: any) => t.status === "approved",
        );
        setHasWhatsappTemplates(hasTemplates);
        if (!hasTemplates) {
          setSelectedChannels((prev) => prev.filter((c) => c !== "whatsapp"));
        }
      } catch (error) {
        console.error("Failed to check templates for objective", error);
        setHasWhatsappTemplates(true);
      }
    };
    checkWhatsappTemplates();
  }, [selectedObjective, selectedObjectiveData]);

  // --- Initialization ---
  useEffect(() => {
    const dealershipId = getDealershipId();
    if (
      dealershipId === "stellantis-india" &&
      selectedChannels.includes("voice")
    ) {
      setVoiceAgentId(STELLANTIS_AGENT_MAP[voiceStartLanguage] || "");
    }
  }, [voiceStartLanguage, selectedChannels]);
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

  // 1. Keep your state
  const [audienceSourceType, setAudienceSourceType] = useState<
    "upload" | "previous" | "fresh" | null
  >(null);
  const [audienceSearch, setAudienceSearch] = useState("");

  // 2. Remove the client-side `usedAudiences` and `freshAudiences` filter variables.
  // We will just use `audienceTasks` directly since the server is filtering it now.

  // 3. Update loadAudienceData to accept and pass the filter type and search
  const loadAudienceData = async (
    currentPage = 1,
    type = audienceSourceType,
    searchVal = audienceSearch,
  ) => {
    // Don't fetch if they selected upload or haven't selected yet
    if (!type || type === "upload") return;

    setIsLoadingAudience(true);
    const fetchcount = 5; // Reduced page size to 5 for a cleaner table UI
    try {
      // Pass the type, search, and campaignType down to the API
      const res: any = await fetchAudienceTasks(
        currentPage,
        fetchcount,
        type,
        "",
        searchVal,
        campaignType,
      );

      let items = [];
      let total = 0;

      if (res.items && Array.isArray(res.items)) {
        items = res.items;
        total = res.total || 0;
      } else if (res.data && Array.isArray(res.data)) {
        items = res.data;
        total = res.total || 0;
      } else if (Array.isArray(res)) {
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

  // 4. Update useEffect to trigger fetching with debounce when search, page, or type changes
  useEffect(() => {
    if (creationStep === "audience") {
      const delayDebounceFn = setTimeout(() => {
        loadAudienceData(page, audienceSourceType, audienceSearch);
      }, 300);

      return () => clearTimeout(delayDebounceFn);
    }
  }, [creationStep, page, audienceSourceType, audienceSearch]);
  // Fetch Objectives
  const [displayObjectives, setDisplayObjectives] = useState<any[]>([]);

  useEffect(() => {
    const fetchObjectives = async () => {
      if (!campaignType) return;

      // Clear the list immediately to stop the "piling up" glitch
      setIsLoadingObjectives(true);
      setDisplayObjectives([]);

      try {
        const dealershipId = getDealershipId();
        const typeParam =
          campaignType === "presales" ? "pre-sales" : "post-sales";
        // Ensure page_size is strictly 9 to keep the grid consistent
        const apiParams = `&page_number=${currentPage}&page_size=9&sort_by=created&sort_reverse=true&search_term=~${searchQuery}`;

        let endpoint = "";
        if (activeTab === "generic") {
          endpoint = `/gryd/db/objects/campaign_objective?campaign_type=${typeParam}&dealership_id=null${apiParams}`;
        } else if (activeTab === "custom") {
          endpoint = `/gryd/db/objects/campaign_objective?campaign_type=${typeParam}&dealership_id=${dealershipId}${apiParams}`;
        } else if (activeTab === "previous") {
          const model =
            campaignType === "presales"
              ? "pre_sales_campaign"
              : "post_sales_campaign";
          endpoint = `/gryd/db/objects/${model}?dealership_id=${dealershipId}${apiParams}`;
        }

        const res: any = await api(endpoint, "GET");
        const rawData = res.data || [];

        setTotalNumber(res.total_number || 0);
        setIsLastPage(res.is_last);

        const mapped = rawData.map((obj: any) => {
          // IMPORTANT: For Previous Used, use the actual campaign ID as the unique identifier
          // Campaigns have their own 'id' or 'campaign_id', objectives have 'campaign_objective_id'
          const uniqueId =
            obj.id || obj.campaign_id || obj.campaign_objective_id;
          const objectiveId = obj.campaign_objective_id || uniqueId;
          const title =
            obj.campaign_name ||
            obj.campaign_objective_name ||
            obj.title ||
            "Untitled";

          return {
            id: uniqueId,
            objectiveId: objectiveId,
            title: title,
            campaignSubType: obj.campaign_sub_type || "other",
            icon: getObjectiveIcon(
              obj.campaign_objective_id || uniqueId,
              title,
            ),
            fullData: obj,
          };
        });

        if (activeTab === "custom" && currentPage === 1 && !searchQuery) {
          mapped.unshift({
            id: "custom",
            objectiveId: "custom",
            title: "Create New Objective",
            campaignSubType: "Flexible",
            icon: <Edit3 className="h-6 w-6" />,
            fullData: null,
          });
        }

        setDisplayObjectives(mapped);
      } catch (e) {
        console.error("Fetch failed", e);
      } finally {
        setIsLoadingObjectives(false);
      }
    };

    fetchObjectives();
  }, [campaignType, activeTab, currentPage, searchQuery]);
  // --- Logic ---

  const handleGenerateCampaign = async () => {
    setTimeout(() => {
      window.scrollTo({
        top: document.documentElement.scrollHeight,
        behavior: "smooth",
      });
    }, 100);
    setIsGenerating(true);

    setGenerationStatusMsg("Initializing...");

    try {
      // Setup payload variables
      // const objectivesList = campaignType === "presales" ? preSalesObjectives : fetchedPostSalesObjectives;
      // const objectiveText = selectedObjective === "custom"
      //   ? customObjective
      //   : objectivesList.find((o) => o.id === selectedObjective)?.title || "";

      // let enhancedText = objectiveText;
      const objectiveItem = displayObjectives.find(
        (o) => o.id === selectedObjective,
      );

      // Determine the text to send to the AI
      const objectiveText =
        selectedObjective === "custom"
          ? customObjective
          : objectiveItem?.title || "";

      if (!objectiveText) {
        alert("Please select an objective or enter a custom one.");
        setIsGenerating(false);
        return;
      }

      let enhancedText = objectiveText;
      if (carModel && selectedObjective.includes("launch"))
        enhancedText += ` for ${carModel}`;

      const customObjects: Record<string, any> = {};
      selectedObjectiveData?.custom_campaign_attributes?.forEach(
        (attr: any) => {
          if (attr.attribute_name && attr.attribute_value)
            customObjects[attr.attribute_name] = attr.attribute_value;
        },
      );
      if (carModel) customObjects["Car Model"] = carModel;
      if (launchDate) customObjects["Launch Date"] = launchDate;

      // Construct payload
      const payload = {
        args: [
          campaignType === "presales" ? "pre-sales" : "post-sales",
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
        runtime_limit: 3600,
        cancellable: true,
      };
      const servicename =
        process.env.NEXT_PUBLIC_AUTOCRM_SHORT_RUN_AGENT_SERVICE_NAME ||
        "autocrm-short-run-agent";
      // Call our new global polling function
      const resultData = await executeTaskWithPolling(
        servicename,
        "generate_campaign_idea",
        payload,
        (statusMessage: string) => setGenerationStatusMsg(statusMessage), // UI Callback
        { maxRetries: 90 }, // Optional: 3 minutes max timeout for this specific heavy task
      );

      // Calculate dates for the UI
      const today = new Date();
      const nextWeek = new Date(today);
      nextWeek.setDate(today.getDate() + 7);
      const formatDate = (d: Date) => {
        const offset = d.getTimezoneOffset();
        const local = new Date(d.getTime() - offset * 60 * 1000);
        return local.toISOString().split("T")[0];
      };

      // Match language code
      const returnedLangLabel = resultData.languages?.[0];
      const matchedLang =
        languageOptions.find(
          (l) => l.label.toLowerCase() === returnedLangLabel?.toLowerCase(),
        )?.value || "en";

      // Set Component States
      setCampaignData({
        name: resultData.campaign_name,
        description: resultData.campaign_description,
        campaignTitle: resultData.campaign_tagline,
        tone: resultData.campaign_tone,
        callToAction: resultData.ctas?.[0] || "Learn More",
        language: matchedLang,
        campaignOffer: resultData.campaign_offer,
        urgencyHook: resultData.urgency_hook,
      });

      setCampaignName(resultData.campaign_name || "");
      setCampaignDescription(resultData.campaign_description || "");
      setUrgencyHook(resultData.urgency_hook || "");
      setCampaignTitle(resultData.campaign_tagline || "");
      setTone(resultData.campaign_tone || "");
      setCallToAction(resultData.ctas?.[0] || "Learn More");
      setLanguage(matchedLang);
      setDuration({ start: formatDate(today), end: formatDate(nextWeek) });
      setSelectedChannels(
        hasWhatsappTemplates
          ? ["voice", "whatsapp", "email"]
          : ["voice", "email"],
      );
    } catch (error: any) {
      console.error(error);
      alert(
        `Failed to generate campaign: ${error.message || "Check console for details."}`,
      );
    } finally {
      setIsGenerating(false);
      setGenerationStatusMsg("");
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
      targetAudience.includes(task.task_id),
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

    // NEW VALIDATION: Check if Voice is selected but agent ID is missing
    // if (selectedChannels.includes("voice") && !voiceAgentId) {
    //   alert("Please provide a Voice Agent ID for the Voice Call channel.");
    //   return;
    // }

    setIsPostingCampaign(true);

    // Make this an explicit type so we can append custom keys
    const commonPayload: Record<string, any> = {
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
      // campaign_objective_id:
      //   selectedObjective === "custom"? customObjective
      //     : selectedObjectiveData?.title || selectedObjective,
      campaign_objective_id:
        selectedObjective === "custom" ? customObjective : selectedObjective,
      campaign_sub_type: selectedObjectiveData?.campaignSubType || "other",
      campaign_user_source: "file",
      campaign_custom_attributes:
        selectedObjectiveData?.custom_campaign_attributes || [],
    };

    // NEW LOGIC: Append Voice configs if voice is selected
    if (selectedChannels.includes("voice")) {
      commonPayload.voice_start_language = voiceStartLanguage;
      commonPayload.voice_agent_id = voiceAgentId;
    }

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
    setLaunchStep(1); // Step 1: Processing Audience

    try {
      // --- Execute Audience Tasks Based on Selection ---
      if (audienceSourceType === "previous" && selectedAudienceDetails) {
        setLaunchStatus("Cloning leads from previous campaign...");
        await cloneLeadsTask(
          campaignType === "presales" ? "pre-sales" : "post-sales",
          selectedAudienceDetails.campaign_id,
          createdCampaignId,
          getDealershipId(),
          ((msg: string) => setLaunchStatus(msg)) as any,
        );
      } else if (audienceSourceType === "fresh" && selectedAudienceDetails) {
        setLaunchStatus("Assigning fresh audience to campaign...");
        await assignAudienceTask(
          campaignType === "presales" ? "pre-sales" : "post-sales",
          createdCampaignId,
          selectedAudienceDetails.campaign_objective_id ||
            selectedAudienceDetails.objective_id ||
            selectedObjective,
          getDealershipId(),
          {
            audience_task_id: selectedAudienceDetails.task_id,
            audience_name: selectedAudienceDetails.audience_name,
          },
          ((msg: string) => setLaunchStatus(msg)) as any,
        );
        try {
          await updateAudienceTask(selectedAudienceDetails.audience_task_id, {
            campaign_id: createdCampaignId,
          });
        } catch (patchErr) {
          console.error(
            "Failed to patch audience task with campaign ID",
            patchErr,
          );
        }
      }
    } catch (err) {
      console.error("Audience task error", err);
      setIsLaunchError(true);
      setLaunchStatus("Failed to process audience. Please retry.");
      return; // Stop execution on error
    }

    setLaunchStep(2); // Step 2: Finalizing setup
    setLaunchStatus(
      isScheduledCampaign
        ? "Scheduling campaign..."
        : "Finalizing audience data...",
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

      try {
        const storedDetailsStr = localStorage.getItem("dealership_details");
        if (storedDetailsStr) {
          const detailsObj = JSON.parse(storedDetailsStr);
          const currentStatus = detailsObj.dealer_status;

          if (currentStatus !== "active" && currentStatus !== "suspended") {
            const coreServiceName =
              process.env.NEXT_PUBLIC_AUTOCRM_CORE_SERVICE_NAME ||
              "autocrm-core";
            await executeTaskWithPolling(
              coreServiceName,
              "dealership_update_status",
              {
                args: [getDealershipId()],
                kwargs: { dealer_status: "active" },
              },
            );
            detailsObj.dealer_status = "active";
            localStorage.setItem(
              "dealership_details",
              JSON.stringify(detailsObj),
            );
          }
        }
      } catch (err) {
        console.error("Failed to update dealership status", err);
      }

      setLaunchStep(3); // Step 3: Triggering Engine

      if (!isScheduledCampaign) {
        setLaunchStatus("Triggering campaign engine...");
        const taskType =
          campaignType === "presales" ? "pre-sales" : "post-sales";
        const serviceName =
          process.env.NEXT_PUBLIC_AUTOCRM_CAMPAIGN_TRIGGER_SERVICE_NAME ||
          "autocrm-campaign";
        await api(`/gryd/task/${serviceName}/trigger_campaign`, "POST", {
          args: [],
          kwargs: { campaign_type: taskType, campaign_id: createdCampaignId },
        });
      }

      setLaunchStep(4); // Step 4: Complete
      setLaunchStatus(
        isScheduledCampaign
          ? "Campaign Scheduled Successfully!"
          : "Campaign Launched Successfully!",
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
        {/* LAUNCH STATUS MODAL */}
        <Dialog
          open={isLaunchSuccessOpen}
          onOpenChange={(o) => {
            if (!o && !isLaunchError && launchStep !== 4) return;
            setIsLaunchSuccessOpen(o);
          }}
        >
          <DialogContent
            className="sm:max-w-md"
            onInteractOutside={(e) => {
              if (!isLaunchError && launchStep !== 4) e.preventDefault();
            }}
          >
            <DialogHeader>
              <div
                className={cn(
                  "mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full transition-colors",
                  isLaunchError
                    ? "bg-destructive/10 text-destructive"
                    : launchStep === 4
                      ? "bg-green-100 text-green-600"
                      : "bg-primary/10 text-primary",
                )}
              >
                {isLaunchError ? (
                  <AlertCircle className="h-7 w-7" />
                ) : launchStep === 4 ? (
                  <Check className="h-7 w-7" />
                ) : isScheduledCampaign ? (
                  <CalendarClock className="h-7 w-7" />
                ) : (
                  <Rocket className="h-7 w-7" />
                )}
              </div>
              <DialogTitle className="text-center text-xl">
                {isLaunchError
                  ? "Launch Failed"
                  : launchStep === 4
                    ? "Success!"
                    : "Launching Campaign"}
              </DialogTitle>
              <DialogDescription className="text-center">
                {isLaunchError
                  ? "An error occurred during launch."
                  : "Please do not close this window."}
              </DialogDescription>
            </DialogHeader>

            {/* STEP TRACKER */}
            <div className="py-4 space-y-5 px-6">
              {/* Step 1: Audience */}
              <div className="flex items-start gap-4">
                <div className="mt-0.5 w-6 h-6 flex-shrink-0 flex justify-center items-center">
                  {launchStep > 1 ? (
                    <Check className="w-5 h-5 text-green-500" />
                  ) : launchStep === 1 && !isLaunchError ? (
                    <RefreshCw className="w-4 h-4 text-primary animate-spin" />
                  ) : isLaunchError && launchStep === 1 ? (
                    <X className="w-5 h-5 text-destructive" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                  )}
                </div>
                <div className="flex flex-col">
                  <span
                    className={cn(
                      "text-sm font-semibold",
                      launchStep >= 1
                        ? "text-foreground"
                        : "text-muted-foreground",
                    )}
                  >
                    Process Audience Target
                  </span>
                  {launchStep === 1 && (
                    <span className="text-xs text-muted-foreground animate-pulse mt-1">
                      {launchStatus}
                    </span>
                  )}
                </div>
              </div>

              {/* Step 2: Finalize */}
              <div className="flex items-start gap-4">
                <div className="mt-0.5 w-6 h-6 flex-shrink-0 flex justify-center items-center">
                  {launchStep > 2 ? (
                    <Check className="w-5 h-5 text-green-500" />
                  ) : launchStep === 2 && !isLaunchError ? (
                    <RefreshCw className="w-4 h-4 text-primary animate-spin" />
                  ) : isLaunchError && launchStep === 2 ? (
                    <X className="w-5 h-5 text-destructive" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                  )}
                </div>
                <div className="flex flex-col">
                  <span
                    className={cn(
                      "text-sm font-semibold",
                      launchStep >= 2
                        ? "text-foreground"
                        : "text-muted-foreground",
                    )}
                  >
                    Finalize Campaign Data
                  </span>
                  {launchStep === 2 && (
                    <span className="text-xs text-muted-foreground animate-pulse mt-1">
                      {launchStatus}
                    </span>
                  )}
                </div>
              </div>

              {/* Step 3: Trigger */}
              <div className="flex items-start gap-4">
                <div className="mt-0.5 w-6 h-6 flex-shrink-0 flex justify-center items-center">
                  {launchStep > 3 ? (
                    <Check className="w-5 h-5 text-green-500" />
                  ) : launchStep === 3 && !isLaunchError ? (
                    <RefreshCw className="w-4 h-4 text-primary animate-spin" />
                  ) : isLaunchError && launchStep === 3 ? (
                    <X className="w-5 h-5 text-destructive" />
                  ) : (
                    <div className="w-2 h-2 rounded-full bg-muted-foreground/30" />
                  )}
                </div>
                <div className="flex flex-col">
                  <span
                    className={cn(
                      "text-sm font-semibold",
                      launchStep >= 3
                        ? "text-foreground"
                        : "text-muted-foreground",
                    )}
                  >
                    {isScheduledCampaign
                      ? "Schedule Engine"
                      : "Trigger Engine Tasks"}
                  </span>
                  {launchStep === 3 && (
                    <span className="text-xs text-muted-foreground animate-pulse mt-1">
                      {launchStatus}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <DialogFooter className="sm:justify-center mt-2">
              {isLaunchError ? (
                <Button
                  variant="outline"
                  onClick={() => setIsLaunchSuccessOpen(false)}
                >
                  Close & Edit
                </Button>
              ) : (
                <Button
                  disabled={launchStep !== 4}
                  onClick={() => router.push("/")}
                  className="w-full sm:w-auto"
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
              {/* --- Replace the "Required Attributes" div with this conditional block --- */}

              {(selectedObjective === "new-car-launch" ||
                (selectedObjectiveData?.custom_campaign_attributes &&
                  selectedObjectiveData.custom_campaign_attributes.length >
                    0)) && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 pb-2 border-b">
                    <Edit3 className="h-4 w-4 text-primary" />
                    <h3 className="font-semibold leading-none tracking-tight">
                      Required Attributes
                    </h3>
                  </div>

                  {/* Car Model & Launch Date Inputs */}
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
                          Launch Date{" "}
                          <span className="text-destructive">*</span>
                        </Label>
                        <Input
                          type="date"
                          value={launchDate}
                          onChange={(e) => setLaunchDate(e.target.value)}
                        />
                      </div>
                    </div>
                  )}

                  {/* Dynamic Custom Attributes */}
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
                    ),
                  )}
                </div>
              )}
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
            // 1. Keep the view on "upload" card
            setAudienceSourceType("upload");

            // 2. Extract the new Task ID
            const newTaskId =
              dataSource?.connectionDetails?.taskId ||
              dataSource?.task_id ||
              dataSource?.id;

            if (newTaskId) {
              setTargetAudience([newTaskId]);

              // 3. Set initial details (Size might be 0 initially while backend processes)
              const initialSize =
                dataSource?.process_size ||
                dataSource?.total_records ||
                dataSource?.total ||
                0;
              setSelectedAudienceDetails({
                task_id: newTaskId,
                process_size: initialSize,
                source_name:
                  dataSource?.source_name ||
                  dataSource?.audience_name ||
                  "Newly Uploaded Audience",
              });

              // 4. Ping server after 3 seconds to get the fully processed size
              setTimeout(async () => {
                try {
                  const res: any = await fetchAudienceTasks(1, 10, "all");
                  const items = res.items || res.data || res || [];
                  const updatedTask = items.find(
                    (t: any) => t.task_id === newTaskId,
                  );
                  if (updatedTask) {
                    setSelectedAudienceDetails(updatedTask); // Updates size automatically
                  }
                } catch (e) {
                  console.error("Failed to refresh uploaded task size", e);
                }
              }, 3000);
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
                        : "hover:border-primary/50 hover:scale-[1.01]",
                    )}
                    onClick={() => setCampaignType("presales")}
                  >
                    <div
                      className={cn(
                        "p-4 rounded-full mb-6 transition-colors",
                        campaignType === "presales"
                          ? "bg-primary/20"
                          : "bg-primary/10",
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
                        : "hover:border-primary/50 hover:scale-[1.01]",
                    )}
                    onClick={() => setCampaignType("postsales")}
                  >
                    <div
                      className={cn(
                        "p-4 rounded-full mb-6 transition-colors",
                        campaignType === "postsales"
                          ? "bg-primary/20"
                          : "bg-primary/10",
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
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <h2 className="text-2xl font-bold flex items-center gap-2">
                        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground">
                          2
                        </span>
                        Select Objective
                      </h2>

                      {/* SERVER-SIDE SEARCH */}
                      <div className="relative w-full md:w-80">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          placeholder="Search objectives..."
                          className="pl-9 bg-background"
                          defaultValue={searchQuery}
                          onChange={(e) => {
                            const params = new URLSearchParams(searchParams);
                            params.set("q", e.target.value);
                            params.set("page", "1"); // Reset to page 1 on new search
                            router.replace(`${pathname}?${params.toString()}`, {
                              scroll: false,
                            });
                          }}
                        />
                      </div>
                    </div>

                    <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                      <CardContent className="pt-6">
                        <Tabs
                          value={activeTab}
                          onValueChange={(val) => {
                            setActiveTab(val);
                            // Reset page to 1 when switching tabs
                            const params = new URLSearchParams(searchParams);
                            params.set("page", "1");
                            router.replace(`${pathname}?${params.toString()}`, {
                              scroll: false,
                            });
                          }}
                        >
                          <TabsList className="mb-6 w-full justify-start h-auto p-1 bg-muted/50">
                            <TabsTrigger value="generic" className="px-6 py-2">
                              Generic
                            </TabsTrigger>
                            <TabsTrigger value="custom" className="px-6 py-2">
                              Custom
                            </TabsTrigger>
                            <TabsTrigger value="previous" className="px-6 py-2">
                              Previously Used
                            </TabsTrigger>
                          </TabsList>

                          <div className="space-y-6">
                            {isLoadingObjectives ? (
                              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {[1, 2, 3, 4, 5, 6].map((i) => (
                                  <div
                                    key={`loader-${i}`}
                                    className="h-40 rounded-xl bg-muted animate-pulse border"
                                  />
                                ))}
                              </div>
                            ) : (
                              <>
                                <div
                                  key={`grid-container-${activeTab}`}
                                  className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
                                >
                                  {displayObjectives.length > 0 ? (
                                    displayObjectives.map((obj) => (
                                      <ObjectiveCard
                                        key={`${activeTab}-${obj.id}`}
                                        {...obj}
                                        selected={selectedObjective === obj.id}
                                        onSelect={() => {
                                          setSelectedObjective(obj.objectiveId);
                                          setSelectedObjectiveData(
                                            obj.fullData || null,
                                          );
                                          setCampaignData(null);
                                          setCreatedCampaignId(null);
                                          // if (obj.id !== "custom-trigger") setIsObjectiveDetailsOpen(true);

                                          if (activeTab === "previous") {
                                            // CASE 1: Previously Used - No AI, just pre-fill
                                            prefillFromExistingCampaign(
                                              obj.fullData,
                                            );
                                            // Scroll down to the configuration section
                                            // window.scrollTo({ top: 400, behavior: "smooth" });
                                            setTimeout(() => {
                                              detailsRef.current?.scrollIntoView(
                                                {
                                                  behavior: "smooth",
                                                  block: "center",
                                                },
                                              );
                                            }, 100);
                                          } else if (obj.id !== "custom") {
                                            // CASE 2: Generic/Custom Templates - Open AI generation modal
                                            setIsObjectiveDetailsOpen(true);
                                          }
                                          //       if (obj.id !== "custom") {
                                          //   setIsObjectiveDetailsOpen(true);
                                          // }
                                        }}
                                      />
                                    ))
                                  ) : (
                                    <div className="col-span-full py-20 text-center border-2 border-dashed rounded-xl text-muted-foreground">
                                      No objectives found in this category.
                                    </div>
                                  )}
                                </div>
                                {selectedObjective === "custom" &&
                                  activeTab === "custom" && (
                                    <div className="mt-6 p-6 border-2 border-dashed rounded-xl bg-primary/5 animate-in fade-in slide-in-from-top-4">
                                      <Label className="mb-2 block font-bold">
                                        What is your campaign idea?
                                      </Label>
                                      <div className="flex gap-2">
                                        <Input
                                          placeholder="e.g. Special weekend service camp for monsoon..."
                                          value={customObjective}
                                          onChange={(e) =>
                                            setCustomObjective(e.target.value)
                                          }
                                          className="h-12 bg-background"
                                        />
                                        <Button
                                          onClick={handleGenerateCampaign}
                                          disabled={
                                            !customObjective || isGenerating
                                          }
                                          className="h-12 px-8"
                                        >
                                          {isGenerating ? (
                                            <RefreshCw className="animate-spin h-4 w-4" />
                                          ) : (
                                            "Generate"
                                          )}
                                        </Button>
                                      </div>
                                    </div>
                                  )}
                                {/* SHARED PAGINATION FOOTER */}
                                <div className="flex items-center justify-between pt-6 border-t border-dashed">
                                  <p className="text-xs text-muted-foreground font-medium">
                                    Page{" "}
                                    <span className="text-foreground">
                                      {currentPage}
                                    </span>{" "}
                                    — {totalNumber} Total Available
                                  </p>
                                  <div className="flex gap-2">
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      disabled={currentPage === 1}
                                      onClick={() => {
                                        const params = new URLSearchParams(
                                          searchParams,
                                        );
                                        params.set(
                                          "page",
                                          (currentPage - 1).toString(),
                                        );
                                        router.replace(
                                          `${pathname}?${params.toString()}`,
                                          { scroll: false },
                                        );
                                      }}
                                    >
                                      <ChevronLeft className="h-4 w-4 mr-1" />{" "}
                                      Previous
                                    </Button>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      disabled={isLastPage}
                                      onClick={() => {
                                        const params = new URLSearchParams(
                                          searchParams,
                                        );
                                        params.set(
                                          "page",
                                          (currentPage + 1).toString(),
                                        );
                                        router.replace(
                                          `${pathname}?${params.toString()}`,
                                          { scroll: false },
                                        );
                                      }}
                                    >
                                      Next{" "}
                                      <ChevronRight className="h-4 w-4 ml-1" />
                                    </Button>
                                  </div>
                                </div>
                              </>
                            )}
                          </div>
                        </Tabs>
                      </CardContent>
                    </Card>
                  </div>

                  {isGenerating && (
                    <Card className="py-12">
                      <div className="flex flex-col items-center justify-center gap-4">
                        <AILoader />
                        {generationStatusMsg && (
                          <p className="text-sm font-medium text-muted-foreground animate-pulse text-center px-4">
                            {generationStatusMsg}
                          </p>
                        )}
                      </div>
                    </Card>
                  )}

                  {/* DETAILS */}
                  {!isGenerating && campaignData && (
                    <div
                      ref={detailsRef}
                      className="space-y-8 animate-in fade-in duration-500"
                    >
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
                                  type="datetime"
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
                                  type="datetime"
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
                                  onChange={(e) =>
                                    setUrgencyHook(e.target.value)
                                  }
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
                              {channels.map((ch) => {
                                const isWhatsappDisabled =
                                  ch.id === "whatsapp" && !hasWhatsappTemplates;
                                return (
                                  <div
                                    key={ch.id}
                                    className="flex flex-col gap-1"
                                  >
                                    <Card
                                      className={cn(
                                        "border-2 transition-all h-full",
                                        isWhatsappDisabled
                                          ? "opacity-60 cursor-not-allowed border-slate-200 bg-slate-50"
                                          : "cursor-pointer",
                                        selectedChannels.includes(ch.id) &&
                                          !isWhatsappDisabled
                                          ? "border-primary bg-primary/5 shadow-sm"
                                          : !isWhatsappDisabled
                                            ? "opacity-50"
                                            : "",
                                      )}
                                      onClick={() => {
                                        if (isWhatsappDisabled) return;
                                        if (selectedChannels.includes(ch.id)) {
                                          setSelectedChannels(
                                            selectedChannels.filter(
                                              (c) => c !== ch.id,
                                            ),
                                          );
                                        } else {
                                          setSelectedChannels([
                                            ...selectedChannels,
                                            ch.id,
                                          ]);
                                        }
                                      }}
                                    >
                                      <CardContent className="flex flex-col items-center justify-center p-4 h-full">
                                        <div
                                          className={cn(
                                            "mb-2",
                                            selectedChannels.includes(ch.id) &&
                                              !isWhatsappDisabled
                                              ? "text-primary"
                                              : "text-muted-foreground",
                                          )}
                                        >
                                          {ch.icon}
                                        </div>
                                        <span className="font-semibold text-center text-sm">
                                          {ch.name}
                                        </span>
                                        {selectedChannels.includes(ch.id) &&
                                          !isWhatsappDisabled && (
                                            <Badge className="mt-2 bg-green-600">
                                              Active
                                            </Badge>
                                          )}
                                      </CardContent>
                                    </Card>
                                    {isWhatsappDisabled && (
                                      <span className="text-[10px] text-red-500 font-medium leading-tight text-center px-1 mt-1">
                                        WhatsApp is not available for this
                                        campaign objective due to no template
                                      </span>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            {/* NEW UI: Voice Call Configuration */}
                            {selectedChannels.includes("voice") && (
                              <div className="mt-6 space-y-4 p-4 border rounded-md bg-slate-50 dark:bg-slate-900/50">
                                <h4 className="font-semibold flex items-center gap-2 text-sm">
                                  <Phone className="h-4 w-4 text-primary" />{" "}
                                  Voice Call Configuration
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                  <div className="space-y-2">
                                    <Label>Voice Start Language</Label>
                                    <Select
                                      value={voiceStartLanguage}
                                      onValueChange={setVoiceStartLanguage}
                                    >
                                      <SelectTrigger>
                                        <SelectValue placeholder="Select language" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="en">
                                          English
                                        </SelectItem>
                                        <SelectItem value="hi">
                                          Hindi
                                        </SelectItem>
                                        <SelectItem value="ta">
                                          Tamil
                                        </SelectItem>
                                        <SelectItem value="ml">
                                          Malayalam
                                        </SelectItem>

                                        <SelectItem value="mr">
                                          Marathi
                                        </SelectItem>
                                        <SelectItem value="te">
                                          Telugu
                                        </SelectItem>
                                        <SelectItem value="kn">
                                          Kannada
                                        </SelectItem>
                                        <SelectItem value="bn">
                                          Bengali
                                        </SelectItem>
                                        <SelectItem value="gu">
                                          Gujarati
                                        </SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                  <div className="space-y-2">
                                    <Label>Voice Agent ID</Label>
                                    <Input
                                      value={voiceAgentId}
                                      onChange={(e) =>
                                        setVoiceAgentId(e.target.value)
                                      }
                                      placeholder="e.g. agent_..."
                                    />
                                  </div>
                                </div>
                              </div>
                            )}
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
                  {/* 3 Audience Source Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card
                      className={cn(
                        "cursor-pointer hover:border-primary transition-all text-center p-4",
                        audienceSourceType === "upload" &&
                          "border-primary bg-primary/5",
                      )}
                      onClick={() => {
                        setAudienceSourceType("upload");
                        setIsUploadDialogOpen(true);
                      }}
                    >
                      <Upload className="h-8 w-8 mx-auto mb-2 text-primary" />
                      <h4 className="font-semibold text-sm">
                        Upload New Audience
                      </h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        Upload via CSV/Excel
                      </p>
                    </Card>

                    <Card
                      className={cn(
                        "cursor-pointer hover:border-primary transition-all text-center p-4",
                        audienceSourceType === "previous" &&
                          "border-primary bg-primary/5",
                      )}
                      onClick={() => {
                        setAudienceSourceType("previous");
                        setTargetAudience([]);
                        setSelectedAudienceDetails(null);
                        setPage(1);
                      }}
                    >
                      <Database className="h-8 w-8 mx-auto mb-2 text-primary" />
                      <h4 className="font-semibold text-sm">Previously Used</h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        Clone from past campaigns
                      </p>
                    </Card>

                    <Card
                      className={cn(
                        "cursor-pointer hover:border-primary transition-all text-center p-4",
                        audienceSourceType === "fresh" &&
                          "border-primary bg-primary/5",
                      )}
                      onClick={() => {
                        setAudienceSourceType("fresh");
                        setTargetAudience([]);
                        setSelectedAudienceDetails(null);
                        setPage(1);
                      }}
                    >
                      <Users className="h-8 w-8 mx-auto mb-2 text-primary" />
                      <h4 className="font-semibold text-sm">
                        Unused Fresh Set
                      </h4>
                      <p className="text-xs text-muted-foreground mt-1">
                        Select unused leads
                      </p>
                    </Card>
                  </div>
                  {/* Render Uploaded Success State */}
                  {audienceSourceType === "upload" &&
                    targetAudience.length > 0 && (
                      <div className="space-y-2 animate-in fade-in slide-in-from-top-4">
                        <div className="p-4 border rounded-md bg-green-50 border-green-200 flex justify-between items-center">
                          <div>
                            <h4 className="font-semibold text-green-900 flex items-center gap-2">
                              <Check className="h-5 w-5 text-green-600" />{" "}
                              Audience Uploaded Successfully
                            </h4>
                            <p className="text-sm text-green-700 mt-1">
                              Selected:{" "}
                              {selectedAudienceDetails?.source_name ||
                                "Custom Audience"}
                            </p>
                            {/* <p className="text-xs text-green-600/80 mt-0.5 font-mono">
                            ID: {targetAudience[0]}
                          </p> */}
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <Badge className="bg-green-600 hover:bg-green-700">
                              Selected
                            </Badge>
                            {/* Show a loading indicator if size is 0 while waiting for background refresh */}
                            {parseInt(
                              selectedAudienceDetails?.process_size || 0,
                            ) === 0 && (
                              <span className="text-xs text-muted-foreground flex items-center gap-1 animate-pulse mt-1">
                                <RefreshCw className="h-3 w-3 animate-spin" />{" "}
                                Processing size...
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  {/* Render Selection list Conditionally */}
                  {(audienceSourceType === "previous" ||
                    audienceSourceType === "fresh") && (
                    <div className="space-y-4 animate-in fade-in slide-in-from-top-4 mt-4 p-4 border rounded-lg bg-slate-50/50">
                      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                        <Label className="font-semibold text-lg text-slate-800">
                          {audienceSourceType === "previous"
                            ? "Select Previously Used Audience"
                            : "Select Fresh Audience"}
                        </Label>
                        {/* Search Input */}
                        <div className="relative w-full sm:w-72">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            type="text"
                            placeholder="Search by name..."
                            value={audienceSearch}
                            onChange={(e) => {
                              setAudienceSearch(e.target.value);
                              setPage(1); // Reset page to 1 when searching
                            }}
                            className="pl-9 h-10 w-full bg-white shadow-sm border-slate-200 focus-visible:ring-primary"
                          />
                        </div>
                      </div>

                      {/* List/Table Container */}
                      <div className="border rounded-md overflow-hidden bg-white shadow-sm">
                        {isLoadingAudience ? (
                          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-2">
                            <RefreshCw className="h-6 w-6 animate-spin text-primary" />
                            <span className="text-sm">
                              Loading audience sets...
                            </span>
                          </div>
                        ) : (
                          <>
                            <div className="divide-y">
                              {audienceTasks.map((task) => {
                                const isSelected =
                                  targetAudience[0] === task.task_id;
                                return (
                                  <div
                                    key={task.task_id}
                                    onClick={() => {
                                      setTargetAudience([task.task_id]);
                                      setSelectedAudienceDetails(task);
                                    }}
                                    className={cn(
                                      "flex items-center justify-between p-4 cursor-pointer transition-all hover:bg-slate-50/80",
                                      isSelected &&
                                        "bg-primary/5 hover:bg-primary/10 border-l-4 border-l-primary",
                                    )}
                                  >
                                    <div className="space-y-1">
                                      <h5 className="font-medium text-slate-900">
                                        {task.audience_name || "Untitled List"}
                                      </h5>
                                      <p className="text-xs text-muted-foreground">
                                        Created:{" "}
                                        {task.created
                                          ? new Date(
                                              task.created * 1000,
                                            ).toLocaleDateString()
                                          : "N/A"}
                                        {" Source Name: "}
                                        {task.source_name || "Untitled List"}
                                      </p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                      <Badge
                                        variant="secondary"
                                        className="bg-slate-100 text-slate-700 font-semibold"
                                      >
                                        {parseInt(
                                          task.process_size || 0,
                                        ).toLocaleString()}{" "}
                                        Records
                                      </Badge>
                                      <div
                                        className={cn(
                                          "w-5 h-5 rounded-full border flex items-center justify-center transition-all",
                                          isSelected
                                            ? "border-primary bg-primary text-white"
                                            : "border-slate-300",
                                        )}
                                      >
                                        {isSelected && (
                                          <Check className="h-3 w-3 stroke-[3]" />
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })}

                              {audienceTasks.length === 0 && (
                                <div className="text-center py-12 text-muted-foreground">
                                  No{" "}
                                  {audienceSourceType === "previous"
                                    ? "previous"
                                    : "fresh"}{" "}
                                  audience lists found.
                                </div>
                              )}
                            </div>

                            {/* Pagination Controls */}
                            {totalPages > 1 && (
                              <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-t">
                                <span className="text-xs text-muted-foreground">
                                  Page{" "}
                                  <strong className="text-slate-800">
                                    {page}
                                  </strong>{" "}
                                  of{" "}
                                  <strong className="text-slate-800">
                                    {totalPages}
                                  </strong>
                                </span>
                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={page <= 1}
                                    onClick={(e) => {
                                      e.preventDefault();
                                      setPage((p) => p - 1);
                                    }}
                                    className="h-8 px-3"
                                  >
                                    <ChevronLeft className="h-4 w-4 mr-1" />{" "}
                                    Previous
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    disabled={page >= totalPages}
                                    onClick={(e) => {
                                      e.preventDefault();
                                      setPage((p) => p + 1);
                                    }}
                                    className="h-8 px-3"
                                  >
                                    Next{" "}
                                    <ChevronRight className="h-4 w-4 ml-1" />
                                  </Button>
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </div>

                      {targetAudience.length > 0 && (
                        <div className="p-3.5 bg-green-50/50 border border-green-200/60 rounded-md flex justify-between items-center text-sm animate-in fade-in zoom-in-95">
                          <div className="flex items-center gap-2 text-green-950 font-medium">
                            <Check className="h-4 w-4 text-green-600 stroke-[3]" />
                            <span>
                              Selected:{" "}
                              {selectedAudienceDetails?.source_name ||
                                selectedAudienceDetails?.audience_name ||
                                "Custom Segment"}
                            </span>
                          </div>
                          <span className="text-xs text-green-700 font-mono bg-green-100/50 px-2 py-0.5 rounded">
                            ID: {targetAudience[0]}
                          </span>
                        </div>
                      )}
                    </div>
                  )}
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
                          (c) => c.id === channelId,
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
                        <span>Estimated Credits Required </span>
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
