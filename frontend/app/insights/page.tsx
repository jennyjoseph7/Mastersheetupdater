"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
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
  ArrowLeft,
  Download,
  Mail,
} from "lucide-react"
import { EngagementFunnel } from "@/components/engagement-funnel"
import { ConversationIntentChart } from "@/components/conversation-intent-chart"
import { CostPerLeadChart } from "@/components/cost-per-lead-chart"
import { CampaignFailureChart } from "@/components/campaign-failure-chart"

// Sample data for leads
const sampleLeads = [
  {
    userId: "USR001",
    name: "John Doe",
    email: "john.doe@example.com",
    contact: "+1234567890",
    lastInteraction: "2024-01-15T14:30:00",
    status: "Converted",
    disposition: "Converted",
    duration: "15 min 30 sec",
    queries: 8,
    unanswered: 1,
    sentiment: "Positive",
    intents: ["Product Inquiry", "Pricing"],
    escalations: 0,
    channel: "chat",
    chatSummary: {
      sentiment: "Positive",
      keyIntents: ["Product Inquiry", "Pricing", "Family Coverage"],
      outcome: "Converted",
    },
    transcript: [
      { type: "user", message: "Hi, I'm interested in your insurance plans", time: "12:21:04" },
      {
        type: "bot",
        message:
          "Hello! I'd be happy to help you find the right insurance plan. What type of coverage are you looking for?",
        time: "12:21:04",
      },
      { type: "user", message: "I need health insurance for my family", time: "12:21:45" },
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
    lastInteraction: "2024-01-14T10:16:02",
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
    callTranscript: [
      { speaker: "agent", text: "Hello, thank you for calling. How can I help you today?", time: "10:15:02" },
      {
        speaker: "customer",
        text: "Hi, I'm calling about my policy renewal. I wanted to know what options are available.",
        time: "10:15:08",
      },
      {
        speaker: "agent",
        text: "Of course! Let me pull up your account. Can I have your policy number please?",
        time: "10:15:15",
      },
      {
        speaker: "customer",
        text: "Sure, it's POL-2024-5678.",
        time: "10:15:20",
      },
      {
        speaker: "agent",
        text: "Thank you. I can see your policy is up for renewal next month. We have several options available with enhanced coverage.",
        time: "10:15:28",
      },
      {
        speaker: "customer",
        text: "What are the pricing differences between the options?",
        time: "10:15:35",
      },
      {
        speaker: "agent",
        text: "Our basic renewal would be $450 per month, while our premium plan with additional benefits is $620 per month.",
        time: "10:15:42",
      },
      {
        speaker: "customer",
        text: "I see. Can I have some time to think about this?",
        time: "10:15:50",
      },
      {
        speaker: "agent",
        text: "I'll send you a detailed comparison via email. Would next week be a good time for a follow-up call?",
        time: "10:15:55",
      },
      {
        speaker: "customer",
        text: "Yes, that works for me. Thank you!",
        time: "10:16:02",
      },
    ],
  },
  {
    userId: "USR003",
    name: "Mike Johnson",
    email: "mike.johnson@example.com",
    contact: "+1234567892",
    lastInteraction: "2024-01-13T14:32:11",
    status: "Lead",
    disposition: "Read",
    duration: "3 min 12 sec",
    queries: 2,
    unanswered: 0,
    sentiment: "Positive",
    intents: ["Product Inquiry"],
    escalations: 0,
    channel: "chat",
    chatSummary: {
      sentiment: "Positive",
      keyIntents: ["Product Inquiry", "Pricing"],
      outcome: "Follow-up Required",
    },
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
]

// Sample data for campaigns
const sampleCampaigns = [
  {
    id: "CMP001",
    name: "Summer Insurance Promo 2024",
    createdOn: "2024-01-15",
    channels: ["WhatsApp", "Email", "SMS"],
    status: "Live" as const,
  },
  {
    id: "CMP002",
    name: "Health Coverage Campaign",
    createdOn: "2024-01-10",
    channels: ["Email", "Voice"],
    status: "Completed" as const,
  },
  {
    id: "CMP003",
    name: "Auto Insurance Renewal",
    createdOn: "2024-02-01",
    channels: ["WhatsApp", "SMS"],
    status: "Scheduled" as const,
  },
  {
    id: "CMP004",
    name: "Life Insurance Awareness",
    createdOn: "2024-01-20",
    channels: ["Email", "WhatsApp", "Voice"],
    status: "Live" as const,
  },
]

export default function CampaignInsights() {
  const [timeFilter, setTimeFilter] = useState("This Week")
  const [searchQuery, setSearchQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState("All Types")
  const [statusFilter, setStatusFilter] = useState("All Status")
  const [sentimentFilter, setSentimentFilter] = useState("All Sentiments")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc" | null>(null)
  const [selectedLead, setSelectedLead] = useState<(typeof sampleLeads)[0] | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [transcriptSearch, setTranscriptSearch] = useState("")
  const [selectedCampaign, setSelectedCampaign] = useState<(typeof sampleCampaigns)[0] | null>(null)

  const filteredCampaigns = sampleCampaigns.filter(
    (campaign) => campaign.status === "Live" || campaign.status === "Completed",
  )

  const filteredLeads = sampleLeads
    .filter((lead) => {
      const matchesSearch =
        lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.userId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lead.email.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesType = typeFilter === "All Types" || lead.channel === typeFilter.toLowerCase()
      const matchesStatus = statusFilter === "All Status" || lead.status === statusFilter
      const matchesSentiment = sentimentFilter === "All Sentiments" || lead.sentiment === sentimentFilter
      return matchesSearch && matchesType && matchesStatus && matchesSentiment
    })
    .sort((a, b) => {
      if (!sortOrder) return 0
      const dateA = new Date(a.lastInteraction).getTime()
      const dateB = new Date(b.lastInteraction).getTime()
      return sortOrder === "asc" ? dateA - dateB : dateB - dateA
    })

  const toggleSort = () => {
    setSortOrder((current) => {
      if (current === null) return "desc"
      if (current === "desc") return "asc"
      return null
    })
  }

  const formatLastInteraction = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 60) {
      return `${diffMins} min${diffMins !== 1 ? "s" : ""} ago`
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`
    } else {
      return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      Converted: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Qualified: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Lead: "bg-amber-100 text-amber-700 hover:bg-amber-100",
      Losing: "bg-orange-100 text-orange-700 hover:bg-orange-100",
      Lost: "bg-red-100 text-red-700 hover:bg-red-100",
    }
    return <Badge className={colors[status] || ""}>{status}</Badge>
  }

  const getSentimentBadge = (sentiment: string) => {
    const colors: Record<string, string> = {
      Positive: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Neutral: "bg-gray-100 text-gray-700 hover:bg-gray-100",
      Negative: "bg-red-100 text-red-700 hover:bg-red-100",
    }
    return <Badge className={colors[sentiment] || ""}>{sentiment}</Badge>
  }

  const getCampaignStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      Live: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Scheduled: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Completed: "bg-gray-100 text-gray-700 hover:bg-gray-100",
    }
    return <Badge className={colors[status] || ""}>{status}</Badge>
  }

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case "WhatsApp":
        return <MessageSquare className="h-3 w-3" />
      case "Email":
        return <Mail className="h-3 w-3" />
      case "Voice":
        return <Phone className="h-3 w-3" />
      case "SMS":
        return <MessageSquare className="h-3 w-3" />
      default:
        return null
    }
  }

  const handleDownloadLeads = (format: "csv" | "pdf") => {
    // Placeholder for download functionality
    console.log(`Downloading leads as ${format}`)
  }

  const openHistory = (lead: (typeof sampleLeads)[0]) => {
    setSelectedLead(lead)
    setHistoryOpen(true)
    setTranscriptSearch("")
  }

  if (selectedCampaign) {
    return (
      <div className="flex min-h-screen flex-col w-full">
        {/* Campaign Detail Header */}
        <div className="border-b bg-background/95 backdrop-blur mb-8">
          <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" onClick={() => setSelectedCampaign(null)} className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
              <div className="h-8 w-px bg-border" />
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-semibold tracking-tight">{selectedCampaign.name}</h1>
                {getCampaignStatusBadge(selectedCampaign.status)}
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
          {/* Tabs for Statistics and Audience */}
          <Tabs defaultValue="statistics" className="w-full">
            <TabsList>
              <TabsTrigger value="statistics">Statistics</TabsTrigger>
              <TabsTrigger value="audience">Audience / Campaign Leads</TabsTrigger>
            </TabsList>

            {/* Statistics Tab */}
            <TabsContent value="statistics" className="space-y-6 mt-6">
              <div className="space-y-6">
                <h2 className="text-xl font-semibold">Campaign Performance Statistics</h2>

                {/* Engagement Funnel */}
                <Card className="shadow">
                  <CardHeader>
                    <CardTitle>Engagement Funnel</CardTitle>
                    <CardDescription>Track user journey from initial contact to conversion</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <EngagementFunnel />
                  </CardContent>
                </Card>

                {/* Failure Reasons Bar Graph */}
                <Card className="shadow">
                  <CardHeader>
                    <CardTitle>Failure Reasons by Channel</CardTitle>
                    <CardDescription>Distribution of delivery failures across channels</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <CampaignFailureChart />
                  </CardContent>
                </Card>

                {/* Analytics Charts */}
                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <Card className="shadow">
                    <CardHeader>
                      <CardTitle>Cost per Lead by Channel</CardTitle>
                      <CardDescription>Average cost to acquire a lead per channel</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <CostPerLeadChart />
                    </CardContent>
                  </Card>

                  <Card className="shadow">
                    <CardHeader>
                      <CardTitle>Intent Distribution by Channel</CardTitle>
                      <CardDescription>Distribution of conversation intents across channels</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <ConversationIntentChart />
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>

            {/* Audience / Campaign Leads Tab */}
            <TabsContent value="audience" className="space-y-6 mt-6">
              <Card className="shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Campaign Leads / Audience</CardTitle>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="outline" className="gap-2 bg-transparent">
                          <Download className="h-4 w-4" />
                          Download
                          <ChevronDown className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleDownloadLeads("csv")}>Download as CSV</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDownloadLeads("pdf")}>Download as PDF</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                  {/* Search and Filters */}
                  <div className="flex flex-col gap-4 mt-4">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        placeholder="Search by name or email..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9"
                      />
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="gap-2 bg-transparent">
                            {timeFilter}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => setTimeFilter("This Week")}>This Week</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setTimeFilter("Last Week")}>Last Week</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setTimeFilter("This Month")}>This Month</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="gap-2 bg-transparent">
                            {typeFilter}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Filter by Type</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => setTypeFilter("All Types")}>All Types</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setTypeFilter("Chat")}>Chat</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setTypeFilter("Voice")}>Voice</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="gap-2 bg-transparent">
                            {statusFilter}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Filter by Status</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => setStatusFilter("All Status")}>All Status</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setStatusFilter("Lead")}>Lead</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setStatusFilter("Qualified")}>Qualified</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setStatusFilter("Converted")}>Converted</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" className="gap-2 bg-transparent">
                            {sentimentFilter}
                            <ChevronDown className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Filter by Sentiment</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => setSentimentFilter("All Sentiments")}>
                            All Sentiments
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSentimentFilter("Positive")}>Positive</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSentimentFilter("Neutral")}>Neutral</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSentimentFilter("Negative")}>Negative</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>User ID</TableHead>
                          <TableHead>Lead Name</TableHead>
                          <TableHead>Email</TableHead>
                          <TableHead>Contact</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Disposition</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead>Queries</TableHead>
                          <TableHead>Unanswered</TableHead>
                          <TableHead>Sentiment</TableHead>
                          <TableHead>Intents</TableHead>
                          <TableHead>Escalations</TableHead>
                          <TableHead>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={toggleSort}
                              className="h-8 px-2 hover:bg-transparent"
                            >
                              Last Interaction
                              {sortOrder === "desc" && <span className="ml-1">↓</span>}
                              {sortOrder === "asc" && <span className="ml-1">↑</span>}
                            </Button>
                          </TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredLeads.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={14} className="text-center text-muted-foreground">
                              No leads found
                            </TableCell>
                          </TableRow>
                        ) : (
                          filteredLeads.map((lead) => (
                            <TableRow key={lead.userId}>
                              <TableCell className="font-medium">{lead.userId}</TableCell>
                              <TableCell>{lead.name}</TableCell>
                              <TableCell>{lead.email}</TableCell>
                              <TableCell>{lead.contact}</TableCell>
                              <TableCell>{getStatusBadge(lead.status)}</TableCell>
                              <TableCell>{lead.disposition}</TableCell>
                              <TableCell>{lead.duration}</TableCell>
                              <TableCell>{lead.queries}</TableCell>
                              <TableCell>{lead.unanswered}</TableCell>
                              <TableCell>{getSentimentBadge(lead.sentiment)}</TableCell>
                              <TableCell>
                                <div className="flex flex-col gap-1">
                                  {lead.intents.map((intent, idx) => (
                                    <span key={idx} className="text-xs">
                                      {intent}
                                    </span>
                                  ))}
                                </div>
                              </TableCell>
                              <TableCell>{lead.escalations}</TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {formatLastInteraction(lead.lastInteraction)}
                              </TableCell>
                              <TableCell className="text-right">
                                <Button variant="ghost" size="sm" onClick={() => openHistory(lead)}>
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
            </TabsContent>
          </Tabs>
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
                    <p className="text-sm font-medium text-muted-foreground">User ID</p>
                    <p className="text-sm font-semibold">{selectedLead.userId}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Status</p>
                    <div className="mt-1">{getStatusBadge(selectedLead.status)}</div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Duration</p>
                    <p className="text-sm font-semibold">{selectedLead.duration}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Sentiment</p>
                    <div className="mt-1">{getSentimentBadge(selectedLead.sentiment)}</div>
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
                      <div key={idx} className={`flex ${message.type === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[80%] rounded-lg p-3 ${
                            message.type === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                          }`}
                        >
                          <p className="text-sm">{message.message}</p>
                          <p className="text-xs mt-1 opacity-70">{message.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <h3 className="font-semibold">Call Transcript Summary</h3>
                    <div className="p-4 bg-muted/50 rounded-lg">
                      <p className="text-sm leading-relaxed">{selectedLead.callSummary}</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col w-full">
      {/* Header Section */}
      <div className="border-b bg-background/95 backdrop-blur mb-8">
        <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Campaign Insights</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Track campaign performance, engagement metrics, and lead conversion across all channels
            </p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2 bg-transparent">
                Filter
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setTimeFilter("This Week")}>This Week</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTimeFilter("Last Week")}>Last Week</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTimeFilter("This Month")}>This Month</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTimeFilter("Last Month")}>Last Month</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTimeFilter("This Year")}>This Year</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="flex-1 space-y-6 px-4 md:px-6 lg:px-8 pb-6 w-full">
        {/* Top KPI Cards */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
          <Card className="shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Reach</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">30,000</div>
              <p className="text-xs text-emerald-600 mt-1">+12% from last period</p>
            </CardContent>
          </Card>

          <Card className="shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">% Engaged</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">62%</div>
              <p className="text-xs text-emerald-600 mt-1">+5% from last period</p>
            </CardContent>
          </Card>

          <Card className="shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">% Converted</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">9%</div>
              <p className="text-xs text-emerald-600 mt-1">+2% from last period</p>
            </CardContent>
          </Card>

          <Card className="shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Failed Delivery</CardTitle>
              <AlertCircle className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">3,800</div>
              <p className="text-xs text-red-600 mt-1">-3% from last period</p>
            </CardContent>
          </Card>

          <Card className="shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Nudged / Retargeted</CardTitle>
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">7,100</div>
              <p className="text-xs text-emerald-600 mt-1">+8% from last period</p>
            </CardContent>
          </Card>
        </div>

        {/* Campaigns Overview Section */}
        <Card className="shadow">
          <CardHeader>
            <CardTitle>Campaigns Overview</CardTitle>
            <CardDescription>View and manage all your campaigns</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Campaign Name</TableHead>
                    <TableHead>Created On</TableHead>
                    <TableHead>Channels Used</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCampaigns.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell className="font-medium">{campaign.name}</TableCell>
                      <TableCell>{new Date(campaign.createdOn).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <div className="flex gap-2">
                          {campaign.channels.map((channel) => (
                            <Badge key={channel} variant="outline" className="gap-1">
                              {getChannelIcon(channel)}
                              {channel}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>{getCampaignStatusBadge(campaign.status)}</TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedCampaign(campaign)}
                          className="gap-2"
                        >
                          <Eye className="h-4 w-4" />
                          View
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
