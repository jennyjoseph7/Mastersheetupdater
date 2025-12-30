"use client"

import { useState } from "react"
import { Download, TrendingUp, LinkIcon, Clock, BarChart3, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const usageData = [
  { month: "Jan", credits: 420 },
  { month: "Feb", credits: 320 },
  { month: "Mar", credits: 680 },
  { month: "Apr", credits: 520 },
  { month: "May", credits: 760 },
  { month: "Jun", credits: 620 },
  { month: "Jul", credits: 890 },
  { month: "Aug", credits: 1150 },
]

const campaignData = [
  {
    name: "Summer Sale Campaign",
    objective: "Seasonal Sale",
    channels: ["WhatsApp", "Email"],
    creditsSpent: 1250,
    status: "Live",
  },
  {
    name: "Product Launch",
    objective: "New Car Launch",
    channels: ["Voice", "Email"],
    creditsSpent: 890,
    status: "Completed",
  },
  {
    name: "Newsletter Outreach",
    objective: "Newsletter",
    channels: ["Email"],
    creditsSpent: 320,
    status: "Drafted",
  },
  {
    name: "Monsoon Campaign",
    objective: "Seasonal Sale",
    channels: ["WhatsApp"],
    creditsSpent: 750,
    status: "Scheduled",
  },
]

export function UsageInsightsTab() {
  const [timeRange, setTimeRange] = useState("monthly")

  return (
    <div className="space-y-6">
      {/* Header with export buttons */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          Updated 5 min ago
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="gap-2 bg-transparent">
            <Download className="h-4 w-4" />
            CSV
          </Button>
          <Button variant="outline" size="sm" className="gap-2 bg-transparent">
            <Download className="h-4 w-4" />
            PDF
          </Button>
        </div>
      </div>

      {/* Key metrics */}
      <div className="grid md:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm text-muted-foreground">Total Credits Used</div>
              <TrendingUp className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-3xl font-bold">3,210</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm text-muted-foreground">Credits Remaining</div>
              <LinkIcon className="h-4 w-4 text-green-600" />
            </div>
            <div className="text-3xl font-bold text-green-600">1,250</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm text-muted-foreground">Avg Daily Usage</div>
              <Clock className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-3xl font-bold">107</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm text-muted-foreground">Avg Weekly Usage</div>
              <BarChart3 className="h-4 w-4 text-purple-600" />
            </div>
            <div className="text-3xl font-bold">802</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm text-muted-foreground">Avg Monthly Usage</div>
              <Calendar className="h-4 w-4 text-orange-600" />
            </div>
            <div className="text-3xl font-bold">3210</div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Line chart */}
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">Credits Usage Over Time</h3>
                <p className="text-sm text-muted-foreground">Credit consumption trend</p>
              </div>
              <Select value={timeRange} onValueChange={setTimeRange}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="daily">Daily</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={usageData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="month" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--background))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "6px",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="credits"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--primary))", r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Donut chart */}
        <Card>
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-lg">Channel Breakdown</h3>
                <p className="text-sm text-muted-foreground">Credits consumed by channel</p>
              </div>
              <Select defaultValue="monthly">
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">Monthly</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-center h-[300px]">
              <svg width="240" height="240" viewBox="0 0 240 240">
                {/* WhatsApp - Light purple */}
                <circle
                  cx="120"
                  cy="120"
                  r="80"
                  fill="none"
                  stroke="hsl(260 98% 31%)"
                  strokeWidth="40"
                  strokeDasharray="168 503"
                  transform="rotate(-90 120 120)"
                />
                {/* Email - Medium purple */}
                <circle
                  cx="120"
                  cy="120"
                  r="80"
                  fill="none"
                  stroke="hsl(260 80% 50%)"
                  strokeWidth="40"
                  strokeDasharray="168 503"
                  strokeDashoffset="-168"
                  transform="rotate(-90 120 120)"
                />
                {/* Voice - Dark purple */}
                <circle
                  cx="120"
                  cy="120"
                  r="80"
                  fill="none"
                  stroke="hsl(260 60% 65%)"
                  strokeWidth="40"
                  strokeDasharray="167 503"
                  strokeDashoffset="-336"
                  transform="rotate(-90 120 120)"
                />
              </svg>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "hsl(260 98% 31%)" }} />
                <div className="flex-1">
                  <div className="text-sm font-medium">WhatsApp</div>
                  <div className="text-xs text-muted-foreground">791</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "hsl(260 80% 50%)" }} />
                <div className="flex-1">
                  <div className="text-sm font-medium">Email</div>
                  <div className="text-xs text-muted-foreground">1032</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "hsl(260 60% 65%)" }} />
                <div className="flex-1">
                  <div className="text-sm font-medium">Voice</div>
                  <div className="text-xs text-muted-foreground">296</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Campaign table */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div>
            <h3 className="font-semibold text-lg">Per-Campaign Breakdown</h3>
            <p className="text-sm text-muted-foreground">Detailed credits usage by campaign</p>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Campaign Name</TableHead>
                <TableHead>Objective</TableHead>
                <TableHead>Channels Used</TableHead>
                <TableHead>Credits Spent</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {campaignData.map((campaign, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">{campaign.name}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{campaign.objective}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {campaign.channels.map((channel) => (
                        <Badge key={channel} variant="outline" className="text-xs">
                          {channel === "WhatsApp" && "💬"}
                          {channel === "Email" && "✉️"}
                          {channel === "Voice" && "📞"} {channel}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>{campaign.creditsSpent.toLocaleString()}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        campaign.status === "Live"
                          ? "default"
                          : campaign.status === "Completed"
                            ? "secondary"
                            : campaign.status === "Scheduled"
                              ? "outline"
                              : "secondary"
                      }
                      className={
                        campaign.status === "Live"
                          ? "bg-green-600"
                          : campaign.status === "Completed"
                            ? "bg-blue-600"
                            : campaign.status === "Scheduled"
                              ? "bg-yellow-600"
                              : ""
                      }
                    >
                      {campaign.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" className="gap-1">
                      👁️ Credits Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
