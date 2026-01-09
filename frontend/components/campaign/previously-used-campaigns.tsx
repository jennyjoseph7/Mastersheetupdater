"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";
import {
  MessageSquare,
  Mail,
  Phone,
  Facebook,
  Instagram,
  ChevronRight,
  Image as ImageIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";
import { fetchPreSalesCampaigns, fetchPostSalesCampaigns } from "@/utils/api";

interface PreviousCampaign {
  id: string;
  name: string;
  objective: string;
  objectiveSummary?: string;
  channels: string[];
  previewImage?: string;
  campaignType: "presales" | "postsales";
  createdAt: string;
  // Full campaign data for reuse
  campaignData?: {
    campaignName?: string;
    campaignDescription?: string;
    selectedChannels?: string[];
    campaignTitle?: string;
    tone?: string;
    callToAction?: string;
    language?: string;
    selectedObjective?: string;
    customObjective?: string;
    duration?: { start: string; end: string };
    targetAudience?: string[];
  };
}

interface PreviouslyUsedCampaignsProps {
  campaignType: "presales" | "postsales";
  onReuseCampaign: (campaign: PreviousCampaign) => void;
}

const channelIcons: Record<string, React.ReactNode> = {
  whatsapp: <MessageSquare className="h-4 w-4" />,
  email: <Mail className="h-4 w-4" />,
  voice: <Phone className="h-4 w-4" />,
  facebook: <Facebook className="h-4 w-4" />,
  instagram: <Instagram className="h-4 w-4" />,
};

const channelColors: Record<string, string> = {
  whatsapp: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400 border-green-200 dark:border-green-800",
  email: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 border-blue-200 dark:border-blue-800",
  voice: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400 border-orange-200 dark:border-orange-800",
  facebook: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400 border-blue-200 dark:border-blue-800",
  instagram: "bg-pink-100 text-pink-700 dark:bg-pink-950 dark:text-pink-400 border-pink-200 dark:border-pink-800",
};

// Dummy data for demonstration
const getDummyCampaigns = (type: "presales" | "postsales"): PreviousCampaign[] => {
  if (type === "presales") {
    return [
      {
        id: "dummy-1",
        name: "Summer Sale 2024",
        objective: "festive-sale",
        objectiveSummary: "Festive Sale",
        channels: ["whatsapp", "email", "facebook"],
        campaignType: "presales",
        createdAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Summer Sale 2024",
          campaignDescription: "Exclusive summer discounts on all models with special financing options",
          selectedChannels: ["whatsapp", "email", "facebook"],
          campaignTitle: "Beat the Heat with Cool Deals",
          tone: "energetic",
          callToAction: "Book Now",
          language: "en",
          selectedObjective: "festive-sale",
        },
      },
      {
        id: "dummy-2",
        name: "New Electric Vehicle Launch",
        objective: "new-car-launch",
        objectiveSummary: "New Car Launch",
        channels: ["whatsapp", "email", "instagram"],
        campaignType: "presales",
        createdAt: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "New Electric Vehicle Launch",
          campaignDescription: "Introducing our latest electric vehicle with cutting-edge technology",
          selectedChannels: ["whatsapp", "email", "instagram"],
          campaignTitle: "The Future is Electric",
          tone: "innovative",
          callToAction: "Learn More",
          language: "en",
          selectedObjective: "new-car-launch",
        },
      },
      {
        id: "dummy-3",
        name: "Year-End Stock Clearance",
        objective: "stock-clearance",
        objectiveSummary: "Stock Clearance",
        channels: ["whatsapp", "email", "voice"],
        campaignType: "presales",
        createdAt: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Year-End Stock Clearance",
          campaignDescription: "Massive discounts on remaining inventory - limited time offer",
          selectedChannels: ["whatsapp", "email", "voice"],
          campaignTitle: "Clearance Sale - Up to 30% Off",
          tone: "urgent",
          callToAction: "Shop Now",
          language: "en",
          selectedObjective: "stock-clearance",
        },
      },
      {
        id: "dummy-4",
        name: "Test Drive Experience Campaign",
        objective: "test-drive",
        objectiveSummary: "Test Drive Campaign",
        channels: ["whatsapp", "email"],
        campaignType: "presales",
        createdAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Test Drive Experience Campaign",
          campaignDescription: "Book a test drive and experience the thrill of our premium vehicles",
          selectedChannels: ["whatsapp", "email"],
          campaignTitle: "Feel the Difference",
          tone: "inviting",
          callToAction: "Schedule Test Drive",
          language: "en",
          selectedObjective: "test-drive",
        },
      },
    ];
  } else {
    return [
      {
        id: "dummy-5",
        name: "Annual Service Reminder",
        objective: "service-reminder",
        objectiveSummary: "Service Reminder",
        channels: ["whatsapp", "email"],
        campaignType: "postsales",
        createdAt: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Annual Service Reminder",
          campaignDescription: "Your vehicle is due for annual service. Book now and get 15% off",
          selectedChannels: ["whatsapp", "email"],
          campaignTitle: "Keep Your Car Running Smoothly",
          tone: "friendly",
          callToAction: "Book Service",
          language: "en",
          selectedObjective: "service-reminder",
        },
      },
      {
        id: "dummy-6",
        name: "Monsoon Service Package",
        objective: "seasonal-service",
        objectiveSummary: "Seasonal Service",
        channels: ["whatsapp", "email", "voice"],
        campaignType: "postsales",
        createdAt: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Monsoon Service Package",
          campaignDescription: "Special monsoon service package to protect your vehicle from the rains",
          selectedChannels: ["whatsapp", "email", "voice"],
          campaignTitle: "Monsoon-Ready Your Vehicle",
          tone: "caring",
          callToAction: "Get Service",
          language: "en",
          selectedObjective: "seasonal-service",
        },
      },
      {
        id: "dummy-7",
        name: "Loyalty Rewards Program",
        objective: "loyalty-reward",
        objectiveSummary: "Loyalty Rewards",
        channels: ["whatsapp", "email", "facebook"],
        campaignType: "postsales",
        createdAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Loyalty Rewards Program",
          campaignDescription: "Thank you for being a valued customer. Redeem your loyalty points now",
          selectedChannels: ["whatsapp", "email", "facebook"],
          campaignTitle: "Your Rewards Await",
          tone: "appreciative",
          callToAction: "Redeem Now",
          language: "en",
          selectedObjective: "loyalty-reward",
        },
      },
      {
        id: "dummy-8",
        name: "Refer a Friend Campaign",
        objective: "referral",
        objectiveSummary: "Referral Program",
        channels: ["whatsapp", "email"],
        campaignType: "postsales",
        createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
        campaignData: {
          campaignName: "Refer a Friend Campaign",
          campaignDescription: "Refer a friend and both of you get exclusive benefits and discounts",
          selectedChannels: ["whatsapp", "email"],
          campaignTitle: "Share the Joy",
          tone: "excited",
          callToAction: "Refer Now",
          language: "en",
          selectedObjective: "referral",
        },
      },
    ];
  }
};

export function PreviouslyUsedCampaigns({
  campaignType,
  onReuseCampaign,
}: PreviouslyUsedCampaignsProps) {
  const [previousCampaigns, setPreviousCampaigns] = useState<PreviousCampaign[]>([]);

  useEffect(() => {
    // Fetch previous campaigns from API for both pre-sales and post-sales, localStorage for others
    const fetchPreviousCampaigns = async () => {
      try {
        // For pre-sales campaigns, fetch from API
        if (campaignType === "presales") {
          try {
            const apiResponse = await fetchPreSalesCampaigns(1, 10);
            const apiCampaigns = apiResponse?.items ?? [];
            
            if (apiCampaigns.length > 0) {
              const mappedCampaigns = apiCampaigns
                .filter((campaign: any) => {
                  const status = campaign.campaign_status?.toLowerCase() || "";
                  return status === "active" || status === "live" || status === "completed";
                })
                .map((campaign: any) => {
                  const channels = Array.isArray(campaign.channels) 
                    ? campaign.channels.map((c: string) => {
                        if (c.includes("whatsapp")) return "whatsapp";
                        if (c.includes("email")) return "email";
                        if (c.includes("voice") || c.includes("phone")) return "voice";
                        return c.toLowerCase();
                      })
                    : [];
                  
                  return {
                    id: campaign.campaign_id || campaign.id || `campaign-${Date.now()}-${Math.random()}`,
                    name: campaign.campaign_name || "Untitled Campaign",
                    objective: campaign.campaign_objective?.[0] || campaign.campaign_objective_id || "custom",
                    objectiveSummary: campaign.campaign_objective_name || campaign.campaign_objective?.[0] || "Custom Campaign",
                    channels: channels,
                    previewImage: undefined,
                    campaignType: "presales" as const,
                    createdAt: campaign.created ? new Date(campaign.created * 1000).toISOString() : new Date().toISOString(),
                    campaignData: {
                      campaignName: campaign.campaign_name,
                      selectedChannels: channels,
                      selectedObjective: campaign.campaign_objective?.[0] || campaign.campaign_objective_id,
                      campaignDescription: campaign.campaign_description,
                      campaignTitle: campaign.campaign_name,
                      tone: campaign.conversation_tone,
                      callToAction: campaign.ctas?.[0],
                      language: campaign.languages?.[0] || "english",
                      duration: campaign.start_date && campaign.end_date ? {
                        start: new Date(campaign.start_date * 1000).toISOString().split('T')[0],
                        end: new Date(campaign.end_date * 1000).toISOString().split('T')[0],
                      } : undefined,
                      targetAudience: campaign.target_audience_tags || [],
                    },
                  } as PreviousCampaign;
                })
                .sort((a: PreviousCampaign, b: PreviousCampaign) => {
                  return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
                })
                .slice(0, 10);
              
              if (mappedCampaigns.length > 0) {
                setPreviousCampaigns(mappedCampaigns);
                return;
              }
            }
          } catch (apiError) {
            console.error("Error fetching pre-sales campaigns from API:", apiError);
            // Fall through to localStorage/dummy data
          }
        }
        
        // For post-sales campaigns, fetch from API
        if (campaignType === "postsales") {
          try {
            const apiResponse = await fetchPostSalesCampaigns();
            const apiCampaigns = apiResponse?.items ?? [];
            
            if (apiCampaigns.length > 0) {
              const mappedCampaigns = apiCampaigns
                .filter((campaign: any) => {
                  const status = campaign.campaign_status?.toLowerCase() || "";
                  return status === "active" || status === "live" || status === "completed";
                })
                .map((campaign: any) => {
                  const channels = Array.isArray(campaign.channels) 
                    ? campaign.channels.map((c: string) => {
                        if (c.includes("whatsapp")) return "whatsapp";
                        if (c.includes("email")) return "email";
                        if (c.includes("voice") || c.includes("phone")) return "voice";
                        return c.toLowerCase();
                      })
                    : [];
                  
                  return {
                    id: campaign.campaign_id || campaign.id || `campaign-${Date.now()}-${Math.random()}`,
                    name: campaign.campaign_name || "Untitled Campaign",
                    objective: campaign.campaign_objective?.[0] || campaign.campaign_objective_id || "custom",
                    objectiveSummary: campaign.campaign_objective_name || campaign.campaign_objective?.[0] || "Custom Campaign",
                    channels: channels,
                    previewImage: undefined,
                    campaignType: "postsales" as const,
                    createdAt: campaign.created ? new Date(campaign.created * 1000).toISOString() : new Date().toISOString(),
                    campaignData: {
                      campaignName: campaign.campaign_name,
                      selectedChannels: channels,
                      selectedObjective: campaign.campaign_objective?.[0] || campaign.campaign_objective_id,
                      campaignDescription: campaign.campaign_description,
                      campaignTitle: campaign.campaign_name,
                      tone: campaign.conversation_tone,
                      callToAction: campaign.ctas?.[0],
                      language: campaign.languages?.[0] || "english",
                      duration: campaign.start_date && campaign.end_date ? {
                        start: new Date(campaign.start_date * 1000).toISOString().split('T')[0],
                        end: new Date(campaign.end_date * 1000).toISOString().split('T')[0],
                      } : undefined,
                      targetAudience: campaign.target_audience_tags || [],
                    },
                  } as PreviousCampaign;
                })
                .sort((a: PreviousCampaign, b: PreviousCampaign) => {
                  return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
                })
                .slice(0, 10);
              
              if (mappedCampaigns.length > 0) {
                setPreviousCampaigns(mappedCampaigns);
                return;
              }
            }
          } catch (apiError) {
            console.error("Error fetching post-sales campaigns from API:", apiError);
            // Fall through to localStorage/dummy data
          }
        }
        
        // Fallback to localStorage for other types or if API fails
        const storedCampaigns = JSON.parse(
          localStorage.getItem("campaigns") || "[]"
        );
        
        // If no stored campaigns, use dummy data
        if (!Array.isArray(storedCampaigns) || storedCampaigns.length === 0) {
          setPreviousCampaigns(getDummyCampaigns(campaignType));
          return;
        }
        
        const objectives = {
          presales: [
            { id: "new-car-launch", title: "New Car Launch" },
            { id: "festive-sale", title: "Festive Sale" },
            { id: "stock-clearance", title: "Stock Clearance" },
            { id: "test-drive", title: "Test Drive Campaign" },
            { id: "custom", title: "Custom Objective" },
          ],
          postsales: [
            { id: "service-reminder", title: "Service Reminder" },
            { id: "seasonal-service", title: "Seasonal Service" },
            { id: "loyalty-reward", title: "Loyalty Rewards" },
            { id: "referral", title: "Referral Program" },
            { id: "custom", title: "Custom Objective" },
          ],
        };

        const objectiveList = objectives[campaignType as "presales" | "postsales"] || [];
        
        // Filter campaigns by type and map to our format
        const filtered = storedCampaigns
          .filter((campaign: any) => {
            if (!campaign) return false;
            // Match campaign type
            const matchesType = campaign.type === campaignType;
            // Only show completed or live campaigns (not drafts)
            const hasValidStatus = campaign.status === "live" || campaign.status === "completed" || campaign.status === "Live" || campaign.status === "Completed";
            return matchesType && hasValidStatus;
          })
          .map((campaign: any) => {
            const objectiveObj = objectiveList.find(
              (o) => o.id === campaign.objective
            );
            const objectiveTitle = objectiveObj?.title || 
              (campaign.objective ? campaign.objective.charAt(0).toUpperCase() + campaign.objective.slice(1).replace(/-/g, " ") : "Custom Campaign");

            // Try to get stored form data for this specific campaign
            // In a real app, this would be stored per campaign
            let campaignFormData: any = {};
            try {
              const stored = localStorage.getItem("campaignFormData");
              if (stored) {
                const parsed = JSON.parse(stored);
                // Only use if it matches the campaign type
                if (parsed.campaignType === campaignType) {
                  campaignFormData = parsed;
                }
              }
            } catch (e) {
              // Ignore errors
            }

            return {
              id: campaign.id?.toString() || `campaign-${Date.now()}-${Math.random()}`,
              name: campaign.name || "Untitled Campaign",
              objective: campaign.objective || "custom",
              objectiveSummary: objectiveTitle,
              channels: Array.isArray(campaign.channels) ? campaign.channels : 
                       Array.isArray(campaign.channelsUsed) ? campaign.channelsUsed.map((c: string) => c.toLowerCase()) : [],
              previewImage: campaign.previewImage || undefined,
              campaignType: campaign.type || campaignType,
              createdAt: campaign.createdAt || campaign.launchDate || campaign.createdOn || new Date().toISOString(),
              campaignData: {
                campaignName: campaign.name,
                selectedChannels: Array.isArray(campaign.channels) ? campaign.channels : 
                                Array.isArray(campaign.channelsUsed) ? campaign.channelsUsed.map((c: string) => c.toLowerCase()) : [],
                selectedObjective: campaign.objective,
                ...campaignFormData,
              },
            } as PreviousCampaign;
          })
          .sort((a: PreviousCampaign, b: PreviousCampaign) => {
            // Sort by most recent first
            return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
          })
          .slice(0, 10); // Limit to 10 most recent

        // If no filtered campaigns, use dummy data
        if (filtered.length === 0) {
          setPreviousCampaigns(getDummyCampaigns(campaignType));
        } else {
          setPreviousCampaigns(filtered);
        }
      } catch (error) {
        console.error("Error fetching previous campaigns:", error);
        // On error, show dummy data
        setPreviousCampaigns(getDummyCampaigns(campaignType));
      }
    };

    fetchPreviousCampaigns();
  }, [campaignType]);

  if (previousCampaigns.length === 0) {
    return null; // Don't show section if no previous campaigns
  }

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <Card className="border-2 shadow-lg bg-gradient-to-br from-background via-background to-primary/5">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <ImageIcon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="text-2xl font-bold tracking-tight">Previously Used Campaigns</h3>
              </div>
              <p className="text-sm text-muted-foreground ml-11">
                Reuse configurations from your past successful campaigns to save time
              </p>
            </div>
          </div>

          <div className="relative overflow-visible py-4">
            <Carousel
              opts={{
                align: "start",
                loop: false,
                dragFree: true,
              }}
              className="w-full"
            >
              <CarouselContent className="-ml-2 md:-ml-4 overflow-visible px-2">
                {previousCampaigns.map((campaign, index) => (
                  <CarouselItem
                    key={campaign.id}
                    className="pl-2 md:pl-4 basis-full sm:basis-1/2 lg:basis-1/3 xl:basis-1/4 overflow-visible"
                  >
                    <Card
                      className={cn(
                        "group cursor-pointer transition-all duration-300 ease-out",
                        "hover:shadow-2xl hover:-translate-y-2",
                        "border-2 hover:border-primary/60",
                        "bg-gradient-to-br from-card via-card to-muted/30",
                        "overflow-visible relative",
                        "before:absolute before:inset-0 before:bg-gradient-to-br before:from-primary/0 before:to-primary/0",
                        "hover:before:from-primary/5 hover:before:to-primary/10",
                        "before:transition-all before:duration-300",
                        "backdrop-blur-sm",
                        "h-full"
                      )}
                      onClick={() => onReuseCampaign(campaign)}
                      style={{
                        animationDelay: `${index * 100}ms`,
                      }}
                    >
                      {/* Preview Image with Enhanced Design */}
                      <div className="relative h-40 w-full overflow-hidden bg-gradient-to-br from-primary/20 via-primary/10 to-muted">
                        {campaign.previewImage ? (
                          <Image
                            src={campaign.previewImage}
                            alt={campaign.name}
                            fill
                            className="object-cover transition-transform duration-700 group-hover:scale-125"
                            unoptimized
                          />
                        ) : (
                          <div className="flex items-center justify-center h-full bg-gradient-to-br from-primary/15 via-primary/8 to-muted/50">
                            <div className="text-center space-y-3">
                              <div className="p-4 rounded-full bg-primary/20 backdrop-blur-sm mx-auto w-fit">
                                <ImageIcon className="h-8 w-8 text-primary/60" />
                              </div>
                              <p className="text-xs font-semibold text-primary/70 uppercase tracking-wider">
                                {campaign.campaignType === "presales" ? "Pre-Sales" : "Post-Sales"}
                              </p>
                            </div>
                          </div>
                        )}
                        {/* Enhanced Gradient Overlay */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent" />
                        {/* Shine effect on hover */}
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/0 to-transparent opacity-0 group-hover:opacity-100 group-hover:via-white/10 transition-opacity duration-500" />
                        <div className="absolute bottom-0 left-0 right-0 p-4">
                          <h4 className="font-bold text-white text-base line-clamp-2 drop-shadow-2xl mb-1">
                            {campaign.name}
                          </h4>
                          <div className="flex items-center gap-1.5">
                            <div className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-xs text-white/90 font-medium">Active Campaign</span>
                          </div>
                        </div>
                      </div>

                      <CardContent className="p-5 space-y-4 bg-gradient-to-b from-transparent to-muted/20">
                        {/* Objective Summary with Icon */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <div className="h-1 w-8 bg-primary rounded-full" />
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                              Objective
                            </p>
                          </div>
                          <p className="text-sm font-semibold text-foreground line-clamp-1 pl-10">
                            {campaign.objectiveSummary}
                          </p>
                        </div>

                        {/* Channels with Enhanced Design */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <div className="h-1 w-8 bg-primary rounded-full" />
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                              Channels
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2 pl-10">
                            {campaign.channels.map((channel) => (
                              <Badge
                                key={channel}
                                variant="outline"
                                className={cn(
                                  "text-xs px-2.5 py-1 border-2 font-medium",
                                  "transition-all duration-300",
                                  "group-hover:scale-105 group-hover:shadow-md",
                                  channelColors[channel.toLowerCase()] ||
                                    "bg-muted text-muted-foreground"
                                )}
                              >
                                <span className="flex items-center gap-1.5">
                                  <span className="transition-transform group-hover:scale-110">
                                    {channelIcons[channel.toLowerCase()] || null}
                                  </span>
                                  <span className="capitalize font-semibold">
                                    {channel === "whatsapp"
                                      ? "WhatsApp"
                                      : channel.charAt(0).toUpperCase() + channel.slice(1)}
                                  </span>
                                </span>
                              </Badge>
                            ))}
                          </div>
                        </div>

                        {/* Enhanced Use Again Button */}
                        <Button
                          className={cn(
                            "w-full mt-4 h-11",
                            "bg-gradient-to-r from-primary to-primary/90",
                            "hover:from-primary/90 hover:to-primary",
                            "text-primary-foreground font-semibold",
                            "shadow-lg hover:shadow-xl",
                            "transition-all duration-300",
                            "border-0"
                          )}
                          size="default"
                          onClick={(e) => {
                            e.stopPropagation();
                            onReuseCampaign(campaign);
                          }}
                        >
                          <span className="flex items-center gap-2">
                            <span>Edit & Reuse</span>
                            <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                          </span>
                        </Button>
                      </CardContent>
                    </Card>
                  </CarouselItem>
                ))}
              </CarouselContent>
              {previousCampaigns.length > 1 && (
                <>
                  <CarouselPrevious className="hidden md:flex -left-12 bg-background/80 backdrop-blur-sm border-2 shadow-lg hover:bg-background" />
                  <CarouselNext className="hidden md:flex -right-12 bg-background/80 backdrop-blur-sm border-2 shadow-lg hover:bg-background" />
                </>
              )}
            </Carousel>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

