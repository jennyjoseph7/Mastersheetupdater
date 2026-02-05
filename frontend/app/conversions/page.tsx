"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Download, Search, Eye, Loader2 } from "lucide-react";
import { LeadJourneyModal } from "@/components/lead-journey-modal";
import {
  getServiceVisitsForDealership,
  getShowroomVisitsForDealership,
  type ServiceVisit,
  type ShowroomVisit,
} from "@/lib/api";
import type { ConversionLead } from "@/types/conversion";

interface ConversionLeadExtended extends ConversionLead {
  visitType: "Service" | "Showroom";
  originalData: ServiceVisit | ShowroomVisit;
}

// Transform service visit to ConversionLead
function transformServiceVisit(visit: ServiceVisit): ConversionLeadExtended {
  const purposeOfVisit = Array.isArray(visit.purpose_of_visit)
    ? visit.purpose_of_visit.join(", ")
    : visit.purpose_of_visit || "Service Visit";

  return {
    userId: visit.user_id || visit.service_visit_id || "N/A",
    leadName: visit.person_name || "Unknown",
    email: visit.email || "N/A",
    contactNumber: visit.phone_number || "N/A",
    campaignName: purposeOfVisit,
    campaignStatus:
      visit.status === "completed"
        ? "Completed"
        : visit.status === "cancelled"
        ? "Paused"
        : "Live",
    channelType: "Service",
    conversionDate:
      visit.appointment_date || new Date().toISOString().split("T")[0],
    visitType: "Service",
    originalData: visit,
  };
}

// Transform showroom visit to ConversionLead
function transformShowroomVisit(visit: ShowroomVisit): ConversionLeadExtended {
  const purposeOfVisit = Array.isArray(visit.purpose_of_visit)
    ? visit.purpose_of_visit.join(", ")
    : visit.purpose_of_visit || "Showroom Visit";

  const status = visit.showroom_visit_status || "Open";
  let campaignStatus: "Live" | "Completed" | "Paused" = "Live";
  if (status === "Closed") campaignStatus = "Completed";
  else if (status === "Follow-Up") campaignStatus = "Live";

  return {
    userId: visit.user_id || visit.showroom_visit_id || "N/A",
    leadName: visit.person_name || "Unknown",
    email: visit.email || "N/A",
    contactNumber: visit.phone_number || "N/A",
    campaignName: purposeOfVisit,
    campaignStatus,
    channelType: "Showroom",
    conversionDate: visit.visit_date || new Date().toISOString().split("T")[0],
    visitType: "Showroom",
    originalData: visit,
  };
}

export default function ConversionsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCampaign, setSelectedCampaign] = useState("All Campaigns");
  const [selectedChannel, setSelectedChannel] = useState("All Channels");
  const [selectedLead, setSelectedLead] =
    useState<ConversionLeadExtended | null>(null);
  const [journeyModalOpen, setJourneyModalOpen] = useState(false);
  const [conversions, setConversions] = useState<ConversionLeadExtended[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch conversions data on mount
  useEffect(() => {
    async function fetchConversions() {
      try {
        setLoading(true);
        setError(null);

        // Get dealership_id from localStorage
        const dealershipId = localStorage.getItem("dealership_id");
        if (!dealershipId) {
          throw new Error("Dealership ID not found. Please login again.");
        }

        // Fetch both service visits and showroom visits
        const [serviceVisits, showroomVisits] = await Promise.all([
          getServiceVisitsForDealership(dealershipId),
          getShowroomVisitsForDealership(dealershipId),
        ]);

        // Transform and combine the data
        const serviceConversions = serviceVisits.map(transformServiceVisit);
        const showroomConversions = showroomVisits.map(transformShowroomVisit);
        const allConversions = [...serviceConversions, ...showroomConversions];

        // Sort by conversion date (most recent first)
        allConversions.sort((a, b) => {
          const dateA = new Date(a.conversionDate).getTime();
          const dateB = new Date(b.conversionDate).getTime();
          return dateB - dateA;
        });

        setConversions(allConversions);
      } catch (err) {
        console.error("Error fetching conversions:", err);
        setError(
          err instanceof Error ? err.message : "Failed to fetch conversions"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchConversions();
  }, []);

  // Get unique campaigns and channels for filters
  const campaigns = useMemo(() => {
    const uniqueCampaigns = Array.from(
      new Set(conversions.map((c) => c.campaignName))
    ).sort();
    return ["All Campaigns", ...uniqueCampaigns];
  }, [conversions]);

  const channels = useMemo(() => {
    const uniqueChannels = Array.from(
      new Set(conversions.map((c) => c.channelType))
    ).sort();
    return ["All Channels", ...uniqueChannels];
  }, [conversions]);

  const filteredLeads = useMemo(() => {
    return conversions.filter((lead) => {
      const matchesSearch =
        lead.leadName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.userId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.contactNumber.includes(searchQuery);
      const matchesCampaign =
        selectedCampaign === "All Campaigns" ||
        lead.campaignName === selectedCampaign;
      const matchesChannel =
        selectedChannel === "All Channels" ||
        lead.channelType === selectedChannel;
      return matchesSearch && matchesCampaign && matchesChannel;
    });
  }, [conversions, searchQuery, selectedCampaign, selectedChannel]);

  const handleDownloadCSV = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "User ID,Lead Name,Email,Contact Number,Campaign Name,Campaign Status,Channel Type,Conversion Date\n" +
      filteredLeads
        .map(
          (lead) =>
            `${lead.userId},${lead.leadName},${lead.email},${lead.contactNumber},${lead.campaignName},${lead.campaignStatus},${lead.channelType},${lead.conversionDate}`
        )
        .join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "conversions.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleViewJourney = (lead: ConversionLeadExtended) => {
    // Transform to match LeadJourneyModal's expected format
    setSelectedLead({
      ...lead,
      name: lead.leadName,
      contact: lead.contactNumber,
      channel: lead.channelType,
    } as any);
    setJourneyModalOpen(true);
  };

  const getCampaignStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      Live: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Scheduled: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Completed: "bg-gray-100 text-gray-700 hover:bg-gray-100",
    };
    return <Badge className={colors[status] || ""}>{status}</Badge>;
  };

  const getChannelBadge = (channel: string) => {
    const colors: Record<string, string> = {
      WhatsApp: "bg-green-100 text-green-700 hover:bg-green-100",
      Email: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Voice: "bg-purple-100 text-purple-700 hover:bg-purple-100",
      SMS: "bg-orange-100 text-orange-700 hover:bg-orange-100",
      Service: "bg-indigo-100 text-indigo-700 hover:bg-indigo-100",
      Showroom: "bg-teal-100 text-teal-700 hover:bg-teal-100",
    };
    return (
      <Badge
        className={
          colors[channel] || "bg-gray-100 text-gray-700 hover:bg-gray-100"
        }
      >
        {channel}
      </Badge>
    );
  };

  return (
    <div className="flex min-h-screen flex-col w-full">
      {/* Header Section */}
      <div className="border-b bg-background/95 backdrop-blur mb-8">
        <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Conversions
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Track all the lead conversion across all channels
            </p>
          </div>
          <Button onClick={handleDownloadCSV} className="gap-2">
            <Download className="h-4 w-4" />
            Download CSV
          </Button>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
        {/* Converted Leads Table */}
        <Card className="shadow">
          <CardHeader>
            <CardTitle>Converted Leads</CardTitle>
            {/* Filters */}
            <div className="flex gap-4 flex-wrap items-center mt-4">
              {/* Search Bar */}
              <div className="relative flex-1 min-w-[280px] max-w-md">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by name, email, or user ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Campaign Name Filter */}
              <Select
                value={selectedCampaign}
                onValueChange={setSelectedCampaign}
              >
                <SelectTrigger className="w-[280px]">
                  <SelectValue placeholder="Select campaign" />
                </SelectTrigger>
                <SelectContent>
                  {campaigns.map((campaign) => (
                    <SelectItem key={campaign} value={campaign}>
                      {campaign}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Channel Type Filter */}
              <Select
                value={selectedChannel}
                onValueChange={setSelectedChannel}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select channel" />
                </SelectTrigger>
                <SelectContent>
                  {channels.map((channel) => (
                    <SelectItem key={channel} value={channel}>
                      {channel}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">
                  Loading conversions...
                </span>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <p className="text-destructive mb-2">{error}</p>
                  <Button
                    variant="outline"
                    onClick={() => {
                      const dealershipId =
                        localStorage.getItem("dealership_id");
                      if (dealershipId) {
                        window.location.reload();
                      }
                    }}
                  >
                    Retry
                  </Button>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User ID</TableHead>
                      <TableHead>Lead Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Contact Number</TableHead>
                      <TableHead>Campaign Name</TableHead>
                      <TableHead>Campaign Status</TableHead>
                      <TableHead>Channel Type</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredLeads.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={8}
                          className="text-center text-muted-foreground py-12"
                        >
                          No converted leads found
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredLeads.map((lead) => (
                        <TableRow key={`${lead.visitType}-${lead.userId}`}>
                          <TableCell className="font-medium">
                            {lead.userId}
                          </TableCell>
                          <TableCell>{lead.leadName}</TableCell>
                          <TableCell>{lead.email}</TableCell>
                          <TableCell>{lead.contactNumber}</TableCell>
                          <TableCell>{lead.campaignName}</TableCell>
                          <TableCell>
                            {getCampaignStatusBadge(lead.campaignStatus)}
                          </TableCell>
                          <TableCell>
                            {getChannelBadge(lead.channelType)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewJourney(lead)}
                              className="gap-2"
                            >
                              <Eye className="h-4 w-4" />
                              View History
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Lead Journey Modal */}
      <LeadJourneyModal
        open={journeyModalOpen}
        onOpenChange={setJourneyModalOpen}
        lead={
          selectedLead
            ? {
                userId: selectedLead.userId,
                name: selectedLead.leadName,
                email: selectedLead.email,
                contact: selectedLead.contactNumber,
                campaignName: selectedLead.campaignName,
                channel: selectedLead.channelType,
              }
            : null
        }
      />
    </div>
  );
}
