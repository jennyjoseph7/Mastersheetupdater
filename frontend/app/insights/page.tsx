"use client";

import { useState, useMemo, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Search,
  MessageSquare,
  Mail,
  Phone,
  RefreshCw,
  Activity,
  Filter,
  ChevronDown,
  Clock,
  User,
  Hash,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
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
import {
  fetchActiveSessions,
  fetchPreSalesCampaigns,
  fetchPostSalesCampaigns,
  getDealershipId,
} from "@/utils/api";
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
  disposition: string;
  phone_number: string;
  session_live: boolean;
  campaign_type: string;
  dealership_id: string;
  campaign_model: string;
  email?: string;
  person_name?: string;
  history?: Array<{
    role: string;
    index: number;
    message: string;
    timestamp: number;
  }>;
  last_response_time?: number;
  history_updated_time?: number;
  id_salt?: string;
}

interface Campaign {
  id?: string | number;
  campaign_id?: string | number;
  name?: string;
  campaign_name?: string;
}

const formatChannel = (channel: string): string => {
  const channelMap: Record<string, string> = {
    whatsapp_chat: "WhatsApp",
    sms: "SMS",
    email: "Email",
    voice: "Voice",
    whatsapp: "WhatsApp",
  };
  return channelMap[channel.toLowerCase()] || channel;
};

const getChannelIcon = (channel: string) => {
  const normalized = channel.toLowerCase();
  if (normalized.includes("whatsapp")) {
    return <MessageSquare className="h-4 w-4" />;
  } else if (normalized.includes("email")) {
    return <Mail className="h-4 w-4" />;
  } else if (normalized.includes("voice")) {
    return <Phone className="h-4 w-4" />;
  } else if (normalized.includes("sms")) {
    return <MessageSquare className="h-4 w-4" />;
  }
  return <MessageSquare className="h-4 w-4" />;
};

const formatPhoneNumber = (phone: string): string => {
  // Remove leading + or country code if present
  let cleaned = phone.replace(/^\+/, "").replace(/^91/, "");
  // Format as Indian phone number if it starts with 9
  if (cleaned.length === 10 && cleaned.startsWith("9")) {
    return `+91 ${cleaned.slice(0, 5)} ${cleaned.slice(5)}`;
  }
  // Otherwise return with +91 prefix
  return `+91 ${cleaned}`;
};

const formatCampaignType = (type: string): string => {
  return type
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join("-");
};

const getStatusBadge = (status: string, disposition: string) => {
  // Map API status/disposition to UI status
  let displayStatus = "Lead";
  let badgeClass = "bg-amber-100 text-amber-700 border-amber-200";

  if (disposition === "engaged" || status === "interacted") {
    if (status === "interacted" && disposition === "engaged") {
      displayStatus = "Qualified";
      badgeClass = "bg-blue-100 text-blue-700 border-blue-200";
    } else {
      displayStatus = "Lead";
    }
  } else if (disposition === "converted" || status === "converted") {
    displayStatus = "Converted";
    badgeClass = "bg-purple-100 text-purple-700 border-purple-200";
  }

  return (
    <Badge className={cn("font-medium border px-3 py-1", badgeClass)}>
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
  const now = Date.now();
  const diffMs = now - timestamp * 1000;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} min${diffMins !== 1 ? "s" : ""} ago`;
  if (diffHours < 24)
    return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
  return formatTimestamp(timestamp);
};

export default function LiveStatusPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [channelFilter, setChannelFilter] = useState<string>("All Channels");
  const [statusFilter, setStatusFilter] = useState<string>("All Status");
  const [campaignTypeFilter, setCampaignTypeFilter] =
    useState<string>("All Types");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [dealershipId, setDealershipId] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // Get dealershipId only on client side to avoid hydration mismatch
  useEffect(() => {
    setIsMounted(true);
    setDealershipId(getDealershipId());
  }, []);

  // Fetch active sessions (only when mounted and dealershipId is available)
  const {
    data: sessionsData,
    mutate: refreshSessions,
    isLoading: isLoadingSessions,
    error: sessionsError,
  } = useSWR(
    isMounted && dealershipId ? ["active-sessions", dealershipId] : null,
    () => fetchActiveSessions(dealershipId!),
    {
      refreshInterval: isMounted && dealershipId ? 30000 : 0, // Refresh every 30 seconds only when mounted
      revalidateOnFocus: true,
    }
  );

  // Debug logging
  useEffect(() => {
    if (sessionsData) {
      console.log("[LiveStatusPage] Sessions data received:", {
        itemsCount: sessionsData?.items?.length ?? 0,
        total: sessionsData?.total ?? 0,
        data: sessionsData,
      });
    }
    if (sessionsError) {
      console.error("[LiveStatusPage] Sessions error:", sessionsError);
    }
  }, [sessionsData, sessionsError]);

  // Fetch campaigns to get campaign names
  const { data: preSalesCampaigns } = useSWR(
    "pre-sales-campaigns",
    () => fetchPreSalesCampaigns(1, 100).catch(() => ({ items: [], total: 0 })),
    { revalidateOnFocus: false }
  );

  const { data: postSalesCampaigns } = useSWR(
    "post-sales-campaigns",
    () => fetchPostSalesCampaigns().catch(() => ({ items: [], total: 0 })),
    { revalidateOnFocus: false }
  );

  // Create campaign name map
  const campaignMap = useMemo(() => {
    const map = new Map<string, string>();
    const campaigns: Campaign[] = [
      ...(preSalesCampaigns?.items || []),
      ...(postSalesCampaigns?.items || []),
    ];
    campaigns.forEach((campaign) => {
      const id = String(campaign.campaign_id || campaign.id);
      const name =
        campaign.name || campaign.campaign_name || "Unknown Campaign";
      map.set(id, name);
    });
    return map;
  }, [preSalesCampaigns, postSalesCampaigns]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refreshSessions();
    setTimeout(() => setIsRefreshing(false), 1000);
  };

  const sessions: SessionData[] = sessionsData?.items || [];

  const filteredSessions = sessions.filter((session) => {
    const campaignName = campaignMap.get(session.campaign_id) || "";
    const phoneFormatted = formatPhoneNumber(session.phone_number);
    const email = session.email || "";
    const personName = session.person_name || "";

    const matchesSearch =
      campaignName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      phoneFormatted.includes(searchQuery) ||
      email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      session.lead_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      personName.toLowerCase().includes(searchQuery.toLowerCase());

    const channelDisplay = formatChannel(session.channel);
    const matchesChannel =
      channelFilter === "All Channels" || channelDisplay === channelFilter;

    const statusDisplay =
      session.disposition === "engaged" || session.status === "interacted"
        ? session.disposition === "engaged" && session.status === "interacted"
          ? "Qualified"
          : "Lead"
        : session.disposition === "converted" || session.status === "converted"
        ? "Converted"
        : "Lead";
    const matchesStatus =
      statusFilter === "All Status" || statusDisplay === statusFilter;

    const campaignTypeDisplay = formatCampaignType(session.campaign_type);
    const matchesType =
      campaignTypeFilter === "All Types" ||
      campaignTypeDisplay === campaignTypeFilter;

    return matchesSearch && matchesChannel && matchesStatus && matchesType;
  });

  // Calculate stats
  const stats = useMemo(() => {
    const qualified = filteredSessions.filter(
      (s) => s.disposition === "engaged" && s.status === "interacted"
    ).length;
    const leads = filteredSessions.filter(
      (s) =>
        !(s.disposition === "engaged" && s.status === "interacted") &&
        s.disposition !== "converted"
    ).length;
    const converted = filteredSessions.filter(
      (s) => s.disposition === "converted" || s.status === "converted"
    ).length;

    return {
      total: filteredSessions.length,
      qualified,
      leads,
      converted,
    };
  }, [filteredSessions]);

  // Show loading state during initial mount to avoid hydration mismatch
  if (!isMounted) {
    return (
      <div className="flex min-h-screen flex-col w-full bg-background">
        {/* Header Section */}
        <div className="border-b bg-background/95 backdrop-blur sticky top-0 z-10">
          <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Live Status</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Real-time campaign activity and performance monitoring
              </p>
            </div>
            <Button variant="outline" size="sm" disabled className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          </div>
        </div>

        <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 py-6 w-full"></div>
      </div>
    );
  }

  if (!dealershipId) {
    return (
      <div className="flex min-h-screen flex-col w-full bg-background items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              Please login to view live status
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col w-full bg-background">
      {/* Header Section */}
      <div className="border-b bg-background/95 backdrop-blur sticky top-0 z-10">
        <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Live Status</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Real-time campaign activity and performance monitoring
            </p>
          </div>
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
                (isRefreshing || isLoadingSessions) && "animate-spin"
              )}
            />
            Refresh
          </Button>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 py-6 w-full">
        {/* Active User Sessions Section */}
        <Card className="shadow-lg border-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl font-semibold">
                  Active User Sessions
                </CardTitle>
                <CardDescription className="mt-1">
                  Real-time view of users currently engaged in campaigns
                </CardDescription>
              </div>
            </div>

            {/* Search and Filters */}
            <div className="flex flex-col gap-4 mt-6">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by campaign name, phone, email, name, or lead ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-10"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2">
                      <Filter className="h-4 w-4" />
                      {channelFilter}
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Channel</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setChannelFilter("All Channels")}
                    >
                      All Channels
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setChannelFilter("WhatsApp")}
                    >
                      WhatsApp
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setChannelFilter("Email")}>
                      Email
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setChannelFilter("SMS")}>
                      SMS
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setChannelFilter("Voice")}>
                      Voice
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2">
                      {statusFilter}
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Status</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setStatusFilter("All Status")}
                    >
                      All Status
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("Lead")}>
                      Lead
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setStatusFilter("Qualified")}
                    >
                      Qualified
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setStatusFilter("Converted")}
                    >
                      Converted
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="gap-2">
                      {campaignTypeFilter}
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Campaign Type</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setCampaignTypeFilter("All Types")}
                    >
                      All Types
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setCampaignTypeFilter("Pre-Sales")}
                    >
                      Pre-Sales
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setCampaignTypeFilter("Post-Sales")}
                    >
                      Post-Sales
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {isLoadingSessions ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : sessionsError ? (
              <div className="text-center py-8">
                <p className="text-destructive">
                  Error loading sessions: {sessionsError.message}
                </p>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">
                  {sessions.length === 0
                    ? "No active sessions found"
                    : "No sessions match your filters"}
                </p>
              </div>
            ) : (
              <div className="relative w-full overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Campaign</TableHead>
                      <TableHead>Channel</TableHead>
                      {/* <TableHead>Lead ID</TableHead> */}
                      <TableHead>Name</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Campaign Type</TableHead>
                      <TableHead>Last Activity</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSessions.map((session) => (
                      <TableRow
                        key={session.session_id}
                        className="hover:bg-muted/50 transition-colors"
                      >
                        <TableCell className="font-medium">
                          {campaignMap.get(session.campaign_id) ||
                            "Unknown Campaign"}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getChannelIcon(session.channel)}
                            <span>{formatChannel(session.channel)}</span>
                          </div>
                        </TableCell>
                        {/* <TableCell>
                          <div className="flex items-center gap-1">
                            <Hash className="h-3 w-3 text-muted-foreground" />
                            <span className="font-mono text-xs">
                              {session.lead_id}
                            </span>
                          </div>
                        </TableCell> */}
                        <TableCell>{session.person_name || "-"}</TableCell>
                        <TableCell>
                          {formatPhoneNumber(session.phone_number)}
                        </TableCell>
                        <TableCell>{session.email || "-"}</TableCell>
                        <TableCell>
                          {getStatusBadge(session.status, session.disposition)}
                        </TableCell>
                        <TableCell>
                          {formatCampaignType(session.campaign_type)}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            {getTimeAgo(session.updated || session.created)}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
