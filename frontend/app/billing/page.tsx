"use client";

import dynamic from "next/dynamic";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { LinkIcon, BarChart3, CreditCard, Loader2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// 1. Lazy load the tab components to reduce the initial bundle size
// Assuming these are named exports based on your original imports
const BuyCreditsTab = dynamic(
  () => import("@/components/billing/buy-credits-tab").then((mod) => mod.BuyCreditsTab),
  { loading: () => <TabSkeleton /> }
);
const UsageInsightsTab = dynamic(
  () => import("@/components/billing/usage-insights-tab").then((mod) => mod.UsageInsightsTab),
  { loading: () => <TabSkeleton /> }
);
const BillingHistoryTab = dynamic(
  () => import("@/components/billing/billing-history-tab").then((mod) => mod.BillingHistoryTab),
  { loading: () => <TabSkeleton /> }
);

// A simple loading skeleton to show while the tab component code is fetching
function TabSkeleton() {
  return (
    <div className="flex items-center justify-center p-12 text-muted-foreground">
      <Loader2 className="h-6 w-6 animate-spin" />
    </div>
  );
}

export default function BillingPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // 2. Read the active tab from the URL, defaulting to "buy-credits"
  const currentTab = searchParams.get("tab") || "buy-credits";

  // 3. Update the URL when the user clicks a new tab
  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", value);
    // Use router.replace to update the URL without adding to browser history,
    // or router.push if you want the back button to navigate between tabs
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

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
        <Tabs 
          value={currentTab} 
          onValueChange={handleTabChange} 
          className="space-y-6"
        >
          <TabsList className="bg-muted/50">
            <TabsTrigger value="buy-credits" className="gap-2">
              <LinkIcon className="h-4 w-4" aria-hidden="true" />
              Buy Credits
            </TabsTrigger>
            <TabsTrigger value="usage-insights" className="gap-2">
              <BarChart3 className="h-4 w-4" aria-hidden="true" />
              Usage Insights
            </TabsTrigger>
            <TabsTrigger value="billing-history" className="gap-2">
              <CreditCard className="h-4 w-4" aria-hidden="true" />
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