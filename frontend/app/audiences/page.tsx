"use client";

import PageHeader from "@/components/page-header";
import { AudienceCard } from "@/components/audience-card";
import type { AudienceGroup } from "@/types/audience";
import { useRouter } from "next/navigation";

// Mock audience groups
const audienceGroups: AudienceGroup[] = [
  {
    id: "car-buyers",
    name: "Car Buyers",
    description: "Customers who have purchased vehicles",
    memberCount: 1247,
    icon: "🚗",
    color: "blue",
    gradient: "bg-gradient-to-br from-blue-400 to-blue-600",
  },
  {
    id: "service-customers",
    name: "Service Customers",
    description: "Regular service and maintenance customers",
    memberCount: 3421,
    icon: "🔧",
    color: "green",
    gradient: "bg-gradient-to-br from-green-400 to-green-600",
  },
  {
    id: "test-drive",
    name: "Test Drive Requests",
    description: "Leads who requested test drives",
    memberCount: 892,
    icon: "🏁",
    color: "purple",
    gradient: "bg-gradient-to-br from-purple-400 to-purple-600",
  },
  {
    id: "financing",
    name: "Financing Inquiries",
    description: "Customers interested in financing options",
    memberCount: 654,
    icon: "💳",
    color: "orange",
    gradient: "bg-gradient-to-br from-orange-400 to-orange-600",
  },
  {
    id: "trade-in",
    name: "Trade-In Leads",
    description: "Customers looking to trade in vehicles",
    memberCount: 421,
    icon: "🔄",
    color: "indigo",
    gradient: "bg-gradient-to-br from-indigo-400 to-indigo-600",
  },
  {
    id: "vip",
    name: "VIP Customers",
    description: "High-value and premium customers",
    memberCount: 187,
    icon: "⭐",
    color: "yellow",
    gradient: "bg-gradient-to-br from-yellow-400 to-yellow-600",
  },
];

export default function AudiencesPage() {
  const router = useRouter();

  // Navigate to detail page on click
  const handleAudienceClick = (audience: AudienceGroup) => {
    router.push(`/audiences/${audience.id}`);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex h-20 items-center px-6 md:px-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audiences</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Explore and manage your customer segments
          </p>
        </div>
      </div>
      <main className="flex-1 space-y-6 p-6 md:p-8 w-full">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {audienceGroups.map((audience) => (
            <AudienceCard
              key={audience.id}
              {...audience}
              isSelected={false}
              onClick={() => handleAudienceClick(audience)}
            />
          ))}
        </div>
      </main>
    </div>
  );
}
