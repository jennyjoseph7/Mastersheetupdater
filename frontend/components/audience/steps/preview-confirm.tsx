"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { DataSourceFormData } from "../add-data-source-dialog"

interface PreviewConfirmProps {
  formData: DataSourceFormData
}

export function PreviewConfirm({ formData }: PreviewConfirmProps) {
  // Mock sample data - in real app, this would be fetched from API/CSV
  const sampleData = [
    {
      name: "Michael Brown",
      email: "michael@email.com",
      phone: "+1-555-0105",
    },
    {
      name: "John Doe",
      email: "john@email.com",
      phone: "+1-555-0101",
    },
    {
      name: "Jane Smith",
      email: "jane@email.com",
      phone: "+1-555-0102",
    },
    {
      name: "Robert Johnson",
      email: "robert@email.com",
      phone: "+1-555-0103",
    },
    {
      name: "Emily Davis",
      email: "emily@email.com",
      phone: "+1-555-0104",
    },
    {
      name: "William Wilson",
      email: "william@email.com",
      phone: "+1-555-0106",
    },
    {
      name: "Sarah Martinez",
      email: "sarah@email.com",
      phone: "+1-555-0107",
    },
    {
      name: "David Anderson",
      email: "david@email.com",
      phone: "+1-555-0108",
    },
    {
      name: "Lisa Taylor",
      email: "lisa@email.com",
      phone: "+1-555-0109",
    },
    {
      name: "James Thomas",
      email: "james@email.com",
      phone: "+1-555-0110",
    },
  ]

  // Use formData.audienceSize if available, otherwise calculate from sample data
  const totalContacts = formData.audienceSize || 3243
  const categoryDisplay = formData.category === "pre_sales" ? "Pre Sales" : formData.category === "post_sales" ? "Post Sales" : formData.category
  const sourceTypeDisplay = formData.sourceType === "File" ? "CSV" : formData.sourceType || "CSV"
  const tagsDisplay = formData.tags && formData.tags.length > 0 ? formData.tags.join(", ") : "None"

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Preview & Confirm Audience Data</h3>
        <p className="text-sm text-muted-foreground">Review audience details before saving.</p>
      </div>

      {/* Summary Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Total Contacts */}
        <Card>
          <CardContent className="pt-6">
            <div className="text-4xl font-bold mb-1">{totalContacts.toLocaleString()}</div>
            <p className="text-sm text-muted-foreground">records retrieved</p>
          </CardContent>
        </Card>

        {/* Category */}
        <Card>
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground mb-1">Category</div>
            <div className="text-lg font-semibold capitalize">{categoryDisplay}</div>
          </CardContent>
        </Card>
      </div>

      {/* Audience Details Section */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Audience Name</p>
                <p className="font-medium">{formData.audienceName || "—"}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Tag</p>
                <p className="font-medium">{tagsDisplay}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Source Type</p>
                <p className="font-medium">
                  <Badge variant="outline">{sourceTypeDisplay}</Badge>
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Preview Section */}
      <Card>
        <CardContent className="pt-6">
          <div className="mb-4">
            <h4 className="text-base font-semibold mb-1">Data Preview (First 10 rows)</h4>
            <p className="text-xs text-muted-foreground">Preview of your audience data</p>
          </div>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Phone</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sampleData.map((row, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-medium">{row.name}</TableCell>
                    <TableCell>{row.email}</TableCell>
                    <TableCell>{row.phone}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <p className="text-xs text-muted-foreground mt-3">
            Showing first 10 rows of {totalContacts.toLocaleString()} total records
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
