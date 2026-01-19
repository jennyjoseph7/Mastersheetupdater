"use client";

import { useEffect, useState, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, BarChart3 } from "lucide-react";
import { fetchCampaignPerformanceSummary } from "@/utils/api";
import { EngagementFunnel } from "@/components/engagement-funnel";
import { CampaignFailureChart } from "@/components/campaign-failure-chart";
import { CostPerLeadChart } from "@/components/cost-per-lead-chart";
import { ConversationIntentChart } from "@/components/conversation-intent-chart";
import { ProtectedRoute } from "@/components/protected-route";

const swrOptions = {
  revalidateOnFocus: false,
  revalidateIfStale: false,
  revalidateOnReconnect: false,
  errorRetryCount: 0,
  shouldRetryOnError: false,
};

// Process engagement stats to create funnel data
function processEngagementStats(engagementStats: any[]) {
  if (!engagementStats || engagementStats.length === 0) {
    return {
      all: [],
      whatsapp: [],
      email: [],
      voice: [],
    };
  }

  // Group by channel
  const byChannel: Record<string, any[]> = {};
  engagementStats.forEach((stat) => {
    const channel = stat.channel || "unknown";
    if (!byChannel[channel]) {
      byChannel[channel] = [];
    }
    byChannel[channel].push(stat);
  });

  // Calculate totals
  const totals: Record<string, number> = {};
  engagementStats.forEach((stat) => {
    const status = stat.status || "";
    totals[status] = (totals[status] || 0) + (stat.count || 0);
  });

  // Find the base count (initiated or sent)
  const baseCount = totals.initiated || totals.sent || totals.called || 1;

  // Create funnel stages
  const createFunnelStages = (channelStats: any[], channelName: string) => {
    const channelTotals: Record<string, number> = {};
    channelStats.forEach((stat) => {
      const status = stat.status || "";
      channelTotals[status] = (channelTotals[status] || 0) + (stat.count || 0);
    });

    const channelBase = channelTotals.initiated || channelTotals.sent || channelTotals.called || baseCount;
    if (channelBase === 0) return [];

    const stages = [];
    
    // Sent/Called
    const sentCount = channelTotals.sent || channelTotals.called || channelTotals.initiated || 0;
    stages.push({
      stage: channelName === "voice" ? "Called" : "Sent",
      value: 100,
      percentage: "100%",
      count: sentCount,
    });

    // Delivered/Answered
    const deliveredCount = channelTotals.delivered || channelTotals.answered || 0;
    const deliveredPercent = sentCount > 0 ? Math.round((deliveredCount / sentCount) * 100) : 0;
    stages.push({
      stage: channelName === "voice" ? "Answered" : "Delivered",
      value: deliveredPercent,
      percentage: `${deliveredPercent}%`,
      count: deliveredCount,
      dropoff: 100 - deliveredPercent,
    });

    // Read/Greeted
    const readCount = channelTotals.read || channelTotals.greeted || 0;
    const readPercent = sentCount > 0 ? Math.round((readCount / sentCount) * 100) : 0;
    stages.push({
      stage: channelName === "voice" ? "Greeted" : "Read",
      value: readPercent,
      percentage: `${readPercent}%`,
      count: readCount,
      dropoff: deliveredPercent - readPercent,
    });

    // Interacted (assuming this is read + some interaction)
    const interactedCount = readCount; // Simplified
    const interactedPercent = sentCount > 0 ? Math.round((interactedCount / sentCount) * 100) : 0;
    stages.push({
      stage: "Interacted",
      value: interactedPercent,
      percentage: `${interactedPercent}%`,
      count: interactedCount,
      dropoff: readPercent - interactedPercent,
    });

    // Dropped-off (failed)
    const droppedCount = channelTotals.failed || 0;
    const droppedPercent = sentCount > 0 ? Math.round((droppedCount / sentCount) * 100) : 0;
    stages.push({
      stage: "Dropped-off",
      value: droppedPercent,
      percentage: `${droppedPercent}%`,
      count: droppedCount,
      dropoff: interactedPercent - droppedPercent,
    });

    // Converted (simplified - would need actual conversion data)
    const convertedCount = Math.max(0, interactedCount - droppedCount);
    const convertedPercent = sentCount > 0 ? Math.round((convertedCount / sentCount) * 100) : 0;
    stages.push({
      stage: "Converted",
      value: convertedPercent,
      percentage: `${convertedPercent}%`,
      count: convertedCount,
      dropoff: interactedPercent - convertedPercent,
    });

    return stages;
  };

  // Process all channels
  const allStages = createFunnelStages(engagementStats, "all");
  const whatsappStats = byChannel.whatsapp_chat || byChannel.whatsapp || [];
  const emailStats = byChannel.email || [];
  const voiceStats = byChannel.voice || [];

  return {
    all: allStages,
    whatsapp: whatsappStats.length > 0 ? createFunnelStages(whatsappStats, "whatsapp") : [],
    email: emailStats.length > 0 ? createFunnelStages(emailStats, "email") : [],
    voice: voiceStats.length > 0 ? createFunnelStages(voiceStats, "voice") : [],
  };
}

// Process failure stats for chart
function processFailureStats(failureStats: any[]) {
  if (!failureStats || failureStats.length === 0) {
    return [];
  }

  const byChannel: Record<string, Record<string, number>> = {};

  failureStats.forEach((stat) => {
    const channel = stat.channel || "unknown";
    const message = stat.message || "Unknown";
    
    if (!byChannel[channel]) {
      byChannel[channel] = {};
    }
    
    byChannel[channel][message] = (byChannel[channel][message] || 0) + (stat.count || 0);
  });

  // Convert to chart format
  const chartData: any[] = [];
  const channelMap: Record<string, string> = {
    whatsapp_chat: "WhatsApp",
    whatsapp: "WhatsApp",
    email: "Email",
    voice: "Voice",
  };

  Object.entries(byChannel).forEach(([channel, failures]) => {
    const channelName = channelMap[channel] || channel;
    const dataPoint: any = { channel: channelName };
    
    Object.entries(failures).forEach(([message, count]) => {
      dataPoint[message] = count;
    });
    
    chartData.push(dataPoint);
  });

  return chartData;
}

export default function CampaignInsightsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const campaignId = searchParams?.get("campaign_id");

  const { data: performanceData, isLoading } = useSWR(
    campaignId ? `campaign-performance-${campaignId}` : null,
    () => fetchCampaignPerformanceSummary(campaignId || ""),
    swrOptions
  );

  const campaignName = performanceData?.campaign_name || "Campaign";
  const campaignType = performanceData?.campaign_type || "";

  // Process data for charts
  const funnelData = useMemo(() => {
    if (!performanceData?.engagement_stats) return null;
    return processEngagementStats(performanceData.engagement_stats);
  }, [performanceData]);

  const failureData = useMemo(() => {
    if (!performanceData?.failure_stats_by_channel) return [];
    return processFailureStats(performanceData.failure_stats_by_channel);
  }, [performanceData]);

  if (!campaignId) {
    return (
      <ProtectedRoute>
        <div className="flex flex-col w-full">
          <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="icon">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Campaign Insights</h1>
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
            <Card>
              <CardContent className="p-6">
                <div className="text-center text-muted-foreground">
                  Please select a campaign to view insights.
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="flex flex-col w-full">
          <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="icon">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Loading...</h1>
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
            <Card>
              <CardContent className="p-6">
                <div className="text-center text-muted-foreground">Loading campaign insights...</div>
              </CardContent>
            </Card>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  if (!performanceData) {
    return (
      <ProtectedRoute>
        <div className="flex flex-col w-full">
          <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="icon">
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight">Campaign Insights</h1>
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
            <Card>
              <CardContent className="p-6">
                <div className="text-center text-muted-foreground">
                  No performance data available for this campaign.
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
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
          {/* Tabs for Statistics and Audience */}
          <Tabs defaultValue="statistics" className="w-full">
            <TabsList>
              <TabsTrigger value="statistics">Statistics</TabsTrigger>
              <TabsTrigger value="audience">Audience / Leads</TabsTrigger>
            </TabsList>

            {/* Statistics Tab */}
            <TabsContent value="statistics" className="space-y-6 mt-6">
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Campaign Performance Statistics</h2>

                {/* Engagement Funnel */}
                {funnelData && (funnelData.all?.length > 0 || funnelData.whatsapp?.length > 0 || funnelData.email?.length > 0 || funnelData.voice?.length > 0) && (
                  <Card className="shadow">
                    <CardHeader>
                      <CardTitle>Engagement Funnel</CardTitle>
                      <CardDescription>Track user journey from initial contact to conversion</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <EngagementFunnel customData={funnelData} />
                    </CardContent>
                  </Card>
                )}

                {/* Failure Reasons Bar Graph */}
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

                {/* Analytics Charts */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  {/* Cost per Lead */}
                  <Card className="shadow">
                    <CardHeader>
                      <CardTitle>Cost per Lead by Channel</CardTitle>
                      <CardDescription>Average cost to acquire a lead per channel</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <CostPerLeadChart />
                    </CardContent>
                  </Card>

                  {/* Intent Distribution */}
                  <Card className="shadow">
                    <CardHeader>
                      <CardTitle>Intent Distribution by Channel</CardTitle>
                      <CardDescription>Distribution of conversation intents across channels</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ConversationIntentChart />
                    </CardContent>
                  </Card>
                </div>
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
    </ProtectedRoute>
  );
}

















