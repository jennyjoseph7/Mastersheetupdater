"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
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
} from "lucide-react";
import { cn } from "@/lib/utils";
import { AILoader } from "@/components/ui/ai-loader";

const preSalesObjectives = [
  {
    id: "new-car-launch",
    title: "New Car Launch",
    icon: <Car className="h-6 w-6" />,
  },
  {
    id: "festive-sale",
    title: "Festive Sale",
    icon: <PartyPopper className="h-6 w-6" />,
  },
  {
    id: "stock-clearance",
    title: "Stock Clearance",
    icon: <Tag className="h-6 w-6" />,
  },
  {
    id: "test-drive",
    title: "Test Drive Campaign",
    icon: <TrendingUp className="h-6 w-6" />,
  },
  {
    id: "custom",
    title: "Custom Objective",
    icon: <Edit3 className="h-6 w-6" />,
  },
];

const postSalesObjectives = [
  {
    id: "service-reminder",
    title: "Service Reminder",
    icon: <Wrench className="h-6 w-6" />,
  },
  {
    id: "seasonal-service",
    title: "Seasonal Service",
    icon: <Sun className="h-6 w-6" />,
  },
  {
    id: "loyalty-reward",
    title: "Loyalty Rewards",
    icon: <Heart className="h-6 w-6" />,
  },
  {
    id: "referral",
    title: "Referral Program",
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
  const [selectedObjective, setSelectedObjective] = useState("");
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
        setSelectedObjective(data.selectedObjective || "");
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
    if (
      selectedObjective &&
      (selectedObjective !== "custom" || customObjective.trim() !== "")
    ) {
      // Check if we need car details
      const needsCarDetails = selectedObjective === "new-car-launch" || selectedObjective === "stock-clearance";
      const hasCarDetails = carModel && (selectedObjective === "stock-clearance" || launchDate);
      
      // Only generate campaign if:
      // 1. No car details needed, OR
      // 2. Car details are provided
      if (!needsCarDetails || hasCarDetails) {
        handleGenerateCampaign();
      }
    }
  }, [selectedObjective, customObjective, carModel, launchDate]);

  const handleGenerateCampaign = async () => {
    if (!selectedObjective) return;
    setIsGenerating(true);

    try {
      const objectiveText =
        selectedObjective === "custom"
          ? customObjective
          : [...preSalesObjectives, ...postSalesObjectives].find(
              (o) => o.id === selectedObjective
            )?.title || "";

      // Build objective text with car details if available
      let enhancedObjectiveText = objectiveText;
      if (carModel) {
        if (selectedObjective === "new-car-launch") {
          enhancedObjectiveText = `${objectiveText} for ${carModel}${launchDate ? ` launching on ${new Date(launchDate).toLocaleDateString()}` : ""}`;
        } else if (selectedObjective === "stock-clearance") {
          enhancedObjectiveText = `${objectiveText} for ${carModel}`;
        }
      }

      const payload = {
        args: [
          campaignType === "presales" ? "pre-sale" : "post-sale",
          enhancedObjectiveText,
        ],
        kwargs: {
          dealership_idea: {
            languages: [
              languageOptions.find((l) => l.value === language)?.label ||
                "English",
            ],
            campaign_offer:
              campaignDescription || "Exclusive offers and rewards await!",
            ...(carModel && { car_model: carModel }),
            ...(launchDate && { launch_date: launchDate }),
          },
        },
      };
      //calling the api for the campaign idea generation
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
        selectedChannels:
          data.channels?.map((ch: string) => ch.replace("_chat", "")) || [],
        campaignOffer: data.campaign_offer,
        urgencyHook: data.urgency_hook,
        campaignObjective: data.campaign_objective,
      };

      // update UI states
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

    const whatsappCredits = selectedChannels.includes("whatsapp")
      ? totalAudience * 5
      : 0;
    const emailCredits = selectedChannels.includes("email")
      ? totalAudience * 1
      : 0;
    const voiceCredits = selectedChannels.includes("voice")
      ? totalAudience * 10
      : 0;

    return whatsappCredits + emailCredits + voiceCredits;
  };

  const handleLaunch = () => {
    const newCampaign = {
      id: Date.now(),
      name: campaignName,
      type: campaignType,
      objective: selectedObjective,
      channels: selectedChannels,
      status: "live",
      launchDate: duration.start,
      credits: calculateCredits(),
      createdAt: new Date().toISOString(),
      language: language,
    };

    const existing = JSON.parse(localStorage.getItem("campaigns") || "[]");
    existing.push(newCampaign);
    localStorage.setItem("campaigns", JSON.stringify(existing));
    localStorage.removeItem("campaignFormData");

    router.push("/");
  };

  const objectives =
    campaignType === "presales" ? preSalesObjectives : postSalesObjectives;
  const totalAudienceSize = audienceSegments
    .filter((seg) => targetAudience.includes(seg.value))
    .reduce((sum, seg) => sum + seg.size, 0);

  return (
    <ProtectedRoute>
      <div className="pb-24">
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
                        onClick={() => setCampaignType("postsales")}
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
                            Select your goal - AI will generate everything automatically
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
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
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
                              Select an objective to get started with your campaign
                            </p>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                            {objectives.map((objective) => (
                              <ObjectiveCard
                                key={objective.id}
                                icon={objective.icon}
                                title={objective.title}
                                selected={selectedObjective === objective.id}
                                onSelect={() => {
                                  setSelectedObjective(objective.id);
                                  if (objective.id !== "custom") {
                                    setCustomObjective("");
                                  }
                                  setCampaignData(null);
                                  // Clear car details when switching objectives
                                  if (objective.id !== "new-car-launch" && objective.id !== "stock-clearance") {
                                    setCarModel("");
                                    setLaunchDate("");
                                  }
                                }}
                              />
                            ))}
                          </div>
                        </div>

                        {/* Custom Objective Input */}
                        {selectedObjective === "custom" && (
                          <Card className="border-2 border-primary/20 bg-primary/5">
                            <CardContent className="p-4">
                              <div className="space-y-2">
                                <Label className="text-base font-semibold">
                                  Enter Your Custom Objective
                                </Label>
                                <Input
                                  placeholder="e.g., Special promotion for premium customers..."
                                  value={customObjective}
                                  onChange={(e) => {
                                    setCustomObjective(e.target.value);
                                    setCampaignData(null);
                                  }}
                                  className="h-12 text-base"
                                />
                              </div>
                            </CardContent>
                          </Card>
                        )}

                        {/* Car Details Form for New Car Launch */}
                        {selectedObjective === "new-car-launch" && (
                          <Card className="border-2 border-primary/20 bg-primary/5 animate-in fade-in slide-in-from-top-2 duration-300">
                            <CardHeader>
                              <CardTitle className="text-lg flex items-center gap-2">
                                <Car className="h-5 w-5 text-primary" />
                                New Car Launch Details
                              </CardTitle>
                              <CardDescription>
                                Provide details about the car model and launch date
                              </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              <div className="space-y-2">
                                <Label htmlFor="carModel" className="text-base font-semibold">
                                  Car Model <span className="text-destructive">*</span>
                                </Label>
                                <Input
                                  id="carModel"
                                  placeholder="e.g., Brezza, Swift, Baleno"
                                  value={carModel}
                                  onChange={(e) => setCarModel(e.target.value)}
                                  className="h-11"
                                />
                              </div>
                              <div className="space-y-2">
                                <Label htmlFor="launchDate" className="text-base font-semibold">
                                  Launch Date <span className="text-destructive">*</span>
                                </Label>
                                <Input
                                  id="launchDate"
                                  type="date"
                                  value={launchDate}
                                  onChange={(e) => setLaunchDate(e.target.value)}
                                  className="h-11"
                                  min={new Date().toISOString().split("T")[0]}
                                />
                              </div>
                            </CardContent>
                          </Card>
                        )}

                        {/* Car Details Form for Stock Clearance */}
                        {selectedObjective === "stock-clearance" && (
                          <Card className="border-2 border-primary/20 bg-primary/5 animate-in fade-in slide-in-from-top-2 duration-300">
                            <CardHeader>
                              <CardTitle className="text-lg flex items-center gap-2">
                                <Tag className="h-5 w-5 text-primary" />
                                Stock Clearance Details
                              </CardTitle>
                              <CardDescription>
                                Provide details about the car model or stock type
                              </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                              <div className="space-y-2">
                                <Label htmlFor="stockCarModel" className="text-base font-semibold">
                                  Car Model or Stock Type <span className="text-destructive">*</span>
                                </Label>
                                <Input
                                  id="stockCarModel"
                                  placeholder="e.g., Brezza, Swift, or 'All Models'"
                                  value={carModel}
                                  onChange={(e) => setCarModel(e.target.value)}
                                  className="h-11"
                                />
                                <p className="text-xs text-muted-foreground">
                                  Enter specific car model(s) or "All Models" for general clearance
                                </p>
                              </div>
                            </CardContent>
                          </Card>
                        )}

                        {/* Show alert only when objective is selected and ready */}
                        {selectedObjective && 
                         (selectedObjective !== "custom" || customObjective.trim() !== "") &&
                         (selectedObjective !== "new-car-launch" && selectedObjective !== "stock-clearance" || carModel) &&
                         (selectedObjective !== "new-car-launch" || launchDate) && (
                          <Alert className="border-primary/20 bg-primary/5 animate-in fade-in duration-300">
                            <Sparkles className="h-5 w-5 text-primary" />
                            <AlertDescription className="text-sm leading-relaxed">
                              <span className="font-semibold">
                                AI will automatically generate:
                              </span>{" "}
                              Campaign name, description, budget, duration, channel
                              recommendations, creative content, audience segments,
                              and messaging
                            </AlertDescription>
                          </Alert>
                        )}
                      </TabsContent>

                      {/* Tab 2: Previously Used Campaigns */}
                      <TabsContent value="previous" className="mt-0">
                        <PreviouslyUsedCampaigns
                          campaignType={campaignType}
                          onReuseCampaign={(campaign) => {
                            // Populate form with reused campaign data
                            if (campaign.campaignData) {
                              const data = campaign.campaignData;
                              
                              // Set objective
                              if (data.selectedObjective) {
                                setSelectedObjective(data.selectedObjective);
                              }
                              if (data.customObjective) {
                                setCustomObjective(data.customObjective);
                              }
                              
                              // Set car details if available
                              if (data.carModel) {
                                setCarModel(data.carModel);
                              }
                              if (data.launchDate) {
                                setLaunchDate(data.launchDate);
                              }
                              
                              // Set campaign details
                              if (data.campaignName) {
                                setCampaignName(data.campaignName);
                              }
                              if (data.campaignDescription) {
                                setCampaignDescription(data.campaignDescription);
                              }
                              if (data.campaignTitle) {
                                setCampaignTitle(data.campaignTitle);
                              }
                              if (data.tone) {
                                setTone(data.tone);
                              }
                              if (data.callToAction) {
                                setCallToAction(data.callToAction);
                              }
                              if (data.language) {
                                setLanguage(data.language);
                              }
                              if (data.selectedChannels) {
                                setSelectedChannels(data.selectedChannels);
                              }
                              if (data.duration) {
                                setDuration(data.duration);
                              }
                              if (data.targetAudience) {
                                setTargetAudience(data.targetAudience);
                              }
                              
                              // Set the full campaign data object
                              setCampaignData({
                                name: data.campaignName || campaign.name,
                                description: data.campaignDescription,
                                campaignTitle: data.campaignTitle,
                                tone: data.tone,
                                callToAction: data.callToAction,
                                language: data.language,
                                selectedChannels: data.selectedChannels || campaign.channels,
                              });
                              
                              // Switch to setup tab to show the filled form
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
