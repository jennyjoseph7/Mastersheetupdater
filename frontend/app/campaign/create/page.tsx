"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, API_BASE_URL } from "@/lib/api";
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
import { ProtectedRoute } from "@/components/protected-route";
import {
  MessageSquare,
  Mail,
  Phone,
  Facebook,
  Instagram,
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AILoader } from "@/components/ui/ai-loader";

// Helper function to get icon for objective
const getObjectiveIcon = (objectiveId: string, title: string) => {
  const id = objectiveId.toLowerCase();
  const titleLower = title.toLowerCase();

  if (
    id.includes("car") ||
    id.includes("launch") ||
    titleLower.includes("car") ||
    titleLower.includes("launch")
  ) {
    return <Car className="h-6 w-6" />;
  }
  if (
    id.includes("festive") ||
    id.includes("sale") ||
    titleLower.includes("festive") ||
    titleLower.includes("sale")
  ) {
    return <PartyPopper className="h-6 w-6" />;
  }
  if (
    id.includes("stock") ||
    id.includes("clearance") ||
    titleLower.includes("stock") ||
    titleLower.includes("clearance")
  ) {
    return <Tag className="h-6 w-6" />;
  }
  if (
    id.includes("test") ||
    id.includes("drive") ||
    titleLower.includes("test") ||
    titleLower.includes("drive")
  ) {
    return <TrendingUp className="h-6 w-6" />;
  }
  if (id === "custom" || titleLower.includes("custom")) {
    return <Edit3 className="h-6 w-6" />;
  }
  return <Target className="h-6 w-6" />;
};

// Default pre-sales objectives
const defaultPreSalesObjectives = [
  {
    id: "new-car-launch",
    title: "New Car Launch",
    campaignSubType: undefined,
    icon: <Car className="h-6 w-6" />,
  },
  {
    id: "festive-sale",
    title: "Festive Sale",
    campaignSubType: undefined,
    icon: <PartyPopper className="h-6 w-6" />,
  },
  {
    id: "stock-clearance",
    title: "Stock Clearance",
    campaignSubType: undefined,
    icon: <Tag className="h-6 w-6" />,
  },
  {
    id: "test-drive",
    title: "Test Drive Campaign",
    campaignSubType: undefined,
    icon: <TrendingUp className="h-6 w-6" />,
  },
  {
    id: "custom",
    title: "Custom Objective",
    campaignSubType: undefined,
    icon: <Edit3 className="h-6 w-6" />,
  },
];

const postSalesObjectives = [
  {
    id: "service-reminder",
    title: "Service Reminder",
    campaignSubType: undefined,
    icon: <Wrench className="h-6 w-6" />,
  },
  {
    id: "seasonal-service",
    title: "Seasonal Service",
    campaignSubType: undefined,
    icon: <Sun className="h-6 w-6" />,
  },
  {
    id: "loyalty-reward",
    title: "Loyalty Rewards",
    campaignSubType: undefined,
    icon: <Heart className="h-6 w-6" />,
  },
  {
    id: "referral",
    title: "Referral Program",
    campaignSubType: undefined,
    icon: <Gift className="h-6 w-6" />,
  },
  {
    id: "custom",
    title: "Custom Objective",
    icon: <Edit3 className="h-6 w-6" />,
  },
];

const channels = [
  {
    id: "whatsapp",
    name: "WhatsApp",
    icon: <MessageSquare className="h-6 w-6" />,
  },
  { id: "email", name: "Email", icon: <Mail className="h-6 w-6" /> },
  { id: "voice", name: "Voice", icon: <Phone className="h-6 w-6" /> },
  { id: "facebook", name: "Facebook", icon: <Facebook className="h-6 w-6" /> },
  {
    id: "instagram",
    name: "Instagram",
    icon: <Instagram className="h-6 w-6" />,
  },
];

const audienceSegments = [
  { value: "high-intent", label: "High Intent Leads", size: 1500 },
  { value: "new-customers", label: "New Customers", size: 3000 },
  { value: "active", label: "Active Customers", size: 8500 },
  { value: "premium", label: "Premium Customers", size: 500 },
  { value: "inactive", label: "Inactive Customers", size: 2200 },
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

function CampaignCreateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [campaignType, setCampaignType] = useState<
    "presales" | "postsales" | ""
  >("");
  const [isLaunchSuccessOpen, setIsLaunchSuccessOpen] = useState(false);
  const [launchStatus, setLaunchStatus] = useState("");
  const [isLaunchError, setIsLaunchError] = useState(false);
  const [selectedObjective, setSelectedObjective] = useState("");
  const [selectedObjectiveData, setSelectedObjectiveData] = useState<any>(null);
  const [customObjective, setCustomObjective] = useState("");

  const [isGenerating, setIsGenerating] = useState(false);
  const [campaignData, setCampaignData] = useState<any>(null);

  const [campaignName, setCampaignName] = useState("");
  const [campaignDescription, setCampaignDescription] = useState("");
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [duration, setDuration] = useState({ start: "", end: "" });
  const [campaignTitle, setCampaignTitle] = useState("");
  const [tone, setTone] = useState("");
  const [callToAction, setCallToAction] = useState("");
  const [language, setLanguage] = useState("en");
  const [targetAudience, setTargetAudience] = useState<string[]>([]);
  const [customAudience, setCustomAudience] = useState<{
    region: string[];
    vehicleType: string[];
    customerStatus: string[];
  }>({ region: [], vehicleType: [], customerStatus: [] });

  // Car details for specific objectives
  const [carModel, setCarModel] = useState("");
  const [launchDate, setLaunchDate] = useState("");
  const [activeTab, setActiveTab] = useState("setup");
  const [preSalesObjectives, setPreSalesObjectives] = useState(
    defaultPreSalesObjectives
  );
  const [fetchedPostSalesObjectives, setFetchedPostSalesObjectives] =
    useState(postSalesObjectives);
  const [isLoadingObjectives, setIsLoadingObjectives] = useState(false);

  // New state to control the objective details dialog
  const [isObjectiveDetailsOpen, setIsObjectiveDetailsOpen] = useState(false);

  useEffect(() => {
    const isNew = searchParams.get("new");
    if (isNew === "true") {
      localStorage.removeItem("campaignFormData");
      router.replace("/campaign/create", { scroll: false });
    }
  }, [searchParams, router]);

  useEffect(() => {
    const formData = {
      campaignType,
      selectedObjective,
      customObjective,
      campaignData,
      campaignName,
      campaignDescription,
      selectedChannels,
      duration,
      campaignTitle,
      tone,
      callToAction,
      language,
      targetAudience,
      customAudience,
      carModel,
      launchDate,
    };
    localStorage.setItem("campaignFormData", JSON.stringify(formData));
  }, [
    campaignType,
    selectedObjective,
    customObjective,
    campaignData,
    campaignName,
    campaignDescription,
    selectedChannels,
    duration,
    campaignTitle,
    tone,
    callToAction,
    language,
    targetAudience,
    customAudience,
    carModel,
    launchDate,
  ]);

  useEffect(() => {
    const saved = localStorage.getItem("campaignFormData");
    if (saved) {
      try {
        const data = JSON.parse(saved);
        setCampaignType(data.campaignType || "");
        setSelectedObjective(""); // Reset selection to force fresh flow
        setCustomObjective(data.customObjective || "");
        setCampaignData(data.campaignData || null);
        setCampaignName(data.campaignName || "");
        setCampaignDescription(data.campaignDescription || "");
        setSelectedChannels(data.selectedChannels || []);
        setDuration(data.duration || { start: "", end: "" });
        setCampaignTitle(data.campaignTitle || "");
        setTone(data.tone || "");
        setCallToAction(data.callToAction || "");
        setLanguage(data.language || "en");
        setTargetAudience(data.targetAudience || []);
        setCustomAudience(
          data.customAudience || {
            region: [],
            vehicleType: [],
            customerStatus: [],
          }
        );
        setCarModel(data.carModel || "");
        setLaunchDate(data.launchDate || "");
      } catch (error) {
        console.error("Error restoring form data:", error);
      }
    }
  }, []);

  useEffect(() => {
    setSelectedObjective("");
    setCustomObjective("");
    setCampaignData(null);
  }, [campaignType]);

  // Fetch pre-sales objectives
  useEffect(() => {
    const fetchPreSalesObjectives = async () => {
      if (campaignType === "presales") {
        setIsLoadingObjectives(true);
        try {
          const response = await api(
            "/gryd/db/objects/campaign_objective?campaign_type=pre-sales",
            "GET",
            undefined,
            { "X-GRYD-ROLE": "admin" }
          );

          if (Array.isArray(response)) {
            const usedIds = new Set<string>();
            const mappedObjectives = response.map((obj: any, index: number) => {
              let id = obj.id || obj.objective_id;
              if (!id || id === "") {
                const baseId = (obj.name || obj.title || obj.objective_name || `objective-${index}`)
                  .toLowerCase()
                  .replace(/\s+/g, "-")
                  .replace(/[^a-z0-9-]/g, "");
                id = baseId;
                let counter = 0;
                while (usedIds.has(id)) { id = `${baseId}-${counter}`; counter++; }
              }
              if (!id || id === "") { id = `objective-${index}`; }
              usedIds.add(id);

              const title = obj.title || obj.name || obj.objective_name || "";
              const campaignSubType = obj.campaign_sub_type || obj.campaignSubType || "";
              return {
                id,
                title,
                campaignSubType,
                icon: getObjectiveIcon(id, title),
                fullData: obj,
              };
            });
            mappedObjectives.push({
              id: "custom",
              title: "Custom Objective",
              campaignSubType: undefined,
              icon: <Edit3 className="h-6 w-6" />,
              fullData: null,
            });
            setPreSalesObjectives(mappedObjectives);
          } else if (response.data && Array.isArray(response.data)) {
            const usedIds = new Set<string>();
            const mappedObjectives = response.data.map((obj: any, index: number) => {
              let id = obj.id || obj.objective_id;
              if (!id || id === "") {
                const baseId = (obj.name || obj.title || obj.objective_name || `objective-${index}`)
                  .toLowerCase()
                  .replace(/\s+/g, "-")
                  .replace(/[^a-z0-9-]/g, "");
                id = baseId;
                let counter = 0;
                while (usedIds.has(id)) { id = `${baseId}-${counter}`; counter++; }
              }
              if (!id || id === "") { id = `objective-${index}`; }
              usedIds.add(id);

              const title = obj.title || obj.name || obj.objective_name || "";
              const campaignSubType = obj.campaign_sub_type || obj.campaignSubType || "";
              return {
                id,
                title,
                campaignSubType,
                icon: getObjectiveIcon(id, title),
                fullData: obj,
              };
            });
            mappedObjectives.push({
              id: "custom",
              title: "Custom Objective",
              campaignSubType: undefined,
              icon: <Edit3 className="h-6 w-6" />,
            });
            setPreSalesObjectives(mappedObjectives);
          }
        } catch (error) {
          console.error("Error fetching campaign objectives:", error);
          setPreSalesObjectives(defaultPreSalesObjectives);
        } finally {
          setIsLoadingObjectives(false);
        }
      } else {
        setPreSalesObjectives(defaultPreSalesObjectives);
      }
    };
    fetchPreSalesObjectives();
  }, [campaignType]);

  // Fetch post-sales objectives
  useEffect(() => {
    const fetchPostSalesObjectives = async () => {
      if (campaignType === "postsales") {
        setIsLoadingObjectives(true);
        try {
          const apiUrl = `/api/campaign-objectives?campaign_type=post-sales`;
          const response = await fetch(apiUrl, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json",
            },
            cache: "no-store",
          });

          if (!response.ok) throw new Error(`API Error: ${response.status}`);
          const responseData = await response.json();
          const objectivesArray = Array.isArray(responseData)
            ? responseData
            : responseData.data && Array.isArray(responseData.data)
            ? responseData.data
            : [];

          if (objectivesArray.length > 0) {
            const usedIds = new Set<string>();
            const mappedObjectives = objectivesArray.map((obj: any, index: number) => {
              let id = obj.campaign_objective_id || obj.id || obj.objective_id;
              if (!id || id === "") {
                const baseId = (obj.campaign_objective_name || obj.name || obj.title || obj.objective_name || `objective-${index}`)
                  .toLowerCase()
                  .replace(/\s+/g, "-")
                  .replace(/[^a-z0-9-]/g, "");
                id = baseId;
                let counter = 0;
                while (usedIds.has(id)) { id = `${baseId}-${counter}`; counter++; }
              }
              if (!id || id === "") { id = `objective-${index}`; }
              usedIds.add(id);

              const title = obj.campaign_objective_name || obj.title || obj.name || obj.objective_name || "";
              const campaignSubType = obj.campaign_sub_type || obj.campaignSubType || "";
              return {
                id,
                title,
                campaignSubType,
                icon: getObjectiveIcon(id, title),
                fullData: obj,
              };
            });
            mappedObjectives.push({
              id: "custom",
              title: "Custom Objective",
              campaignSubType: undefined,
              icon: <Edit3 className="h-6 w-6" />,
              fullData: null,
            });
            setFetchedPostSalesObjectives(mappedObjectives);
          } else {
            setFetchedPostSalesObjectives(postSalesObjectives);
          }
        } catch (error) {
          console.error("Error fetching post-sales campaign objectives:", error);
          setFetchedPostSalesObjectives(postSalesObjectives);
        } finally {
          setIsLoadingObjectives(false);
        }
      } else {
        setFetchedPostSalesObjectives(postSalesObjectives);
      }
    };
    fetchPostSalesObjectives();
  }, [campaignType]);

  // Handle generating campaign
  const handleGenerateCampaign = async () => {
    // Basic validation
    if (!selectedObjective && !customObjective) return;
    
    setIsGenerating(true);

    try {
      const objectiveText = selectedObjective === "custom"
          ? customObjective
          : [...preSalesObjectives, ...fetchedPostSalesObjectives].find(o => o.id === selectedObjective)?.title || "";

      let enhancedObjectiveText = objectiveText;
      // Add standard car details to objective text if needed, mostly for logging/reference
      if (carModel && selectedObjective === "new-car-launch") {
          enhancedObjectiveText = `${objectiveText} for ${carModel}`;
      }

      // Prepare Custom Objects
      const customObjects: Record<string, any> = {};

      // 1. Add attributes from the selected objective data (dynamic fields)
      if (selectedObjectiveData?.custom_attributes && Array.isArray(selectedObjectiveData.custom_attributes)) {
          selectedObjectiveData.custom_attributes.forEach((attr: any) => {
              if (attr.attribute_name && attr.attribute_value) {
                  customObjects[attr.attribute_name] = attr.attribute_value;
              }
          });
      }

      // 2. Add specific fields captured in the UI
      if (carModel) customObjects["Car Model"] = carModel;
      if (launchDate) customObjects["Launch Date"] = launchDate;

      // 3. Construct Campaign Offer text
      let offerText = campaignDescription || "Exclusive offers and rewards await!";
      if (selectedObjectiveData) {
          if (selectedObjectiveData.campaign_objective_description) {
              offerText = selectedObjectiveData.campaign_objective_description;
          }
          if (selectedObjectiveData.why_user_should_avail_this) {
              offerText += `\n\nValue Proposition: ${selectedObjectiveData.why_user_should_avail_this}`;
          }
      }

      // Payload Construction
      const payload = {
        args: [
          campaignType === "presales" ? "pre-sale" : "post-sale",
          enhancedObjectiveText,
        ],
        kwargs: {
          dealership_idea: {
            languages: [
              languageOptions.find((l) => l.value === language)?.label || "English",
            ],
            campaign_offer: offerText,
            custom_objects: customObjects,
          },
        },
      };

      console.log("Generating campaign with payload:", JSON.stringify(payload, null, 2));

      const data = await api(
        "/gryd/api/autocrm-agent/generate_campaign_idea",
        "POST",
        payload
      );
      
      console.log("Generated campaign idea", data);

      const generated = {
        name: data.campaign_name,
        description: data.campaign_description,
        campaignTitle: data.campaign_tagline,
        tone: data.campaign_tone,
        callToAction: data.ctas?.[0] || "Learn More",
        language: data.languages?.[0] || "English",
        selectedChannels: data.channels?.map((ch: string) => ch.replace("_chat", "")) || [],
        campaignOffer: data.campaign_offer,
        urgencyHook: data.urgency_hook,
        campaignObjective: data.campaign_objective,
      };

      setCampaignData(generated);
      setCampaignName(generated.name);
      setCampaignDescription(generated.description);
      setSelectedChannels(generated.selectedChannels);
      setCampaignTitle(generated.campaignTitle);
      setTone(generated.tone);
      setCallToAction(generated.callToAction);
      setLanguage(generated.language);
    } catch (error) {
      console.error("Error generating campaign:", error);
      alert("Failed to generate campaign. Please try again.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRegenerate = async () => {
    setCampaignData(null);
    await handleGenerateCampaign();
  };

  const toggleChannel = (channelId: string) => {
    setSelectedChannels((prev) =>
      prev.includes(channelId)
        ? prev.filter((id) => id !== channelId)
        : [...prev, channelId]
    );
  };

  const toggleAudience = (audienceId: string) => {
    setTargetAudience((prev) =>
      prev.includes(audienceId)
        ? prev.filter((id) => id !== audienceId)
        : [...prev, audienceId]
    );
  };

  const calculateCredits = () => {
    const totalAudience = audienceSegments
      .filter((seg) => targetAudience.includes(seg.value))
      .reduce((sum, seg) => sum + seg.size, 0);

    const whatsappCredits = selectedChannels.includes("whatsapp") ? totalAudience * 5 : 0;
    const emailCredits = selectedChannels.includes("email") ? totalAudience * 1 : 0;
    const voiceCredits = selectedChannels.includes("voice") ? totalAudience * 10 : 0;

    return whatsappCredits + emailCredits + voiceCredits;
  };

 const handleLaunch = async () => {
    // 1. Validation
    if (!campaignName || !duration.start || !duration.end) {
      alert("Please fill in all required fields (Name, Start Date, End Date)");
      return;
    }

    // 2. Helpers
    const toEpoch = (dateStr: string) => Math.floor(new Date(dateStr).getTime() / 1000);
    
    const mapChannels = (channels: string[]) => {
      const map: Record<string, string> = {
        whatsapp: "whatsapp_chat",
        email: "email",
        voice: "voice_phone",
        facebook: "facebook",
        instagram: "instagram",
        web: "web_chat",
      };
      return channels.map((c) => map[c] || c);
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

    // 3. Prepare Payloads
    const commonPayload = {
      campaign_name: campaignName,
      campaign_description: campaignDescription,
      campaign_status: "Active",
      start_date: toEpoch(duration.start),
      end_date: toEpoch(duration.end),
      channels: mapChannels(selectedChannels),
      languages: [mapLanguage(language)],
      campaign_offer: campaignData?.campaignOffer || campaignDescription,
      urgency_hook: [campaignData?.urgencyHook || ""],
      ctas: [callToAction],
      number_targeted: totalAudienceSize,
      budget_allocated: calculateCredits(),
      campaign_objective: selectedObjective === "custom" ? customObjective : selectedObjectiveData?.title || selectedObjective,
      campaign_sub_type: selectedObjectiveData?.campaignSubType || "General",
      
      // Defaults
      cost_per_lead: 0,
      actual_spent: 0,
      number_engaged: 0,
      number_reached: 0,
      number_contacted: 0,
      number_converted: 0,
      conversion_rate_percent: 0,
       campaign_user_source: "file",

      
    };

    // --- START MODAL & LOADING STATE ---
    setIsLaunchSuccessOpen(true);
    setIsLaunchError(false);
    setLaunchStatus("Creating campaign records...");

    try {
      let createEndpoint = "";
      let createPayload = {};
      let taskCampaignType = ""; 

      if (campaignType === "presales") {
        createEndpoint = "/gryd/db/object/pre_sales_campaign";
        taskCampaignType = "pre-sales";
        createPayload = {
          ...commonPayload,
          campaign_type: "pre-sales",
          dealership_id: "nexa-delhi-south-nexa-dealer-group-north-india",
          region_id: "north-india",
          dealer_name: "NEXA Delhi South",
          supported_brands: ["NEXA"],
        };
      } else {
        createEndpoint = "/gryd/db/object/post_sales_campaign";
        taskCampaignType = "post-sales";
        createPayload = {
          ...commonPayload,
          campaign_type: "post_sales",
          workshop_id: "ambal-auto - ambal-auto---service-center - coimbatore",
          dealership_id: "nexa-delhi-south-nexa-dealer-group-north-india",
          campaign_objective_type: ["lead volume"],
        };
      }

      // --- STEP 1: CREATE CAMPAIGN IN DB ---
      const createResponse = await api(createEndpoint, "POST", createPayload);
      
      const newCampaignId = createResponse?.data?.id || createResponse?.id || createResponse?.campaign_id;

      if (!newCampaignId) {
        throw new Error("Campaign created but ID was not returned.");
      }

      // --- STEP 2: TRIGGER TASK ---
      setLaunchStatus("Triggering campaign engine...");
      
      const triggerPayload = {
        args: [],
        kwargs: {
          campaign_type: taskCampaignType,
          campaign_id: newCampaignId
        }
      };

      await api(
        "/gryd/task/autocrm-campaign/trigger_campaign",
        "POST",
        triggerPayload
      );

      // --- FINISH ---
      setLaunchStatus("Campaign launched successfully!");
      
      // Cleanup local storage after success
      setTimeout(() => {
        localStorage.removeItem("campaignFormData");
      }, 500);

    } catch (error) {
      console.error("Launch Failed:", error);
      setIsLaunchError(true);
      setLaunchStatus("Launch failed. Please try again.");
    }
  };

  const objectives = campaignType === "presales" ? preSalesObjectives : fetchedPostSalesObjectives;
  const totalAudienceSize = audienceSegments
    .filter((seg) => targetAudience.includes(seg.value))
    .reduce((sum, seg) => sum + seg.size, 0);

  return (
    <ProtectedRoute>
      <div className="pb-24">
        {/* EDIT CAMPAIGN DETAILS DIALOG */}
        <Dialog open={isObjectiveDetailsOpen} onOpenChange={setIsObjectiveDetailsOpen}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Edit3 className="h-5 w-5 text-primary" />
                Review Campaign Details
              </DialogTitle>
              <DialogDescription>
                Confirm objective details and fill in required attributes.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-4">
              {/* SECTION 1: CAMPAIGN INFO (Read Only) */}
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
                            {selectedObjectiveData.why_user_should_avail_this && (
                                <div className="space-y-1 md:col-span-2">
                                    <Label className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Value Proposition</Label>
                                    <div className="text-sm text-foreground/80 leading-relaxed bg-emerald-50/50 dark:bg-emerald-900/10 p-3 rounded-md border border-emerald-100 dark:border-emerald-900/20">
                                        {selectedObjectiveData.why_user_should_avail_this}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                 </div>
              )}

              {/* SECTION 2: REQUIRED ATTRIBUTES (Editable) */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 pb-2 border-b">
                     <Edit3 className="h-4 w-4 text-primary" />
                     <h3 className="font-semibold leading-none tracking-tight">Required Attributes</h3>
                </div>

                {/* Special Inputs for New Car Launch */}
                {selectedObjective === "new-car-launch" && (
                    <Card className="border-primary/20 bg-primary/5">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Car className="h-4 w-4" /> Launch Specifics
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="dialog-car">Car Model <span className="text-destructive">*</span></Label>
                                    <Input 
                                        id="dialog-car" 
                                        value={carModel} 
                                        onChange={(e) => setCarModel(e.target.value)} 
                                        placeholder="e.g. Vitara Brezza" 
                                        className="bg-background"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="dialog-date">Launch Date <span className="text-destructive">*</span></Label>
                                    <Input 
                                        id="dialog-date" 
                                        type="date" 
                                        value={launchDate} 
                                        onChange={(e) => setLaunchDate(e.target.value)} 
                                        className="bg-background"
                                    />
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Special Inputs for Stock Clearance */}
                {selectedObjective === "stock-clearance" && (
                    <Card className="border-primary/20 bg-primary/5">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Tag className="h-4 w-4" /> Clearance Specifics
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="dialog-stock">Car Model / Type <span className="text-destructive">*</span></Label>
                                <Input 
                                    id="dialog-stock" 
                                    value={carModel} 
                                    onChange={(e) => setCarModel(e.target.value)} 
                                    placeholder="e.g. All 2023 Models" 
                                    className="bg-background"
                                />
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Dynamic Custom Attributes */}
                {selectedObjectiveData?.custom_attributes &&
                  Array.isArray(selectedObjectiveData.custom_attributes) &&
                  selectedObjectiveData.custom_attributes.length > 0 ? (
                    <div className="grid grid-cols-1 gap-3">
                        {selectedObjectiveData.custom_attributes.map((attr: any, idx: number) => (
                            <Card key={idx} className="bg-muted/30 border-dashed hover:border-solid transition-colors">
                                <CardContent className="p-4">
                                    <div className="space-y-2">
                                        <div className="flex justify-between items-center">
                                            <Label className="text-sm font-medium">
                                                {attr.attribute_name || `Attribute ${idx + 1}`}
                                                <span className="text-destructive ml-1">*</span>
                                            </Label>
                                            <Badge variant="secondary" className="text-[10px] uppercase tracking-wider">{attr.attribute_type || "text"}</Badge>
                                        </div>
                                        <Input
                                            value={attr.attribute_value || ""}
                                            placeholder={`Enter ${attr.attribute_name}...`}
                                            onChange={(e) => {
                                                const updatedAttrs = [...selectedObjectiveData.custom_attributes];
                                                updatedAttrs[idx] = { ...attr, attribute_value: e.target.value };
                                                setSelectedObjectiveData({ ...selectedObjectiveData, custom_attributes: updatedAttrs });
                                            }}
                                            className="bg-background"
                                        />
                                        {attr.attribute_description && (
                                            <p className="text-xs text-muted-foreground">{attr.attribute_description}</p>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                  ) : (
                    // Show message if no extra attributes needed and not a special type
                    (selectedObjective !== "new-car-launch" && selectedObjective !== "stock-clearance") && (
                        <div className="flex items-center justify-center p-8 border-2 border-dashed rounded-lg text-muted-foreground">
                            <p>No additional attributes required for this objective.</p>
                        </div>
                    )
                  )}
              </div>
            </div>
            
            <DialogFooter>
                <Button variant="outline" onClick={() => setIsObjectiveDetailsOpen(false)}>Cancel</Button>
                <Button onClick={() => { setIsObjectiveDetailsOpen(false); handleGenerateCampaign(); }}>
                    <Sparkles className="mr-2 h-4 w-4" />
                    Generate Campaign
                </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

{/* LAUNCH STATUS MODAL */}
        <Dialog 
          open={isLaunchSuccessOpen} 
          onOpenChange={(open) => {
            // Prevent closing while loading (only allow close on error or success)
            if (!open && !isLaunchError && launchStatus !== "Campaign launched successfully!") {
              return; 
            }
            setIsLaunchSuccessOpen(open);
          }}
        >
          <DialogContent className="sm:max-w-md text-center" onInteractOutside={(e) => {
             // Prevent clicking outside to close while loading
             if (!isLaunchError && launchStatus !== "Campaign launched successfully!") {
                e.preventDefault();
             }
          }}>
            <DialogHeader>
              <div className={cn(
                "mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full transition-colors duration-300",
                isLaunchError ? "bg-red-100" : "bg-green-100"
              )}>
                {isLaunchError ? (
                   <AlertCircle className="h-6 w-6 text-red-600" />
                ) : (
                   <Rocket className="h-6 w-6 text-green-600" />
                )}
              </div>
              <DialogTitle className="text-center text-xl">
                {isLaunchError ? "Launch Error" : "Launching Campaign"}
              </DialogTitle>
              <DialogDescription className="text-center">
                {isLaunchError 
                  ? "We encountered an issue while launching your campaign." 
                  : "Please wait while we set up your campaign and audience."}
              </DialogDescription>
            </DialogHeader>
            
            <div className="py-6 space-y-4">
              <div className="flex flex-col items-center gap-4">
                {isLaunchError ? (
                   <X className="h-10 w-10 text-red-500 animate-in zoom-in duration-300" />
                ) : launchStatus === "Campaign launched successfully!" ? (
                   <Check className="h-10 w-10 text-green-500 animate-in zoom-in duration-300" />
                ) : (
                   <RefreshCw className="h-10 w-10 text-primary animate-spin" />
                )}
                
                <p className={cn(
                  "text-sm font-medium transition-colors",
                  isLaunchError ? "text-red-600" : "text-muted-foreground"
                )}>
                  {launchStatus}
                </p>
              </div>
            </div>

            <DialogFooter className="sm:justify-center gap-2">
              {isLaunchError ? (
                <Button 
                   variant="outline"
                   onClick={() => setIsLaunchSuccessOpen(false)}
                >
                  Close & Retry
                </Button>
              ) : (
                <Button 
                  className="w-full sm:w-auto min-w-[140px]" 
                  onClick={() => router.push("/")}
                  disabled={launchStatus !== "Campaign launched successfully!"}
                >
                  {launchStatus === "Campaign launched successfully!" ? "Go to Dashboard" : "Processing..."}
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <div className="w-full px-4 py-8 md:px-6 lg:px-8">
          <div className="mx-auto max-w-5xl space-y-8">
            {!campaignType && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div className="text-center space-y-3">
                  <h1 className="text-4xl font-bold tracking-tight">
                    Create Campaign
                  </h1>
                  <p className="text-lg text-muted-foreground">
                    Step 1: Choose your campaign type to get started
                  </p>
                </div>

                <Card className="shadow-xl border-2">
                  <CardHeader>
                    <CardTitle className="text-2xl">
                      Select Campaign Type
                    </CardTitle>
                    <CardDescription className="text-base">
                      Are you targeting new customers or engaging existing ones?
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <Card
                        className="cursor-pointer transition-all hover:shadow-xl hover:scale-[1.02] duration-300 border-2 hover:border-primary/50"
                        onClick={() => setCampaignType("presales")}
                      >
                        <CardContent className="flex flex-col items-center justify-center p-12">
                          <div className="mb-6 p-5 rounded-full bg-primary/10">
                            <Target className="h-20 w-20 text-primary" />
                          </div>
                          <h3 className="font-bold text-2xl mb-3">Pre-Sales</h3>
                          <p className="text-muted-foreground text-center leading-relaxed">
                            Generate leads, launch new products, and drive
                            customer acquisition
                          </p>
                        </CardContent>
                      </Card>

                      <Card
                        className="cursor-pointer transition-all hover:shadow-xl hover:scale-[1.02] duration-300 border-2 hover:border-primary/50"
                        onClick={() => {
                          setCampaignType("postsales");
                        }}
                      >
                        <CardContent className="flex flex-col items-center justify-center p-12">
                          <div className="mb-6 p-5 rounded-full bg-primary/10">
                            <Users className="h-20 w-20 text-primary" />
                          </div>
                          <h3 className="font-bold text-2xl mb-3">
                            Post-Sales
                          </h3>
                          <p className="text-muted-foreground text-center leading-relaxed">
                            Retain customers, increase loyalty, and boost repeat
                            business
                          </p>
                        </CardContent>
                      </Card>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {campaignType && (
              <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-700">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <h1 className="text-4xl font-bold tracking-tight">
                      Campaign Manager
                    </h1>
                    <p className="text-lg text-muted-foreground capitalize">
                      Step 2: {campaignType} Campaign Objective
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    onClick={() => setCampaignType("")}
                    className="gap-2"
                  >
                    <X className="h-4 w-4" />
                    Change Type
                  </Button>
                </div>

                <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-full bg-primary/10">
                          <Sparkles className="h-7 w-7 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-2xl">
                            Campaign Objective
                          </CardTitle>
                          <CardDescription className="text-base">
                            Select your goal - AI will generate everything
                            automatically
                          </CardDescription>
                        </div>
                      </div>
                      {campaignData && (
                        <Button
                          variant="outline"
                          onClick={handleRegenerate}
                          className="gap-2 bg-transparent"
                          disabled={isGenerating}
                        >
                          <RefreshCw
                            className={cn(
                              "h-4 w-4",
                              isGenerating && "animate-spin"
                            )}
                          />
                          Regenerate
                        </Button>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <Tabs
                      value={activeTab}
                      onValueChange={setActiveTab}
                      className="w-full"
                    >
                      <TabsList className="grid w-full grid-cols-2 mb-6 h-12 bg-muted/50">
                        <TabsTrigger
                          value="setup"
                          className="text-base font-semibold data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                        >
                          <Target className="h-4 w-4 mr-2" />
                          Campaign Objectives
                        </TabsTrigger>
                        <TabsTrigger
                          value="previous"
                          className="text-base font-semibold data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                        >
                          <ImageIcon className="h-4 w-4 mr-2" />
                          Previously Used Campaigns
                        </TabsTrigger>
                      </TabsList>

                      {/* Tab 1: Campaign Objectives */}
                      <TabsContent value="setup" className="space-y-6 mt-0">
                        <div className="space-y-4">
                          <div>
                            <Label className="text-base font-semibold">
                              Choose Your Campaign Objective
                            </Label>
                            <p className="text-sm text-muted-foreground mt-1">
                              Select an objective to configure details
                            </p>
                          </div>
                          {isLoadingObjectives &&
                          (campaignType === "presales" ||
                            campaignType === "postsales") ? (
                            <div className="flex items-center justify-center py-8">
                              <RefreshCw className="h-6 w-6 animate-spin text-primary mr-2" />
                              <span className="text-muted-foreground">
                                Loading objectives...
                              </span>
                            </div>
                          ) : (
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                              {objectives.map((objective, index) => {
                                const objectiveId = objective.id || `objective-${index}`;
                                const isSelected = selectedObjective !== "" && selectedObjective === objectiveId;

                                return (
                                  <ObjectiveCard
                                    key={`${objectiveId}-${index}`}
                                    icon={objective.icon}
                                    title={objective.title}
                                    campaignSubType={objective.campaignSubType}
                                    selected={isSelected}
                                    onSelect={() => {
                                      // INTERCEPT SELECTION: Open Dialog instead of generating
                                      setSelectedObjective(objectiveId);
                                      
                                      if ((objective as any).fullData) {
                                        setSelectedObjectiveData((objective as any).fullData);
                                        // Open dialog for everything except "custom"
                                        if (objectiveId !== "custom") {
                                            setIsObjectiveDetailsOpen(true);
                                        }
                                      } else {
                                        setSelectedObjectiveData(null);
                                        // Still open dialog for standard ones like new-car-launch that might not have fullData but have local handlers
                                        if (objectiveId !== "custom") {
                                            setIsObjectiveDetailsOpen(true);
                                        }
                                      }
                                      
                                      if (objectiveId !== "custom") {
                                        setCustomObjective("");
                                      }
                                      setCampaignData(null);
                                      // Reset car details unless sticking to same objective
                                      if (
                                        objectiveId !== "new-car-launch" &&
                                        objectiveId !== "stock-clearance"
                                      ) {
                                        setCarModel("");
                                        setLaunchDate("");
                                      }
                                    }}
                                  />
                                );
                              })}
                            </div>
                          )}
                        </div>

                        {/* Custom Objective Input - Stays Inline */}
                        {selectedObjective === "custom" && (
                          <Card className="border-2 border-primary/20 bg-primary/5">
                            <CardContent className="p-4">
                              <div className="space-y-2">
                                <Label className="text-base font-semibold">
                                  Enter Your Custom Objective
                                </Label>
                                <div className="flex gap-2">
                                    <Input
                                    placeholder="e.g., Special promotion for premium customers..."
                                    value={customObjective}
                                    onChange={(e) => {
                                        setCustomObjective(e.target.value);
                                        setCampaignData(null);
                                    }}
                                    className="h-12 text-base"
                                    />
                                    <Button size="lg" className="h-12" onClick={handleGenerateCampaign} disabled={!customObjective.trim()}>Generate</Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        )}
                      </TabsContent>

                      {/* Tab 2: Previously Used Campaigns */}
                      <TabsContent value="previous" className="mt-0">
                        <PreviouslyUsedCampaigns
                          campaignType={campaignType}
                          onReuseCampaign={(campaign) => {
                            if (campaign.campaignData) {
                              const data = campaign.campaignData;
                              if (data.selectedObjective) setSelectedObjective(data.selectedObjective);
                              if (data.customObjective) setCustomObjective(data.customObjective);
                              if ((data as any).carModel) setCarModel((data as any).carModel);
                              if ((data as any).launchDate) setLaunchDate((data as any).launchDate);
                              if (data.campaignName) setCampaignName(data.campaignName);
                              if (data.campaignDescription) setCampaignDescription(data.campaignDescription);
                              if (data.campaignTitle) setCampaignTitle(data.campaignTitle);
                              if (data.tone) setTone(data.tone);
                              if (data.callToAction) setCallToAction(data.callToAction);
                              if (data.language) setLanguage(data.language);
                              if (data.selectedChannels) setSelectedChannels(data.selectedChannels);
                              if (data.duration) setDuration(data.duration);
                              if (data.targetAudience) setTargetAudience(data.targetAudience);

                              setCampaignData({
                                name: data.campaignName || campaign.name,
                                description: data.campaignDescription,
                                campaignTitle: data.campaignTitle,
                                tone: data.tone,
                                callToAction: data.callToAction,
                                language: data.language,
                                selectedChannels: data.selectedChannels || campaign.channels,
                              });

                              setActiveTab("setup");
                            }
                          }}
                        />
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>

                {isGenerating && (
                  <Card className="shadow-xl border-primary/20 animate-in fade-in duration-500">
                    <CardContent className="py-20">
                      <AILoader
                        quotes={[
                          "AI is analyzing your campaign objective...",
                          "Personalized campaigns increase engagement by 50%",
                          "Machine learning optimizes targeting in real-time",
                          "Multi-channel strategies boost ROI by 300%",
                          "Data-driven insights lead to better conversions",
                        ]}
                        facts={[
                          "Did you know? Segmented campaigns see 14% higher click rates",
                          "Fun fact: Personalized emails have 26% higher open rates",
                          "Interesting: AI can predict customer behavior with 85% accuracy",
                          "Cool fact: Automated campaigns save 80% of manual time",
                          "Amazing: Dynamic content increases conversion by 202%",
                        ]}
                      />
                      <div className="mt-8 text-center space-y-2">
                        <p className="text-2xl font-bold text-primary">
                          Generating Your Campaign
                        </p>
                        <p className="text-muted-foreground">
                          Creating optimized content and recommendations...
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {!isGenerating && campaignData && (
                  <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
                    <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                      <CardHeader>
                        <CardTitle className="text-2xl flex items-center gap-2">
                          <Check className="h-6 w-6 text-emerald-500" />
                          Campaign Attributes
                        </CardTitle>
                        <CardDescription className="text-base">
                          Review and modify as needed
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <Label className="text-base font-semibold">
                              Campaign Name
                            </Label>
                            <Input
                              value={campaignName}
                              onChange={(e) => setCampaignName(e.target.value)}
                              className="h-11"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-base font-semibold">
                              Campaign Title
                            </Label>
                            <Input
                              value={campaignTitle}
                              onChange={(e) => setCampaignTitle(e.target.value)}
                              className="h-11"
                              placeholder="Enter campaign title"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label className="text-base font-semibold">
                            Description
                          </Label>
                          <Textarea
                            value={campaignDescription}
                            onChange={(e) =>
                              setCampaignDescription(e.target.value)
                            }
                            rows={4}
                            className="resize-none"
                          />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <Label className="text-base font-semibold">
                              Start Date
                            </Label>
                            <Input
                              type="date"
                              value={duration.start}
                              onChange={(e) =>
                                setDuration({
                                  ...duration,
                                  start: e.target.value,
                                })
                              }
                              className="h-11"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-base font-semibold">
                              End Date
                            </Label>
                            <Input
                              type="date"
                              value={duration.end}
                              onChange={(e) =>
                                setDuration({
                                  ...duration,
                                  end: e.target.value,
                                })
                              }
                              className="h-11"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-2">
                            <Label className="text-base font-semibold">
                              Tone of Voice
                            </Label>
                            <Input
                              value={tone}
                              onChange={(e) => setTone(e.target.value)}
                              className="h-11"
                              placeholder="e.g., Professional, Friendly, Urgent"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label className="text-base font-semibold">
                              Call to Action
                            </Label>
                            <Input
                              value={callToAction}
                              onChange={(e) => setCallToAction(e.target.value)}
                              className="h-11"
                              placeholder="e.g., Book Now, Learn More, Get Started"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label className="text-base font-semibold">
                            Language
                          </Label>
                          <select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            className="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {languageOptions.map((lang) => (
                              <option key={lang.value} value={lang.value}>
                                {lang.label}
                              </option>
                            ))}
                          </select>
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                      <CardHeader>
                        <CardTitle className="text-2xl">
                          Campaign Channels
                        </CardTitle>
                        <CardDescription className="text-base">
                          Add or remove platforms
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                          {channels.map((channel) => (
                            <Card
                              key={channel.id}
                              className={cn(
                                "cursor-pointer transition-all hover:shadow-lg hover:scale-[1.05] duration-300",
                                selectedChannels.includes(channel.id) &&
                                  "border-primary ring-2 ring-primary ring-offset-2 bg-primary/5"
                              )}
                              onClick={() => toggleChannel(channel.id)}
                            >
                              <CardContent className="flex flex-col items-center justify-center p-6 relative">
                                {selectedChannels.includes(channel.id) && (
                                  <div className="absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                                    <Check className="h-4 w-4" />
                                  </div>
                                )}
                                <div
                                  className={cn(
                                    "mb-3 transition-colors",
                                    selectedChannels.includes(channel.id)
                                      ? "text-primary"
                                      : "text-muted-foreground"
                                  )}
                                >
                                  {channel.icon}
                                </div>
                                <p
                                  className={cn(
                                    "font-semibold text-sm",
                                    selectedChannels.includes(channel.id) &&
                                      "text-primary"
                                  )}
                                >
                                  {channel.name}
                                </p>
                              </CardContent>
                            </Card>
                          ))}
                        </div>
                      </CardContent>
                    </Card>

                    <Card className="shadow-xl border-2 border-l-4 border-l-primary">
                      <CardHeader>
                        <CardTitle className="text-2xl">
                          Target Audience
                        </CardTitle>
                        <CardDescription className="text-base">
                          Select and refine your audience segments
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="space-y-4">
                          {audienceSegments.map((segment) => (
                            <Card
                              key={segment.value}
                              className={cn(
                                "cursor-pointer transition-all hover:shadow-md duration-300",
                                targetAudience.includes(segment.value) &&
                                  "border-primary bg-primary/5"
                              )}
                              onClick={() => toggleAudience(segment.value)}
                            >
                              <CardContent className="flex items-center justify-between p-6">
                                <div className="flex items-center gap-4">
                                  <div
                                    className={cn(
                                      "h-10 w-10 rounded-full flex items-center justify-center",
                                      targetAudience.includes(segment.value)
                                        ? "bg-primary text-primary-foreground"
                                        : "bg-muted"
                                    )}
                                  >
                                    {targetAudience.includes(segment.value) ? (
                                      <Check className="h-5 w-5" />
                                    ) : (
                                      <Users className="h-5 w-5" />
                                    )}
                                  </div>
                                  <div>
                                    <p className="font-semibold text-base">
                                      {segment.label}
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                      {segment.size.toLocaleString()} contacts
                                    </p>
                                  </div>
                                </div>
                                <Badge
                                  variant={
                                    targetAudience.includes(segment.value)
                                      ? "default"
                                      : "outline"
                                  }
                                >
                                  {targetAudience.includes(segment.value)
                                    ? "Selected"
                                    : "Available"}
                                </Badge>
                              </CardContent>
                            </Card>
                          ))}
                        </div>

                        <Alert className="border-primary/20 bg-primary/5">
                          <AlertCircle className="h-5 w-5 text-primary" />
                          <AlertDescription>
                            <span className="font-semibold">Total Reach: </span>
                            {totalAudienceSize.toLocaleString()} contacts
                          </AlertDescription>
                        </Alert>
                      </CardContent>
                    </Card>

                    <Card className="shadow-xl border-2 border-primary/50 bg-gradient-to-br from-primary/5 to-transparent">
                      <CardHeader>
                        <CardTitle className="text-2xl flex items-center gap-2">
                          <Rocket className="h-6 w-6 text-primary" />
                          Campaign Summary
                        </CardTitle>
                        <CardDescription className="text-base">
                          Review before launching
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div className="space-y-3">
                            <div className="flex justify-between">
                              <span className="font-medium">Campaign:</span>
                              <span className="text-muted-foreground">
                                {campaignName}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Type:</span>
                              <span className="text-muted-foreground capitalize">
                                {campaignType}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Objective:</span>
                              <span className="text-muted-foreground">
                                {objectives.find(
                                  (o) => o.id === selectedObjective
                                )?.title || customObjective}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Duration:</span>
                              <span className="text-muted-foreground">
                                {duration.start && duration.end
                                  ? `${Math.ceil(
                                      (new Date(duration.end).getTime() -
                                        new Date(duration.start).getTime()) /
                                        (1000 * 60 * 60 * 24)
                                    )} days`
                                  : "Not set"}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Tone:</span>
                              <span className="text-muted-foreground">
                                {tone}
                              </span>
                            </div>
                          </div>
                          <div className="space-y-3">
                            <div className="flex justify-between">
                              <span className="font-medium">Channels:</span>
                              <span className="text-muted-foreground">
                                {selectedChannels.length}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Audience:</span>
                              <span className="text-muted-foreground">
                                {totalAudienceSize.toLocaleString()}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">Language:</span>
                              <span className="text-muted-foreground">
                                {
                                  languageOptions.find(
                                    (l) => l.value === language
                                  )?.label
                                }
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">
                                Call to Action:
                              </span>
                              <span className="text-muted-foreground">
                                {callToAction}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="font-medium">
                                Campaign Title:
                              </span>
                              <span className="text-muted-foreground">
                                {campaignTitle}
                              </span>
                            </div>
                            <div className="flex justify-between items-center">
                              <span className="font-medium">
                                Credits Required:
                              </span>
                              <span className="text-xl font-bold text-primary">
                                {calculateCredits().toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="pt-4 border-t">
                          <div className="flex flex-wrap gap-2 mb-3">
                            <span className="font-medium">
                              Selected Channels:
                            </span>
                            {selectedChannels.map((channelId) => {
                              const channel = channels.find(
                                (c) => c.id === channelId
                              );
                              return (
                                <Badge key={channelId} className="bg-primary">
                                  {channel?.name}
                                </Badge>
                              );
                            })}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <span className="font-medium">
                              Audience Segments:
                            </span>
                            {targetAudience.map((audienceId) => {
                              const segment = audienceSegments.find(
                                (s) => s.value === audienceId
                              );
                              return (
                                <Badge key={audienceId} variant="outline">
                                  {segment?.label}
                                </Badge>
                              );
                            })}
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    <div className="flex justify-between items-center pt-4">
                      <Button
                        variant="outline"
                        onClick={() => router.push("/")}
                        className="gap-2 h-12 px-6"
                      >
                        Save as Draft
                      </Button>
                      <Button
                        onClick={handleLaunch}
                        size="lg"
                        className="gap-2 h-12 px-8 text-base"
                      >
                        <Rocket className="h-5 w-5" />
                        Launch Campaign
                      </Button>
                    </div>
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