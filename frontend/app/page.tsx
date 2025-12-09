"use client";
import useSWR from "swr";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  fetchAPIData,
  fetchPivotCountForCampaign,
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
import { count } from "console";
import { set } from "date-fns";

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
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [campaignTypeFilter, setCampaignTypeFilter] =
    useState<string>("post_sales"); // default

  const [mergedCampaigns, setMergedCampaigns] = useState<Campaign[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [activeCount, setActiveCount] = useState<number>(0);
  const [totalCampaignCount, setTotalCampaignCount] = useState<number>(0);
  const [activeCampaignCount, setActiveCampaignCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);

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
  } = useSWR(
    ["campaigns", campaignTypeFilter, page],
    () => fetchCampaigns(campaignTypeFilter, page),
    swrOptions
  );

  // Update counts header (total campaigns of current type)
  useEffect(() => {
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
  }, [counts, campaignTypeFilter]);

  // Update campaigns and total count whenever data or type changes
  useEffect(() => {
    if (campaignsData) {
      setMergedCampaigns(campaignsData.merged ?? []);
      setTotalCount(campaignsData.total ?? 0);
    }
  }, [campaignsData, campaignTypeFilter]);

  const filteredCampaigns = useMemo<Campaign[]>(() => {
    const q = (searchQuery || "").trim().toLowerCase();

    return mergedCampaigns.filter((campaign: Campaign) => {
      const matchesSearch =
        q === "" || (campaign.name ?? "").toLowerCase().includes(q);
      const matchesStatus =
        statusFilter === "all" || campaign.campaign_status === statusFilter;
      const matchesChannel =
        channelFilter === "all" ||
        (campaign.channels ?? []).includes(channelFilter);

      const normalize = (val: string | undefined) =>
        val?.toLowerCase().replace("-", "_");

      const matchesCampaignType =
        campaignTypeFilter === "all" ||
        normalize(campaign.campaign_type) === normalize(campaignTypeFilter);

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
                  {campaignTypeFilter === "pre_sales"
                    ? "Pre-Sales"
                    : "Post-Sales"}
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
                <div className="text-2xl font-bold">156.8K</div>
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
                <div className="text-2xl font-bold">9.8%</div>
                <p className="text-xs text-muted-foreground mt-1">
                  +1.2% from last month
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Campaign Table */}
          <div
            className="transform-gpu transition-transform duration-500 ease-out"
            style={{
              transform: "perspective(1000px) rotateX(1deg) rotateY(-1deg)",
              transformStyle: "preserve-3d",
            }}
          >
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
                        <DropdownMenuItem
                          onClick={() => setStatusFilter("all")}
                        >
                          All
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setStatusFilter("draft")}
                        >
                          Draft
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setStatusFilter("scheduled")}
                        >
                          Scheduled
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setStatusFilter("live")}
                        >
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
                        <DropdownMenuItem
                          onClick={() => setChannelFilter("all")}
                        >
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
                            : "Post-Sales"}
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
                            setCampaignTypeFilter("post_sales");
                            setPage(1);
                          }}
                        >
                          Post-Sales
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
                      displaySlice.map((campaign) => (
                        <TableRow
                          key={`${campaign.campaign_id}-${
                            campaign.campaign_type ?? "type"
                          }`}
                        >
                          <TableCell className="font-medium">
                            {campaign.campaign_type === "pre-sales" ||
                            campaign.campaign_type === "pre_sales"
                              ? "Pre-Sales"
                              : campaign.campaign_type === "post-sales" ||
                                campaign.campaign_type === "post_sales"
                              ? "Post-Sales"
                              : "—"}
                          </TableCell>
                          <TableCell className="font-medium">
                            {campaign.campaign_name ?? "—"}
                          </TableCell>
                          <TableCell>
                            {getChannelBadges(campaign.channels)}
                          </TableCell>
                          <TableCell>
                            {getStatusBadge(campaign.campaign_status)}
                          </TableCell>
                          <TableCell>
                            {epochToIST(campaign.start_date) ??
                              campaign.start_date ??
                              "—"}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon">
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem>
                                  <Pencil className="mr-2 h-4 w-4" /> Edit
                                </DropdownMenuItem>
                                <DropdownMenuItem>
                                  <Copy className="mr-2 h-4 w-4" /> Duplicate
                                </DropdownMenuItem>
                                {campaign.campaign_status === "live" ? (
                                  <DropdownMenuItem>
                                    <Pause className="mr-2 h-4 w-4" /> Pause
                                  </DropdownMenuItem>
                                ) : campaign.campaign_status === "draft" ||
                                  campaign.campaign_status === "scheduled" ? (
                                  <DropdownMenuItem>
                                    <Play className="mr-2 h-4 w-4" /> Launch
                                  </DropdownMenuItem>
                                ) : null}
                                <DropdownMenuSeparator />
                                <DropdownMenuItem className="text-destructive">
                                  Insights
                                </DropdownMenuItem>
                                <DropdownMenuItem className="text-destructive">
                                  <Trash2 className="mr-2 h-4 w-4" /> Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))
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
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                    >
                      Next
                    </Button>
                  </div>

                  <div className="text-sm text-muted-foreground">
                    Page {page} of {totalPages} • Showing {displaySlice.length}{" "}
                    of {totalCount} campaigns
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
