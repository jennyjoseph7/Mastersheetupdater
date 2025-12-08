"use client"

import { MessageSquare, Clock, BarChart3 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function OverviewStats() {
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <Card className="border-l-4 border-l-primary shadow">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Total Chatbot Sessions</CardTitle>
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-primary">1,258</div>
          <p className="text-xs text-muted-foreground">10.1% of website visitors</p>
        </CardContent>
      </Card>
      <Card className="border-l-4 border-l-primary shadow">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Avg. Conversation Duration</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-primary">5 min</div>
          <p className="text-xs text-muted-foreground">+30 sec from last month</p>
        </CardContent>
      </Card>
      <Card className="border-l-4 border-l-primary shadow">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Avg. Response Time</CardTitle>
          <Clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-primary">10 sec</div>
          <p className="text-xs text-muted-foreground">-2 sec from last month</p>
        </CardContent>
      </Card>
      <Card className="border-l-4 border-l-primary shadow">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium">Queries Per Session</CardTitle>
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-primary">6.5</div>
          <p className="text-xs text-muted-foreground">+0.8 from last month</p>
        </CardContent>
      </Card>
    </div>
  )
}
