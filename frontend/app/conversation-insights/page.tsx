"use client"

import { useState } from "react"
import PageHeader from "@/components/page-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { DonutChart } from "@/components/charts/donut-chart"
import { CircularProgress } from "@/components/circular-progress"
import { ResponsiveChartContainer } from "@/components/responsive-chart-container"
import { ChannelFilter, type ChannelType } from "@/components/channel-filter"

export default function ConversationInsightsPage() {
  const [selectedChannel, setSelectedChannel] = useState<ChannelType>("all")

  // Mock data for Commonly Asked Questions
  const getCommonlyAskedQuestions = (channel: ChannelType) => {
    if (channel === "voicebots") {
      return [
        { question: "How do I file a claim over the phone?", category: "Claims" },
        { question: "Can you help me with my policy details?", category: "Policy Coverage" },
        { question: "I want to make a premium payment", category: "Premium Payment" },
        { question: "How do I add a new vehicle to my policy?", category: "Policy Change" },
        { question: "What documents do I need for a phone claim?", category: "Claims" },
      ]
    }

    return [
      { question: "How do I file a claim?", category: "Claims" },
      { question: "What is my deductible?", category: "Policy Coverage" },
      { question: "How can I pay my premium?", category: "Premium Payment" },
      { question: "Can I add a new vehicle to my policy?", category: "Policy Change" },
      { question: "What documents do I need for a claim?", category: "Claims" },
    ]
  }

  const getChannelSpecificData = (channel: ChannelType) => {
    switch (channel) {
      case "voicebots":
        return {
          flowsTitle: "Total Executed Flows",
          flowsDescription: "Distribution of Call Topics",
          questionsTitle: "Commonly Asked Questions in Calls",
          questionsDescription: "List of frequently asked questions during calls",
        }
      default:
        return {
          flowsTitle: "Total Executed Flows",
          flowsDescription: "Distribution of Conversation Topics",
          questionsTitle: "Commonly Asked Questions",
          questionsDescription:
            channel === "all"
              ? "List of frequently asked questions across all channels"
              : "List of frequently asked questions on the chatbot",
        }
    }
  }

  const channelData = getChannelSpecificData(selectedChannel)
  const commonlyAskedQuestions = getCommonlyAskedQuestions(selectedChannel)

  return (
    <div className="flex min-h-screen flex-col">
      <PageHeader
        title="Conversation Insights"
        description="User intent and conversation flow analysis"
        actions={<ChannelFilter onChannelChange={setSelectedChannel} defaultValue={selectedChannel} />}
      />
      <main className="flex-1 space-y-6 p-6 md:p-8 w-full">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-1">
          <Card className="col-span-1 shadow">
            <CardHeader className="pb-2">
              <CardTitle>{channelData.flowsTitle}</CardTitle>
              <CardDescription>{channelData.flowsDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveChartContainer>
                <DonutChart
                  data={[
                    { name: "Policy Awareness", value: 45, color: "#39019a" },
                    { name: "Claims", value: 25, color: "#7029b2" },
                    { name: "Premium Payment", value: 20, color: "#a752ca" },
                    { name: "Other Queries", value: 10, color: "#de7be2" },
                  ]}
                />
              </ResponsiveChartContainer>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <CircularProgress value={75} label="Policy Inquiry" color="#39019a" />
                <CircularProgress value={20} label="Insurance Renewal" color="#39019a" />
                <CircularProgress value={5} label="Premium Payment" color="#39019a" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow">
          <CardHeader className="pb-2">
            <CardTitle>{channelData.questionsTitle}</CardTitle>
            <CardDescription>{channelData.questionsDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {commonlyAskedQuestions.map((item, index) => (
                <div key={index} className="flex items-center justify-between rounded-md bg-muted/50 p-3">
                  <span className="text-sm font-medium">{item.question}</span>
                  <span className="text-xs text-muted-foreground">{item.category}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
