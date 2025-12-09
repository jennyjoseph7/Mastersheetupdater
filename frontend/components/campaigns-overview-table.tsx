"use client";

import { useRouter } from "next/navigation";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Eye, Download } from "lucide-react";
import type { Campaign } from "@/types/campaign";

interface CampaignsOverviewTableProps {
  campaigns: Campaign[];
}

export function CampaignsOverviewTable({
  campaigns,
}: CampaignsOverviewTableProps) {
  const router = useRouter();

  const handleViewAnalytics = (campaign: Campaign) => {
    router.push(`/conversions/analytics/${campaign.id}`);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Live":
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400";
      case "Completed":
        return "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400";
      case "Paused":
        return "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400";
      case "Draft":
        return "bg-gray-100 text-gray-700 dark:bg-gray-950 dark:text-gray-400";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getChannelColor = (channel: string) => {
    switch (channel) {
      case "WhatsApp":
        return "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400";
      case "Email":
        return "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400";
      case "SMS":
        return "bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400";
      case "Voice":
        return "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  return (
    <>
      <Card className="shadow-lg">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl font-bold">
                Campaigns Conversions
              </CardTitle>
              <CardDescription className="mt-1">
                View and manage all your campaigns
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 bg-transparent"
            >
              <Download className="h-4 w-4" />
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-3 text-left text-sm font-semibold">
                    Campaign Name
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">
                    Created On
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">
                    Channels Used
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">
                    Status
                  </th>
                  <th className="px-4 py-3 text-center text-sm font-semibold">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((campaign) => (
                  <tr
                    key={campaign.id}
                    className="border-b border-border hover:bg-muted/50 transition-colors"
                  >
                    <td className="px-4 py-4 font-medium">{campaign.name}</td>
                    <td className="px-4 py-4 text-sm text-muted-foreground">
                      {new Date(campaign.createdOn).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-1">
                        {campaign.channelsUsed.map((channel) => (
                          <Badge
                            key={channel}
                            variant="secondary"
                            className={`text-xs ${getChannelColor(channel)}`}
                          >
                            {channel}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <Badge className={getStatusColor(campaign.status)}>
                        {campaign.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-4 text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewAnalytics(campaign)}
                        className="gap-2 hover:bg-primary/10"
                      >
                        <Eye className="h-4 w-4" />
                        View Analytics
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
