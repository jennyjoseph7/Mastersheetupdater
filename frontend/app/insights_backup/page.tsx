"use client";

import { useState } from "react";
import Link from "next/link";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Search,
  Users,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  MessageSquare,
  Phone,
  ChevronDown,
  Eye,
  Download,
} from "lucide-react";
import { EngagementFunnel } from "@/components/engagement-funnel";
import { SentimentAnalysis } from "@/components/sentiment-analysis";
import { ConversationIntentChart } from "@/components/conversation-intent-chart";
import { CostPerLeadChart } from "@/components/cost-per-lead-chart";
import { campaignConversions } from "@/lib/campaign-insights-data";

// Sample data for leads
const sampleLeads = [
  {
    userId: "USR001",
    name: "John Doe",
    email: "john.doe@example.com",
    contact: "+1234567890",
    status: "Converted",
    disposition: "Converted",
    duration: "15 min 30 sec",
    queries: 8,
    unanswered: 1,
    sentiment: "Positive",
    intents: ["Product Inquiry", "Pricing"],
    escalations: 0,
    channel: "chat",
    transcript: [
      {
        type: "user",
        message: "Hi, I'm interested in your insurance plans",
        time: "12:21:04",
      },
      {
        type: "bot",
        message:
          "Hello! I'd be happy to help you find the right insurance plan. What type of coverage are you looking for?",
        time: "12:21:04",
      },
      {
        type: "user",
        message: "I need health insurance for my family",
        time: "12:21:45",
      },
      {
        type: "bot",
        message:
          "Great! We have several family health insurance plans. How many family members would you like to cover?",
        time: "12:21:46",
      },
    ],
  },
  {
    userId: "USR002",
    name: "Jane Smith",
    email: "jane.smith@example.com",
    contact: "+1234567891",
    status: "Qualified",
    disposition: "Interacted",
    duration: "8 min 18 sec",
    queries: 5,
    unanswered: 2,
    sentiment: "Neutral",
    intents: ["Support Request"],
    escalations: 1,
    channel: "voice",
    callSummary:
      "Customer called regarding policy renewal. Discussed various options and pricing. Customer requested time to think about the decision. Follow-up scheduled for next week.",
  },
  {
    userId: "USR003",
    name: "Mike Johnson",
    email: "mike.johnson@example.com",
    contact: "+1234567892",
    status: "Lead",
    disposition: "Read",
    duration: "3 min 12 sec",
    queries: 2,
    unanswered: 0,
    sentiment: "Positive",
    intents: ["Product Inquiry"],
    escalations: 0,
    channel: "chat",
    transcript: [
      { type: "user", message: "What are your rates?", time: "14:32:10" },
      {
        type: "bot",
        message:
          "Our rates vary based on coverage type and your specific needs. Would you like me to provide a personalized quote?",
        time: "14:32:11",
      },
    ],
  },
];

export default function CampaignInsights() {
  const [timeFilter, setTimeFilter] = useState("This Week");
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("All Types");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [sentimentFilter, setSentimentFilter] = useState("All Sentiments");
  const [selectedLead, setSelectedLead] = useState<
    (typeof sampleLeads)[0] | null
  >(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [transcriptSearch, setTranscriptSearch] = useState("");

  const filteredLeads = sampleLeads.filter((lead) => {
    const matchesSearch =
      lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.userId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.email.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesType =
      typeFilter === "All Types" || lead.channel === typeFilter.toLowerCase();
    const matchesStatus =
      statusFilter === "All Status" || lead.status === statusFilter;
    const matchesSentiment =
      sentimentFilter === "All Sentiments" ||
      lead.sentiment === sentimentFilter;
    return matchesSearch && matchesType && matchesStatus && matchesSentiment;
  });

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      Converted: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Qualified: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Lead: "bg-amber-100 text-amber-700 hover:bg-amber-100",
      Losing: "bg-orange-100 text-orange-700 hover:bg-orange-100",
      Lost: "bg-red-100 text-red-700 hover:bg-red-100",
    };
    return <Badge className={colors[status] || ""}>{status}</Badge>;
  };

  const getCampaignStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      Live: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Completed: "bg-blue-100 text-blue-700 hover:bg-blue-100",
    };
    return <Badge className={colors[status] || ""}>{status}</Badge>;
  };

  const getSentimentBadge = (sentiment: string) => {
    const colors: Record<string, string> = {
      Positive: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Neutral: "bg-gray-100 text-gray-700 hover:bg-gray-100",
      Negative: "bg-red-100 text-red-700 hover:bg-red-100",
    };
    return <Badge className={colors[sentiment] || ""}>{sentiment}</Badge>;
  };

  const openHistory = (lead: (typeof sampleLeads)[0]) => {
    setSelectedLead(lead);
    setHistoryOpen(true);
    setTranscriptSearch("");
  };

  return (
    <div className="flex min-h-screen flex-col w-full ">
      <div>
        <div className="flex h-16 items-center justify-between px-6 lg:px-8 w-full max-w-[1600px] mx-auto">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Campaign Insights
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Track performance, engagement metrics, and lead conversion
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              className="gap-2 bg-transparent"
            >
              <Download className="h-4 w-4" />
              Export Report
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="gap-2 bg-transparent">
                  {timeFilter}
                  <ChevronDown className="h-4 w-4 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => setTimeFilter("This Week")}>
                  This Week
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTimeFilter("Last Week")}>
                  Last Week
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTimeFilter("This Month")}>
                  This Month
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTimeFilter("Last Month")}>
                  Last Month
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setTimeFilter("This Year")}>
                  This Year
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      <div className="flex-1 space-y-8 px-6 lg:px-8 py-8 w-full max-w-[1600px] mx-auto">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Card className="shadow-md hover:shadow-lg transition-shadow border-l-4 border-l-blue-500">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Reach
              </CardTitle>
              <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-950 flex items-center justify-center">
                <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">30,000</div>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                +12% from last period
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow border-l-4 border-l-emerald-500">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                % Engaged
              </CardTitle>
              <div className="h-10 w-10 rounded-full bg-emerald-100 dark:bg-emerald-950 flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">62%</div>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                +5% from last period
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow border-l-4 border-l-purple-500">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                % Converted
              </CardTitle>
              <div className="h-10 w-10 rounded-full bg-purple-100 dark:bg-purple-950 flex items-center justify-center">
                <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">9%</div>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                +2% from last period
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow border-l-4 border-l-red-500">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Failed Delivery
              </CardTitle>
              <div className="h-10 w-10 rounded-full bg-red-100 dark:bg-red-950 flex items-center justify-center">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">3,800</div>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                -3% from last period
              </p>
            </CardContent>
          </Card>

          <Card className="shadow-md hover:shadow-lg transition-shadow border-l-4 border-l-amber-500">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Nudged / Retargeted
              </CardTitle>
              <div className="h-10 w-10 rounded-full bg-amber-100 dark:bg-amber-950 flex items-center justify-center">
                <RefreshCw className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">7,100</div>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                +8% from last period
              </p>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-lg border-0 bg-card/80">
          <CardHeader className="pb-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-xl">Campaigns Conversions</CardTitle>
                <CardDescription className="mt-1">
                  View and manage all your campaigns
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2 bg-transparent self-start sm:self-auto"
              >
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="font-semibold">
                      Campaign Name
                    </TableHead>
                    <TableHead className="font-semibold">Created On</TableHead>
                    <TableHead className="font-semibold">
                      Channels Used
                    </TableHead>
                    <TableHead className="font-semibold">Status</TableHead>
                    <TableHead className="text-right font-semibold">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {campaignConversions.map((campaign) => (
                    <TableRow
                      key={campaign.slug}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <TableCell className="font-medium">
                        {campaign.name}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {campaign.createdOn}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-2">
                          {campaign.channels.map((channel) => (
                            <Badge
                              key={channel}
                              variant="secondary"
                              className="text-xs"
                            >
                              {channel}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        {getCampaignStatusBadge(campaign.status)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-2"
                          asChild
                        >
                          <Link href={`/campaigns/${campaign.slug}/analytics`}>
                            <Eye className="h-4 w-4" />
                            View Analytics
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl">Engagement Funnel</CardTitle>
                  <CardDescription className="mt-1">
                    Track user journey from initial contact to conversion
                  </CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      {timeFilter}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("This Week")}
                    >
                      This Week
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("Last Week")}
                    >
                      Last Week
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("This Month")}
                    >
                      This Month
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </CardHeader>
            <CardContent>
              <EngagementFunnel />
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-xl">Sentiment Analysis</CardTitle>
                  <CardDescription className="mt-1">
                    Customer sentiment across all interactions
                  </CardDescription>
                </div>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      {timeFilter}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("This Week")}
                    >
                      This Week
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("Last Week")}
                    >
                      Last Week
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("This Month")}
                    >
                      This Month
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </CardHeader>
            <CardContent>
              <SentimentAnalysis />
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">
                Conversation Intent by Channel
              </CardTitle>
              <CardDescription className="mt-1">
                Distribution of conversation intents across channels
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <ConversationIntentChart />
            </CardContent>
          </Card>

          <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/50">
            <CardHeader className="pb-4">
              <CardTitle className="text-xl">
                Cost per Lead by Channel
              </CardTitle>
              <CardDescription className="mt-1">
                Average cost to acquire a lead per channel
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-2">
              <CostPerLeadChart />
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/50">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl">
                  Campaign Leads / Audience
                </CardTitle>
                <CardDescription className="mt-1">
                  Detailed view of all campaign interactions and conversions
                </CardDescription>
              </div>
              <Badge variant="secondary" className="text-sm px-3 py-1">
                {filteredLeads.length} leads
              </Badge>
            </div>
            <div className="flex flex-col gap-3 mt-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by User ID, name, or email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-10"
                />
              </div>
              <div className="flex gap-2 flex-wrap">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      {timeFilter}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("This Week")}
                    >
                      This Week
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("Last Week")}
                    >
                      Last Week
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setTimeFilter("This Month")}
                    >
                      This Month
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      {typeFilter}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setTypeFilter("All Types")}
                    >
                      All Types
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTypeFilter("Chat")}>
                      Chat
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setTypeFilter("Voice")}>
                      Voice
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      {statusFilter}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
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
                    <DropdownMenuItem onClick={() => setStatusFilter("Losing")}>
                      Losing
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatusFilter("Lost")}>
                      Lost
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      {sentimentFilter}
                      <ChevronDown className="h-4 w-4 opacity-50" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    <DropdownMenuLabel>Filter by Sentiment</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setSentimentFilter("All Sentiments")}
                    >
                      All Sentiments
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setSentimentFilter("Positive")}
                    >
                      Positive
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setSentimentFilter("Neutral")}
                    >
                      Neutral
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setSentimentFilter("Negative")}
                    >
                      Negative
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="font-semibold">User ID</TableHead>
                    <TableHead className="font-semibold">Name</TableHead>
                    <TableHead className="font-semibold">Email</TableHead>
                    <TableHead className="font-semibold">Contact</TableHead>
                    <TableHead className="font-semibold">Status</TableHead>
                    <TableHead className="font-semibold">Disposition</TableHead>
                    <TableHead className="font-semibold">Duration</TableHead>
                    <TableHead className="font-semibold">Queries</TableHead>
                    <TableHead className="font-semibold">Unanswered</TableHead>
                    <TableHead className="font-semibold">Sentiment</TableHead>
                    <TableHead className="font-semibold">Intents</TableHead>
                    <TableHead className="font-semibold">Escalations</TableHead>
                    <TableHead className="text-right font-semibold">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLeads.length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={13}
                        className="text-center text-muted-foreground py-8"
                      >
                        No leads found matching your filters
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredLeads.map((lead) => (
                      <TableRow
                        key={lead.userId}
                        className="hover:bg-muted/30 transition-colors"
                      >
                        <TableCell className="font-medium">
                          {lead.userId}
                        </TableCell>
                        <TableCell>{lead.name}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {lead.email}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {lead.contact}
                        </TableCell>
                        <TableCell>{getStatusBadge(lead.status)}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {lead.disposition}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {lead.duration}
                        </TableCell>
                        <TableCell className="text-center">
                          {lead.queries}
                        </TableCell>
                        <TableCell className="text-center">
                          {lead.unanswered}
                        </TableCell>
                        <TableCell>
                          {getSentimentBadge(lead.sentiment)}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            {lead.intents.map((intent, idx) => (
                              <span
                                key={idx}
                                className="text-xs text-muted-foreground"
                              >
                                {intent}
                              </span>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          {lead.escalations}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openHistory(lead)}
                            className="hover:bg-primary/10"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Interaction History Modal */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="max-w-5xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedLead?.channel === "chat" ? (
                <MessageSquare className="h-5 w-5" />
              ) : (
                <Phone className="h-5 w-5" />
              )}
              Interaction History - {selectedLead?.name}
            </DialogTitle>
          </DialogHeader>

          {selectedLead && (
            <div className="space-y-6">
              {/* Header Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-muted/50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    User ID
                  </p>
                  <p className="text-sm font-semibold">{selectedLead.userId}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Status
                  </p>
                  <div className="mt-1">
                    {getStatusBadge(selectedLead.status)}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Duration
                  </p>
                  <p className="text-sm font-semibold">
                    {selectedLead.duration}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    Sentiment
                  </p>
                  <div className="mt-1">
                    {getSentimentBadge(selectedLead.sentiment)}
                  </div>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search within transcript..."
                  value={transcriptSearch}
                  onChange={(e) => setTranscriptSearch(e.target.value)}
                  className="pl-9"
                />
              </div>

              {/* Transcript or Call Summary */}
              {selectedLead.channel === "chat" ? (
                <div className="space-y-4 max-h-96 overflow-y-auto p-4 border rounded-lg">
                  {selectedLead.transcript?.map((message, idx) => (
                    <div
                      key={idx}
                      className={`flex ${
                        message.type === "user"
                          ? "justify-end"
                          : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg p-3 ${
                          message.type === "user"
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted text-foreground"
                        }`}
                      >
                        <p className="text-sm">{message.message}</p>
                        <p className="text-xs mt-1 opacity-70">
                          {message.time}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-4">
                  <h3 className="font-semibold">Call Transcript Summary</h3>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-sm leading-relaxed">
                      {selectedLead.callSummary}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
