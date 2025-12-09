"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreVertical, Pencil, Trash2 } from "lucide-react"
import type { EmailConnection } from "@/app/connection/page"

interface EmailConnectionsTableProps {
  connections: EmailConnection[]
  onEdit: (id: string) => void
  onRemove: (id: string) => void
}

export function EmailConnectionsTable({ connections, onEdit, onRemove }: EmailConnectionsTableProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "Connected":
        return "bg-green-100 text-green-700 hover:bg-green-100"
      case "Error":
        return "bg-red-100 text-red-700 hover:bg-red-100"
      case "Under Review":
        return "bg-orange-100 text-orange-700 hover:bg-orange-100"
      default:
        return "bg-gray-100 text-gray-700 hover:bg-gray-100"
    }
  }

  if (connections.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-12 text-center">
        <p className="text-muted-foreground">
          No email accounts connected yet. Connect your first email account above.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Sender Name</TableHead>
            <TableHead>Email Address</TableHead>
            <TableHead>Domain</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="w-[70px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {connections.map((connection) => (
            <TableRow key={connection.id}>
              <TableCell className="font-medium">{connection.senderName}</TableCell>
              <TableCell>{connection.emailAddress}</TableCell>
              <TableCell>{connection.domain}</TableCell>
              <TableCell>
                <Badge variant="outline">{connection.type}</Badge>
              </TableCell>
              <TableCell>
                <Badge className={getStatusColor(connection.status)}>{connection.status}</Badge>
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon">
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onEdit(connection.id)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onRemove(connection.id)} className="text-red-600">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Remove
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
