"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { MoreVertical, Edit, Trash2 } from "lucide-react"
import type { Connection } from "@/app/connection/page"

interface ConnectionsTableProps {
  connections: Connection[]
  onEdit: (id: string) => void
  onRemove: (id: string) => void
}

export function ConnectionsTable({ connections, onEdit, onRemove }: ConnectionsTableProps) {
  const getStatusColor = (status: Connection["status"]) => {
    switch (status) {
      case "Connected":
        return "bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400"
      case "Under Review":
        return "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400"
      case "Error":
        return "bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400"
      default:
        return "bg-gray-100 text-gray-700 dark:bg-gray-900/20 dark:text-gray-400"
    }
  }

  if (connections.length === 0) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <p className="text-lg font-medium">No connections found</p>
            <p className="text-sm mt-1">Use Quick Connect or Register New Number to add a connection</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sender Name</TableHead>
              <TableHead>Registered Number</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {connections.map((connection) => (
              <TableRow key={connection.id}>
                <TableCell className="font-medium">{connection.senderName}</TableCell>
                <TableCell>{connection.registeredNumber}</TableCell>
                <TableCell>{connection.provider}</TableCell>
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
                      <DropdownMenuItem onClick={() => onEdit(connection.id)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => onRemove(connection.id)} className="text-red-600">
                        <Trash2 className="h-4 w-4 mr-2" />
                        Remove
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
