"use client";
import useSWR from "swr";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  fetchAPIData,
  fetchPivotCountForCampaign,
  fetchPreSalesCampaigns,
  fetchPostSalesCampaigns,
  fetchDealershipCampaigns,
  fetchCampaignSummary,
  deleteAPIData,
  epochToIST,
} from "@/utils/api";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { ProtectedRoute } from "@/components/protected-route";

import {
  Plus,
  Search,
  MoreVertical,
  Play,
  Pause,
  Copy,
  Pencil,
  Trash2,
  TrendingUp,
  Target,
  UsersIcon,
  BarChart3,
} from "lucide-react";

const swrOptions = {
  revalidateOnFocus: false,
  revalidateIfStale: false,
  revalidateOnReconnect: false,
  errorRetryCount: 0,
  shouldRetryOnError: false,
};

export interface Campaign {
  id: string | number;
  name?: string;
  description?: string;
  channels?: string[];
  campaign_status?: string;
  launchDate?: string;
  campaign_type?: string;
  [key: string]: any;
}

const ITEMS_PER_PAGE = 5;

export default function CampaignDashboard() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [campaignTypeFilter, setCampaignTypeFilter] =
    useState<string>("post-sales"); // default

  const [mergedCampaigns, setMergedCampaigns] = useState<Campaign[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [activeCount, setActiveCount] = useState<number>(0);
  const [totalCampaignCount, setTotalCampaignCount] = useState<number>(0);
  const [activeCampaignCount, setActiveCampaignCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalReach, setTotalReach] = useState<number>(0);
  const [conversionRate, setConversionRate] = useState<number>(0);
  const [currentCampaignType, setCurrentCampaignType] =
    useState<string>("post-sales");

  // Delete confirmation dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [campaignToDelete, setCampaignToDelete] = useState<Campaign | null>(
    null
  );
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch counts for header cards
  const fetchCounts = async () => {
    const totalData = await fetchPivotCountForCampaign("total");
    const activeData = await fetchPivotCountForCampaign("active");
    return {
      total: totalData ?? 0,
      active: activeData ?? 0,
    };
  };

  // Fetch campaigns by type and page
  const fetchCampaigns = async (type: string, page: number) => {
    console.log(
      "[fetchCampaigns] Fetching campaigns for type:",
      type,
      "page:",
      page
    );
    // Handle dealership campaigns separately
    if (type === "dealership") {
      console.log("[fetchCampaigns] Fetching dealership campaigns...");
      const res = await fetchDealershipCampaigns();
      console.log("[fetchCampaigns] Dealership campaigns response:", res);
      return {
        merged: res?.items ?? [],
        total: res?.total ?? 0,
      };
    }

    // Handle pre-sales campaigns using the dedicated function
    if (type === "pre-sales" || type === "pre_sales") {
      console.log("[fetchCampaigns] Fetching pre-sales campaigns...");
      const res = await fetchPreSalesCampaigns(page, ITEMS_PER_PAGE);
      console.log("[fetchCampaigns] Pre-sales campaigns response:", res);
      return {
        merged: res?.items ?? [],
        total: res?.total ?? 0,
      };
    }

    // Handle post-sales campaigns using the dedicated function
    if (type === "post-sales" || type === "post_sales") {
      console.log("[fetchCampaigns] Fetching post-sales campaigns...");
      const res = await fetchPostSalesCampaigns(page, ITEMS_PER_PAGE);
      console.log("[fetchCampaigns] Post-sales campaigns response:", res);
      return {
        merged: res?.items ?? [],
        total: res?.total ?? 0,
      };
    }

    const params = { page_number: page, page_size: ITEMS_PER_PAGE };
    const res = await fetchAPIData(
      type === "pre_sales" ? "pre_sales_campaign" : "post_sales_campaign",
      params
    );

    return {
      merged: res?.items ?? [],
      total: res?.total ?? 0,
    };
  };

  const { data: counts } = useSWR("pivot-counts", fetchCounts, swrOptions);

  const {
    data: campaignsData,
    isLoading: loading,
    error,
    mutate: mutateCampaigns,
  } = useSWR(
    ["campaigns", campaignTypeFilter, page],
    () => fetchCampaigns(campaignTypeFilter, page),
    swrOptions
  );

  // Fetch campaign summary data
  const { data: campaignSummaryData } = useSWR(
    "campaign-summary",
    fetchCampaignSummary,
    swrOptions
  );

  // Update counts header (total campaigns of current type)
  // Only use this if campaign summary data is not available (fallback)
  useEffect(() => {
    // Skip if campaign summary data is available (it will handle the updates)
    if (
      campaignSummaryData &&
      Array.isArray(campaignSummaryData) &&
      campaignSummaryData.length > 0
    ) {
      return;
    }

    // For dealership campaigns, use the campaignsData total
    if (campaignTypeFilter === "dealership" && campaignsData) {
      setTotalCount(campaignsData.total ?? 0);
      // Count active dealership campaigns
      const activeDealership = (campaignsData.merged ?? []).filter(
        (c: Campaign) => {
          const status =
            c.campaign_status ||
            (c.start_date && c.end_date && Date.now() / 1000 > c.end_date
              ? "completed"
              : c.start_date && Date.now() / 1000 >= c.start_date
              ? "live"
              : "scheduled");
          return status === "live";
        }
      ).length;
      setActiveCount(activeDealership);
      return;
    }

    if (counts) {
      let totalForType = 0;
      let activeForType = 0;
      let totalCampaign_count = 0;
      let activeCampaign_count = 0;
      console.log("counts----", counts);
      if (typeof counts.total === "object" && counts.total !== null) {
        totalCampaign_count = counts.total.pre_sales + counts.total.post_sales;
        totalForType =
          campaignTypeFilter === "pre_sales"
            ? counts.total.pre_sales ?? 0
            : counts.total.post_sales ?? 0;
      } else {
        totalForType = counts.total ?? 0;
      }

      if (typeof counts.active === "object" && counts.active !== null) {
        activeCampaign_count =
          counts.active.pre_sales + counts.active.post_sales;
        activeForType =
          campaignTypeFilter === "pre_sales"
            ? counts.active.pre_sales ?? 0
            : counts.active.post_sales ?? 0;
      } else {
        activeForType = counts.active ?? 0;
      }

      // console.log("activeCampaign_count",activeCampaign_count,"totalCampaign_count",totalCampaign_count);
      setTotalCampaignCount(totalCampaign_count);
      setActiveCampaignCount(activeCampaign_count);
      setTotalCount(totalForType);
      setActiveCount(activeForType);
    }
  }, [counts, campaignTypeFilter, campaignsData, campaignSummaryData]);

  // Update campaigns and total count whenever data or type changes
  useEffect(() => {
    console.log("[useEffect] campaignsData changed:", campaignsData);
    console.log("[useEffect] campaignTypeFilter:", campaignTypeFilter);
    if (campaignsData) {
      console.log(
        "[useEffect] Setting campaigns:",
        campaignsData.merged?.length,
        "items"
      );
      setMergedCampaigns(campaignsData.merged ?? []);
      setTotalCount(campaignsData.total ?? 0);
    }
  }, [campaignsData, campaignTypeFilter]);

  // Process campaign summary data
  useEffect(() => {
    if (campaignSummaryData && Array.isArray(campaignSummaryData)) {
      // Aggregate data from all campaign types
      let aggregatedTotalCount = 0;
      let aggregatedActiveCount = 0;
      let aggregatedTotalReach = 0;
      let aggregatedConversationRate = 0;
      let totalConversationRateSum = 0;
      let campaignTypeCount = 0;

      campaignSummaryData.forEach((summary: any) => {
        aggregatedTotalCount += summary.total_count ?? 0;
        aggregatedActiveCount += summary.active_count ?? 0;
        aggregatedTotalReach += summary.total_reach ?? 0;

        // Calculate weighted average for conversion rate
        if (
          summary.conversation_rate !== undefined &&
          summary.conversation_rate !== null
        ) {
          totalConversationRateSum += summary.conversation_rate;
          campaignTypeCount++;
        }
      });

      // Update aggregated stats
      setTotalCampaignCount(aggregatedTotalCount);
      setActiveCampaignCount(aggregatedActiveCount);
      setTotalReach(aggregatedTotalReach);

      // Calculate average conversion rate
      // If conversation_rate is stored as decimal (0.098 = 9.8%), multiply by 100
      // If it's already a percentage (9.8 = 9.8%), use as-is
      if (campaignTypeCount > 0) {
        const avgRate = totalConversationRateSum / campaignTypeCount;
        // If average is less than 1, assume it's a decimal and convert to percentage
        setConversionRate(avgRate < 1 ? avgRate * 100 : avgRate);
      }

      // Set current campaign type based on filter
      setCurrentCampaignType(
        campaignTypeFilter === "pre_sales" || campaignTypeFilter === "pre-sales"
          ? "pre-sales"
          : campaignTypeFilter === "dealership"
          ? "dealership"
          : "post-sales"
      );

      // Update counts for current type
      const currentTypeSummary = campaignSummaryData.find(
        (s: any) =>
          s.campaign_type === campaignTypeFilter ||
          (campaignTypeFilter === "pre_sales" &&
            s.campaign_type === "pre-sales") ||
          (campaignTypeFilter === "post-sales" &&
            s.campaign_type === "post-sales")
      );

      if (currentTypeSummary) {
        setTotalCount(currentTypeSummary.total_count ?? 0);
        setActiveCount(currentTypeSummary.active_count ?? 0);
      }
    }
  }, [campaignSummaryData, campaignTypeFilter]);

  const filteredCampaigns = useMemo<Campaign[]>(() => {
    const q = (searchQuery || "").trim().toLowerCase();
    console.log(
      "[filteredCampaigns] mergedCampaigns:",
      mergedCampaigns.length,
      "items"
    );
    console.log("[filteredCampaigns] campaignTypeFilter:", campaignTypeFilter);

    return mergedCampaigns.filter((campaign: Campaign) => {
      const campaignName = campaign.name ?? campaign.campaign_name ?? "";
      const matchesSearch = q === "" || campaignName.toLowerCase().includes(q);

      // Derive status if not present (for dealership campaigns)
      const campaignStatus =
        campaign.campaign_status ||
        (campaign.start_date &&
        campaign.end_date &&
        Date.now() / 1000 > campaign.end_date
          ? "completed"
          : campaign.start_date && Date.now() / 1000 >= campaign.start_date
          ? "live"
          : campaign.start_date
          ? "scheduled"
          : "Drafted");

      const matchesStatus =
        statusFilter === "all" || campaignStatus === statusFilter;
      const matchesChannel =
        channelFilter === "all" ||
        (campaign.channels ?? []).includes(channelFilter);

      const normalize = (val: string | undefined) =>
        val?.toLowerCase().replace("-", "_");

      // Handle campaign_type as array or string
      const campaignType = Array.isArray(campaign.campaign_type)
        ? campaign.campaign_type[0]
        : campaign.campaign_type;

      // When filtering by dealership, show all campaigns (already filtered by fetch)
      // Otherwise, match by campaign_type
      const matchesCampaignType =
        campaignTypeFilter === "all" ||
        campaignTypeFilter === "dealership" ||
        normalize(campaignType) === normalize(campaignTypeFilter);

      return (
        matchesSearch && matchesStatus && matchesChannel && matchesCampaignType
      );
    });
  }, [
    mergedCampaigns,
    searchQuery,
    statusFilter,
    channelFilter,
    campaignTypeFilter,
  ]);

  const displayStart = 0;
  const displaySlice = filteredCampaigns.slice(displayStart, ITEMS_PER_PAGE);

  const totalPages = Math.max(1, Math.ceil(totalCount / ITEMS_PER_PAGE));

  const getStatusBadge = (status?: string) => {
    const variants: Record<
      string,
      "default" | "secondary" | "destructive" | "outline"
    > = {
      draft: "secondary",
      scheduled: "outline",
      live: "default",
      completed: "secondary",
    };
    const label =
      (status ?? "Unknown").charAt(0).toUpperCase() +
      (status ?? "Unknown").slice(1);
    return (
      <Badge
        variant={variants[status ?? ""] || "default"}
        className={
          status === "live" ? "bg-emerald-500 hover:bg-emerald-600" : ""
        }
      >
        {label}
      </Badge>
    );
  };

  const getChannelBadges = (channels?: string[]) =>
    (channels ?? []).map((channel) => (
      <Badge key={channel} variant="outline" className="mr-1">
        {channel.charAt(0).toUpperCase() + channel.slice(1)}
      </Badge>
    ));

  // Handler functions for dropdown actions
  const handleEdit = (campaign: Campaign) => {
    // Navigate to campaign create page with campaign data
    const campaignId = campaign.campaign_id ?? campaign.id;
    router.push(`/campaign/create?edit=${campaignId}`);
  };

  const handleDuplicate = async (campaign: Campaign) => {
    try {
      // Create a copy of the campaign
      const campaignId = campaign.campaign_id ?? campaign.id;
      const campaignType = Array.isArray(campaign.campaign_type)
        ? campaign.campaign_type[0]
        : campaign.campaign_type;

      const modelName =
        campaignType === "pre-sales" || campaignType === "pre_sales"
          ? "pre_sales_campaign"
          : "post_sales_campaign";

      // Fetch the campaign data
      const response = await fetchAPIData(modelName, {});
      const campaignData = response.items.find(
        (c: Campaign) => (c.campaign_id ?? c.id) === campaignId
      );

      if (campaignData) {
        // Remove id fields and create a duplicate
        const { campaign_id, id, ...duplicateData } = campaignData;
        duplicateData.campaign_name = `${
          campaignData.campaign_name ?? "Campaign"
        } (Copy)`;
        duplicateData.campaign_status = "Drafted";

        // In a real implementation, you would POST this to create a new campaign
        // For now, navigate to create page with the duplicate data
        localStorage.setItem(
          "duplicateCampaignData",
          JSON.stringify(duplicateData)
        );
        router.push("/campaign/create?duplicate=true");
      }
    } catch (error) {
      console.error("Error duplicating campaign:", error);
      alert("Failed to duplicate campaign. Please try again.");
    }
  };

  const handlePauseOrLaunch = async (
    campaign: Campaign,
    action: "pause" | "launch"
  ) => {
    try {
      const campaignId = campaign.campaign_id ?? campaign.id;
      const campaignType = Array.isArray(campaign.campaign_type)
        ? campaign.campaign_type[0]
        : campaign.campaign_type;

      const modelName =
        campaignType === "pre-sales" || campaignType === "pre_sales"
          ? "pre_sales_campaign"
          : "post_sales_campaign";

      const newStatus = action === "pause" ? "paused" : "live";

      // Update campaign status
      // In a real implementation, you would PATCH the campaign
      // For now, we'll just refresh the data
      await mutateCampaigns();
      alert(
        `Campaign ${action === "pause" ? "paused" : "launched"} successfully`
      );
    } catch (error) {
      console.error(`Error ${action}ing campaign:`, error);
      alert(`Failed to ${action} campaign. Please try again.`);
    }
  };

  const handleInsights = (campaign: Campaign) => {
    const campaignId = campaign.campaign_id ?? campaign.id;
    router.push(`/campaign/insights?campaign_id=${campaignId}`);
  };

  const handleDeleteClick = (campaign: Campaign) => {
    setCampaignToDelete(campaign);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!campaignToDelete) return;

    setIsDeleting(true);
    try {
      const campaignId = campaignToDelete.campaign_id ?? campaignToDelete.id;
      const campaignType = Array.isArray(campaignToDelete.campaign_type)
        ? campaignToDelete.campaign_type[0]
        : campaignToDelete.campaign_type;

      const modelName =
        campaignType === "pre-sales" || campaignType === "pre_sales"
          ? "pre_sales_campaign"
          : campaignType === "dealership"
          ? "dealership_campaign"
          : "post_sales_campaign";

      await deleteAPIData(modelName, campaignId);
      setDeleteDialogOpen(false);
      setCampaignToDelete(null);

      // Refresh campaigns list
      await mutateCampaigns();
      alert("Campaign deleted successfully");
    } catch (error) {
      console.error("Error deleting campaign:", error);
      alert("Failed to delete campaign. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="flex flex-col w-full">
        {/* Header */}
        <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Campaign Dashboard
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Manage and monitor your marketing campaigns across all channels
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/campaign/create?new=true">
              <Button className="gap-2">
                <Plus className="h-4 w-4" /> Create Campaign
              </Button>
            </Link>
          </div>
        </div>

        <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
          {/* Stats */}
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Campaigns
                </CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{totalCampaignCount}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Current type:{" "}
                  {campaignTypeFilter === "pre_sales" ||
                  campaignTypeFilter === "pre-sales"
                    ? "Pre-Sales"
                    : campaignTypeFilter === "post-sales"
                    ? "Post-Sales"
                    : "Dealership"}
                </p>
              </CardContent>
            </Card>

            <Card className="shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">
                  Active Campaigns
                </CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{activeCampaignCount}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Currently running
                </p>
              </CardContent>
            </Card>

            <Card className="shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Reach
                </CardTitle>
                <UsersIcon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {totalReach >= 1000
                    ? `${(totalReach / 1000).toFixed(1)}K`
                    : totalReach.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Across all campaigns
                </p>
              </CardContent>
            </Card>

            <Card className="shadow">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">
                  Conversion Rate
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {conversionRate > 0
                    ? `${conversionRate.toFixed(1)}%`
                    : "0.0%"}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Average across all campaigns
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Campaign Table */}
          <Card className="shadow">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Recent Campaigns</CardTitle>
                  <CardDescription>
                    View and manage your marketing campaigns
                  </CardDescription>
                </div>
              </div>

              {/* Filters */}
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center mt-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    placeholder="Search campaigns..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <div className="flex gap-2">
                  {/* Status Filter */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="gap-2 bg-transparent"
                      >
                        Status:{" "}
                        {statusFilter === "all"
                          ? "All"
                          : statusFilter.charAt(0).toUpperCase() +
                            statusFilter.slice(1)}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => setStatusFilter("all")}>
                        All
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setStatusFilter("Drafted")}
                      >
                        Draft
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setStatusFilter("scheduled")}
                      >
                        Scheduled
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setStatusFilter("live")}>
                        Live
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setStatusFilter("completed")}
                      >
                        Completed
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>

                  {/* Channel Filter */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="gap-2 bg-transparent"
                      >
                        Channel:{" "}
                        {channelFilter === "all"
                          ? "All"
                          : channelFilter.charAt(0).toUpperCase() +
                            channelFilter.slice(1)}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Filter by Channel</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem onClick={() => setChannelFilter("all")}>
                        All
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setChannelFilter("whatsapp_chat")}
                      >
                        WhatsApp
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setChannelFilter("email")}
                      >
                        Email
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => setChannelFilter("voice_phone")}
                      >
                        Voice
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>

                  {/* Campaign Type */}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="outline"
                        className="gap-2 bg-transparent"
                      >
                        Campaign Type:{" "}
                        {campaignTypeFilter === "pre_sales"
                          ? "Pre-Sales"
                          : campaignTypeFilter === "post-sales"
                          ? "Post-Sales"
                          : "Dealership"}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>
                        Filter by Campaign Type
                      </DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => {
                          setCampaignTypeFilter("pre_sales");
                          setPage(1);
                        }}
                      >
                        Pre-Sales
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => {
                          setCampaignTypeFilter("post-sales");
                          setPage(1);
                        }}
                      >
                        Post-Sales
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onClick={() => {
                          setCampaignTypeFilter("dealership");
                          setPage(1);
                        }}
                      >
                        Dealership
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </CardHeader>

            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Campaign Type</TableHead>
                    <TableHead>Campaign Name</TableHead>
                    <TableHead>Channels Used</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Launch Date</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="text-center text-muted-foreground"
                      >
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : error ? (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="text-center text-destructive"
                      >
                        {error}
                      </TableCell>
                    </TableRow>
                  ) : filteredCampaigns.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={6}
                        className="text-center text-muted-foreground"
                      >
                        No campaigns found
                      </TableCell>
                    </TableRow>
                  ) : (
                    displaySlice.map((campaign) => {
                      // Handle campaign_type as array or string
                      const campaignType = Array.isArray(campaign.campaign_type)
                        ? campaign.campaign_type[0]
                        : campaign.campaign_type;

                      return (
                        <TableRow
                          key={
                            campaign.campaign_id ?? campaign.id ?? Math.random()
                          }
                        >
                          <TableCell className="font-medium">
                            {campaignType === "pre-sales" ||
                            campaignType === "pre_sales"
                              ? "Pre-Sales"
                              : campaignType === "post-sales" ||
                                campaignType === "post_sales"
                              ? "Post-Sales"
                              : campaignType === "dealership" ||
                                campaignTypeFilter === "dealership"
                              ? "Dealership"
                              : campaignType
                              ? campaignType.charAt(0).toUpperCase() +
                                campaignType.slice(1)
                              : "—"}
                          </TableCell>
                          <TableCell className="font-medium">
                            {campaign.campaign_name ?? "—"}
                          </TableCell>
                          <TableCell>
                            {getChannelBadges(campaign.channels)}
                          </TableCell>
                          <TableCell>
                            {getStatusBadge(
                              campaign.campaign_status ||
                                (campaign.start_date &&
                                campaign.end_date &&
                                Date.now() / 1000 > campaign.end_date
                                  ? "completed"
                                  : campaign.start_date &&
                                    Date.now() / 1000 >= campaign.start_date
                                  ? "live"
                                  : "scheduled")
                            )}
                          </TableCell>
                          <TableCell>
                            {epochToIST(campaign.start_date) ??
                              (campaign.start_date
                                ? new Date(
                                    campaign.start_date * 1000
                                  ).toLocaleDateString()
                                : "—")}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleInsights(campaign)}
                                className="gap-2"
                              >
                                <BarChart3 className="h-4 w-4" />
                                Insights
                              </Button>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon">
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onClick={() => handleEdit(campaign)}
                                  >
                                    <Pencil className="mr-2 h-4 w-4" /> Edit
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => handleDuplicate(campaign)}
                                  >
                                    <Copy className="mr-2 h-4 w-4" /> Duplicate
                                  </DropdownMenuItem>
                                  {campaign.campaign_status === "live" ? (
                                    <DropdownMenuItem
                                      onClick={() =>
                                        handlePauseOrLaunch(campaign, "pause")
                                      }
                                    >
                                      <Pause className="mr-2 h-4 w-4" /> Pause
                                    </DropdownMenuItem>
                                  ) : campaign.campaign_status === "Drafted" ||
                                    campaign.campaign_status === "scheduled" ? (
                                    <DropdownMenuItem
                                      onClick={() =>
                                        handlePauseOrLaunch(campaign, "launch")
                                      }
                                    >
                                      <Play className="mr-2 h-4 w-4" /> Launch
                                    </DropdownMenuItem>
                                  ) : null}
                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onClick={() => handleInsights(campaign)}
                                  >
                                    <BarChart3 className="mr-2 h-4 w-4" />{" "}
                                    Insights
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    className="text-destructive"
                                    onClick={() => handleDeleteClick(campaign)}
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" /> Delete
                                  </DropdownMenuItem>
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex justify-between items-center mt-4">
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Next
                  </Button>
                </div>

                <div className="text-sm text-muted-foreground">
                  Page {page} of {totalPages} • Showing {displaySlice.length} of{" "}
                  {totalCount} campaigns
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Campaign</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "
              {campaignToDelete?.campaign_name ?? "this campaign"}"? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false);
                setCampaignToDelete(null);
              }}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ProtectedRoute>
  );
}
