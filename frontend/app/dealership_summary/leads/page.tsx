"use client";

import { useState, useEffect, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import PageHeader from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronLeft, ChevronRight, Search, Download, RefreshCw, Layers } from "lucide-react";

function LeadsListContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const type = searchParams.get("type") || "leads";
  const dealershipId = searchParams.get("dealership_id") || "dave-ai-india";

  // Server-level pagination and filter states
  const [campaignType, setCampaignType] = useState<"pre-sales" | "post-sales">("pre-sales");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(50); // Options: 50, 100, 150, 1000000 (All)
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedChannel, setSelectedChannel] = useState("all");
  const [selectedDisposition, setSelectedDisposition] = useState(() => {
    if (type === "connected") return "engaged";
    if (type === "converted") return "converted";
    if (type === "failed") return "failed";
    if (type === "pending") return "queued";
    return "all";
  });
  const [startDate, setStartDate] = useState(searchParams.get("start_date") || "");
  const [endDate, setEndDate] = useState(searchParams.get("end_date") || "");

  const [data, setData] = useState<any[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1); // Reset to page 1 on new search
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Handle date filters resetting page
  const handleStartDateChange = (val: string) => {
    setStartDate(val);
    setPage(1);
  };

  const handleEndDateChange = (val: string) => {
    setEndDate(val);
    setPage(1);
  };

  // Set default disposition filter based on card type clicked
  useEffect(() => {
    if (type === "connected") {
      setSelectedDisposition("engaged"); // Default to one of the connected states
    } else if (type === "converted") {
      setSelectedDisposition("converted");
    } else if (type === "failed") {
      setSelectedDisposition("failed");
    } else if (type === "pending") {
      setSelectedDisposition("queued");
    } else {
      setSelectedDisposition("all");
    }
    setPage(1);
  }, [type]);

  const getPageTitle = () => {
    switch (type) {
      case "leads": return "Total Leads Triggered";
      case "connected": return "Connected Leads";
      case "converted": return "Converted Leads";
      case "sessions": return "Total Sessions";
      case "retriggers": return "Retrigger Details";
      case "failed": return "Failed / Pending Leads";
      default: return "Leads Details";
    }
  };

  const fetchData = async () => {
    let activeDisposition = selectedDisposition;
    if (selectedDisposition === "all") {
      if (type === "connected") activeDisposition = "engaged";
      else if (type === "converted") activeDisposition = "converted";
      else if (type === "failed") activeDisposition = "failed";
      else if (type === "pending") activeDisposition = "queued";
    }

    let url = "";
    if (type === "sessions") {
      url = `/gryd/db/objects/session?dealership_id=${dealershipId}&page_number=${page}&page_size=${pageSize}&sort_by=created&sort_reverse=true`;
      if (selectedChannel !== "all") {
        url += `&channel=${encodeURIComponent(selectedChannel)}`;
      }
      if (activeDisposition !== "all") {
        url += `&disposition=${encodeURIComponent(activeDisposition)}`;
      }
      if (debouncedSearch) {
        url += `&search_term=~${encodeURIComponent(debouncedSearch)}`;
      }
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
        const startSec = Math.floor(startMs / 1000);
        const endSec = Math.floor(endMs / 1000);
        url += `&created=${startSec},${endSec}`;
      }
    } else {
      const endpoint = campaignType === "pre-sales" ? "pre_sales_lead" : "post_sales_lead";
      url = `/gryd/db/objects/${endpoint}?dealership_id=${dealershipId}&page_number=${page}&page_size=${pageSize}&sort_by=updated&sort_reverse=true`;
      
      if (selectedChannel !== "all") {
        url += `&last_session_channel=${encodeURIComponent(selectedChannel)}`;
      }
      if (activeDisposition !== "all") {
        url += `&disposition=${encodeURIComponent(activeDisposition)}`;
      }
      if (debouncedSearch) {
        url += `&search_term=~${encodeURIComponent(debouncedSearch)}`;
      }
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
        const startSec = Math.floor(startMs / 1000);
        const endSec = Math.floor(endMs / 1000);
        const dateField = type === "leads" ? "created" : "updated";
        url += `&${dateField}=${startSec},${endSec}`;
      }
    }

    return api(url);
  };

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await fetchData();
        if (active) {
          setData(res?.data || []);
          setTotalCount(res?.total_number || res?.total || 0);
        }
      } catch (err: any) {
        if (active) {
          console.error(err);
          setError(err?.message || "Failed to load detailed record list.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    load();
    return () => {
      active = false;
    };
  }, [type, dealershipId, campaignType, page, pageSize, selectedChannel, selectedDisposition, debouncedSearch, startDate, endDate]);

  const totalPages = useMemo(() => Math.ceil(totalCount / pageSize), [totalCount, pageSize]);

  const handleExportCSV = () => {
    if (data.length === 0) return;

    const headers = ["Name", "Campaign Name", "Channel", "Status", "Contact Details", "Date"];
    const rows = data.map((row) => {
      const name = row.person_name || row.leadName || "Unknown";
      const campaign = row.campaign_name || "N/A";
      const channel = row.channel || row.last_session_channel || "N/A";
      const disposition = row.disposition || row.status || "N/A";
      const contact = row.phone_number || row.email || "N/A";
      const dateVal = row.created || row.updated;
      let dateStr = "N/A";
      if (dateVal) {
        dateStr = new Date(dateVal > 1e11 ? dateVal : dateVal * 1000).toISOString().split("T")[0];
      }

      return `"${name}","${campaign}","${channel}","${disposition}","${contact}","${dateStr}"`;
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${dealershipId}_${type}_records_${new Date().toISOString().split("T")[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex flex-col space-y-6 pb-10">
      <PageHeader
        title={getPageTitle()}
        description={`Granular breakdowns with server-side pagination for ${dealershipId}`}
        actions={
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/dealership_summary?dealership_id=${dealershipId}`)}
              className="gap-2"
            >
              <ChevronLeft className="h-4 w-4" />
              Back
            </Button>
            <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} className="gap-2">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Reload
            </Button>
            <Button variant="default" size="sm" onClick={handleExportCSV} disabled={data.length === 0} className="gap-2">
              <Download className="h-4 w-4" />
              CSV Export
            </Button>
          </div>
        }
      />

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4">
            <div>
              <CardTitle className="text-base font-bold">Leads breakdown list</CardTitle>
              <CardDescription>Configure server filters and explore entries below</CardDescription>
            </div>
            
            {/* Server Filters Panel */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mt-2">
              {/* Campaign Type Selector (only for non-sessions) */}
              {type !== "sessions" ? (
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Campaign Type</label>
                  <Select
                    value={campaignType}
                    onValueChange={(val: any) => {
                      setCampaignType(val);
                      setPage(1);
                    }}
                  >
                    <SelectTrigger className="text-xs h-9 bg-transparent">
                      <SelectValue placeholder="Campaign Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pre-sales">Pre-Sales Leads</SelectItem>
                      <SelectItem value="post-sales">Post-Sales Leads</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="space-y-1.5 invisible md:block">
                  {/* Spacer to keep layout aligned */}
                </div>
              )}

              {/* Channel Filter */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Channel</label>
                <Select
                  value={selectedChannel}
                  onValueChange={(val) => {
                    setSelectedChannel(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="text-xs h-9 bg-transparent capitalize">
                    <SelectValue placeholder="Channel" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Channels</SelectItem>
                    <SelectItem value="whatsapp_chat">WhatsApp Chat</SelectItem>
                    <SelectItem value="voice_phone">Voice Phone</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="rcs">RCS</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Status / Disposition Filter */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Status / Disposition</label>
                <Select
                  value={selectedDisposition}
                  onValueChange={(val) => {
                    setSelectedDisposition(val);
                    setPage(1);
                  }}
                >
                  <SelectTrigger className="text-xs h-9 bg-transparent capitalize">
                    <SelectValue placeholder="Disposition" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Statuses</SelectItem>
                    <SelectItem value="queued">Queued</SelectItem>
                    <SelectItem value="attempted">Attempted</SelectItem>
                    <SelectItem value="engaged">Engaged</SelectItem>
                    <SelectItem value="reached">Reached</SelectItem>
                    <SelectItem value="contacted">Contacted</SelectItem>
                    <SelectItem value="converted">Converted</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                    <SelectItem value="busy">Busy</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Start Date */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Start Date</label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => handleStartDateChange(e.target.value)}
                  className="bg-transparent text-xs h-9"
                />
              </div>

              {/* End Date */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">End Date</label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => handleEndDateChange(e.target.value)}
                  className="bg-transparent text-xs h-9"
                />
              </div>

              {/* Search input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-muted-foreground">Quick Search</label>
                <div className="relative flex items-center">
                  <Search className="absolute left-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="text"
                    placeholder="Search name, campaign..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 text-xs h-9 bg-transparent"
                  />
                </div>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Fetching records...</span>
            </div>
          ) : error ? (
            <div className="text-center py-20 text-destructive font-medium">{error}</div>
          ) : data.length === 0 ? (
            <div className="text-center py-20 text-muted-foreground font-medium">No matching records found.</div>
          ) : (
            <>
              <div className="overflow-x-auto border border-border/30 rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="px-6 font-semibold">Name</TableHead>
                      <TableHead className="px-6 font-semibold">Campaign</TableHead>
                      <TableHead className="px-6 font-semibold">Channel</TableHead>
                      <TableHead className="px-6 font-semibold">Disposition</TableHead>
                      <TableHead className="px-6 font-semibold">Contact Details</TableHead>
                      <TableHead className="px-6 font-semibold text-right">Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.map((row, i) => {
                      const name = row.person_name || row.leadName || "Unknown";
                      const campaign = row.campaign_name || "N/A";
                      const channel = row.channel || row.last_session_channel || "N/A";
                      const disposition = row.disposition || row.status || "N/A";
                      const contact = row.phone_number || row.email || "N/A";

                      const dateVal = row.created || row.updated;
                      let formattedDate = "N/A";
                      if (dateVal) {
                        const dObj = new Date(dateVal > 1e11 ? dateVal : dateVal * 1000);
                        formattedDate = dObj.toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        });
                      }

                      return (
                        <TableRow key={row.pre_sales_lead_id || row.post_sales_lead_id || row.session_id || i}>
                          <TableCell className="px-6 font-medium text-foreground">{name}</TableCell>
                          <TableCell className="px-6 capitalize">{campaign}</TableCell>
                          <TableCell className="px-6 capitalize">{channel.replace(/_/g, " ")}</TableCell>
                          <TableCell className="px-6">
                            <Badge variant="outline" className="capitalize">
                              {disposition}
                            </Badge>
                          </TableCell>
                          <TableCell className="px-6 text-xs font-mono">{contact}</TableCell>
                          <TableCell className="px-6 text-right text-muted-foreground">{formattedDate}</TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Server Pagination Panel */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6">
                {/* Page Size selector */}
                <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                  <span>Show</span>
                  <Select
                    value={String(pageSize)}
                    onValueChange={(val) => {
                      setPageSize(Number(val));
                      setPage(1);
                    }}
                  >
                    <SelectTrigger className="w-20 h-8 text-xs bg-transparent">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                      <SelectItem value="150">150</SelectItem>
                      <SelectItem value="1000000">All</SelectItem>
                    </SelectContent>
                  </Select>
                  <span>records</span>
                </div>

                <div className="text-xs text-muted-foreground">
                  Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, totalCount)} of {totalCount} entries
                </div>

                {/* Page Navigation */}
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="h-8 w-8 p-0"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <span className="text-xs font-semibold px-2">
                    Page {page} of {Math.max(1, totalPages)}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="h-8 w-8 p-0"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function LeadsListPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-muted-foreground animate-pulse">Loading leads breakdown...</div>}>
      <LeadsListContent />
    </Suspense>
  );
}
