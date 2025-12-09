"use client";
import { useState, useMemo, useEffect } from "react";
import useSWR from "swr";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { Search, FileText, CheckCircle2, XCircle, Clock } from "lucide-react";

import { TemplateStatusTable } from "@/components/template/template-status-table";

import { fetchAPIData, capitalize } from "@/utils/api";

const swrOptions = {
  revalidateOnFocus: false,
  revalidateIfStale: false,
  revalidateOnReconnect: false,
  errorRetryCount: 0,
  shouldRetryOnError: false,
};

export interface Template {
  template_id: string;
  template_name: string;
  language: string;
  channel: "WhatsApp" | "Email";
  campaignName: string;
  provider_name:string;
  status: "Pending" | "Approved" | "Rejected";
  updated: string;
  rejectionReason?: string;
}

const ITEMS_PER_PAGE = 20;

export default function TemplatePage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [page, setPage] = useState(1);

  const [searchQuery, setSearchQuery] = useState("");
  const [channelFilter, setChannelFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Fetch templates from API
  const { data, error, isLoading } = useSWR(
    ["templates-api", page],
    async () => {
      const params = {
        page_number: page,
        page_size: ITEMS_PER_PAGE
      };

      const apiResponse = await fetchAPIData("template",params);
      return apiResponse?.items ?? [];
    },
    swrOptions
  );

  // Update component templates when API returns data
  useEffect(() => {
    if (data) {
      setTemplates(data);
    }
  }, [data]);

  // Calculate KPI metrics
  const metrics = useMemo(() => {
    return {
      pending: templates.filter((t) => t.status[0].includes("Pending")).length,
      approved: templates.filter((t) => t.status[0].includes("Approved")).length,
      rejected: templates.filter((t) => t.status[0].includes("Rejected")).length,
      total: templates.length,
    };
  }, [templates]);

  console.log("Metrics:", metrics);
  

  // Apply search + filters
  const filteredTemplates = useMemo(() => {
    return templates.filter((template) => {
      const matchesSearch =
        searchQuery === "" ||
        template.template_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.template_id.toLowerCase().includes(searchQuery.toLowerCase()) 
        // template.campaignName.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesChannel =
        channelFilter === "all" || template.channel === channelFilter;
      const matchesStatus =
        statusFilter === "all" || capitalize(template.status[0]) === statusFilter;

      return matchesSearch && matchesChannel && matchesStatus;
    });
  }, [templates, searchQuery, channelFilter, statusFilter]);

  // Delete handler
  const handleDelete = (id: string) => {
    setTemplates(templates.filter((t) => t.template_id !== id));
  };

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <div>
        <div className="flex h-20 items-center px-6 md:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Template Status
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Monitor and manage all your campaign templates and their approval
              status.
            </p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 p-6 md:p-8 space-y-6">
        {/* KPI Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Pending Approval
                  </p>
                  <p className="text-3xl font-bold mt-2">{metrics.pending}</p>
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
                  <p className="text-3xl font-bold mt-2">{metrics.approved}</p>
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
                  <p className="text-3xl font-bold mt-2">{metrics.rejected}</p>
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
                  <p className="text-3xl font-bold mt-2">{metrics.total}</p>
                </div>
                <div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-3">
                  <FileText className="h-6 w-6 text-blue-600 dark:text-blue-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search + Filters */}
        <Card>
          <CardContent>
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              {/* Search */}
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by template name or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Filters */}
              <div className="flex gap-2">
                <Select value={channelFilter} onValueChange={setChannelFilter}>
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="Channel" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Channels</SelectItem>
                    <SelectItem value="WhatsApp">WhatsApp</SelectItem>
                    <SelectItem value="Email">Email</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[140px]">
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
          </CardContent>
        </Card>

        {/* Table */}
        <TemplateStatusTable
          templates={filteredTemplates}
          onDelete={handleDelete}
        />

        {/* Pagination Buttons */}
        <div className="flex justify-end gap-3 mt-4">
          <button
            className="px-4 py-2 border rounded disabled:opacity-40"
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </button>

          <button
            className="px-4 py-2 border rounded"
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      </main>
    </div>
  );
}
