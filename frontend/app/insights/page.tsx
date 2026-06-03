"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Search,
  MessageSquare,
  Mail,
  Phone,
  RefreshCw,
  Filter,
  ChevronDown,
  Clock,
  Download,
  ChevronLeft,
  ChevronRight,
  ArrowUp,
  ArrowDown,
  Calendar,
  PlayCircle,
  X,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { fetchActiveSessions, getDealershipId } from "@/utils/api";
import useSWR from "swr";
import { Skeleton } from "@/components/ui/skeleton";

interface SessionData {
  status: string;
  channel: string;
  created: number;
  lead_id: string;
  updated: number;
  user_id: string;
  lead_model: string;
  session_id: string;
  start_time: number;
  campaign_id: string;
  disposition?: string;
  phone_number: string;
  session_live: boolean;
  campaign_type: string;
  dealership_id: string;
  campaign_model: string;
  call_recording?: string;
  duration?: number;
  email?: string;
  person_name?: string;
  id_salt?: string;
  campaign_name?: string;
  campaign_objective_name?: string;
}

// --- Utility Functions ---
const formatChannel = (channel: string): string => {
  const channelMap: Record<string, string> = {
    whatsapp_chat: "WhatsApp",
    sms: "SMS",
    email: "Email",
    voice: "Voice",
    voice_phone: "Voice",
    whatsapp: "WhatsApp",
  };
  return channelMap[channel.toLowerCase()] || channel;
};

const getChannelIcon = (channel: string) => {
  const normalized = channel.toLowerCase();
  if (normalized.includes("whatsapp"))
    return <MessageSquare className="h-4 w-4" />;
  if (normalized.includes("email")) return <Mail className="h-4 w-4" />;
  if (normalized.includes("voice")) return <Phone className="h-4 w-4" />;
  if (normalized.includes("sms")) return <MessageSquare className="h-4 w-4" />;
  return <MessageSquare className="h-4 w-4" />;
};

const formatPhoneNumber = (phone: string): string => {
  let cleaned = phone.replace(/^\+/, "").replace(/^91/, "");
  if (cleaned.length === 10)
    return `+91 ${cleaned.slice(0, 5)} ${cleaned.slice(5)}`;
  return `+91 ${cleaned}`;
};

const formatCampaignType = (type: string): string => {
  return type
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join("-");
};

const getStatusBadge = (status: string) => {
  // Fallback to "Unknown" if status is missing, null, or undefined
  if (!status) {
    return (
      <Badge className="font-medium border px-3 py-1 bg-gray-100 text-gray-700 border-gray-200">
        Unknown
      </Badge>
    );
  }

  // Capitalize the first letter of the raw status string exactly as it comes from the DB
  const displayStatus = status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <Badge className="font-medium border px-3 py-1 whitespace-nowrap bg-amber-100 text-amber-700 border-amber-200">
      {displayStatus}
    </Badge>
  );
};

const formatTimestamp = (timestamp: number) => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
};

const getTimeAgo = (timestamp: number): string => {
  const diffMs = Date.now() - timestamp * 1000;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";

  if (diffMins < 60) return `${diffMins} min${diffMins !== 1 ? "s" : ""} ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} hr${diffHours !== 1 ? "s" : ""} ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;

  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12)
    return `${diffMonths} month${diffMonths !== 1 ? "s" : ""} ago`;

  const diffYears = Math.floor(diffDays / 365);
  return `${diffYears} year${diffYears !== 1 ? "s" : ""} ago`;
};

export default function LiveStatusPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [dealershipId, setDealershipId] = useState<string | null>(null);

  // Client-Side Filters (Search Only)
  const [searchQuery, setSearchQuery] = useState("");

  // Server-Side Filters (Dates and Dropdowns)
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [channelFilter, setChannelFilter] = useState<string>("All Channels");
  const [statusFilter, setStatusFilter] = useState<string>("All Status");
  const [campaignTypeFilter, setCampaignTypeFilter] =
    useState<string>("All Types");

  // Pagination & Sorting (Server-Side)
  const [p, setP] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState("created");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const [isLoaded, setIsLoaded] = useState(false);

  // Load filters from localStorage on mount
  useEffect(() => {
    const savedSearch = localStorage.getItem("live_searchQuery");
    const savedStart = localStorage.getItem("live_startDate");
    const savedEnd = localStorage.getItem("live_endDate");
    const savedChannel = localStorage.getItem("live_channelFilter");
    const savedStatus = localStorage.getItem("live_statusFilter");
    const savedType = localStorage.getItem("live_campaignTypeFilter");
    const savedPage = localStorage.getItem("live_page");
    const savedPageSize = localStorage.getItem("live_pageSize");

    if (savedSearch) setSearchQuery(savedSearch);
    if (savedStart) setStartDate(savedStart);
    if (savedEnd) setEndDate(savedEnd);
    if (savedChannel) setChannelFilter(savedChannel);
    if (savedStatus) setStatusFilter(savedStatus);
    if (savedType) setCampaignTypeFilter(savedType);
    if (savedPage) setP(parseInt(savedPage));
    if (savedPageSize) setPageSize(parseInt(savedPageSize));

    setIsLoaded(true);
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    localStorage.setItem("live_searchQuery", searchQuery);
    localStorage.setItem("live_startDate", startDate);
    localStorage.setItem("live_endDate", endDate);
    localStorage.setItem("live_channelFilter", channelFilter);
    localStorage.setItem("live_statusFilter", statusFilter);
    localStorage.setItem("live_campaignTypeFilter", campaignTypeFilter);
    localStorage.setItem("live_page", p.toString());
    localStorage.setItem("live_pageSize", pageSize.toString());
  }, [
    searchQuery,
    startDate,
    endDate,
    channelFilter,
    statusFilter,
    campaignTypeFilter,
    p,
    pageSize,
    isLoaded,
  ]);

  const [isRefreshing, setIsRefreshing] = useState(false);

  // Audio Player State
  const [activeRecording, setActiveRecording] = useState<{
    url: string;
    name: string;
  } | null>(null);

  // Mount logic
  useEffect(() => {
    setIsMounted(true);
    setDealershipId(getDealershipId());
  }, []);

  // Handle server-side filter changes (resets pagination)
  const handleServerFilterChange = (
    setter: React.Dispatch<React.SetStateAction<string>>,
    value: string,
  ) => {
    setter(value);
    setP(1);
  };

  const handleDateChange = (type: "start" | "end", value: string) => {
    if (type === "start") setStartDate(value);
    if (type === "end") setEndDate(value);
    setP(1); // Reset to page 1 whenever date filters change
  };

  const clearDates = () => {
    setStartDate("");
    setEndDate("");
    setP(1);
  };

  const handlePageSizeChange = (size: number) => {
    setPageSize(size);
    setP(1);
  };

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("desc");
    }
    setP(1);
  };

  // Construct Query Params for SWR
  const queryParams = useMemo(() => {
    return {
      p,
      page_size: pageSize,
      channel: channelFilter !== "All Channels" ? channelFilter : undefined,
      status: statusFilter !== "All Status" ? statusFilter : undefined,
      campaign_type:
        campaignTypeFilter !== "All Types"
          ? campaignTypeFilter.toLowerCase()
          : undefined,
      sort_by: sortBy,
      sort_order: sortOrder,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    };
  }, [
    p,
    pageSize,
    channelFilter,
    statusFilter,
    campaignTypeFilter,
    sortBy,
    sortOrder,
    startDate,
    endDate,
  ]);

  // Main Session API Call
  const {
    data: sessionsData,
    mutate: refreshSessions,
    isLoading: isLoadingSessions,
    error: sessionsError,
  } = useSWR(
    isMounted && dealershipId
      ? ["active-sessions", dealershipId, JSON.stringify(queryParams)]
      : null,
    () => fetchActiveSessions(dealershipId!, queryParams),
    {
      refreshInterval: isMounted && dealershipId ? 30000 : 0,
      revalidateOnFocus: true,
    },
  );

  // Server Data
  const rawSessions: SessionData[] = sessionsData?.data || [];
  const serverTotalItems = sessionsData?.total_number || 0;
  const totalPages = Math.ceil(serverTotalItems / pageSize);

  // Client-Side Filtering Logic (Only for Search input now)
  const filteredSessions = useMemo(() => {
    return rawSessions.filter((session) => {
      const searchLower = searchQuery.toLowerCase();
      const campaignName = (session.campaign_name || "").toLowerCase();
      const objectiveName = (
        session.campaign_objective_name || ""
      ).toLowerCase();
      const personName = (session.person_name || "").toLowerCase();
      const email = (session.email || "").toLowerCase();
      const phoneFormatted = formatPhoneNumber(session.phone_number);

      return (
        !searchQuery ||
        campaignName.includes(searchLower) ||
        objectiveName.includes(searchLower) ||
        personName.includes(searchLower) ||
        email.includes(searchLower) ||
        phoneFormatted.includes(searchQuery)
      );
    });
  }, [rawSessions, searchQuery]);

  // Manual Refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refreshSessions();
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  // CSV Export Logic
  const handleExportCSV = () => {
    if (!filteredSessions || filteredSessions.length === 0) return;

    const headers = [
      "Campaign Name",
      "Objective",
      "Channel",
      "Name",
      "Phone",
      "Email",
      "Status",
      "Campaign Type",
      "Created Date",
      "Recording Link",
    ];
    const csvRows = [headers.join(",")];

    filteredSessions.forEach((session) => {
      const row = [
        `"${session.campaign_name || "Unknown Campaign"}"`,
        `"${session.campaign_objective_name || "-"}"`,
        `"${formatChannel(session.channel)}"`,
        `"${session.person_name || "-"}"`,
        `"${session.phone_number}"`,
        `"${session.email || "-"}"`,
        `"${session.status}"`,
        `"${formatCampaignType(session.campaign_type)}"`,
        `"${formatTimestamp(session.created)}"`,
        `"${session.call_recording || "No Recording"}"`,
      ];
      csvRows.push(row.join(","));
    });

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `live_sessions_export_${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Render Sortable Header Helper
  const SortableHeader = ({
    title,
    column,
  }: {
    title: string;
    column: string;
  }) => (
    <TableHead
      onClick={() => handleSort(column)}
      className="cursor-pointer hover:bg-muted/50 select-none"
    >
      <div className="flex items-center gap-1">
        {title}
        {sortBy === column &&
          (sortOrder === "asc" ? (
            <ArrowUp className="h-3 w-3" />
          ) : (
            <ArrowDown className="h-3 w-3" />
          ))}
      </div>
    </TableHead>
  );

  if (!isMounted) return <div className="min-h-screen w-full bg-background" />;
  if (!dealershipId)
    return (
      <div className="flex min-h-screen w-full bg-background items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              Please login to view live status
            </p>
          </CardContent>
        </Card>
      </div>
    );

  return (
    <div className="flex min-h-screen flex-col w-full bg-background">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur sticky top-0 z-10">
        <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Live Status</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Real-time campaign activity and performance monitoring
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCSV}
              className="gap-2"
            >
              <Download className="h-4 w-4" /> Export CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing || isLoadingSessions}
              className="gap-2"
            >
              <RefreshCw
                className={cn(
                  "h-4 w-4",
                  (isRefreshing || isLoadingSessions) && "animate-spin",
                )}
              />{" "}
              Refresh
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 py-6 w-full relative">
        <Card className="shadow-lg border-2">
          <CardHeader>
            <CardTitle className="text-xl font-semibold">
              Active User Sessions
            </CardTitle>

            {/* Filters Row */}
            <div className="flex flex-col xl:flex-row gap-4 mt-6">
              {/* Client-Side Search Box */}
              <div className="relative flex-1 min-w-[250px]">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search table data..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-10"
                />
              </div>

              {/* Filters */}
              <div className="flex gap-2 flex-wrap items-center">
                {/* Server-Side Date Filters */}
                <div className="flex items-center gap-2 border rounded-md px-3 bg-background">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => handleDateChange("start", e.target.value)}
                    className="h-8 border-0 bg-transparent w-[130px] p-0 focus-visible:ring-0 shadow-none text-sm"
                  />
                  <span className="text-muted-foreground text-sm">to</span>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => handleDateChange("end", e.target.value)}
                    className="h-8 border-0 bg-transparent w-[130px] p-0 focus-visible:ring-0 shadow-none text-sm"
                  />
                  {(startDate || endDate) && (
                    <Button
                      variant="ghost"
                      className="h-6 w-6 p-0 ml-1 rounded-full text-muted-foreground hover:text-foreground"
                      onClick={clearDates}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                {/* Server-Side Channel Filter */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2 h-10">
                      <Filter className="h-4 w-4" /> {channelFilter}{" "}
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(
                          setChannelFilter,
                          "All Channels",
                        )
                      }
                    >
                      All Channels
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(
                          setChannelFilter,
                          "whatsapp_chat",
                        )
                      }
                    >
                      WhatsApp
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(setChannelFilter, "email")
                      }
                    >
                      Email
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(setChannelFilter, "SMS")
                      }
                    >
                      SMS
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(
                          setChannelFilter,
                          "voice_phone",
                        )
                      }
                    >
                      Voice
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Server-Side Status Filter */}
                {/* <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2 h-10">
                      {statusFilter} <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem onClick={() => handleServerFilterChange(setStatusFilter, "All Status")}>All Status</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleServerFilterChange(setStatusFilter, "Lead")}>Lead</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleServerFilterChange(setStatusFilter, "Qualified")}>Qualified</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleServerFilterChange(setStatusFilter, "Converted")}>Converted</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleServerFilterChange(setStatusFilter, "Attempted")}>Attempted</DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu> */}

                {/* Server-Side Campaign Type Filter */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2 h-10">
                      {campaignTypeFilter} <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(
                          setCampaignTypeFilter,
                          "All Types",
                        )
                      }
                    >
                      All Types
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(
                          setCampaignTypeFilter,
                          "Pre-Sales",
                        )
                      }
                    >
                      Pre-Sales
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() =>
                        handleServerFilterChange(
                          setCampaignTypeFilter,
                          "Post-Sales",
                        )
                      }
                    >
                      Post-Sales
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardHeader>

          <CardContent className="flex flex-col min-h-[500px]">
            {isLoadingSessions ? (
              <div className="space-y-4 flex-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : sessionsError ? (
              <div className="text-center py-8 flex-1 flex items-center justify-center">
                <p className="text-destructive">
                  Error loading sessions: {sessionsError.message}
                </p>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="text-center py-8 flex-1 flex items-center justify-center">
                <p className="text-muted-foreground">
                  No sessions match your search/date criteria in the current
                  page.
                </p>
              </div>
            ) : (
              <>
                {/* Table Data */}
                <div className="relative w-full overflow-x-auto border rounded-t-md pb-4">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <SortableHeader
                          title="Campaign"
                          column="campaign_name"
                        />
                        <SortableHeader
                          title="Objective"
                          column="campaign_objective_name"
                        />
                        <SortableHeader title="Channel" column="channel" />
                        <SortableHeader title="Name" column="person_name" />
                        <SortableHeader title="Phone" column="phone_number" />
                        <SortableHeader title="Status" column="status" />
                        <SortableHeader title="Type" column="campaign_type" />
                        <TableHead>Recording</TableHead>
                        <SortableHeader title="Created" column="created" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredSessions.map((session) => (
                        <TableRow
                          key={session.session_id}
                          className="hover:bg-muted/50 transition-colors"
                        >
                          <TableCell
                            className="font-medium max-w-[150px] truncate"
                            title={session.campaign_name}
                          >
                            {session.campaign_name || "Unknown Campaign"}
                          </TableCell>
                          <TableCell
                            className="max-w-[150px] truncate"
                            title={session.campaign_objective_name}
                          >
                            {session.campaign_objective_name || "-"}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              {getChannelIcon(session.channel)}
                              <span>{formatChannel(session.channel)}</span>
                            </div>
                          </TableCell>
                          <TableCell>{session.person_name || "-"}</TableCell>
                          <TableCell>
                            {formatPhoneNumber(session.phone_number)}
                          </TableCell>
                          <TableCell>
                             {getStatusBadge(session.status)}
                          </TableCell>
                          <TableCell>
                            {formatCampaignType(session.campaign_type)}
                          </TableCell>
                          <TableCell>
                            {session.call_recording ? (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 gap-1.5 px-2.5 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:text-blue-800 border-blue-200"
                                onClick={() =>
                                  setActiveRecording({
                                    url: session.call_recording!,
                                    name:
                                      session.person_name ||
                                      formatPhoneNumber(session.phone_number),
                                  })
                                }
                              >
                                <PlayCircle className="h-3.5 w-3.5" />
                                <span className="text-xs font-medium">
                                  Play
                                </span>
                              </Button>
                            ) : (
                              <span className="text-muted-foreground text-xs italic pl-2">
                                -
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div
                              className="flex items-center gap-1 text-sm text-muted-foreground whitespace-nowrap cursor-help"
                              title={formatTimestamp(session.created)}
                            >
                              <Clock className="h-3 w-3" />
                              {getTimeAgo(session.created)}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Server-Side Pagination Footer */}
                <div className="flex items-center justify-between px-4 py-4 border-x border-b rounded-b-md bg-muted/20 mt-4">
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>
                      {searchQuery
                        ? `Showing ${filteredSessions.length} filtered items (Server total: ${serverTotalItems})`
                        : `Total ${serverTotalItems} items`}
                    </span>
                    <div className="flex items-center gap-2">
                      <span>Rows per page:</span>
                      <select
                        className="bg-transparent border rounded p-1 cursor-pointer"
                        value={pageSize}
                        onChange={(e) =>
                          handlePageSizeChange(Number(e.target.value))
                        }
                      >
                        <option value={10}>10</option>
                        <option value={20}>20</option>
                        <option value={50}>50</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">
                      Page {p} of {Math.max(1, totalPages)}
                    </span>
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => setP((prev) => Math.max(1, prev - 1))}
                        disabled={p === 1 || isLoadingSessions}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          setP((prev) => Math.min(totalPages, prev + 1))
                        }
                        disabled={
                          p === totalPages ||
                          totalPages === 0 ||
                          isLoadingSessions
                        }
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Floating Audio Player */}
        {activeRecording && (
          <div className="fixed bottom-6 right-6 z-50 bg-card border shadow-xl rounded-xl p-4 w-[350px] animate-in slide-in-from-bottom-5">
            <div className="flex items-center justify-between mb-3">
              <div className="font-semibold text-sm truncate pr-4 text-primary">
                Playing: {activeRecording.name}
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 rounded-full hover:bg-muted"
                onClick={() => setActiveRecording(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <audio
              controls
              autoPlay
              src={activeRecording.url}
              className="w-full h-10 outline-none"
            >
              Your browser does not support the audio element.
            </audio>
          </div>
        )}
      </div>
    </div>
  );
}
