"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Edit, Trash2, RefreshCw } from "lucide-react"
import type { DataSource } from "@/app/audience/page"

interface DataSourcesTableProps {
  dataSources: DataSource[]
  onRemove: (id: string) => void
  onResync: (id: string) => void
}

export function DataSourcesTable({ dataSources, onRemove, onResync }: DataSourcesTableProps) {
  const getStatusBadge = (status: DataSource["status"]) => {
    switch (status) {
      case "Connected":
        return <Badge className="bg-emerald-500 hover:bg-emerald-600">Connected</Badge>
      case "Error":
        return <Badge variant="destructive">Error</Badge>
      case "Expired":
        return (
          <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-300">
            Expired
          </Badge>
        )
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Connected Data Sources</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Source Name</TableHead>
                <TableHead>Audience Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Audience Size</TableHead>
                <TableHead>Last Synced</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {dataSources.map((source) => (
                <TableRow key={source.id}>
                  <TableCell className="font-medium">{source.sourceName}</TableCell>
                  <TableCell>{source.audienceName}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{source.type}</Badge>
                  </TableCell>
                  <TableCell>{source.audienceSize.toLocaleString()} contacts</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{formatDate(source.lastSynced)}</TableCell>
                  <TableCell>{getStatusBadge(source.status)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="sm">
                        <Edit className="h-4 w-4" />
                      </Button>
                      
                      <Button variant="ghost" size="sm" onClick={() => onRemove(source.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
