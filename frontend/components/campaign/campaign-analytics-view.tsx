"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FunnelChart } from "@/components/charts/funnel-chart";
import { DonutChart } from "@/components/charts/donut-chart";
import { formatNumber } from "@/lib/utils";
import type { CampaignConversion } from "@/lib/campaign-insights-data";
import { ChevronDown, ChevronLeft, Download } from "lucide-react";

type CampaignAnalyticsViewProps = {
  campaign: CampaignConversion;
};

export function CampaignAnalyticsView({
  campaign,
}: CampaignAnalyticsViewProps) {
  const [timeFilter, setTimeFilter] = useState("This Week");
  const [channelFilter, setChannelFilter] = useState("All Channels");

  const channelOptions = ["All Channels", "WhatsApp", "Email", "Voice"];

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <div className="border-b bg-card/60">
        <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-6 px-6 py-8">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Link
              href="/insights"
              className="inline-flex items-center gap-1 text-sm font-medium text-foreground hover:text-primary"
            >
              <ChevronLeft className="h-4 w-4" />
              Back to Campaign Insights
            </Link>
          </div>
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div className="space-y-3">
              <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                Campaign Analytics
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">
                  {campaign.name}
                </h1>
                <CardDescription className="mt-1 text-base">
                  Deep dive into engagement, conversion, and sentiment signals
                </CardDescription>
              </div>
              <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                <span>
                  Created on <strong className="text-foreground">{campaign.createdOn}</strong>
                </span>
                <span className="inline-flex items-center gap-1">
                  Status: {campaign.status === "Live" ? (
                    <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
                      {campaign.status}
                    </Badge>
                  ) : (
                    <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                      {campaign.status}
                    </Badge>
                  )}
                </span>
                <span className="inline-flex items-center gap-2">
                  Channels:
                  <div className="flex flex-wrap gap-1.5">
                    {campaign.channels.map((channel) => (
                      <Badge key={channel} variant="secondary" className="text-xs">
                        {channel}
                      </Badge>
                    ))}
                  </div>
                </span>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="gap-2 bg-transparent">
                    {timeFilter}
                    <ChevronDown className="h-4 w-4 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>Filter by Time</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {["This Week", "Last Week", "This Month", "Last Month", "This Year"].map(
                    (option) => (
                      <DropdownMenuItem
                        key={option}
                        onClick={() => setTimeFilter(option)}
                      >
                        {option}
                      </DropdownMenuItem>
                    )
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
              <Button variant="outline" className="gap-2 bg-transparent">
                <Download className="h-4 w-4" />
                Export
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 w-full bg-background">
        <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-8 px-6 py-10">
          <section className="space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">
                  Engagement Funnel
                </h2>
                <p className="text-sm text-muted-foreground">
                  Track user journey from initial contact to conversion
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {channelOptions.map((channel) => (
                  <Button
                    key={channel}
                    variant={channelFilter === channel ? "default" : "outline"}
                    size="sm"
                    onClick={() => setChannelFilter(channel)}
                  >
                    {channel}
                  </Button>
                ))}
              </div>
            </div>
            <Card className="border border-muted bg-card/70">
              <CardContent className="pt-6">
                <FunnelChart
                  data={campaign.analytics.funnel.map((stage) => ({
                    name: stage.stage,
                    value: stage.percent,
                  }))}
                  width={960}
                  height={420}
                />
              </CardContent>
            </Card>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {campaign.analytics.funnel.map((item) => (
                <Card key={item.stage} className="border border-muted bg-muted/10">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-muted-foreground">
                      {item.stage}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-3xl font-semibold">
                      {formatNumber(item.count)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {item.percent}% of previous stage
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Card className="border border-muted bg-muted/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">
                    Conversion Rate
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-semibold">
                    {campaign.analytics.conversionRate}%
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-muted bg-muted/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">
                    Total Reached
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-semibold">
                    {formatNumber(campaign.analytics.totalReached)}
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-muted bg-muted/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">
                    Converted
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-semibold">
                    {formatNumber(campaign.analytics.converted)}
                  </p>
                </CardContent>
              </Card>
            </div>
          </section>

          <section className="space-y-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">
                  Sentiment Analysis
                </h2>
                <p className="text-sm text-muted-foreground">
                  Customer sentiment across all interactions
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {channelOptions.map((channel) => (
                  <Button
                    key={`sentiment-${channel}`}
                    variant={channelFilter === channel ? "default" : "outline"}
                    size="sm"
                    onClick={() => setChannelFilter(channel)}
                  >
                    {channel}
                  </Button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="border border-muted bg-card/70">
                <CardContent className="pt-6">
                  <DonutChart
                    data={campaign.analytics.sentiment.map((sentiment) => ({
                      name: sentiment.label,
                      value: sentiment.percent,
                      color:
                        sentiment.label === "Positive"
                          ? "#10b981"
                          : sentiment.label === "Neutral"
                          ? "#fbbf24"
                          : "#ef4444",
                    }))}
                    width={420}
                    height={380}
                  />
                </CardContent>
              </Card>
              <div className="grid grid-cols-1 gap-4">
                {campaign.analytics.sentiment.map((sentiment) => (
                  <Card
                    key={sentiment.label}
                    className="border border-muted bg-muted/10"
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm text-muted-foreground">
                        {sentiment.label}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-3xl font-semibold">
                        {sentiment.percent}%
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {formatNumber(sentiment.count)} interactions
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <Card className="border border-muted bg-muted/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">
                    Total Analyzed
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-semibold">
                    {formatNumber(campaign.analytics.totalAnalyzed)}
                  </p>
                </CardContent>
              </Card>
              <Card className="border border-muted bg-muted/10">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-muted-foreground">
                    Satisfaction
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-semibold">
                    {campaign.analytics.satisfaction}%
                  </p>
                </CardContent>
              </Card>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

