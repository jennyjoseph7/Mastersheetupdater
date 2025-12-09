"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FunnelChart } from "@/components/charts/funnel-chart"
import { ResponsiveChartContainer } from "@/components/responsive-chart-container"

interface FlowDropoffChartProps {
  title: string
  description: string
}

export function FlowDropoffChart({ title, description }: FlowDropoffChartProps) {
  const [selectedFlow, setSelectedFlow] = useState("default")

  const getFlowData = () => {
    switch (selectedFlow) {
      case "default":
        return [
          { name: "Total Sessions", value: 100 },
          { name: "CTA Clicked", value: 45 },
          { name: "Flow Finished", value: 25 },
        ]
      case "policy-inquiry":
        return [
          { name: "Policy Inquiry Started", value: 100 },
          { name: "Policy Number Provided", value: 80 },
          { name: "Information Retrieved", value: 65 },
          { name: "Query Resolved", value: 55 },
        ]
      case "claims-process":
        return [
          { name: "Claims Process Started", value: 100 },
          { name: "Claim Type Selected", value: 75 },
          { name: "Documents Uploaded", value: 50 },
          { name: "Claim Submitted", value: 40 },
          { name: "Confirmation Received", value: 35 },
        ]
      case "premium-payment":
        return [
          { name: "Payment Flow Started", value: 100 },
          { name: "Payment Method Selected", value: 85 },
          { name: "Amount Confirmed", value: 70 },
          { name: "Payment Processed", value: 60 },
        ]
      default:
        return [
          { name: "Total Sessions", value: 100 },
          { name: "CTA Clicked", value: 45 },
          { name: "Flow Finished", value: 25 },
        ]
    }
  }

  const getFlowDescription = () => {
    switch (selectedFlow) {
      case "policy-inquiry":
        return "Policy inquiry conversation flow"
      case "claims-process":
        return "Claims processing conversation flow"
      case "premium-payment":
        return "Premium payment conversation flow"
      default:
        return "Overall conversation flow completion"
    }
  }

  return (
    <Card className="shadow">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{description}</CardDescription>
          </div>
          <Select value={selectedFlow} onValueChange={setSelectedFlow}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">Default Flow</SelectItem>
              <SelectItem value="policy-inquiry">Policy Inquiry</SelectItem>
              <SelectItem value="claims-process">Claims Process</SelectItem>
              <SelectItem value="premium-payment">Premium Payment</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveChartContainer className="h-[350px]">
          <FunnelChart data={getFlowData()} height={320} />
        </ResponsiveChartContainer>
        <div className="mt-4 w-full px-2 text-center">
          <p className="text-sm text-muted-foreground">{getFlowDescription()}</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Completion rate: {getFlowData()[getFlowData().length - 1].value}%
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
