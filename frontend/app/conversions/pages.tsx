"use client";

import { useState, useEffect } from "react";
import PageHeader from "@/components/page-header";
import { CampaignsOverviewTable } from "@/components/campaigns-overview-table";
import type { Campaign } from "@/types/campaign";
import { ProtectedRoute } from "@/components/protected-route";

// Sample campaigns data
const sampleCampaigns: Campaign[] = [
  {
    id: "CPG001",
    name: "Summer Insurance Promo 2024",
    createdOn: "2024-01-15",
    channelsUsed: ["WhatsApp", "Email", "SMS"],
    status: "Live",
    totalLeads: 320,
    conversions: 87,
    budget: 50000,
  },
  {
    id: "CPG002",
    name: "Health Coverage Campaign",
    createdOn: "2024-01-10",
    channelsUsed: ["Email", "Voice"],
    status: "Completed",
    totalLeads: 245,
    conversions: 68,
    budget: 35000,
  },
  {
    id: "CPG003",
    name: "Life Insurance Awareness",
    createdOn: "2024-01-20",
    channelsUsed: ["Email", "WhatsApp", "Voice"],
    status: "Live",
    totalLeads: 180,
    conversions: 52,
    budget: 42000,
  },
];

export default function ConversionsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  useEffect(() => {
    // In production, fetch from API
    setCampaigns(sampleCampaigns);
  }, []);

  return (
    <ProtectedRoute>
      <div className="flex min-h-screen flex-col">
        <div className="flex h-20 items-center px-6 md:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Conversions
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Here you get all your people how replied to you
            </p>
          </div>
        </div>

        <main className="flex-1 space-y-6 px-6 md:px-8 pb-8 w-full">
          <CampaignsOverviewTable campaigns={campaigns} />
        </main>
      </div>
    </ProtectedRoute>
  );
}
