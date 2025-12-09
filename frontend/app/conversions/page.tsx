"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Download, Search, Eye } from "lucide-react"
import { LeadJourneyModal } from "@/components/lead-journey-modal"

// Sample converted leads data
const sampleConvertedLeads = [
  {
    userId: "USR001",
    name: "John Doe",
    email: "john.doe@example.com",
    contact: "+1234567890",
    campaignName: "Summer Insurance Promo 2024",
    campaignStatus: "Live",
    channel: "WhatsApp",
    convertedDate: "2024-01-17",
  },
  {
    userId: "USR004",
    name: "Sarah Williams",
    email: "sarah.williams@example.com",
    contact: "+1234567893",
    campaignName: "Health Coverage Campaign",
    campaignStatus: "Completed",
    channel: "Email",
    convertedDate: "2024-01-16",
  },
  {
    userId: "USR007",
    name: "Michael Brown",
    email: "michael.brown@example.com",
    contact: "+1234567896",
    campaignName: "Auto Insurance Renewal",
    campaignStatus: "Live",
    channel: "Voice",
    convertedDate: "2024-01-18",
  },
  {
    userId: "USR010",
    name: "Emily Davis",
    email: "emily.davis@example.com",
    contact: "+1234567899",
    campaignName: "Life Insurance Awareness",
    campaignStatus: "Live",
    channel: "SMS",
    convertedDate: "2024-01-19",
  },
  {
    userId: "USR013",
    name: "David Wilson",
    email: "david.wilson@example.com",
    contact: "+1234567902",
    campaignName: "Summer Insurance Promo 2024",
    campaignStatus: "Live",
    channel: "WhatsApp",
    convertedDate: "2024-01-20",
  },
]

// Sample campaigns for filter
const campaigns = [
  "All Campaigns",
  "Summer Insurance Promo 2024",
  "Health Coverage Campaign",
  "Auto Insurance Renewal",
  "Life Insurance Awareness",
]

export default function ConversionsPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCampaign, setSelectedCampaign] = useState("All Campaigns")
  const [selectedChannel, setSelectedChannel] = useState("All Channels")
  const [selectedLead, setSelectedLead] = useState<(typeof sampleConvertedLeads)[0] | null>(null)
  const [journeyModalOpen, setJourneyModalOpen] = useState(false)

  const filteredLeads = sampleConvertedLeads.filter((lead) => {
    const matchesSearch =
      lead.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      lead.userId.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCampaign = selectedCampaign === "All Campaigns" || lead.campaignName === selectedCampaign
    const matchesChannel = selectedChannel === "All Channels" || lead.channel === selectedChannel
    return matchesSearch && matchesCampaign && matchesChannel
  })

  const handleDownloadCSV = () => {
    console.log("Downloading CSV...")
    // Placeholder for CSV download functionality
  }

  const handleViewJourney = (lead: (typeof sampleConvertedLeads)[0]) => {
    setSelectedLead(lead)
    setJourneyModalOpen(true)
  }

  const getCampaignStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      Live: "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
      Scheduled: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Completed: "bg-gray-100 text-gray-700 hover:bg-gray-100",
    }
    return <Badge className={colors[status] || ""}>{status}</Badge>
  }

  const getChannelBadge = (channel: string) => {
    const colors: Record<string, string> = {
      WhatsApp: "bg-green-100 text-green-700 hover:bg-green-100",
      Email: "bg-blue-100 text-blue-700 hover:bg-blue-100",
      Voice: "bg-purple-100 text-purple-700 hover:bg-purple-100",
      SMS: "bg-orange-100 text-orange-700 hover:bg-orange-100",
    }
    return <Badge className={colors[channel] || ""}>{channel}</Badge>
  }

  return (
    <div className="flex min-h-screen flex-col w-full">
      {/* Header Section */}
      <div className="border-b bg-background/95 backdrop-blur mb-8">
        <div className="flex h-20 items-center justify-between px-4 md:px-6 lg:px-8 w-full">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Conversions</h1>
            <p className="text-sm text-muted-foreground mt-1">Track all the lead conversion across all channels</p>
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
              <Select value={selectedCampaign} onValueChange={setSelectedCampaign}>
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
              <Select value={selectedChannel} onValueChange={setSelectedChannel}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select channel" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="All Channels">All Channels</SelectItem>
                  <SelectItem value="Voice">Voice</SelectItem>
                  <SelectItem value="WhatsApp">WhatsApp</SelectItem>
                  <SelectItem value="Email">Email</SelectItem>
                  <SelectItem value="SMS">SMS</SelectItem>
                </SelectContent>
              </Select>
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
                      <TableCell colSpan={8} className="text-center text-muted-foreground">
                        No converted leads found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredLeads.map((lead) => (
                      <TableRow key={lead.userId}>
                        <TableCell className="font-medium">{lead.userId}</TableCell>
                        <TableCell>{lead.name}</TableCell>
                        <TableCell>{lead.email}</TableCell>
                        <TableCell>{lead.contact}</TableCell>
                        <TableCell>{lead.campaignName}</TableCell>
                        <TableCell>{getCampaignStatusBadge(lead.campaignStatus)}</TableCell>
                        <TableCell>{getChannelBadge(lead.channel)}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" onClick={() => handleViewJourney(lead)} className="gap-2">
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
          </CardContent>
        </Card>
      </div>

      {/* Lead Journey Modal */}
      <LeadJourneyModal open={journeyModalOpen} onOpenChange={setJourneyModalOpen} lead={selectedLead} />
    </div>
  )
}
