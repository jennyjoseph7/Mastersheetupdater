"use client"

import { useState, useMemo } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Search, ChevronUp, ChevronDown, Download, Eye, Mail, Phone, MessageSquare } from "lucide-react"
import type { ConversionLead } from "@/types/conversion"
import { ViewConversionModal } from "./view-conversion-modal"

interface ConversionsDatatableProps {
  data: ConversionLead[]
}

export function ConversionsDatatable({ data }: ConversionsDatatableProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [sortColumn, setSortColumn] = useState<keyof ConversionLead | null>(null)
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc")
  const [campaignFilter, setCampaignFilter] = useState<string>("all")
  const [channelFilter, setChannelFilter] = useState<string>("all")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [currentPage, setCurrentPage] = useState(1)
  const [selectedLead, setSelectedLead] = useState<ConversionLead | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const itemsPerPage = 10

  const campaigns = useMemo(() => Array.from(new Set(data.map((item) => item.campaignName))).sort(), [data])
  const channels = useMemo(() => Array.from(new Set(data.map((item) => item.channelType))).sort(), [data])

  const filteredAndSortedData = useMemo(() => {
    let filtered = data.filter((item) => {
      const matchesSearch =
        item.leadName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.userId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.contactNumber.includes(searchTerm)

      const matchesCampaign = campaignFilter === "all" || item.campaignName === campaignFilter
      const matchesChannel = channelFilter === "all" || item.channelType === channelFilter
      const matchesStatus = statusFilter === "all" || item.campaignStatus === statusFilter

      return matchesSearch && matchesCampaign && matchesChannel && matchesStatus
    })

    if (sortColumn) {
      filtered = filtered.sort((a, b) => {
        const aValue = a[sortColumn]
        const bValue = b[sortColumn]

        if (typeof aValue === "string" && typeof bValue === "string") {
          return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
        }
        if (typeof aValue === "number" && typeof bValue === "number") {
          return sortDirection === "asc" ? aValue - bValue : bValue - aValue
        }
        return 0
      })
    }

    return filtered
  }, [data, searchTerm, sortColumn, sortDirection, campaignFilter, channelFilter, statusFilter])

  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return filteredAndSortedData.slice(startIndex, startIndex + itemsPerPage)
  }, [filteredAndSortedData, currentPage])

  const totalPages = Math.ceil(filteredAndSortedData.length / itemsPerPage)

  const handleSort = (column: keyof ConversionLead) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortColumn(column)
      setSortDirection("asc")
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Live":
        return "bg-emerald-100 text-emerald-800 hover:bg-emerald-100 border-emerald-200"
      case "Completed":
        return "bg-blue-100 text-blue-800 hover:bg-blue-100 border-blue-200"
      case "Paused":
        return "bg-gray-100 text-gray-800 hover:bg-gray-100 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 hover:bg-gray-100 border-gray-200"
    }
  }

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case "WhatsApp":
        return <MessageSquare className="h-4 w-4" />
      case "Email":
        return <Mail className="h-4 w-4" />
      case "Voice":
      case "SMS":
        return <Phone className="h-4 w-4" />
      default:
        return null
    }
  }

  const handleExport = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "User ID,Lead Name,Email,Contact Number,Campaign Name,Campaign Status,Channel Type,Conversion Date\n" +
      filteredAndSortedData
        .map(
          (item) =>
            `${item.userId},${item.leadName},${item.email},${item.contactNumber},${item.campaignName},${item.campaignStatus},${item.channelType},${item.conversionDate}`,
        )
        .join("\n")

    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", "converted-leads.csv")
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleViewConversation = (lead: ConversionLead) => {
    setSelectedLead(lead)
    setIsModalOpen(true)
  }

  return (
    <>
      <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-card/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Converted Leads</CardTitle>
              <CardDescription className="mt-1">
                {filteredAndSortedData.length} lead{filteredAndSortedData.length !== 1 ? "s" : ""} converted across all
                channels
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={handleExport} className="gap-2 bg-transparent">
              <Download className="h-4 w-4" />
              Export CSV
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center mt-6">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name, email, or phone..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 h-10"
              />
            </div>

            <div className="flex gap-2 flex-wrap">
              <Select value={campaignFilter} onValueChange={setCampaignFilter}>
                <SelectTrigger className="w-[180px] h-10">
                  <SelectValue placeholder="All Campaigns" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Campaigns</SelectItem>
                  {campaigns.map((campaign) => (
                    <SelectItem key={campaign} value={campaign}>
                      {campaign}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={channelFilter} onValueChange={setChannelFilter}>
                <SelectTrigger className="w-[160px] h-10">
                  <SelectValue placeholder="All Channels" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Channels</SelectItem>
                  {channels.map((channel) => (
                    <SelectItem key={channel} value={channel}>
                      {channel}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[160px] h-10">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="Live">Live</SelectItem>
                  <SelectItem value="Completed">Completed</SelectItem>
                  <SelectItem value="Paused">Paused</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <div className="rounded-lg border bg-card overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("userId")}>
                    <div className="flex items-center gap-1">
                      User ID
                      {sortColumn === "userId" &&
                        (sortDirection === "asc" ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        ))}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("leadName")}>
                    <div className="flex items-center gap-1">
                      Lead Name
                      {sortColumn === "leadName" &&
                        (sortDirection === "asc" ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        ))}
                    </div>
                  </TableHead>
                  <TableHead className="font-semibold">Email</TableHead>
                  <TableHead className="font-semibold">Contact Number</TableHead>
                  <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("campaignName")}>
                    <div className="flex items-center gap-1">
                      Campaign Name
                      {sortColumn === "campaignName" &&
                        (sortDirection === "asc" ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        ))}
                    </div>
                  </TableHead>
                  <TableHead className="font-semibold">Campaign Status</TableHead>
                  <TableHead className="font-semibold">Channel Type</TableHead>
                  <TableHead className="cursor-pointer font-semibold" onClick={() => handleSort("conversionDate")}>
                    <div className="flex items-center gap-1">
                      Conversion Date
                      {sortColumn === "conversionDate" &&
                        (sortDirection === "asc" ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        ))}
                    </div>
                  </TableHead>
                  <TableHead className="text-center font-semibold">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData.length > 0 ? (
                  paginatedData.map((lead) => (
                    <TableRow key={lead.userId} className="hover:bg-muted/30 transition-colors">
                      <TableCell className="font-medium">{lead.userId}</TableCell>
                      <TableCell className="font-medium">{lead.leadName}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{lead.email}</TableCell>
                      <TableCell className="text-sm">{lead.contactNumber}</TableCell>
                      <TableCell>{lead.campaignName}</TableCell>
                      <TableCell>
                        <Badge className={getStatusBadge(lead.campaignStatus)}>{lead.campaignStatus}</Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getChannelIcon(lead.channelType)}
                          <span>{lead.channelType}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm">{new Date(lead.conversionDate).toLocaleDateString()}</TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:bg-primary/10"
                          onClick={() => handleViewConversation(lead)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={9} className="h-32 text-center text-muted-foreground">
                      No converted leads found matching your criteria.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between space-x-2 py-4">
              <div className="text-sm text-muted-foreground">
                Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                {Math.min(currentPage * itemsPerPage, filteredAndSortedData.length)} of {filteredAndSortedData.length}{" "}
                results
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                >
                  Previous
                </Button>
                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                    let page
                    if (totalPages <= 5) {
                      page = i + 1
                    } else if (currentPage <= 3) {
                      page = i + 1
                    } else if (currentPage >= totalPages - 2) {
                      page = totalPages - 4 + i
                    } else {
                      page = currentPage - 2 + i
                    }
                    return (
                      <Button
                        key={page}
                        variant={currentPage === page ? "default" : "outline"}
                        size="sm"
                        onClick={() => setCurrentPage(page)}
                        className="w-8 h-8 p-0"
                      >
                        {page}
                      </Button>
                    )
                  })}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedLead && (
        <ViewConversionModal lead={selectedLead} isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
      )}
    </>
  )
}
