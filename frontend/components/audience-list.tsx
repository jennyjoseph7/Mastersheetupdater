"use client"

import { useState, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronUp, Search } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Message {
  id: string
  sender: "user" | "bot"
  text: string
  timestamp: string
  rating?: "thumbs-up" | "thumbs-down"
}

export interface Audience {
  id: string
  userId: string
  name: string
  email: string
  contactNumber: string
  status: "Lead" | "Qualified" | "Converted" | "Losing" | "Lost"
  disposition: string
  totalDuration: number
  queries: number
  unanswered: number
  sentiment: "Positive" | "Negative" | "Neutral"
  intents: string[]
  escalations: number
  interactionType: "chat" | "call"
  messages?: Message[]
  callTranscript?: string
}

interface AudienceListProps {
  audiences: Audience[]
  onViewHistory: (audience: Audience) => void
}

export function AudienceList({ audiences, onViewHistory }: AudienceListProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [sortColumn, setSortColumn] = useState<keyof Audience | null>(null)
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [sentimentFilter, setSentimentFilter] = useState<string>("all")
  const [interactionTypeFilter, setInteractionTypeFilter] = useState<string>("all")
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const filteredAndSortedAudiences = useMemo(() => {
    let filtered = audiences.filter((audience) => {
      const matchesSearch =
        audience.userId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        audience.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        audience.email.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus = statusFilter === "all" || audience.status === statusFilter
      const matchesSentiment = sentimentFilter === "all" || audience.sentiment === sentimentFilter
      const matchesInteractionType =
        interactionTypeFilter === "all" || audience.interactionType === interactionTypeFilter

      return matchesSearch && matchesStatus && matchesSentiment && matchesInteractionType
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
  }, [audiences, searchTerm, sortColumn, sortDirection, statusFilter, sentimentFilter, interactionTypeFilter])

  const paginatedAudiences = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return filteredAndSortedAudiences.slice(startIndex, startIndex + itemsPerPage)
  }, [filteredAndSortedAudiences, currentPage])

  const totalPages = Math.ceil(filteredAndSortedAudiences.length / itemsPerPage)

  const handleSort = (column: keyof Audience) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortColumn(column)
      setSortDirection("asc")
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Converted":
        return "bg-green-100 text-green-800 border-green-200"
      case "Qualified":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "Lead":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "Losing":
        return "bg-orange-100 text-orange-800 border-orange-200"
      case "Lost":
        return "bg-red-100 text-red-800 border-red-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "Positive":
        return "bg-green-100 text-green-800 border-green-200"
      case "Negative":
        return "bg-red-100 text-red-800 border-red-200"
      case "Neutral":
        return "bg-gray-100 text-gray-800 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const formatDuration = (totalMinutes: number) => {
    const minutes = Math.floor(totalMinutes)
    const seconds = Math.round((totalMinutes - minutes) * 60)
    return `${minutes} min ${seconds} sec`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audience Management</CardTitle>
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by User ID, name, or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8"
            />
          </div>

          <div className="flex gap-2">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="Lead">Lead</SelectItem>
                <SelectItem value="Qualified">Qualified</SelectItem>
                <SelectItem value="Converted">Converted</SelectItem>
                <SelectItem value="Losing">Losing</SelectItem>
                <SelectItem value="Lost">Lost</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sentimentFilter} onValueChange={setSentimentFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All Sentiments" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sentiments</SelectItem>
                <SelectItem value="Positive">Positive</SelectItem>
                <SelectItem value="Negative">Negative</SelectItem>
                <SelectItem value="Neutral">Neutral</SelectItem>
              </SelectContent>
            </Select>

            <Select value={interactionTypeFilter} onValueChange={setInteractionTypeFilter}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="chat">Chat</SelectItem>
                <SelectItem value="call">Call</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="cursor-pointer" onClick={() => handleSort("userId")}>
                  User ID
                  {sortColumn === "userId" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead className="cursor-pointer" onClick={() => handleSort("name")}>
                  Name
                  {sortColumn === "name" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead className="cursor-pointer" onClick={() => handleSort("status")}>
                  Status
                  {sortColumn === "status" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead>Disposition</TableHead>
                <TableHead className="cursor-pointer" onClick={() => handleSort("totalDuration")}>
                  Duration
                  {sortColumn === "totalDuration" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead className="cursor-pointer" onClick={() => handleSort("queries")}>
                  Queries
                  {sortColumn === "queries" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead>Unanswered</TableHead>
                <TableHead>Sentiment</TableHead>
                <TableHead>Intents</TableHead>
                <TableHead>Escalations</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedAudiences.length > 0 ? (
                paginatedAudiences.map((audience) => (
                  <TableRow key={audience.id} className="hover:bg-muted/50">
                    <TableCell className="font-medium">{audience.userId}</TableCell>
                    <TableCell>{audience.name}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{audience.email}</TableCell>
                    <TableCell className="text-sm">{audience.contactNumber}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(audience.status)}>{audience.status}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">{audience.disposition}</TableCell>
                    <TableCell>{formatDuration(audience.totalDuration)}</TableCell>
                    <TableCell>{audience.queries}</TableCell>
                    <TableCell>{audience.unanswered}</TableCell>
                    <TableCell>
                      <Badge className={getSentimentColor(audience.sentiment)}>{audience.sentiment}</Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      <div className="flex flex-wrap gap-1">
                        {audience.intents.slice(0, 2).map((intent, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {intent}
                          </Badge>
                        ))}
                        {audience.intents.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{audience.intents.length - 2}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{audience.escalations}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => onViewHistory(audience)}>
                        View History
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={13} className="h-24 text-center text-muted-foreground">
                    No audiences found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between space-x-2 py-4">
            <div className="text-sm text-muted-foreground">
              Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
              {Math.min(currentPage * itemsPerPage, filteredAndSortedAudiences.length)} of{" "}
              {filteredAndSortedAudiences.length} results
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
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <Button
                    key={page}
                    variant={currentPage === page ? "default" : "outline"}
                    size="sm"
                    onClick={() => setCurrentPage(page)}
                    className="w-8 h-8 p-0"
                  >
                    {page}
                  </Button>
                ))}
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
  )
}
