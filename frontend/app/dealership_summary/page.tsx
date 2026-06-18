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
import { Input } from "@/components/ui/input";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
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
  "var(--primary)",
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

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("dealership_id");
      if (saved) {
        setDealershipId(saved);
      }
    }
  }, []);

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

      let url = `/gryd/db/objects/daily_dealership_summary?sort_by=activity_date&sort_reverse=true&dealership_id=${dealershipId}&page_size=1000`;

      if (startDate && endDate) {
        const parseDateToUtcMs = (dateStr: string, isEnd: boolean) => {
          const [year, month, day] = dateStr.split("-").map(Number);
          if (isEnd) {
            return Date.UTC(year, month - 1, day, 23, 59, 59, 999);
          } else {
            return Date.UTC(year, month - 1, day, 0, 0, 0, 0);
          }
        };

        const startMs = parseDateToUtcMs(startDate, false);
        const endMs = parseDateToUtcMs(endDate, true);

        url += `&activity_date=${startMs},${endMs}`;
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

        let dateObj = new Date();
        if (!isNaN(ms)) {
          try {
            dateObj = new Date(ms > 1e11 ? ms : ms * 1000);
            if (isNaN(dateObj.getTime())) {
              dateObj = new Date();
            }
          } catch {
            dateObj = new Date();
          }
        }

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
      // Date filter
      if (startDate && item.isodate < startDate) {
        return false;
      }
      if (endDate && item.isodate > endDate) {
        return false;
      }
      return true;
    });
  }, [parsedData, selectedChannels, searchQuery, startDate, endDate]);

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
      <PageHeader
        title="Dealership Performance Summary"
        description={`Real-time metric plots and channel analysis for ${dealershipId}`}
        actions={
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 border rounded-lg text-xs font-semibold text-muted-foreground h-9">
              <span>Dealership:</span>
              <span className="text-foreground font-bold">{dealershipId}</span>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={fetchData}
              disabled={loading}
              className="gap-2"
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
              Sync
            </Button>

            <Button
              variant="default"
              size="sm"
              onClick={handleExportCSV}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              CSV Export
            </Button>
          </div>
        }
      />

      {/* FILTER PANEL */}
      <Card>
        <CardHeader className="flex flex-row items-center space-x-2 pb-2">
          <Filter className="h-4 w-4 text-primary" />
          <CardTitle className="text-sm font-medium">
            Dashboard Filters
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
                    className="cursor-pointer capitalize text-xs transition-all"
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
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-transparent text-xs"
              />
              <span className="text-muted-foreground text-xs">to</span>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-transparent text-xs"
              />
            </div>
          </div>

          {/* Quick Search */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-muted-foreground">
              Search Channels
            </label>
            <div className="relative flex items-center">
              <Search className="absolute left-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search channel..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 text-xs bg-transparent"
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
          <Card>
            <div className="absolute top-0 left-0 w-full h-[3px] bg-blue-500" />
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Campaigns</CardTitle>
              <Megaphone className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.campaigns.toLocaleString()}
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">
                Total campaign runs
              </p>
            </CardContent>
          </Card>

          <Card>
            <div className="absolute top-0 left-0 w-full h-[3px] bg-violet-500" />
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                Leads Triggered
              </CardTitle>
              <Users className="h-4 w-4 text-violet-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.leads.toLocaleString()}
              </div>
              <p className="text-[10px] text-muted-foreground mt-1">
                Total customer pipelines
              </p>
            </CardContent>
          </Card>

          <Card>
            <div className="absolute top-0 left-0 w-full h-[3px] bg-sky-500" />
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Connected</CardTitle>
              <PhoneCall className="h-4 w-4 text-sky-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.connected.toLocaleString()}
              </div>
              <p className="text-[10px] text-emerald-500 dark:text-emerald-400 font-semibold mt-1">
                {metrics.connectRate.toFixed(1)}% Connect Rate
              </p>
            </CardContent>
          </Card>

          <Card>
            <div className="absolute top-0 left-0 w-full h-[3px] bg-emerald-500" />
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Converted</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics.converted.toLocaleString()}
              </div>
              <p className="text-[10px] text-emerald-500 dark:text-emerald-400 font-semibold mt-1">
                {metrics.overallConversionRate.toFixed(1)}% Sales Rate
              </p>
            </CardContent>
          </Card>

          <Card>
            <div className="absolute top-0 left-0 w-full h-[3px] bg-rose-500" />
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                Failed / Pending
              </CardTitle>
              <AlertTriangle className="h-4 w-4 text-rose-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
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
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
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
                        stroke="var(--border)"
                      />
                      <XAxis
                        dataKey="date"
                        tick={{
                          fill: "var(--muted-foreground)",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={{ stroke: "var(--border)" }}
                      />
                      <YAxis
                        tick={{
                          fill: "var(--muted-foreground)",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={{ stroke: "var(--border)" }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--card)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius)",
                          color: "var(--foreground)",
                        }}
                        itemStyle={{
                          color: "var(--foreground)",
                        }}
                        labelStyle={{
                          color: "var(--muted-foreground)",
                          fontWeight: "bold",
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        height={36}
                        wrapperStyle={{
                          fontSize: 12,
                          color: "var(--foreground)",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="leads"
                        name="Leads Triggered"
                        stroke="var(--primary)"
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
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <BarChart className="h-4 w-4 text-primary" />
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
                          <span className="font-bold text-primary">
                            ({stage.percentage}%)
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-secondary/30 h-6 rounded-full overflow-hidden border border-border/20">
                        <div
                          className="h-full rounded-full bg-primary transition-all duration-1000 flex items-center justify-end pr-3"
                          style={{ width: `${stage.percentage}%` }}
                        >
                          {stage.percentage > 10 && (
                            <span className="text-[10px] font-bold text-primary-foreground">
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
            <Card>
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
                          backgroundColor: "var(--card)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius)",
                          color: "var(--foreground)",
                        }}
                        itemStyle={{
                          color: "var(--foreground)",
                        }}
                        labelStyle={{
                          color: "var(--muted-foreground)",
                          fontWeight: "bold",
                        }}
                      />
                      <Legend
                        verticalAlign="bottom"
                        iconType="circle"
                        wrapperStyle={{
                          fontSize: 11,
                          color: "var(--foreground)",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Bar Chart: Channel efficiency */}
            <Card>
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
                        stroke="var(--border)"
                      />
                      <XAxis
                        dataKey="name"
                        tick={{
                          fill: "var(--muted-foreground)",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={{ stroke: "var(--border)" }}
                      />
                      <YAxis
                        tick={{
                          fill: "var(--muted-foreground)",
                          fontSize: 10,
                        }}
                        axisLine={{ stroke: "var(--border)" }}
                        tickLine={{ stroke: "var(--border)" }}
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--card)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--radius)",
                          color: "var(--foreground)",
                        }}
                        itemStyle={{
                          color: "var(--foreground)",
                        }}
                        labelStyle={{
                          color: "var(--muted-foreground)",
                          fontWeight: "bold",
                        }}
                      />
                      <Legend
                        verticalAlign="top"
                        height={36}
                        wrapperStyle={{
                          fontSize: 12,
                          color: "var(--foreground)",
                        }}
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
          <Card>
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
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="px-6 font-semibold">
                        Activity Date
                      </TableHead>
                      <TableHead className="px-6 font-semibold">
                        Channel
                      </TableHead>
                      <TableHead className="px-6 font-semibold text-right">
                        Campaigns
                      </TableHead>
                      <TableHead className="px-6 font-semibold text-right">
                        Leads
                      </TableHead>
                      <TableHead className="px-6 font-semibold text-right">
                        Connected
                      </TableHead>
                      <TableHead className="px-6 font-semibold text-right">
                        Converted
                      </TableHead>
                      <TableHead className="px-6 font-semibold text-right">
                        Failed
                      </TableHead>
                      <TableHead className="px-6 font-semibold text-right">
                        Pending
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredData
                      .slice()
                      .reverse()
                      .map((row, i) => (
                        <TableRow key={row.daily_dealership_summary_id || i}>
                          <TableCell className="px-6 font-medium text-foreground">
                            {row.formattedDate}
                          </TableCell>
                          <TableCell className="px-6 capitalize">
                            {row.channel.replace(/_/g, " ")}
                          </TableCell>
                          <TableCell className="px-6 text-right">
                            {row.total_campaign_triggered.toLocaleString()}
                          </TableCell>
                          <TableCell className="px-6 text-right">
                            {row.total_leads_triggered.toLocaleString()}
                          </TableCell>
                          <TableCell className="px-6 text-right">
                            {row.total_connected.toLocaleString()}
                          </TableCell>
                          <TableCell className="px-6 text-right">
                            {row.total_converted.toLocaleString()}
                          </TableCell>
                          <TableCell className="px-6 text-right">
                            {row.total_failed.toLocaleString()}
                          </TableCell>
                          <TableCell className="px-6 text-right">
                            {row.total_pending.toLocaleString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    {filteredData.length === 0 && (
                      <TableRow>
                        <TableCell
                          colSpan={8}
                          className="px-6 py-8 text-center text-muted-foreground"
                        >
                          No matching records found for active filters.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
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
