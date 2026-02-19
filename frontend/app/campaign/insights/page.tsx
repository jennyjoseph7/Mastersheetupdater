"use client";

import { useMemo, Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { 
  ArrowLeft, 
  AlertCircle, 
  TrendingUp, 
  Users, 
  AlertTriangle, 
  PieChart as PieIcon, 
  DollarSign,
  Download,
  ChevronLeft,
  ChevronRight,
  Search,
  ArrowUpDown,
  ChevronUp,
  ChevronDown
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
  LabelList,
} from "recharts";

// --- UI Component Imports ---
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// --- Custom Component Imports ---
import { ProfessionalFunnel } from "@/components/engagement-funnel";
import { ProtectedRoute } from "@/components/protected-route";
import { EngagementModal } from "@/components/engagement-modal";
import {
  fetchCampaignPerformanceSummary,
  fetchCampaignLeads,
  epochToIST,
} from "@/utils/api";

// --- Constants & Configuration ---

const SWR_OPTIONS = {
  revalidateOnFocus: false,
  revalidateIfStale: false,
  revalidateOnReconnect: false,
  errorRetryCount: 0,
  shouldRetryOnError: false,
};

const CHANNEL_COLORS: Record<string, string> = {
  whatsapp_chat: "#10B981",
  whatsapp: "#10B981",
  email: "#EF4444",
  voice: "#3B82F6",
  sms: "#F59E0B",
  rcs: "#6366F1",
  default: "#64748B",
};

const PIE_COLORS = [
  "#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#3B82F6", "#F43F5E",
];

// --- TypeScript Interfaces ---

interface EngagementStat {
  channel: string; total: number; converted: number; interacted: number;
  sent_called: number; read_greeted: number; delivered_answered: number;
  [key: string]: any;
}

interface FailureStat {
  channel: string; message: string; count: number;
}

interface IntentStat {
  count: number; disposition_detail?: string; [key: string]: any;
}

interface CostStat {
  channel: string; total_cost: number; cost_per_lead: number; converted_leads: number;
}

interface CampaignLead {
  pre_sales_lead_id?: string; post_sales_lead_id?: string; lead_id?: string;
  user_id?: string; person_name: string; phone_number: string; email?: string;
  disposition: string; provider_status?: string; last_interaction_time?: number;
  audience_name: string; created: number; updated: number; channel?: string;
  campaign_name?: string; dealer_name?: string; region_name?: string;
  [key: string]: any;
}

// --- Helper Logic ---

function processFailureStats(failureStats: FailureStat[]) {
  if (!failureStats || failureStats.length === 0) return [];
  return failureStats.map((stat) => ({
    ...stat,
    channelName: stat.channel === "whatsapp_chat" ? "WhatsApp" : (stat.channel || "Unknown"),
    fill: CHANNEL_COLORS[stat.channel === "whatsapp_chat" ? "whatsapp" : stat.channel] || CHANNEL_COLORS.default
  }));
}

function processIntentStats(intentStats: IntentStat[]) {
  if (!intentStats || intentStats.length === 0) return [];
  return intentStats
    .sort((a, b) => b.count - a.count)
    .map((stat, index) => ({
      name: stat.disposition_detail || "Other",
      value: stat.count,
      fill: PIE_COLORS[index % PIE_COLORS.length],
    }));
}

function processCostStats(costStats: CostStat[]) {
  if (!costStats || costStats.length === 0) return [];
  return costStats.map((stat) => ({
    name: stat.channel === "whatsapp_chat" ? "WhatsApp" : stat.channel,
    cpl: stat.cost_per_lead,
    total: stat.total_cost,
    leads: stat.converted_leads,
    fill: CHANNEL_COLORS[stat.channel] || CHANNEL_COLORS.default,
  }));
}

function exportToCSV(data: CampaignLead[], filename: string) {
  if (!data || !data.length) return;

  const headers = ["Name", "Phone", "Email", "Disposition", "Provider Status", "Last Interaction"];
  
  const rows = data.map(lead => [
    `"${lead.person_name || ''}"`,
    `"${lead.phone_number || ''}"`,
    `"${lead.email || ''}"`,
    `"${lead.disposition || ''}"`,
    `"${lead.provider_status || ''}"`,
    `"${lead.last_interaction_time ? epochToIST(lead.last_interaction_time) : ''}"`
  ]);

  const csvContent = [
    headers.join(","), 
    ...rows.map(e => e.join(","))
  ].join("\n");

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// --- Inner Component ---

function CampaignInsightsContent() {
  const searchParams = useSearchParams();
  const campaignId = searchParams?.get("campaign_id");
  const [engagementModalOpen, setEngagementModalOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState<{
    userId: string;
    personName?: string;
  } | null>(null);

  // --- Table & Pagination State ---
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [dispositionFilter, setDispositionFilter] = useState("all"); // Added Disposition State
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null);
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);

  // Debounce search term to avoid hitting the API on every single keystroke
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 500);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // 1. Fetch Performance Data (This determines the Campaign Type)
  const {
    data: rawData,
    isLoading: perfLoading,
    error: perfError,
  } = useSWR<any>(
    campaignId ? `campaign-performance-${campaignId}` : null,
    () => fetchCampaignPerformanceSummary(campaignId || ""),
    SWR_OPTIONS
  );

  const performanceData = (rawData?.data && Array.isArray(rawData.data)) 
    ? rawData.data[0] 
    : rawData;

  const campaignName = performanceData?.campaign_name || "Campaign";
  const campaignType = performanceData?.campaign_type || "";

  // 2. Prepare Data for Charts (Memoized)
  const failureData = useMemo(() => processFailureStats(performanceData?.failure_stats_by_channel || []), [performanceData]);
  const intentData = useMemo(() => processIntentStats(performanceData?.intent_distribution_by_channel || []), [performanceData]);
  const costData = useMemo(() => processCostStats(performanceData?.cost_per_lead_by_channel || []), [performanceData]);
  const funnelApiResponse = useMemo(() => {
    if (!performanceData) return undefined;
    return { data: [{ ...performanceData, campaign_id: campaignId || "" }] };
  }, [performanceData, campaignId]);

  // 3. Conditional Fetch Leads (Server Pagination & Sorting)
  const {
    data: leadsDataRaw,
    isLoading: leadsLoading,
    error: leadsError,
  } = useSWR<{ items: CampaignLead[]; total_number: number }>(
    campaignId && campaignType 
      // Include dispositionFilter in SWR cache key so it refetches when it changes
      ? ['campaign-leads', campaignId, campaignType, currentPage, pageSize, debouncedSearch, sortConfig?.key, sortConfig?.direction, dispositionFilter] 
      : null,
    ([_, id, type, page, size, searchStr, sortKey, sortDir, dispFilter]) => 
      fetchCampaignLeads({
        campaignId: id as string,
        campaignType: type as string,
        page_number: page as number,
        page_size: size as number,
        search: searchStr as string,
        sort_by: sortKey as string | undefined,
        sort_dir: sortDir as string | undefined,
        disposition: dispFilter === "all" ? undefined : dispFilter as string // Pass the filter to the API
      }),
    SWR_OPTIONS
  );

  // Server-processed records
  const serverLeads = leadsDataRaw?.items || [];
  const totalRecords = leadsDataRaw?.total_number || 0;
  const totalPages = Math.ceil(totalRecords / pageSize) || 1;

  // Handlers
  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage((prev) => prev + 1);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  const handleSort = (key: string) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig && sortConfig.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });
    setCurrentPage(1); // Reset to first page when sorting changes
  };

  // Helper for rendering sort arrows in headers
  const getSortIcon = (columnKey: string) => {
    if (sortConfig?.key !== columnKey) {
      return <ArrowUpDown className="ml-2 h-4 w-4 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />;
    }
    return sortConfig.direction === "asc" ? (
      <ChevronUp className="ml-2 h-4 w-4 text-slate-900 dark:text-slate-100" />
    ) : (
      <ChevronDown className="ml-2 h-4 w-4 text-slate-900 dark:text-slate-100" />
    );
  };

  if (perfLoading) {
    return (
      <div className="flex flex-col w-full space-y-6 px-4 md:px-6 lg:px-8 pb-6 mt-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-[250px]" />
        </div>
        <Skeleton className="h-[400px] w-full" />
      </div>
    );
  }

  if (perfError || !performanceData) {
    return (
      <div className="flex-1 px-4 md:px-6 lg:px-8 pb-6 w-full mt-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {perfError ? perfError.message : "No campaign data available."}
          </AlertDescription>
        </Alert>
        <Link href="/">
          <Button variant="outline" className="mt-4">
            <ArrowLeft className="mr-2 h-4 w-4" /> Back
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full min-h-screen bg-slate-50/50 dark:bg-slate-950/50">
      
      {/* Header Section */}
      <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full border-b bg-background sticky top-0 z-10 backdrop-blur-sm bg-white/80 dark:bg-slate-950/80">
        <div className="flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="icon" className="hover:bg-slate-100 dark:hover:bg-slate-800">
              <ArrowLeft className="h-5 w-5 text-slate-600 dark:text-slate-400" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                {campaignName}
              </h1>
              <Badge
                variant={campaignType === "post-sales" ? "default" : "secondary"}
                className="rounded-full px-3 font-normal"
              >
                {campaignType === "post-sales" ? "Post-Sales" : "Pre-Sales"}
              </Badge>
            </div>
            <p className="text-sm text-slate-500 mt-0.5">Performance Overview</p>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-10 w-full mt-8">
        <Tabs defaultValue="audience" className="w-full">
          <TabsList>
            <TabsTrigger value="statistics">Statistics</TabsTrigger>
            <TabsTrigger value="audience">Audience / Leads</TabsTrigger>
          </TabsList>

          <TabsContent value="statistics" className="space-y-6 mt-6">
            
            {/* 1. Engagement Funnel Card */}
            {performanceData.engagement_stats?.length > 0 && (
              <Card className="shadow-sm border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <CardHeader className="pb-4 border-b border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-indigo-50 dark:bg-indigo-950/30 rounded-lg">
                      <TrendingUp className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div>
                      <CardTitle className="text-base font-semibold text-slate-900 dark:text-slate-100">
                        Engagement Funnel
                      </CardTitle>
                      <CardDescription>Conversion journey breakdown</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-6">
                  <ProfessionalFunnel apiResponse={funnelApiResponse as any} />
                </CardContent>
              </Card>
            )}

            {/* 2. Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Intent Distribution - Donut Chart */}
              <Card className="shadow-sm border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col col-span-1 lg:col-span-2">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
                      <PieIcon className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                    <div>
                      <CardTitle className="text-base font-semibold">Intent Distribution</CardTitle>
                      <CardDescription>Customer responses by category</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 min-h-[300px] flex items-center justify-center">
                  {intentData.length > 0 ? (
                    <div className="w-full h-[320px] flex flex-row items-center">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={intentData}
                            cx="40%" 
                            cy="50%"
                            innerRadius={70} 
                            outerRadius={100}
                            paddingAngle={3}
                            dataKey="value"
                            stroke="none"
                          >
                            {intentData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.fill} />
                            ))}
                          </Pie>
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: 'white', 
                              borderRadius: '8px', 
                              border: '1px solid #e2e8f0',
                              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                            }}
                            itemStyle={{ color: '#1e293b', fontSize: '13px', fontWeight: 500 }}
                          />
                          <Legend 
                            layout="vertical" 
                            verticalAlign="middle" 
                            align="right"
                            wrapperStyle={{ 
                              paddingLeft: "20px",
                              fontSize: "13px",
                              lineHeight: "26px",
                              maxWidth: "55%" 
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="text-slate-400 text-sm flex items-center gap-2">
                      <AlertCircle className="h-4 w-4" /> No intent data
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Delivery Issues - Inline Chart */}
              <Card className="shadow-sm border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-red-50 dark:bg-red-950/30 rounded-lg">
                        <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
                      </div>
                      <div>
                        <CardTitle className="text-base font-semibold">Delivery Issues</CardTitle>
                        <CardDescription>Top failure reasons</CardDescription>
                      </div>
                    </div>
                    {failureData.length > 0 && (
                      <Badge variant="outline" className="border-red-200 text-red-700 bg-red-50">
                        {failureData.reduce((a, b) => a + b.count, 0)} Failed
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-auto pt-4">
                  {failureData.length > 0 ? (
                    <div className="space-y-4">
                      {/* Chart */}
                      <div className="h-[220px] w-full mb-2">
                         <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={failureData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                                <XAxis 
                                  dataKey="channelName" 
                                  axisLine={false} 
                                  tickLine={false} 
                                  tick={{ fontSize: 12, fill: '#64748b' }} 
                                  dy={10} 
                                />
                                <YAxis 
                                  allowDecimals={false}
                                  axisLine={false} 
                                  tickLine={false} 
                                  tick={{ fontSize: 12, fill: '#64748b' }} 
                                  width={30}
                                />
                                <Tooltip 
                                  cursor={{ fill: 'rgba(0,0,0,0.05)' }}
                                  content={({ active, payload }) => {
                                    if (active && payload && payload.length) {
                                      const data = payload[0].payload;
                                      return (
                                        <div className="bg-white border rounded p-2 shadow-sm text-xs">
                                          <p className="font-semibold mb-1">{data.channelName}</p>
                                          <p className="text-slate-500">{data.message}</p>
                                          <p className="font-bold mt-1">{data.count} failed</p>
                                        </div>
                                      );
                                    }
                                    return null;
                                  }}
                                />
                                <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={24} maxBarSize={40}>
                                  {failureData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.fill} />
                                  ))}
                                </Bar>
                            </BarChart>
                         </ResponsiveContainer>
                      </div>
                      
                      {/* List View */}
                      <div className="space-y-3">
                        {failureData.map((item, idx) => (
                          <div key={idx} className="flex items-center justify-between text-sm border-b border-slate-50 pb-2 last:border-0 last:pb-0">
                             <div className="flex flex-col max-w-[70%]">
                                <span className="font-medium text-slate-700 capitalize flex items-center gap-2">
                                  <span 
                                    className="w-2 h-2 rounded-full" 
                                    style={{ backgroundColor: item.fill }}
                                  />
                                  {item.channelName}
                                </span>
                                <span className="text-xs text-slate-500 truncate pl-4" title={item.message}>
                                  {item.message}
                                </span>
                             </div>
                             <div className="font-bold text-slate-900">{item.count}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                      No failures recorded
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* 3. Cost Analysis - Vertical Columns */}
            <Card className="shadow-sm border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                      <DollarSign className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <CardTitle className="text-base font-semibold">Cost Analysis</CardTitle>
                      <CardDescription>Cost Per Lead (CPL) by Channel</CardDescription>
                    </div>
                  </div>
                  {costData.length > 0 && (
                    <div className="text-right">
                       <p className="text-xs text-slate-500 uppercase tracking-wide">Total Spend</p>
                       <p className="text-xl font-bold text-slate-900">
                         ₹{costData.reduce((acc, item) => acc + item.total, 0).toLocaleString()}
                       </p>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {costData.length > 0 ? (
                  <div className="h-[320px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={costData}
                        margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                        barCategoryGap="30%" 
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                        <XAxis 
                          dataKey="name" 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fill: '#64748b', fontSize: 13, fontWeight: 500 }}
                          dy={10}
                        />
                        <YAxis 
                          axisLine={false} 
                          tickLine={false} 
                          tick={{ fill: '#64748b', fontSize: 12 }}
                          tickFormatter={(value) => `₹${value}`}
                        />
                        <Tooltip
                          cursor={{ fill: 'rgba(241, 245, 249, 0.4)' }}
                          content={({ active, payload }) => {
                            if (active && payload && payload.length) {
                              const data = payload[0].payload;
                              return (
                                <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg min-w-[150px]">
                                  <p className="font-semibold text-slate-900 mb-2">{data.name}</p>
                                  <div className="space-y-1">
                                    <div className="flex justify-between text-sm">
                                      <span className="text-slate-500">CPL:</span>
                                      <span className="font-medium text-emerald-600">₹{data.cpl.toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between text-xs text-slate-400">
                                      <span>Total Cost:</span>
                                      <span>₹{data.total.toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between text-xs text-slate-400">
                                      <span>Leads:</span>
                                      <span>{data.leads}</span>
                                    </div>
                                  </div>
                                </div>
                              );
                            }
                            return null;
                          }}
                        />
                        <Bar 
                          dataKey="cpl" 
                          radius={[6, 6, 0, 0]} 
                          maxBarSize={60}
                        >
                          {costData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                          <LabelList 
                            dataKey="cpl" 
                            position="top" 
                            formatter={(val: any) => typeof val === 'number' ? `₹${val.toFixed(0)}` : ''} 
                            style={{ fill: '#64748b', fontSize: 12, fontWeight: 600 }}
                          />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                   <div className="h-[200px] flex flex-col items-center justify-center text-slate-400">
                      <div className="p-3 bg-slate-50 rounded-full mb-3">
                         <DollarSign className="h-6 w-6 text-slate-300" />
                      </div>
                      <p>No cost data recorded</p>
                   </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* AUDIENCE TAB CONTENT - Filter, Sort, Server Paginate */}
          <TabsContent value="audience" className="space-y-6 mt-6">
            <Card className="shadow-sm border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
              <CardHeader className="flex flex-col md:flex-row items-start md:items-center justify-between pb-4 gap-4">
                <div className="flex items-center gap-2">
                   <div className="p-2 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
                      <Users className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                   </div>
                   <div>
                    <CardTitle className="text-base font-semibold">Campaign Leads</CardTitle>
                    <CardDescription>
                      View and manage leads from this campaign ({totalRecords} records)
                    </CardDescription>
                   </div>
                </div>

                {/* Table Tool Bar */}
                <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
                  {/* Search Input */}
                  <div className="relative w-full sm:w-64">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                    <Input 
                      placeholder="Search leads..." 
                      className="pl-8 h-9 w-full bg-slate-50"
                      value={searchTerm}
                      onChange={(e) => {
                        setSearchTerm(e.target.value);
                        setCurrentPage(1); // Reset to first page on search
                      }}
                    />
                  </div>
                  
                  {/* Disposition Filter Dropdown */}
                  <select
                    className="h-9 rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-400 w-full sm:w-auto cursor-pointer"
                    value={dispositionFilter}
                    onChange={(e) => {
                      setDispositionFilter(e.target.value);
                      setCurrentPage(1); // Reset to first page on filter change
                    }}
                  >
                    <option value="all">Status: All</option>
                    <option value="queued">Queued</option>
                    <option value="engaged">Engaged</option>
                    <option value="contacted">Contacted</option>
                  </select>

                  {/* Page Size Dropdown */}
                  <select 
                    className="h-9 rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-400 w-full sm:w-auto cursor-pointer"
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1); // Reset to first page when changing size
                    }}
                  >
                    <option value={10}>10 per page</option>
                    <option value={25}>25 per page</option>
                    <option value={50}>50 per page</option>
                    <option value={100}>100 per page</option>
                  </select>

                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="gap-2 h-9 w-full sm:w-auto"
                    disabled={serverLeads.length === 0}
                    onClick={() => exportToCSV(serverLeads, `campaign_leads_${campaignId || 'data'}.csv`)}
                  >
                    <Download className="h-4 w-4" /> Export
                  </Button>
                </div>
              </CardHeader>
              
              <CardContent>
                {leadsLoading ? (
                  <div className="space-y-4">
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-12 w-full" />
                  </div>
                ) : leadsError ? (
                  <div className="p-8 text-center text-red-500 bg-red-50 rounded-lg border border-red-100">
                    <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-red-400" />
                    <p>Failed to load leads data</p>
                  </div>
                ) : !serverLeads || serverLeads.length === 0 ? (
                  <div className="text-center text-slate-500 py-12 bg-slate-50/50 rounded-lg border border-dashed border-slate-200 flex flex-col items-center">
                    <Search className="h-8 w-8 text-slate-300 mb-3" />
                    <p>No matching leads found.</p>
                    {searchTerm && (
                      <Button variant="link" onClick={() => setSearchTerm("")} className="mt-2 text-blue-600">
                        Clear search
                      </Button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-md border border-slate-100 overflow-hidden">
                      <Table>
                        <TableHeader className="bg-slate-50/50">
                          <TableRow>
                            {/* Sortable Column Headers */}
                            <TableHead 
                              className="w-[200px] font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 group transition-colors"
                              onClick={() => handleSort("person_name")}
                            >
                              <div className="flex items-center">Name {getSortIcon("person_name")}</div>
                            </TableHead>
                            
                            <TableHead 
                              className="font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 group transition-colors"
                              onClick={() => handleSort("phone_number")}
                            >
                              <div className="flex items-center">Phone {getSortIcon("phone_number")}</div>
                            </TableHead>

                            <TableHead 
                              className="font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 group transition-colors"
                              onClick={() => handleSort("email")}
                            >
                              <div className="flex items-center">Email {getSortIcon("email")}</div>
                            </TableHead>

                            <TableHead 
                              className="text-center font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 group transition-colors"
                              onClick={() => handleSort("disposition")}
                            >
                              <div className="flex items-center justify-center">Disposition {getSortIcon("disposition")}</div>
                            </TableHead>

                            <TableHead 
                              className="text-center font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 group transition-colors"
                              onClick={() => handleSort("provider_status")}
                            >
                              <div className="flex items-center justify-center">Status {getSortIcon("provider_status")}</div>
                            </TableHead>

                            <TableHead 
                              className="text-right font-semibold text-slate-600 cursor-pointer hover:bg-slate-100 group transition-colors"
                              onClick={() => handleSort("last_interaction_time")}
                            >
                              <div className="flex items-center justify-end">Last Interaction {getSortIcon("last_interaction_time")}</div>
                            </TableHead>

                            <TableHead className="text-right font-semibold text-slate-600">Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {serverLeads.map((lead, index) => {
                            const leadId =
                              lead.pre_sales_lead_id ||
                              lead.post_sales_lead_id ||
                              lead.lead_id ||
                              `lead-${index}`;

                            return (
                              <TableRow key={leadId} className="hover:bg-slate-50/50 transition-colors">
                                <TableCell className="font-medium text-slate-900">
                                  {lead.person_name || "Unknown User"}
                                </TableCell>
                                <TableCell className="text-slate-500">
                                  {lead.phone_number}
                                </TableCell>
                                <TableCell className="text-slate-500 text-xs">
                                  {lead.email || "-"}
                                </TableCell>
                                <TableCell className="text-center">
                                  <Badge
                                    variant="outline"
                                    className={`
                                      capitalize font-normal border
                                      ${lead.disposition === "contacted" ? "border-green-200 text-green-700 bg-green-50" : ""}
                                      ${lead.disposition === "failed" ? "border-red-200 text-red-700 bg-red-50" : ""}
                                      ${lead.disposition === "queued" ? "border-blue-200 text-blue-700 bg-blue-50" : ""}
                                      ${lead.disposition === "reached" ? "border-purple-200 text-purple-700 bg-purple-50" : ""}
                                      ${!lead.disposition ? "border-slate-200 text-slate-500" : ""}
                                    `}
                                  >
                                    {lead.disposition || "-"}
                                  </Badge>
                                </TableCell>
                                <TableCell className="text-center">
                                  {lead.provider_status ? (
                                    <Badge variant="secondary" className="font-normal text-xs bg-slate-100 text-slate-600 hover:bg-slate-200">
                                      {lead.provider_status}
                                    </Badge>
                                  ) : <span className="text-slate-300">-</span>}
                                </TableCell>
                                <TableCell className="text-right text-xs text-slate-500">
                                  {lead.last_interaction_time ? epochToIST(lead.last_interaction_time) : "-"}
                                </TableCell>
                                <TableCell className="text-right">
                                  {/* Conditionally hide the button if disposition is "queued" */}
                                  {lead.disposition?.toLowerCase() !== "queued" && (
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      disabled={!campaignId}
                                      onClick={() => {
                                        const effectiveUserId = lead.pre_sales_lead_id || lead.post_sales_lead_id || lead.lead_id || lead.user_id;
                                        
                                        if (effectiveUserId && campaignId) {
                                          setSelectedLead({
                                            userId: effectiveUserId, 
                                            personName: lead.person_name,
                                          });
                                          setEngagementModalOpen(true);
                                        }
                                      }}
                                    >
                                      Engagement
                                    </Button>
                                  )}
                                </TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>

                    {/* Server Pagination Controls */}
                    <div className="flex items-center justify-between px-2">
                        <div className="text-sm text-slate-500">
                          Showing {totalRecords === 0 ? 0 : (currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} entries
                        </div>
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handlePrevPage}
                            disabled={currentPage === 1}
                            className="h-8 w-8 p-0"
                          >
                            <span className="sr-only">Go to previous page</span>
                            <ChevronLeft className="h-4 w-4" />
                          </Button>
                          <div className="text-sm font-medium px-2">
                            Page {currentPage} of {totalPages}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleNextPage}
                            disabled={currentPage >= totalPages}
                            className="h-8 w-8 p-0"
                          >
                            <span className="sr-only">Go to next page</span>
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {selectedLead && campaignId && (
        <EngagementModal
          isOpen={engagementModalOpen}
          onClose={() => {
            setEngagementModalOpen(false);
            setSelectedLead(null);
          }}
          userId={selectedLead.userId}
          campaignId={campaignId}
          personName={selectedLead.personName}
        />
      )}
    </div>
  );
}

export default function CampaignInsightsPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<div className="p-8"><Skeleton className="h-64 w-full" /></div>}>
        <CampaignInsightsContent />
      </Suspense>
    </ProtectedRoute>
  );
}