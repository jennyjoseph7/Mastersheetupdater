"use client";

import { LinkIcon, BarChart3, CreditCard } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BuyCreditsTab } from "@/components/billing/buy-credits-tab";
import { UsageInsightsTab } from "@/components/billing/usage-insights-tab";
import { BillingHistoryTab } from "@/components/billing/billing-history-tab";

export default function BillingPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8 space-y-6">
        {/* Page header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Billing & Usage</h1>
          <p className="text-muted-foreground mt-1">
            Manage credits, view usage insights, and billing history
          </p>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="buy-credits" className="space-y-6">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="buy-credits" className="gap-2">
              <LinkIcon className="h-4 w-4" />
              Buy Credits
            </TabsTrigger>
            <TabsTrigger value="usage-insights" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              Usage Insights
            </TabsTrigger>
            <TabsTrigger value="billing-history" className="gap-2">
              <CreditCard className="h-4 w-4" />
              Billing History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="buy-credits">
            <BuyCreditsTab />
          </TabsContent>

          <TabsContent value="usage-insights">
            <UsageInsightsTab />
          </TabsContent>

          <TabsContent value="billing-history">
            <BillingHistoryTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
