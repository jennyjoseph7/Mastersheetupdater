"use client"

import { useState, useMemo } from "react"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

export interface UnansweredQuery {
  id: string
  queryText: string
  timestamp: string
  sessionId: string
  status: "pending" | "resolved" | "escalated" | "garbage" | "incorrect-answer" | "faq-added" | "not-supported"
}

interface UnansweredQueryListProps {
  queries: UnansweredQuery[]
  onTakeAction?: (queryId: string) => void
}

export function UnansweredQueryList({ queries, onTakeAction }: UnansweredQueryListProps) {
  const [searchTerm, setSearchTerm] = useState("")
  const [sortColumn, setSortColumn] = useState<keyof UnansweredQuery | null>(null)
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc")

  const filteredAndSortedQueries = useMemo(() => {
    let filtered = queries.filter(
      (query) =>
        query.queryText.toLowerCase().includes(searchTerm.toLowerCase()) ||
        query.sessionId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        query.status.toLowerCase().includes(searchTerm.toLowerCase()),
    )

    if (sortColumn) {
      filtered = filtered.sort((a, b) => {
        const aValue = a[sortColumn]
        const bValue = b[sortColumn]

        if (typeof aValue === "string" && typeof bValue === "string") {
          return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
        }
        return 0
      })
    }
    return filtered
  }, [queries, searchTerm, sortColumn, sortDirection])

  const handleSort = (column: keyof UnansweredQuery) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortColumn(column)
      setSortDirection("asc")
    }
  }

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-orange-500 hover:bg-orange-600"
      case "resolved":
        return "bg-green-500 hover:bg-green-600"
      case "escalated":
        return "bg-red-500 hover:bg-red-600"
      case "garbage":
        return "bg-gray-500 hover:bg-gray-600"
      case "incorrect-answer":
        return "bg-yellow-500 hover:bg-yellow-600"
      case "faq-added":
        return "bg-blue-500 hover:bg-blue-600"
      case "not-supported":
        return "bg-purple-500 hover:bg-purple-600"
      default:
        return "bg-orange-500 hover:bg-orange-600"
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "incorrect-answer":
        return "Incorrect Answer"
      case "faq-added":
        return "FAQ Added"
      case "not-supported":
        return "Not Supported"
      default:
        return status.charAt(0).toUpperCase() + status.slice(1)
    }
  }

  return (
    <div className="space-y-4">
      <Input
        placeholder="Search queries by text or session ID..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="max-w-sm"
      />
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="cursor-pointer" onClick={() => handleSort("queryText")}>
                Query Text
                {sortColumn === "queryText" &&
                  (sortDirection === "asc" ? (
                    <ChevronUp className="inline h-4 w-4 ml-1" />
                  ) : (
                    <ChevronDown className="inline h-4 w-4 ml-1" />
                  ))}
              </TableHead>
              <TableHead className="cursor-pointer" onClick={() => handleSort("timestamp")}>
                Timestamp
                {sortColumn === "timestamp" &&
                  (sortDirection === "asc" ? (
                    <ChevronUp className="inline h-4 w-4 ml-1" />
                  ) : (
                    <ChevronDown className="inline h-4 w-4 ml-1" />
                  ))}
              </TableHead>
              <TableHead className="cursor-pointer" onClick={() => handleSort("sessionId")}>
                Session ID
                {sortColumn === "sessionId" &&
                  (sortDirection === "asc" ? (
                    <ChevronUp className="inline h-4 w-4 ml-1" />
                  ) : (
                    <ChevronDown className="inline h-4 w-4 ml-1" />
                  ))}
              </TableHead>
              <TableHead className="cursor-pointer" onClick={() => handleSort("status")}>
                Status
                {sortColumn === "status" &&
                  (sortDirection === "asc" ? (
                    <ChevronUp className="inline h-4 w-4 ml-1" />
                  ) : (
                    <ChevronDown className="inline h-4 w-4 ml-1" />
                  ))}
              </TableHead>
              <TableHead>Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredAndSortedQueries.length > 0 ? (
              filteredAndSortedQueries.map((query) => (
                <TableRow key={query.id}>
                  <TableCell className="font-medium max-w-[300px] truncate">{query.queryText}</TableCell>
                  <TableCell>{new Date(query.timestamp).toLocaleString()}</TableCell>
                  <TableCell>{query.sessionId}</TableCell>
                  <TableCell>
                    <Badge className={cn(getStatusBadgeColor(query.status))}>{getStatusLabel(query.status)}</Badge>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onTakeAction?.(query.id)}
                      disabled={query.status !== "pending"}
                    >
                      Take Action
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                  No unanswered queries found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
