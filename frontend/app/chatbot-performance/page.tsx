"use client"

import { useState } from "react"
import PageHeader from "@/components/page-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ResponsiveChartContainer } from "@/components/responsive-chart-container"
import { SurveyAnalysisCard } from "@/components/survey-analysis-card"
import { UpdatedOverallSatisfactionCard } from "@/components/updated-overall-satisfaction-card"
import { OverallScoreCard } from "@/components/overall-score-card"
import { FilterableResolutionChart } from "@/components/filterable-resolution-chart"
import { FlowDropoffChart } from "@/components/flow-dropoff-chart"
import { MetricCard } from "@/components/metric-card"
import { DonutChart } from "@/components/charts/donut-chart"
import { ChannelFilter, type ChannelType } from "@/components/channel-filter"

export default function ChatbotPerformancePage() {
  const [selectedChannel, setSelectedChannel] = useState<ChannelType>("all")

  const surveyMetrics = [
    {
      id: "clarity",
      name: "Clarity of Responses",
      score: 4.2,
      maxScore: 5,
      description: "User feedback on clarity",
    },
    {
      id: "accuracy",
      name: "Accuracy of Responses",
      score: 3.8,
      maxScore: 5,
      description: "User feedback on accuracy",
    },
    {
      id: "satisfaction",
      name: "Satisfaction Rating",
      score: 4.0,
      maxScore: 5,
      description: "Overall satisfaction rating",
    },
  ]

  const satisfactionData = {
    totalResponses: 1691,
    responseRating: 4.1,
    maxRating: 5,
    positiveCount: 1456,
    negativeCount: 234,
  }

  const getChannelSpecificData = (channel: ChannelType) => {
    switch (channel) {
      case "chatbots":
      case "avatar-chatbots":
      case "whatsapp":
        return {
          completionTitle:
            channel === "chatbots"
              ? "Chat Completion Rate"
              : channel === "avatar-chatbots"
                ? "Avatar Chat Completion Rate"
                : "WhatsApp Completion Rate",
          fallbackTitle: "Fallback Rate",
          showEscalation: false,
          showSentiment: false,
          showSatisfaction: true,
        }
      case "voicebots":
        return {
          completionTitle: "Call Completion Rate",
          fallbackTitle: "Fallback Rate",
          showEscalation: false,
          showSentiment: true,
          showSatisfaction: false,
        }
      default:
        return {
          completionTitle: "Completion Rate",
          fallbackTitle: "Fallback Rate",
          showEscalation: false,
          showSentiment: true,
          showSatisfaction: true,
        }
    }
  }

  const channelData = getChannelSpecificData(selectedChannel)

  return (
    <div className="flex min-h-screen flex-col">
      <PageHeader
        title="Chatbot Performance"
        description="Key metrics about chatbot usage and effectiveness"
        actions={<ChannelFilter onChannelChange={setSelectedChannel} defaultValue={selectedChannel} />}
      />
      <main className="flex-1 space-y-6 p-6 md:p-8 w-full">
        {/* Chat Metrics */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title={channelData.completionTitle}
            value="75%"
            description={
              selectedChannel === "voicebots"
                ? "Calls completed without escalation"
                : "Conversations completed without escalation"
            }
            trend="+3%"
            trendDirection="up"
          />
          <MetricCard
            title={channelData.fallbackTitle}
            value="12%"
            description={
              selectedChannel === "voicebots"
                ? "Calls bot failed to understand"
                : "Queries chatbot failed to understand"
            }
            trend="-1%"
            trendDirection="down"
          />
        </div>

        {/* Conditional Content Based on Channel */}
        {selectedChannel === "voicebots" ? (
          <>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <OverallScoreCard
                score={4.1}
                maxScore={5}
                description="Comprehensive performance score across all metrics"
              />

              <Card className="shadow">
                <CardHeader className="pb-2">
                  <CardTitle>Inbound Calls Sentiment</CardTitle>
                  <CardDescription>Organic call sentiment analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveChartContainer>
                    <DonutChart
                      data={[
                        { name: "Positive", value: 65, color: "hsl(142, 76%, 36%)" },
                        { name: "Neutral", value: 25, color: "hsl(45, 93%, 47%)" },
                        { name: "Negative", value: 10, color: "hsl(0, 84%, 60%)" },
                      ]}
                    />
                  </ResponsiveChartContainer>
                  <div className="mt-4 w-full px-2 text-center">
                    <p className="text-sm text-muted-foreground">65% positive sentiment in organic calls</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow">
                <CardHeader className="pb-2">
                  <CardTitle>Outbound Calls Sentiment</CardTitle>
                  <CardDescription>Campaign call sentiment analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveChartContainer>
                    <DonutChart
                      data={[
                        { name: "Positive", value: 45, color: "hsl(142, 76%, 36%)" },
                        { name: "Neutral", value: 35, color: "hsl(45, 93%, 47%)" },
                        { name: "Negative", value: 20, color: "hsl(0, 84%, 60%)" },
                      ]}
                    />
                  </ResponsiveChartContainer>
                  <div className="mt-4 w-full px-2 text-center">
                    <p className="text-sm text-muted-foreground">45% positive sentiment in campaign calls</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        ) : selectedChannel === "all" ? (
          <>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <SurveyAnalysisCard metrics={surveyMetrics} />
              <OverallScoreCard
                score={4.1}
                maxScore={5}
                description="Comprehensive performance score across all metrics"
              />
              <UpdatedOverallSatisfactionCard
                totalResponses={satisfactionData.totalResponses}
                responseRating={satisfactionData.responseRating}
                maxRating={5}
                positiveCount={satisfactionData.positiveCount}
                negativeCount={satisfactionData.negativeCount}
              />
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="shadow">
                <CardHeader className="pb-2">
                  <CardTitle>Overall Sentiment Score</CardTitle>
                  <CardDescription>Inbound Calls (Organic) sentiment analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveChartContainer>
                    <DonutChart
                      data={[
                        { name: "Positive", value: 65, color: "hsl(142, 76%, 36%)" },
                        { name: "Neutral", value: 25, color: "hsl(45, 93%, 47%)" },
                        { name: "Negative", value: 10, color: "hsl(0, 84%, 60%)" },
                      ]}
                    />
                  </ResponsiveChartContainer>
                  <div className="mt-4 w-full px-2 text-center">
                    <p className="text-sm text-muted-foreground">65% positive sentiment in organic interactions</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="shadow">
                <CardHeader className="pb-2">
                  <CardTitle>Overall Sentiment Score</CardTitle>
                  <CardDescription>Outbound Calls (Campaigns) sentiment analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveChartContainer>
                    <DonutChart
                      data={[
                        { name: "Positive", value: 45, color: "hsl(142, 76%, 36%)" },
                        { name: "Neutral", value: 35, color: "hsl(45, 93%, 47%)" },
                        { name: "Negative", value: 20, color: "hsl(0, 84%, 60%)" },
                      ]}
                    />
                  </ResponsiveChartContainer>
                  <div className="mt-4 w-full px-2 text-center">
                    <p className="text-sm text-muted-foreground">45% positive sentiment in campaign interactions</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        ) : (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <SurveyAnalysisCard metrics={surveyMetrics} />
            <OverallScoreCard
              score={4.1}
              maxScore={5}
              description="Comprehensive performance score across all metrics"
            />
            <UpdatedOverallSatisfactionCard
              totalResponses={satisfactionData.totalResponses}
              responseRating={satisfactionData.responseRating}
              maxRating={5}
              positiveCount={satisfactionData.positiveCount}
              negativeCount={satisfactionData.negativeCount}
            />
          </div>
        )}

        {/* Resolution Rate - Always shown */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-1">
          <FilterableResolutionChart title="Resolution Rate" description="Resolution rate trend with time filters" />
        </div>

        {/* Drop-off Points - Always shown */}
        <div className="grid grid-cols-1">
          <FlowDropoffChart
            title="Drop-off Points"
            description={
              selectedChannel === "voicebots"
                ? "User drop-off analysis by call flow"
                : "User drop-off analysis by conversation flow"
            }
          />
        </div>
      </main>
    </div>
  )
}
