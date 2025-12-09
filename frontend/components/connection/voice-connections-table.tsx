"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { MoreVertical } from "lucide-react"
import type { VoiceConnection } from "@/app/connection/page"

interface VoiceConnectionsTableProps {
  connections: VoiceConnection[]
  onEdit: (id: string) => void
  onRemove: (id: string) => void
}

export function VoiceConnectionsTable({ connections, onEdit, onRemove }: VoiceConnectionsTableProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "Connected":
        return "bg-green-100 text-green-700 hover:bg-green-100"
      case "Under Review":
        return "bg-orange-100 text-orange-700 hover:bg-orange-100"
      case "Error":
        return "bg-red-100 text-red-700 hover:bg-red-100"
      default:
        return "bg-gray-100 text-gray-700 hover:bg-gray-100"
    }
  }

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name / ID</TableHead>
            <TableHead>Number</TableHead>
            <TableHead>Provider</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {connections.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                No voice connections found. Register a new number to get started.
              </TableCell>
            </TableRow>
          ) : (
            connections.map((connection) => (
              <TableRow key={connection.id}>
                <TableCell className="font-medium">{connection.name}</TableCell>
                <TableCell>
                  {connection.type === "Number Pool" ? (
                    <span className="text-muted-foreground">{connection.poolNumbers?.length || 0} numbers</span>
                  ) : (
                    connection.number
                  )}
                </TableCell>
                <TableCell>
                  {Array.isArray(connection.provider) ? (
                    <div className="flex flex-wrap gap-1">
                      {connection.provider.map((p, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    connection.provider
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant="outline">{connection.type}</Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className={getStatusColor(connection.status)}>
                    {connection.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => onEdit(connection.id)}>Edit</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onRemove(connection.id)} className="text-red-600">
                        Remove
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
