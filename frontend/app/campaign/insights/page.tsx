"use client";

import { useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { ArrowLeft, AlertCircle, BarChart3, AlertTriangle } from "lucide-react";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Cell 
} from 'recharts';

// --- UI Component Imports ---
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// --- Custom Component Imports ---
import { EngagementFunnel } from "@/components/engagement-funnel";
import { CampaignFailureChart } from "@/components/campaign-failure-chart";
import { CostPerLeadChart } from "@/components/cost-per-lead-chart";
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

const WA_TO_DISPOSITION: Record<string, string> = {
  "read": "contacted",
  "sent": "attempted",
  "initiated": "queued",
  "delivered": "reached",
  "failed": "failed",
  "interacted": "engaged",
  "converted": "converted"
};

const CHANNEL_COLORS: Record<string, string> = {
  "whatsapp_chat": "#25D366",
  "whatsapp": "#25D366",
  "email": "#EA4335",
  "voice": "#4285F4",
  "sms": "#FACC15",
  "default": "#8884d8"
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

interface IntentStat {
  channel: string;
  count: number;
  intent?: string;
}

interface CampaignPerformance {
  campaign_name: string;
  campaign_type: string;
  engagement_stats: EngagementStat[];
  failure_stats_by_channel: FailureStat[];
  intent_distribution_by_channel: IntentStat[];
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

function processEngagementStats(engagementStats: EngagementStat[]) {
  if (!engagementStats || engagementStats.length === 0) {
    return { all: [], whatsapp: [], email: [], voice: [] };
  }

  const byChannel: Record<string, EngagementStat[]> = {};
  let globalTotal = 0;

  engagementStats.forEach((stat) => {
    const channel = stat.channel || "unknown";
    if (!byChannel[channel]) byChannel[channel] = [];
    byChannel[channel].push(stat);
    globalTotal += (stat.count || 0);
  });

  const createFunnelStages = (channelStats: EngagementStat[]): FunnelStage[] => {
    const counts = {
      queued: 0,
      attempted: 0,
      reached: 0,
      contacted: 0,
      engaged: 0,
      converted: 0,
      failed: 0
    };

    let channelTotal = 0;

    channelStats.forEach((stat) => {
      const rawStatus = (stat.status || "").toLowerCase();
      const disposition = WA_TO_DISPOSITION[rawStatus];
      
      if (disposition && disposition in counts) {
        counts[disposition as keyof typeof counts] += (stat.count || 0);
        channelTotal += (stat.count || 0);
      }
    });

    if (channelTotal === 0) return [];

    const stages: FunnelStage[] = [];
    const pushStage = (name: string, val: number) => {
      stages.push({
        stage: name,
        value: calculatePercentage(val, channelTotal),
        percentage: `${calculatePercentage(val, channelTotal)}%`,
        count: val,
        dropoff: 0
      });
    };

    pushStage("Queued", counts.queued);
    pushStage("Attempted", counts.attempted);
    pushStage("Reached", counts.reached);
    pushStage("Contacted", counts.contacted);
    pushStage("Engaged", counts.engaged);
    pushStage("Converted", counts.converted);

    return stages;
  };

  return {
    all: createFunnelStages(engagementStats),
    whatsapp: createFunnelStages(byChannel.whatsapp_chat || byChannel.whatsapp || []),
    email: createFunnelStages(byChannel.email || []),
    voice: createFunnelStages(byChannel.voice || []),
  };
}

function processFailureStats(failureStats: FailureStat[]) {
  if (!failureStats || failureStats.length === 0) return [];
  return failureStats.map(stat => ({
    ...stat,
    channelName: stat.channel === "whatsapp_chat" ? "WhatsApp" : stat.channel
  }));
}

function processIntentStats(intentStats: IntentStat[]) {
  if (!intentStats || intentStats.length === 0) return [];
  
  return intentStats.map(stat => ({
    name: stat.channel === "whatsapp_chat" ? "WhatsApp" : stat.channel,
    count: stat.count,
    fill: CHANNEL_COLORS[stat.channel] || CHANNEL_COLORS.default
  }));
}

// --- Inner Component ---

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

  // Data Memoization
  const funnelData = useMemo(() => 
    processEngagementStats(performanceData?.engagement_stats || []), 
  [performanceData]);

  const failureData = useMemo(() => 
    processFailureStats(performanceData?.failure_stats_by_channel || []), 
  [performanceData]);

  const intentData = useMemo(() => 
    processIntentStats(performanceData?.intent_distribution_by_channel || []), 
  [performanceData]);

  // -- Render States --
  if (isLoading) {
    return (
      <div className="flex flex-col w-full space-y-6 px-4 md:px-6 lg:px-8 pb-6 mt-6">
         <div className="space-y-2"><Skeleton className="h-8 w-[250px]" /></div>
         <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 px-4 md:px-6 lg:px-8 pb-6 w-full mt-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>Failed to load data. {error.message}</AlertDescription>
        </Alert>
        <Link href="/"><Button variant="outline" className="mt-4"><ArrowLeft className="mr-2 h-4 w-4" /> Back</Button></Link>
      </div>
    );
  }

  if (!performanceData) {
    return (
       <div className="flex-1 px-4 md:px-6 lg:px-8 pb-6 w-full mt-6">
        <Alert><AlertTitle>No Data</AlertTitle><AlertDescription>No campaign selected.</AlertDescription></Alert>
       </div>
    );
  }

  return (
    <div className="flex flex-col w-full">
      {/* Header */}
      <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{campaignName}</h1>
              <Badge variant={campaignType === "post-sales" ? "default" : "secondary"}>
                {campaignType === "post-sales" ? "Post-Sales" : campaignType === "pre-sales" ? "Pre-Sales" : campaignType}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-1">Campaign Performance Statistics</p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
        <Tabs defaultValue="statistics" className="w-full">
          <TabsList>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="audience">Audience / Leads</TabsTrigger>
          </TabsList>

          <TabsContent value="statistics" className="space-y-6 mt-6">
            
            {/* 1. Engagement Funnel */}
            {(funnelData.all?.length > 0) && (
              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle>Engagement Funnel</CardTitle>
                  <CardDescription>Current status distribution (Non-Cumulative)</CardDescription>
                </CardHeader>
                <CardContent>
                  <EngagementFunnel customData={funnelData} />
                </CardContent>
              </Card>
            )}

            {/* 2. Combined Row: Failure Chart, Failure Grid, Intent Distribution */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Column 1: Failure Chart */}
              <Card className="shadow-sm flex flex-col">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-medium">Failure Chart</CardTitle>
                  <CardDescription>Visual breakdown of errors</CardDescription>
                </CardHeader>
                <CardContent className="flex-1 min-h-[250px]">
                  {failureData.length > 0 ? (
                    <CampaignFailureChart customData={failureData} />
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">No failures recorded</div>
                  )}
                </CardContent>
              </Card>

              {/* Column 2: Failure Reasons Grid */}
              <Card className="shadow-sm flex flex-col">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-base font-medium">Failure Reasons</CardTitle>
                      <CardDescription>Detailed list</CardDescription>
                    </div>
                    {failureData.length > 0 && (
                      <Badge variant="destructive" className="ml-2 h-6">
                        {failureData.reduce((acc, curr) => acc + curr.count, 0)} Failed
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto">
                   {failureData.length > 0 ? (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[100px]">Channel</TableHead>
                          <TableHead>Error</TableHead>
                          <TableHead className="text-right">#</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {failureData.map((item, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-medium capitalize text-xs">{item.channelName}</TableCell>
                            <TableCell className="text-muted-foreground text-xs truncate max-w-[120px]" title={item.message}>
                              {item.message}
                            </TableCell>
                            <TableCell className="text-right font-bold text-xs">{item.count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                   ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">No failures recorded</div>
                   )}
                </CardContent>
              </Card>

              {/* Column 3: Intent Distribution */}
              <Card className="shadow-sm flex flex-col">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-medium">Intent Distribution</CardTitle>
                  <CardDescription>By Channel</CardDescription>
                </CardHeader>
                <CardContent className="flex-1 min-h-[250px]">
                  {intentData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={intentData} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                        <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                        <Tooltip 
                          cursor={{ fill: 'transparent' }}
                          contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                        />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={40}>
                          {intentData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                      No intent data available
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* 3. Cost Metrics (Separate Row) */}
            <div className="grid grid-cols-1" style={{display: "none"}}>
              <Card className="shadow-sm">
                <CardHeader>
                  <CardTitle>Cost per Lead</CardTitle>
                  <CardDescription>Average cost to acquire a lead</CardDescription>
                </CardHeader>
                <CardContent>
                  <CostPerLeadChart />
                </CardContent>
              </Card>
            </div>

          </TabsContent>

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

// --- Main Page Export ---

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