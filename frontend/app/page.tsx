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
import { VerifyProfileBanner } from "@/components/dealership/verify-profile-banner";
import { CompleteSetupModal } from "@/components/dealership/complete-setup-modal";
import { useAuth } from "@/lib/auth-context";

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
  RefreshCw,
  Eye,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
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
  campaign_id?: string | number;
  name?: string;
  campaign_name?: string;
  description?: string;
  channels?: string[];
  campaign_status?: string;
  launchDate?: string | number;
  start_date?: number;
  end_date?: number;
  campaign_type?: string | string[];
  [key: string]: any;
}

const ITEMS_PER_PAGE = 5;

export default function CampaignDashboard() {
  const router = useRouter();
  const { isDealershipSetupComplete, checkDealershipSetup } = useAuth();
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [campaignTypeFilter, setCampaignTypeFilter] = useState<string>("all"); // default to "all" to show both types

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
 // In page.tsx

// ... existing imports and ITEMS_PER_PAGE constant ...

// Replace your existing fetchCampaigns function with this:
const fetchCampaigns = async (type: string, page: number) => {
  console.log("[fetchCampaigns] Type:", type, "Page:", page, "Size:", ITEMS_PER_PAGE);

  // 1. Handle Dealership Campaigns
  if (type === "dealership") {
    const res = await fetchDealershipCampaigns(page, ITEMS_PER_PAGE);
    return {
      merged: res?.items ?? [],
      total: res?.total ?? 0,
    };
  }

  // 2. Handle "Pre-Sales" (Pass page & size!)
  if (type === "pre-sales" || type === "pre_sales") {
    const res = await fetchPreSalesCampaigns(page, ITEMS_PER_PAGE);
    return {
      merged: res?.items ?? [],
      total: res?.total ?? 0,
    };
  }

  // 3. Handle "Post-Sales" (Pass page & size!)
  if (type === "post-sales" || type === "post_sales") {
    const res = await fetchPostSalesCampaigns(page, ITEMS_PER_PAGE);
    return {
      merged: res?.items ?? [],
      total: res?.total ?? 0,
    };
  }

  // 4. Handle "All"
  // Note: True server-side pagination for "All" is complex because it requires merging 
  // two different API endpoints. For now, we fetch a larger batch (e.g. 50) 
  // of each to ensure the client-side list is populated.
 if (type === "all") {
    const [preRes, postRes] = await Promise.all([
      // FIXED: Pass 'page' and 'ITEMS_PER_PAGE' instead of 1 and 50
      fetchPreSalesCampaigns(page, ITEMS_PER_PAGE),
      fetchPostSalesCampaigns(page, ITEMS_PER_PAGE),
    ]);

    const preItems = preRes?.items ?? [];
    const postItems = postRes?.items ?? [];
    const merged = [...preItems, ...postItems];

    // Sort by creation date (newest first)
    merged.sort((a, b) => {
      const dateA = a.created || a.start_date || 0;
      const dateB = b.created || b.start_date || 0;
      return dateB - dateA;
    });

    return {
      merged: merged,
      total: (preRes?.total ?? 0) + (postRes?.total ?? 0),
    };
  }

  return { merged: [], total: 0 };
};

  const { data: counts, mutate: mutateCounts } = useSWR(
    "pivot-counts",
    fetchCounts,
    swrOptions
  );

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

  // Safe check for localStorage
  const dealershipId =
    typeof window !== "undefined"
      ? localStorage.getItem("dealership_id")
      : null;

  // Fetch campaign summary data
  const { data: campaignSummaryData, mutate: mutateCampaignSummary } = useSWR(
    dealershipId, // If null, this won't run
    fetchCampaignSummary,
    swrOptions
  );

  // Refresh setup status when dashboard loads and on route changes
  useEffect(() => {
    const refreshStatus = async () => {
      console.log("[Dashboard] Refreshing setup status...");
      await checkDealershipSetup();
      await new Promise((resolve) => setTimeout(resolve, 300));
    };
    refreshStatus();
  }, [checkDealershipSetup]);

  // Show modal if setup is not complete
  useEffect(() => {
    if (isDealershipSetupComplete === false) {
      setShowSetupModal(true);
    } else {
      setShowSetupModal(false);
    }
  }, [isDealershipSetupComplete]);

  // Update counts header (Legacy/Fallback or Dealership specific)
  useEffect(() => {
    // If we have summary data, we let the other useEffect handle stats
    // UNLESS we are in dealership mode (which might not be in the summary API)
    if (
      campaignSummaryData &&
      Array.isArray(campaignSummaryData) &&
      campaignSummaryData.length > 0 &&
      campaignTypeFilter !== "dealership" &&
      campaignTypeFilter !== "all"
    ) {
      return;
    }

    // For dealership campaigns, use the campaignsData total
    if (campaignTypeFilter === "dealership" && campaignsData) {
      setTotalCount(campaignsData.total ?? 0);
      setTotalCampaignCount(campaignsData.total ?? 0);

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
      setActiveCampaignCount(activeDealership);
      setTotalReach(0); // Dealership specific reach if available
      setConversionRate(0); // Dealership specific rate
      return;
    }

    // For "all" type, sum both pre-sales and post-sales counts
    if (campaignTypeFilter === "all") {
      // Use summary data if available (more accurate than filtering campaigns)
      if (campaignSummaryData && Array.isArray(campaignSummaryData)) {
        const preSalesSummary = campaignSummaryData.find(
          (s: any) =>
            s.campaign_type === "pre-sales" || s.campaign_type === "pre_sales"
        );
        const postSalesSummary = campaignSummaryData.find(
          (s: any) =>
            s.campaign_type === "post-sales" || s.campaign_type === "post_sales"
        );

        // Sum up total and active counts from summaries
        const totalCountSum =
          (preSalesSummary?.total_count ?? 0) +
          (postSalesSummary?.total_count ?? 0);
        const activeCountSum =
          (preSalesSummary?.active_count ?? 0) +
          (postSalesSummary?.active_count ?? 0);
        const totalReachSum =
          (preSalesSummary?.total_reach ?? 0) +
          (postSalesSummary?.total_reach ?? 0);
        const preRate = preSalesSummary?.conversation_rate ?? 0;
        const postRate = postSalesSummary?.conversation_rate ?? 0;
        const avgRate =
          preSalesSummary && postSalesSummary
            ? ((preRate < 1 ? preRate * 100 : preRate) +
                (postRate < 1 ? postRate * 100 : postRate)) /
              2
            : (preRate < 1 ? preRate * 100 : preRate) ||
              (postRate < 1 ? postRate * 100 : postRate);

        setTotalCampaignCount(totalCountSum);
        setTotalCount(totalCountSum);
        setActiveCampaignCount(activeCountSum);
        setActiveCount(activeCountSum);
        setTotalReach(totalReachSum);
        setConversionRate(avgRate);
      } else if (campaignsData) {
        // Fallback: calculate from campaigns data
        setTotalCount(campaignsData.total ?? 0);
        setTotalCampaignCount(campaignsData.total ?? 0);

        const activeAll = (campaignsData.merged ?? []).filter((c: Campaign) => {
          const status =
            c.campaign_status ||
            (c.start_date && c.end_date && Date.now() / 1000 > c.end_date
              ? "completed"
              : c.start_date && Date.now() / 1000 >= c.start_date
              ? "live"
              : "scheduled");
          return status === "live" || status === "active";
        }).length;

        setActiveCount(activeAll);
        setActiveCampaignCount(activeAll);
      } else if (counts) {
        // Fallback to pivot counts
        let totalForAll = 0;
        let activeForAll = 0;

        if (typeof counts.total === "object" && counts.total !== null) {
          totalForAll =
            (counts.total.pre_sales ?? 0) + (counts.total.post_sales ?? 0);
        } else {
          totalForAll = counts.total ?? 0;
        }

        if (typeof counts.active === "object" && counts.active !== null) {
          activeForAll =
            (counts.active.pre_sales ?? 0) + (counts.active.post_sales ?? 0);
        } else {
          activeForAll = counts.active ?? 0;
        }

        setTotalCampaignCount(totalForAll);
        setTotalCount(totalForAll);
        setActiveCampaignCount(activeForAll);
        setActiveCount(activeForAll);
      }
      return;
    }

    // Fallback using pivot-counts API
    if (counts) {
      let totalForType = 0;
      let activeForType = 0;

      if (typeof counts.total === "object" && counts.total !== null) {
        totalForType =
          campaignTypeFilter === "pre_sales"
            ? counts.total.pre_sales ?? 0
            : counts.total.post_sales ?? 0;
      } else {
        totalForType = counts.total ?? 0;
      }

      if (typeof counts.active === "object" && counts.active !== null) {
        activeForType =
          campaignTypeFilter === "pre_sales"
            ? counts.active.pre_sales ?? 0
            : counts.active.post_sales ?? 0;
      } else {
        activeForType = counts.active ?? 0;
      }

      setTotalCampaignCount(totalForType);
      setTotalCount(totalForType);
      setActiveCampaignCount(activeForType);
      setActiveCount(activeForType);
    }
  }, [counts, campaignTypeFilter, campaignsData, campaignSummaryData]);

  // Update campaigns and total count whenever data or type changes
  useEffect(() => {
    if (campaignsData) {
      setMergedCampaigns(campaignsData.merged ?? []);
      setTotalCount(campaignsData.total ?? 0);
    }
  }, [campaignsData, campaignTypeFilter]);

  // Process campaign summary data (FIXED: Filter by type instead of sum)
  useEffect(() => {
    // If we are on dealership tab or "all" tab, the previous useEffect handles it
    if (campaignTypeFilter === "dealership" || campaignTypeFilter === "all")
      return;

    if (campaignSummaryData && Array.isArray(campaignSummaryData)) {
      // Find the specific summary for the selected campaign type
      const currentTypeSummary = campaignSummaryData.find(
        (s: any) =>
          s.campaign_type === campaignTypeFilter ||
          (campaignTypeFilter === "pre_sales" &&
            s.campaign_type === "pre-sales") ||
          (campaignTypeFilter === "post-sales" &&
            s.campaign_type === "post-sales")
      );

      // Update UI with specific stats
      if (currentTypeSummary) {
        setTotalCampaignCount(currentTypeSummary.total_count ?? 0);
        setActiveCampaignCount(currentTypeSummary.active_count ?? 0);
        setTotalReach(currentTypeSummary.total_reach ?? 0);

        const rate = currentTypeSummary.conversation_rate ?? 0;
        setConversionRate(rate < 1 ? rate * 100 : rate);

        // Also ensure internal counts match
        setTotalCount(currentTypeSummary.total_count ?? 0);
        setActiveCount(currentTypeSummary.active_count ?? 0);
      } else {
        // If data exists but not for this specific type (e.g., 0 campaigns)
        setTotalCampaignCount(0);
        setActiveCampaignCount(0);
        setTotalReach(0);
        setConversionRate(0);
        setTotalCount(0);
        setActiveCount(0);
      }

      setCurrentCampaignType(
        campaignTypeFilter === "pre_sales" || campaignTypeFilter === "pre-sales"
          ? "pre-sales"
          : "post-sales"
      );
    }
  }, [campaignSummaryData, campaignTypeFilter]);

  const filteredCampaigns = useMemo<Campaign[]>(() => {
    const q = (searchQuery || "").trim().toLowerCase();

    return mergedCampaigns.filter((campaign: Campaign) => {
      const campaignName = campaign.name ?? campaign.campaign_name ?? "";
      const matchesSearch = q === "" || campaignName.toLowerCase().includes(q);

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

      const campaignType = Array.isArray(campaign.campaign_type)
        ? campaign.campaign_type[0]
        : campaign.campaign_type;

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

  // const displayStart = (page - 1) * ITEMS_PER_PAGE;
  // const displaySlice = filteredCampaigns.slice(
  //   displayStart,
  //   displayStart + ITEMS_PER_PAGE
  // );
  // const displaySlice = filteredCampaigns;

  // const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE);
const displaySlice = useMemo(() => {
    // 1. For "All", we fetch a large batch (e.g. 50+), so we MUST slice client-side
    //    to show only 5 per page.
    if (campaignTypeFilter === "all") {
      const displayStart = (page - 1) * ITEMS_PER_PAGE;
      return filteredCampaigns.slice(displayStart, displayStart + ITEMS_PER_PAGE);
    }

    // 2. For specific types (Pre/Post/Dealership), the API already returns
    //    exactly 5 items for the current page. Do NOT slice again.
    return filteredCampaigns;
  }, [filteredCampaigns, page, campaignTypeFilter]);

  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE);

  // ... continue with rendering ...
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

  const handleEdit = (campaign: Campaign) => {
    const campaignId = campaign.campaign_id ?? campaign.id;
    router.push(`/campaign/create?edit=${campaignId}`);
  };

  const handleDuplicate = async (campaign: Campaign) => {
    try {
      const campaignId = campaign.campaign_id ?? campaign.id;
      const campaignType = Array.isArray(campaign.campaign_type)
        ? campaign.campaign_type[0]
        : campaign.campaign_type;

      const modelName =
        campaignType === "pre-sales" || campaignType === "pre_sales"
          ? "pre_sales_campaign"
          : "post_sales_campaign";

      const response = await fetchAPIData(modelName, {});
      const campaignData = response.items.find(
        (c: Campaign) => (c.campaign_id ?? c.id) === campaignId
      );

      if (campaignData) {
        const { campaign_id, id, ...duplicateData } = campaignData;
        duplicateData.campaign_name = `${
          campaignData.campaign_name ?? "Campaign"
        } (Copy)`;
        duplicateData.campaign_status = "Drafted";

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

      await mutateCampaigns();
    } catch (error) {
      console.error("Error deleting campaign:", error);
      alert("Failed to delete campaign. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleRefresh = async () => {
    try {
      await Promise.all([
        mutateCampaigns(),
        mutateCounts(),
        mutateCampaignSummary(),
      ]);
    } catch (error) {
      console.error("Error refreshing data:", error);
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
            <Button
              variant="outline"
              className="gap-2"
              onClick={handleRefresh}
              disabled={loading}
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />{" "}
              Refresh
            </Button>
            <Button
              className="gap-2"
              onClick={() => {
                if (isDealershipSetupComplete === false) {
                  router.push("/dealership/update-details");
                } else {
                  router.push("/campaign/create?new=true");
                }
              }}
            >
              <Plus className="h-4 w-4" /> Create Campaign
            </Button>
          </div>
        </div>

        <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
          {/* Verify Profile Banner - Show only if setup not complete */}
          {isDealershipSetupComplete === false && <VerifyProfileBanner />}

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
                  {campaignTypeFilter === "all"
                    ? "All Types"
                    : campaignTypeFilter === "pre_sales" ||
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
                        {campaignTypeFilter === "all"
                          ? "All"
                          : campaignTypeFilter === "pre_sales"
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
                          setCampaignTypeFilter("all");
                          setPage(1);
                        }}
                      >
                        All
                      </DropdownMenuItem>
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
                    <TableHead>Analytics</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>

                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className="text-center text-muted-foreground"
                      >
                        Loading...
                      </TableCell>
                    </TableRow>
                  ) : error ? (
                    <TableRow>
                      <TableCell
                        colSpan={7}
                        className="text-center text-destructive"
                      >
                        {error}
                      </TableCell>
                    </TableRow>
                  ) : filteredCampaigns.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={7}
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
                        <TableRow key={campaign.id || campaign.campaign_id}>
                          <TableCell className="font-medium capitalize">
                            {campaignType?.replace("_", " ") || "Unknown"}
                          </TableCell>
                          <TableCell>
                            {campaign.name ||
                              campaign.campaign_name ||
                              "Unnamed"}
                          </TableCell>
                          <TableCell>
                            {getChannelBadges(campaign.channels)}
                          </TableCell>
                          <TableCell>
                            {getStatusBadge(campaign.campaign_status)}
                          </TableCell>
                          <TableCell>
                            {campaign.launchDate || campaign.start_date
                              ? epochToIST(
                                  campaign.launchDate || campaign.start_date
                                )
                              : "-"}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 gap-1.5 px-2 text-xs"
                              onClick={() => handleInsights(campaign)}
                            >
                              <Eye className="h-3.5 w-3.5" />
                              View Analytics
                            </Button>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    className="h-8 w-8 p-0"
                                  >
                                    <span className="sr-only">Open menu</span>
                                    <MoreVertical className="h-4 w-4" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                  <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                  <DropdownMenuItem
                                    onClick={() => handleEdit(campaign)}
                                  >
                                    <Pencil className="mr-2 h-4 w-4" />
                                    Edit
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={() => handleDuplicate(campaign)}
                                  >
                                    <Copy className="mr-2 h-4 w-4" />
                                    Duplicate
                                  </DropdownMenuItem>

                                  {campaign.campaign_status === "live" ? (
                                    <DropdownMenuItem
                                      onClick={() =>
                                        handlePauseOrLaunch(campaign, "pause")
                                      }
                                    >
                                      <Pause className="mr-2 h-4 w-4" /> Pause
                                    </DropdownMenuItem>
                                  ) : (
                                    <DropdownMenuItem
                                      onClick={() =>
                                        handlePauseOrLaunch(campaign, "launch")
                                      }
                                    >
                                      <Play className="mr-2 h-4 w-4" /> Launch
                                    </DropdownMenuItem>
                                  )}

                                  <DropdownMenuSeparator />
                                  <DropdownMenuItem
                                    onClick={() => handleDeleteClick(campaign)}
                                    className="text-destructive focus:text-destructive"
                                  >
                                    <Trash2 className="mr-2 h-4 w-4" />
                                    Delete
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
             {/* Pagination Controls */}
{/* Pagination */}
<div className="flex items-center justify-center space-x-2 mt-4">
  <Button
    variant="outline"
    className="h-8 w-8 p-0"
    onClick={() => setPage(1)}
    disabled={page === 1}
  >
    <span className="sr-only">Go to first page</span>
    <ChevronsLeft className="h-4 w-4" />
  </Button>
  
  <Button
    variant="outline"
    className="h-8 w-8 p-0"
    onClick={() => setPage((p) => Math.max(1, p - 1))}
    disabled={page === 1}
  >
    <span className="sr-only">Go to previous page</span>
    <ChevronLeft className="h-4 w-4" />
  </Button>
  
  <div className="flex w-[100px] items-center justify-center text-sm font-medium">
    Page {page} of {totalPages}
  </div>
  
  <Button
    variant="outline"
    className="h-8 w-8 p-0"
    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
    disabled={page === totalPages}
  >
    <span className="sr-only">Go to next page</span>
    <ChevronRight className="h-4 w-4" />
  </Button>
  
  <Button
    variant="outline"
    className="h-8 w-8 p-0"
    onClick={() => setPage(totalPages)}
    disabled={page === totalPages}
  >
    <span className="sr-only">Go to last page</span>
    <ChevronsRight className="h-4 w-4" />
  </Button>
</div>
            </CardContent>
          </Card>
        </div>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Are you sure?</DialogTitle>
              <DialogDescription>
                This action cannot be undone. This will permanently delete the
                campaign{" "}
                <span className="font-medium text-foreground">
                  {campaignToDelete?.name || campaignToDelete?.campaign_name}
                </span>{" "}
                and remove data from our servers.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete Campaign"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Setup Modal */}
        <CompleteSetupModal
          open={showSetupModal}
          onOpenChange={setShowSetupModal}
        />
      </div>
    </ProtectedRoute>
  );
}
