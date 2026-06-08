"use client";

import { useState, useEffect, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import PageHeader from "@/components/page-header";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  TrendingUp,
  Users,
  PhoneCall,
  CheckCircle2,
  AlertTriangle,
  Megaphone,
  Download,
  RefreshCw,
  Search,
  Filter,
} from "lucide-react";

// Types
interface DailySummaryItem {
  channel: string;
  created: number;
  updated: number;
  total_failed: number;
  activity_date: number | string;
  dealership_id: string;
  total_pending: number;
  total_connected: number;
  total_converted: number;
  total_leads_triggered: number;
  total_campaign_triggered: number;
  daily_dealership_summary_id: string;
}

const COLORS = [
  "#8b5cf6",
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
  "#14b8a6",
];

function DealershipSummaryContent() {
  const searchParams = useSearchParams();
  const dealershipIdParam =
    searchParams.get("dealership_id") || "dave-ai-india";

  const getWeekRange = () => {
    const today = new Date();
    const day = today.getDay();
    const diffToMonday = today.getDate() - day + (day === 0 ? -6 : 1);

    const monday = new Date(today);
    monday.setDate(diffToMonday);

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    const format = (d: Date) => {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const dayStr = String(d.getDate()).padStart(2, "0");
      return `${y}-${m}-${dayStr}`;
    };

    return {
      start: format(monday),
      end: format(sunday),
    };
  };

  const initialRange = useMemo(() => getWeekRange(), []);

  const [dealershipId, setDealershipId] = useState(dealershipIdParam);
  const [data, setData] = useState<DailySummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters State
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [startDate, setStartDate] = useState(initialRange.start);
  const [endDate, setEndDate] = useState(initialRange.end);
  const [searchQuery, setSearchQuery] = useState("");

  // Fetch data
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      let url = `/gryd/db/objects/daily_dealership_summary?sort_by=updated&sort_reverse=true&dealership_id=${dealershipId}&page_size=1000`;

      if (startDate && endDate) {
        // Parse startDate to local midnight (local timezone seconds)
        const startD = new Date(startDate);
        startD.setHours(0, 0, 0, 0);
        const startSec = Math.floor(startD.getTime() / 1000);

        // Parse endDate to local 23:59:59.999 (local timezone seconds with ms)
        const endD = new Date(endDate);
        endD.setHours(23, 59, 59, 999);
        const endSec = endD.getTime() / 1000;

        url += `&activity_date=${startSec},${endSec}`;
      }

      const res = await api(url);
      setData(res?.data || []);
    } catch (err: any) {
      console.error("[Fetch Summary Error]", err);
      setError(err?.message || "Failed to fetch dealership summary data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [dealershipId, startDate, endDate]);

  // Process Data
  const parsedData = useMemo(() => {
    return data
      .map((item) => {
        const ms =
          typeof item.activity_date === "string"
            ? parseFloat(item.activity_date)
            : item.activity_date;
        const dateObj = !isNaN(ms)
          ? new Date(ms > 1e11 ? ms : ms * 1000)
          : new Date();
        const formattedDate = dateObj.toLocaleDateString("en-IN", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });
        const isodate = dateObj.toISOString().split("T")[0]; // YYYY-MM-DD

        return {
          ...item,
          dateObj,
          formattedDate,
          isodate,
        };
      })
      .sort((a, b) => a.dateObj.getTime() - b.dateObj.getTime());
  }, [data]);

  // Get available filters
  const uniqueChannels = useMemo(() => {
    const channels = new Set(parsedData.map((d) => d.channel));
    return Array.from(channels);
  }, [parsedData]);

  // Initialize channels filter
  useEffect(() => {
    if (uniqueChannels.length > 0 && selectedChannels.length === 0) {
      setSelectedChannels(uniqueChannels);
    }
  }, [uniqueChannels]);

  // Apply active filters
  const filteredData = useMemo(() => {
    return parsedData.filter((item) => {
      // Channel filter
      if (
        selectedChannels.length > 0 &&
        !selectedChannels.includes(item.channel)
      ) {
        return false;
      }
      // Search query filter (channel name)
      if (
        searchQuery &&
        !item.channel.toLowerCase().includes(searchQuery.toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [parsedData, selectedChannels, searchQuery]);

  // Compute KPI totals
  const metrics = useMemo(() => {
    let campaigns = 0;
    let leads = 0;
    let connected = 0;
    let converted = 0;
    let failed = 0;
    let pending = 0;

    filteredData.forEach((d) => {
      campaigns += d.total_campaign_triggered || 0;
      leads += d.total_leads_triggered || 0;
      connected += d.total_connected || 0;
      converted += d.total_converted || 0;
      failed += d.total_failed || 0;
      pending += d.total_pending || 0;
    });

    const connectRate = leads > 0 ? (connected / leads) * 100 : 0;
    const conversionRate = connected > 0 ? (converted / connected) * 100 : 0;
    const overallConversionRate = leads > 0 ? (converted / leads) * 100 : 0;

    return {
      campaigns,
      leads,
      connected,
      converted,
      failed,
      pending,
      connectRate,
      conversionRate,
      overallConversionRate,
    };
  }, [filteredData]);

  // Chart Data: Trend over time
  const trendChartData = useMemo(() => {
    const grouped: Record<
      string,
      { date: string; leads: number; connected: number; converted: number }
    > = {};

    filteredData.forEach((item) => {
      const key = item.formattedDate;
      if (!grouped[key]) {
        grouped[key] = { date: key, leads: 0, connected: 0, converted: 0 };
      }
      grouped[key].leads += item.total_leads_triggered || 0;
      grouped[key].connected += item.total_connected || 0;
      grouped[key].converted += item.total_converted || 0;
    });

    return Object.values(grouped);
  }, [filteredData]);

  // Chart Data: Channel distribution
  const channelDistributionData = useMemo(() => {
    const grouped: Record<string, number> = {};
    filteredData.forEach((item) => {
      grouped[item.channel] =
        (grouped[item.channel] || 0) + item.total_leads_triggered;
    });

    return Object.entries(grouped).map(([name, value]) => ({
      name: name.replace(/_/g, " ").toUpperCase(),
      value,
    }));
  }, [filteredData]);

  // Chart Data: Channel efficiency
  const channelEfficiencyData = useMemo(() => {
    const grouped: Record<
      string,
      { name: string; leads: number; connected: number; converted: number }
    > = {};

    filteredData.forEach((item) => {
      const key = item.channel;
      if (!grouped[key]) {
        grouped[key] = {
          name: key.replace(/_/g, " ").toUpperCase(),
          leads: 0,
          connected: 0,
          converted: 0,
        };
      }
      grouped[key].leads += item.total_leads_triggered || 0;
      grouped[key].connected += item.total_connected || 0;
      grouped[key].converted += item.total_converted || 0;
    });

    return Object.values(grouped).map((c) => ({
      name: c.name,
      "Connect Rate (%)":
        c.leads > 0 ? Math.round((c.connected / c.leads) * 100) : 0,
      "Conversion Rate (%)":
        c.connected > 0 ? Math.round((c.converted / c.connected) * 100) : 0,
    }));
  }, [filteredData]);

  // Funnel data
  const funnelData = useMemo(() => {
    return [
      { name: "Total Leads", value: metrics.leads, percentage: 100 },
      {
        name: "Connected",
        value: metrics.connected,
        percentage:
          metrics.leads > 0
            ? Math.round((metrics.connected / metrics.leads) * 100)
            : 0,
      },
      {
        name: "Converted",
        value: metrics.converted,
        percentage:
          metrics.connected > 0
            ? Math.round((metrics.converted / metrics.connected) * 100)
            : 0,
      },
    ];
  }, [metrics]);

  // CSV Exporter
  const handleExportCSV = () => {
    if (filteredData.length === 0) return;

    const headers = [
      "Activity Date",
      "Channel",
      "Campaigns Triggered",
      "Leads Triggered",
      "Connected",
      "Converted",
      "Failed",
      "Pending",
    ];

    const rows = filteredData.map((d) => [
      d.formattedDate,
      d.channel,
      d.total_campaign_triggered,
      d.total_leads_triggered,
      d.total_connected,
      d.total_converted,
      d.total_failed,
      d.total_pending,
    ]);

    const csvContent =
      "data:text/csv;charset=utf-8," +
      [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `${dealershipId}_dealership_summary_${new Date().toISOString().split("T")[0]}.csv`,
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleChannelSelection = (channelName: string) => {
    if (selectedChannels.includes(channelName)) {
      setSelectedChannels(selectedChannels.filter((c) => c !== channelName));
    } else {
      setSelectedChannels([...selectedChannels, channelName]);
    }
  };

  return (
    <div className="flex flex-col space-y-6 pb-10">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 via-blue-500 to-emerald-400 bg-clip-text text-transparent">
            Dealership Performance Summary
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time metric plots and channel analysis for{" "}
            <strong>{dealershipId}</strong>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center space-x-2 bg-card border border-border/50 rounded-lg px-3 py-1.5 shadow-sm">
            <span className="text-xs text-muted-foreground font-semibold">
              Dealership:
            </span>
            <input
              type="text"
              value={dealershipId}
              onChange={(e) => setDealershipId(e.target.value)}
              className="bg-transparent border-none outline-none text-sm font-bold text-primary w-36 focus:ring-0"
              placeholder="Dealership ID"
            />
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Sync
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={handleExportCSV}
            className="gap-2 bg-violet-600 hover:bg-violet-700"
          >
            <Download className="h-4 w-4" />
            CSV Export
          </Button>
        </div>
      </div>

      {/* FILTER PANEL */}
      <Card className="border-border/50 bg-card/40 backdrop-blur-md">
        <CardHeader className="py-3 px-6 flex flex-row items-center space-x-2">
          <Filter className="h-4 w-4 text-violet-500" />
          <CardTitle className="text-sm font-bold">
            Interactive Dashboard Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="px-6 pb-4 pt-1 grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Channel Filters */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">
              Channels ({selectedChannels.length} selected)
            </label>
            <div className="flex flex-wrap gap-2">
              {uniqueChannels.map((ch) => {
                const active = selectedChannels.includes(ch);
                return (
                  <Badge
                    key={ch}
                    variant={active ? "default" : "outline"}
                    className={`cursor-pointer capitalize text-xs transition-all ${
                      active
                        ? "bg-violet-600 hover:bg-violet-700 text-white"
                        : "text-muted-foreground hover:bg-muted"
                    }`}
                    onClick={() => toggleChannelSelection(ch)}
                  >
                    {ch.replace(/_/g, " ")}
                  </Badge>
                );
              })}
            </div>
          </div>

          {/* Date Picker Range */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">
              Activity Date Range
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-background border border-border/50 rounded px-2.5 py-1 text-xs outline-none text-primary focus:border-violet-500 w-full"
              />
              <span className="text-muted-foreground text-xs">to</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-background border border-border/50 rounded px-2.5 py-1 text-xs outline-none text-primary focus:border-violet-500 w-full"
              />
            </div>
          </div>

          {/* Quick Search */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">
              Search Channels
            </label>
            <div className="relative">
              <Search className="absolute left-2.5 top-2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search channel..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-background border border-border/50 rounded pl-9 pr-3 py-1 text-xs outline-none text-primary focus:border-violet-500 w-full"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI GRID */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <Card
              key={i}
              className="animate-pulse bg-card/30 border-border/40 h-28"
            />
          ))}
        </div>
      ) : error ? (
        <Card className="border-destructive/30 bg-destructive/5 text-destructive p-6">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-5 w-5" />
            <h3 className="font-bold">Error loading summary</h3>
          </div>
          <p className="text-sm mt-2">{error}</p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card className="border-border/50 bg-card/60 backdrop-blur-md relative overflow-hidden group hover:shadow-md transition-all">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-blue-500" />
            <CardHeader className="py-4 pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold text-muted-foreground tracking-wide uppercase">
                Campaigns
              </CardTitle>
              <Megaphone className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">
                {metrics.campaigns.toLocaleString()}
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">
                Total campaign runs
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/60 backdrop-blur-md relative overflow-hidden group hover:shadow-md transition-all">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-violet-500" />
            <CardHeader className="py-4 pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold text-muted-foreground tracking-wide uppercase">
                Leads Triggered
              </CardTitle>
              <Users className="h-4 w-4 text-violet-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">
                {metrics.leads.toLocaleString()}
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">
                Total customer pipelines
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/60 backdrop-blur-md relative overflow-hidden group hover:shadow-md transition-all">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-sky-500" />
            <CardHeader className="py-4 pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold text-muted-foreground tracking-wide uppercase">
                Connected
              </CardTitle>
              <PhoneCall className="h-4 w-4 text-sky-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">
                {metrics.connected.toLocaleString()}
              </div>
              <p className="text-[10px] text-emerald-400 font-semibold mt-1">
                {metrics.connectRate.toFixed(1)}% Connect Rate
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/60 backdrop-blur-md relative overflow-hidden group hover:shadow-md transition-all">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-emerald-500" />
            <CardHeader className="py-4 pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold text-muted-foreground tracking-wide uppercase">
                Converted
              </CardTitle>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">
                {metrics.converted.toLocaleString()}
              </div>
              <p className="text-[10px] text-emerald-400 font-semibold mt-1">
                {metrics.overallConversionRate.toFixed(1)}% Sales Rate
              </p>
            </CardContent>
          </Card>

          <Card className="border-border/50 bg-card/60 backdrop-blur-md relative overflow-hidden group hover:shadow-md transition-all">
            <div className="absolute top-0 left-0 w-full h-[3px] bg-rose-500" />
            <CardHeader className="py-4 pb-2 flex flex-row items-center justify-between">
              <CardTitle className="text-xs font-semibold text-muted-foreground tracking-wide uppercase">
                Failed / Pending
              </CardTitle>
              <AlertTriangle className="h-4 w-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">
                {(metrics.failed + metrics.pending).toLocaleString()}
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">
                Failed: {metrics.failed.toLocaleString()} | Pending:{" "}
                {metrics.pending.toLocaleString()}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* PLOT VISUALIZATIONS SECTION */}
      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Trend Chart */}
            <Card className="border-border/50 bg-card/45 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-violet-500" />
                  Performance Trends Over Time
                </CardTitle>
                <CardDescription>
                  Daily breakdown of Leads, Connected and Converted outcomes
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[350px] w-full mt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendChartData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="rgba(255,255,255,0.05)"
                      />
                      <XAxis
                        dataKey="date"
                        tick={{
                          fill: "hsl(var(--muted-foreground))",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                      />
                      <YAxis
                        tick={{
                          fill: "hsl(var(--muted-foreground))",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgba(24, 24, 27, 0.95)",
                          border: "1px solid rgba(255, 255, 255, 0.1)",
                          borderRadius: "8px",
                          boxShadow: "0 10px 15px -3px rgba(0,0,0,0.5)",
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        height={36}
                        wrapperStyle={{ fontSize: 12 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="leads"
                        name="Leads Triggered"
                        stroke="#8b5cf6"
                        strokeWidth={2.5}
                        activeDot={{ r: 6 }}
                      />
                      <Line
                        type="monotone"
                        dataKey="connected"
                        name="Connected"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />
                      <Line
                        type="monotone"
                        dataKey="converted"
                        name="Converted"
                        stroke="#10b981"
                        strokeWidth={2.5}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Funnel Dropoff Chart */}
            <Card className="border-border/50 bg-card/45 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <BarChart className="h-4 w-4 text-blue-500" />
                  Conversion Funnel
                </CardTitle>
                <CardDescription>
                  Drop-off efficiency analysis through customer pipeline stages
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col justify-center h-[380px]">
                <div className="space-y-6 px-4">
                  {funnelData.map((stage, i) => (
                    <div key={stage.name} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="font-semibold text-primary">
                          {stage.name}
                        </span>
                        <div className="space-x-2">
                          <span className="text-muted-foreground">
                            {stage.value.toLocaleString()}
                          </span>
                          <span className="font-bold text-violet-400">
                            ({stage.percentage}%)
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-secondary/30 h-6 rounded-full overflow-hidden border border-border/20">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-600 transition-all duration-1000 flex items-center justify-end pr-3"
                          style={{ width: `${stage.percentage}%` }}
                        >
                          {stage.percentage > 10 && (
                            <span className="text-[10px] font-bold text-white">
                              {stage.percentage}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Donut Chart: Channel Share */}
            <Card className="border-border/50 bg-card/45 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold">
                  Lead Share by Channel
                </CardTitle>
                <CardDescription>
                  Visual channel breakdown for incoming prospect engagement
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center justify-center h-[350px]">
                <div className="h-[260px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={channelDistributionData}
                        cx="50%"
                        cy="50%"
                        innerRadius={65}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {channelDistributionData.map((entry, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgba(24, 24, 27, 0.95)",
                          border: "1px solid rgba(255, 255, 255, 0.1)",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend
                        verticalAlign="bottom"
                        iconType="circle"
                        wrapperStyle={{ fontSize: 11 }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Bar Chart: Channel efficiency */}
            <Card className="border-border/50 bg-card/45 backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="text-base font-bold">
                  Channel Connect & Sales Efficiency
                </CardTitle>
                <CardDescription>
                  Comparative Connect vs Conversion percentages per channel
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[320px] w-full mt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={channelEfficiencyData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        vertical={false}
                        stroke="rgba(255,255,255,0.05)"
                      />
                      <XAxis
                        dataKey="name"
                        tick={{
                          fill: "hsl(var(--muted-foreground))",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                      />
                      <YAxis
                        tick={{
                          fill: "hsl(var(--muted-foreground))",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgba(24, 24, 27, 0.95)",
                          border: "1px solid rgba(255, 255, 255, 0.1)",
                          borderRadius: "8px",
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        height={36}
                        wrapperStyle={{ fontSize: 12 }}
                      />
                      <Bar
                        dataKey="Connect Rate (%)"
                        fill="#3b82f6"
                        radius={[4, 4, 0, 0]}
                      />
                      <Bar
                        dataKey="Conversion Rate (%)"
                        fill="#10b981"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* DATA EXPLORER TABLE */}
          <Card className="border-border/50 bg-card/45 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="text-base font-bold">
                Daily Analytics Breakdown Explorer
              </CardTitle>
              <CardDescription>
                Scrollable log of daily performance values mapped by activity
                date
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto border border-border/30 rounded-lg">
                <table className="w-full text-sm text-left text-muted-foreground border-collapse">
                  <thead className="text-xs uppercase bg-muted/65 text-muted-foreground border-b border-border/30">
                    <tr>
                      <th className="px-6 py-3 font-semibold text-primary">
                        Activity Date
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary">
                        Channel
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary text-right">
                        Campaigns
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary text-right">
                        Leads
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary text-right">
                        Connected
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary text-right">
                        Converted
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary text-right">
                        Failed
                      </th>
                      <th className="px-6 py-3 font-semibold text-primary text-right">
                        Pending
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredData
                      .slice()
                      .reverse()
                      .map((row, i) => (
                        <tr
                          key={row.daily_dealership_summary_id || i}
                          className="border-b border-border/25 hover:bg-muted/15 transition-colors"
                        >
                          <td className="px-6 py-3 font-medium text-primary">
                            {row.formattedDate}
                          </td>
                          <td className="px-6 py-3 capitalize">
                            {row.channel.replace(/_/g, " ")}
                          </td>
                          <td className="px-6 py-3 text-right">
                            {row.total_campaign_triggered.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right">
                            {row.total_leads_triggered.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right">
                            {row.total_connected.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right">
                            {row.total_converted.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right">
                            {row.total_failed.toLocaleString()}
                          </td>
                          <td className="px-6 py-3 text-right">
                            {row.total_pending.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    {filteredData.length === 0 && (
                      <tr>
                        <td
                          colSpan={8}
                          className="px-6 py-8 text-center text-muted-foreground"
                        >
                          No matching records found for active filters.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

export default function DealershipSummaryPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center text-muted-foreground animate-pulse font-medium">
          Loading Dealership Summary dashboard...
        </div>
      }
    >
      <DealershipSummaryContent />
    </Suspense>
  );
}
