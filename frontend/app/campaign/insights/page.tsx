"use client";

import { useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { ArrowLeft, AlertCircle } from "lucide-react";

// --- UI Component Imports (Adjust paths if necessary) ---
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// --- Custom Component Imports ---
import { EngagementFunnel } from "@/components/engagement-funnel";
import { CampaignFailureChart } from "@/components/campaign-failure-chart";
import { CostPerLeadChart } from "@/components/cost-per-lead-chart";
import { ConversationIntentChart } from "@/components/conversation-intent-chart";
import { ProtectedRoute } from "@/components/protected-route";
import { fetchCampaignPerformanceSummary } from "@/utils/api";

// --- Constants & Configuration ---

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateIfStale: false,
  revalidateOnReconnect: false,
  errorRetryCount: 0,
  shouldRetryOnError: false,
};

// Mapping raw statuses to funnel dispositions
const WA_TO_DISPOSITION: Record<string, string> = {
  "initiated": "queued",
  "queued": "queued",
  
  "sent": "attempted",
  "attempted": "attempted",
  
  "delivered": "reached",
  "reached": "reached",
  
  "read": "contacted",
  "contacted": "contacted",
  
  "interacted": "engaged",
  "engaged": "engaged",
  
  "converted": "converted",
  
  "failed": "failed",
  "error": "failed" 
};

// --- TypeScript Interfaces ---

interface EngagementStat {
  channel: string;
  status: string;
  count: number;
}

interface FailureStat {
  channel: string;
  message: string;
  count: number;
}

interface CampaignPerformance {
  campaign_name: string;
  campaign_type: string;
  engagement_stats: EngagementStat[];
  failure_stats_by_channel: FailureStat[];
}

interface FunnelStage {
  stage: string;
  value: number;
  percentage: string;
  count: number;
  dropoff?: number;
}

// --- Helper Logic ---

const calculatePercentage = (part: number, total: number) => {
  if (!total || total === 0) return 0;
  return Math.round((part / total) * 100);
};

// Process stats into a Waterfall Funnel
function processEngagementStats(engagementStats: EngagementStat[]) {
  if (!engagementStats || engagementStats.length === 0) {
    return { all: [], whatsapp: [], email: [], voice: [] };
  }

  // 1. Group raw stats by channel
  const byChannel: Record<string, EngagementStat[]> = {};
  engagementStats.forEach((stat) => {
    const channel = stat.channel || "unknown";
    if (!byChannel[channel]) byChannel[channel] = [];
    byChannel[channel].push(stat);
  });

  // 2. Logic to build stages for a specific list of stats
  const createFunnelStages = (channelStats: EngagementStat[]): FunnelStage[] => {
    // Initialize base counters
    const counts = {
      queued: 0,
      attempted: 0,
      reached: 0,
      contacted: 0,
      engaged: 0,
      converted: 0,
      failed: 0
    };

    // Map raw status to standard disposition and sum distinct counts
    channelStats.forEach((stat) => {
      const rawStatus = (stat.status || "").toLowerCase();
      const disposition = WA_TO_DISPOSITION[rawStatus];
      
      // Only count known dispositions
      if (disposition && disposition in counts) {
        counts[disposition as keyof typeof counts] += (stat.count || 0);
      }
    });

    // --- WATERFALL CALCULATION ---
    // We sum from bottom (Converted) to top (Queued) to create the funnel.
    // Logic: If you are "Converted", you were implicitly "Engaged", "Contacted", etc.

    const totalConverted = counts.converted;
    const totalEngaged = counts.engaged + totalConverted;
    const totalContacted = counts.contacted + totalEngaged;
    const totalReached = counts.reached + totalContacted;
    const totalFailed = counts.failed;
    
    // Attempted includes Successes (Reached) + Failures
    const totalAttempted = counts.attempted + totalReached + totalFailed;
    
    // Queued includes everything
    const totalQueued = counts.queued + totalAttempted;

    // Safety check: if no data
    if (totalQueued === 0) return [];

    const stages: FunnelStage[] = [];

    // 1. Queued
    stages.push({
      stage: "Queued",
      value: 100,
      percentage: "100%",
      count: totalQueued,
      dropoff: 0
    });

    // 2. Attempted
    const attemptedPct = calculatePercentage(totalAttempted, totalQueued);
    stages.push({
      stage: "Attempted",
      value: attemptedPct,
      percentage: `${attemptedPct}%`,
      count: totalAttempted,
      dropoff: 100 - attemptedPct
    });

    // 3. Reached (Delivered)
    const reachedPct = calculatePercentage(totalReached, totalQueued);
    stages.push({
      stage: "Reached",
      value: reachedPct,
      percentage: `${reachedPct}%`,
      count: totalReached,
      // Dropoff here represents failures (Attempted - Reached)
      dropoff: attemptedPct - reachedPct 
    });

    // 4. Contacted (Read)
    const contactedPct = calculatePercentage(totalContacted, totalQueued);
    stages.push({
      stage: "Contacted",
      value: contactedPct,
      percentage: `${contactedPct}%`,
      count: totalContacted,
      dropoff: reachedPct - contactedPct
    });

    // 5. Engaged (Interacted)
    const engagedPct = calculatePercentage(totalEngaged, totalQueued);
    stages.push({
      stage: "Engaged",
      value: engagedPct,
      percentage: `${engagedPct}%`,
      count: totalEngaged,
      dropoff: contactedPct - engagedPct
    });

    // 6. Converted
    const convertedPct = calculatePercentage(totalConverted, totalQueued);
    stages.push({
      stage: "Converted",
      value: convertedPct,
      percentage: `${convertedPct}%`,
      count: totalConverted,
      dropoff: engagedPct - convertedPct
    });

    return stages;
  };

  return {
    all: createFunnelStages(engagementStats),
    whatsapp: createFunnelStages(byChannel.whatsapp_chat || byChannel.whatsapp || []),
    email: createFunnelStages(byChannel.email || []),
    voice: createFunnelStages(byChannel.voice || []),
  };
}

// Process failure stats for the bar chart
function processFailureStats(failureStats: FailureStat[]) {
  if (!failureStats || failureStats.length === 0) return [];

  const byChannel: Record<string, Record<string, number>> = {};

  failureStats.forEach((stat) => {
    const channel = stat.channel || "unknown";
    const message = stat.message || "Unknown Error";
    
    if (!byChannel[channel]) byChannel[channel] = {};
    byChannel[channel][message] = (byChannel[channel][message] || 0) + (stat.count || 0);
  });

  const channelMap: Record<string, string> = {
    whatsapp_chat: "WhatsApp",
    whatsapp: "WhatsApp",
    email: "Email",
    voice: "Voice",
  };

  return Object.entries(byChannel).map(([channel, failures]) => {
    const dataPoint: any = { channel: channelMap[channel] || channel };
    Object.entries(failures).forEach(([message, count]) => {
      dataPoint[message] = count;
    });
    return dataPoint;
  });
}

// --- Inner Component (Contains Logic) ---

function CampaignInsightsContent() {
  const searchParams = useSearchParams();
  const campaignId = searchParams?.get("campaign_id");

  const { 
    data: performanceData, 
    isLoading,
    error 
  } = useSWR<CampaignPerformance>(
    campaignId ? `campaign-performance-${campaignId}` : null,
    () => fetchCampaignPerformanceSummary(campaignId || ""),
    SWR_OPTIONS
  );

  const campaignName = performanceData?.campaign_name || "Campaign";
  const campaignType = performanceData?.campaign_type || "";

  // Memoize data processing
  const funnelData = useMemo(() => {
    if (!performanceData?.engagement_stats) return { all: [], whatsapp: [], email: [], voice: [] };
    return processEngagementStats(performanceData.engagement_stats);
  }, [performanceData]);

  const failureData = useMemo(() => {
    if (!performanceData?.failure_stats_by_channel) return [];
    return processFailureStats(performanceData.failure_stats_by_channel);
  }, [performanceData]);

  // -- Render States --

  if (isLoading) {
    return (
      <div className="flex flex-col w-full space-y-6 px-4 md:px-6 lg:px-8 pb-6 mt-6">
         <div className="space-y-2">
            <Skeleton className="h-8 w-[250px]" />
            <Skeleton className="h-4 w-[150px]" />
         </div>
         <div className="grid grid-cols-1 gap-6">
            <Skeleton className="h-[300px] w-full" />
            <Skeleton className="h-[300px] w-full" />
         </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 px-4 md:px-6 lg:px-8 pb-6 w-full mt-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load campaign data. {error.message}
          </AlertDescription>
        </Alert>
        <Link href="/">
            <Button variant="outline" className="mt-4">
              <ArrowLeft className="mr-2 h-4 w-4" /> Back to Campaigns
            </Button>
        </Link>
      </div>
    );
  }

  if (!performanceData) {
    return (
      <div className="flex flex-col w-full">
         <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="icon">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <h1 className="text-2xl font-semibold tracking-tight">Campaign Insights</h1>
            </div>
          </div>
          <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                No campaign selected or data unavailable.
              </CardContent>
            </Card>
          </div>
      </div>
    );
  }

  // -- Main Data View --

  return (
    <div className="flex flex-col w-full">
      {/* Header */}
      <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{campaignName}</h1>
              <Badge variant={campaignType === "post-sales" ? "default" : "secondary"}>
                {campaignType === "post-sales" ? "Post-Sales" : campaignType === "pre-sales" ? "Pre-Sales" : campaignType}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Campaign Performance Statistics
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
        <Tabs defaultValue="statistics" className="w-full">
          <TabsList>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="audience">Audience / Leads</TabsTrigger>
          </TabsList>

          {/* Statistics Tab */}
          <TabsContent value="statistics" className="space-y-6 mt-6">
            
            {/* 1. Engagement Funnel */}
            {(funnelData.all?.length > 0) && (
              <Card className="shadow">
                <CardHeader>
                  <CardTitle>Engagement Funnel</CardTitle>
                  <CardDescription>
                    Tracking user journey from Queue to Conversion
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {/* Pass the calculated waterfall data to your funnel component */}
                  <EngagementFunnel customData={funnelData} />
                </CardContent>
              </Card>
            )}

            {/* 2. Failure Reasons */}
            {failureData.length > 0 && (
              <Card className="shadow">
                <CardHeader>
                  <CardTitle>Failure Reasons by Channel</CardTitle>
                  <CardDescription>Distribution of delivery failures across channels</CardDescription>
                </CardHeader>
                <CardContent>
                  <CampaignFailureChart customData={failureData} />
                </CardContent>
              </Card>
            )}

            {/* 3. Analytics Grid (Cost & Intent) */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="shadow">
                <CardHeader>
                  <CardTitle>Cost per Lead by Channel</CardTitle>
                  <CardDescription>Average cost to acquire a lead per channel</CardDescription>
                </CardHeader>
                <CardContent>
                  <CostPerLeadChart />
                </CardContent>
              </Card>

              <Card className="shadow">
                <CardHeader>
                  <CardTitle>Intent Distribution</CardTitle>
                  <CardDescription>Distribution of conversation intents across channels</CardDescription>
                </CardHeader>
                <CardContent>
                  <ConversationIntentChart />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Audience Tab */}
          <TabsContent value="audience" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Campaign Leads</CardTitle>
                <CardDescription>View and manage leads from this campaign</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center text-muted-foreground py-8">
                  Lead data will be displayed here
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// --- Main Page Export (Wrapped in Suspense) ---

export default function CampaignInsightsPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={
        <div className="p-8 space-y-4">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-64 w-full" />
        </div>
      }>
        <CampaignInsightsContent />
      </Suspense>
    </ProtectedRoute>
  );
}