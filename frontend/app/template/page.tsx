"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Search,
  FileText,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Loader2,
  RefreshCw,
} from "lucide-react";

import { TemplateStatusTable } from "@/components/template/template-status-table";
import { fetchAPIData, deleteAPIData, capitalize } from "@/utils/api";

export interface Template {
  template_id: string;
  template_name: string;
  language: string;
  channel: "WhatsApp" | "Email";
  campaignName: string;
  provider_name: string;
  status: "Pending" | "Approved" | "Rejected";
  updated: number;
  rejectionReason?: string;

  // New fields for preview
  template_message?: string;
  template_type?: string;
  template_variables?: string[];
  buttons?: Array<{ text: string; type: string }>;

  [key: string]: any;
}

const ITEMS_PER_PAGE = 10;

// Custom debounce hook for search
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

export default function TemplatePage() {
  // --- State ---
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const debouncedSearch = useDebounce(searchQuery, 500);

  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, channelFilter, statusFilter]);

  // --- Fetch Main Table Data ---
  const { data, error, isLoading, mutate } = useSWR(
    ["templates", page, debouncedSearch, channelFilter, statusFilter],
    async () => {
      const queryParams: Record<string, any> = {
        page_number: page,
        page_size: ITEMS_PER_PAGE,
      };

      // Map filters to API params
      if (debouncedSearch) {
        queryParams.template_name = debouncedSearch;
      }
      // Assuming API wants 'whatsapp_chat' instead of 'WhatsApp'
      if (channelFilter !== "all") {
        queryParams.channel =
          channelFilter === "WhatsApp"
            ? "whatsapp_chat"
            : channelFilter.toLowerCase();
      }
      // API uses lowercase status
      if (statusFilter !== "all") {
        queryParams.status = statusFilter.toLowerCase();
      }

      const apiResponse = await fetchAPIData("template", queryParams);

      // Normalize Data for UI
      const items = (apiResponse.items || []).map((item: any) => ({
        ...item,
        // Map 'whatsapp_chat' to 'WhatsApp' for the UI
        channel:
          item.channel === "whatsapp_chat"
            ? "WhatsApp"
            : capitalize(item.channel),
        // Map lowercase 'approved' to 'Approved'
        status: capitalize(item.status),
        // Fallback for campaign name since API returns 'campaign_type'
        campaignName: item.campaign_type
          ? capitalize(item.campaign_type)
          : item.campaign_name || "-",
      }));

      return {
        items,
        total: apiResponse.total,
      };
    },
    {
      keepPreviousData: true,
      revalidateOnFocus: false,
    }
  );

  // --- Fetch KPI Stats ---
  const { data: stats, mutate: mutateStats } = useSWR(
    "template-stats",
    async () => {
      // Fetch stats with lowercase status values as per API data
      const [pending, approved, rejected] = await Promise.all([
        fetchAPIData("template", { status: "pending", page_size: 1 }),
        fetchAPIData("template", { status: "approved", page_size: 1 }),
        fetchAPIData("template", { status: "rejected", page_size: 1 }),
      ]);
      return {
        pending: pending.total,
        approved: approved.total,
        rejected: rejected.total,
      };
    },
    { revalidateOnFocus: false }
  );

  const handleRefresh = async () => {
    await Promise.all([mutate(), mutateStats()]);
  };

  const templates = data?.items || [];
  const totalItems = data?.total || 0;
  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);

  const handleDelete = async (id: string) => {
    try {
      await deleteAPIData("template", id);
      mutate(); // Refresh list
    } catch (error) {
      console.error("Failed to delete template", error);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="flex h-20 items-center justify-between px-6 md:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Template Status
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Monitor and manage all your campaign templates and their approval
              status.
            </p>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 p-6 md:p-8 space-y-6">
        {/* KPI Cards Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Pending Approval
                  </p>
                  <p className="text-3xl font-bold mt-2">
                    {stats?.pending ?? "-"}
                  </p>
                </div>
                <div className="rounded-full bg-yellow-100 dark:bg-yellow-900/20 p-3">
                  <Clock className="h-6 w-6 text-yellow-600 dark:text-yellow-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Approved
                  </p>
                  <p className="text-3xl font-bold mt-2">
                    {stats?.approved ?? "-"}
                  </p>
                </div>
                <div className="rounded-full bg-green-100 dark:bg-green-900/20 p-3">
                  <CheckCircle2 className="h-6 w-6 text-green-600 dark:text-green-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Rejected
                  </p>
                  <p className="text-3xl font-bold mt-2">
                    {stats?.rejected ?? "-"}
                  </p>
                </div>
                <div className="rounded-full bg-red-100 dark:bg-red-900/20 p-3">
                  <XCircle className="h-6 w-6 text-red-600 dark:text-red-500" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Total Templates
                  </p>
                  <p className="text-3xl font-bold mt-2">
                    {!stats
                      ? data?.total ?? "-"
                      : stats.pending + stats.approved + stats.rejected}
                  </p>
                </div>
                <div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-3">
                  <FileText className="h-6 w-6 text-blue-600 dark:text-blue-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters & Search */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <div className="flex gap-2 w-full md:w-auto">
            <Select value={channelFilter} onValueChange={setChannelFilter}>
              <SelectTrigger className="w-full md:w-[150px]">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                <SelectItem value="WhatsApp">WhatsApp</SelectItem>
                <SelectItem value="Email">Email</SelectItem>
              </SelectContent>
            </Select>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="Pending">Pending</SelectItem>
                <SelectItem value="Approved">Approved</SelectItem>
                <SelectItem value="Rejected">Rejected</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Table Area */}
        <div className="space-y-4">
          <div className="relative min-h-[200px]">
            {isLoading && (
              <div className="absolute inset-0 bg-background/50 z-10 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-primary" />
              </div>
            )}
            <TemplateStatusTable
              templates={templates}
              onDelete={handleDelete}
            />
          </div>

          {/* Pagination Controls */}
          {totalItems > 0 && (
            <div className="flex items-center justify-between px-2">
              <div className="text-sm text-muted-foreground">
                Showing{" "}
                <span className="font-medium">
                  {Math.min((page - 1) * ITEMS_PER_PAGE + 1, totalItems)}
                </span>{" "}
                to{" "}
                <span className="font-medium">
                  {Math.min(page * ITEMS_PER_PAGE, totalItems)}
                </span>{" "}
                of <span className="font-medium">{totalItems}</span> results
              </div>

              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPage(1)}
                  disabled={page === 1 || isLoading}
                >
                  <ChevronsLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1 || isLoading}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>

                <div className="flex items-center gap-1 mx-2">
                  <span className="text-sm font-medium">
                    Page {page} of {totalPages || 1}
                  </span>
                </div>

                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages || isLoading}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPage(totalPages)}
                  disabled={page >= totalPages || isLoading}
                >
                  <ChevronsRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
