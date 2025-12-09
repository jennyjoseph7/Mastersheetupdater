"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw } from "lucide-react";
import type { DataSource } from "@/app/audience/page";

interface StatusCellProps {
  status: DataSource["status"];
  sourceId: string;
  onRefreshStatus?: (id: string) => Promise<void>;
}

const getStatusBadge = (status: DataSource["status"]) => {
  const statusLower = status?.toLowerCase() || "";

  switch (statusLower) {
    case "connected":
      return (
        <Badge className="bg-emerald-500 hover:bg-emerald-600">Connected</Badge>
      );
    case "error":
    case "failed":
      return <Badge variant="destructive">Error</Badge>;
    case "expired":
      return (
        <Badge
          variant="outline"
          className="bg-orange-50 text-orange-700 border-orange-300"
        >
          Expired
        </Badge>
      );
    case "pending":
      return (
        <Badge
          variant="outline"
          className="bg-yellow-50 text-yellow-700 border-yellow-300"
        >
          Pending
        </Badge>
      );
    case "processing":
    case "in_progress":
      return (
        <Badge
          variant="outline"
          className="bg-blue-50 text-blue-700 border-blue-300"
        >
          Processing
        </Badge>
      );
    case "completed":
    case "success":
      return (
        <Badge className="bg-emerald-500 hover:bg-emerald-600">Completed</Badge>
      );
    default:
      // Capitalize first letter for display
      const displayStatus = status
        ? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
        : "Unknown";
      return <Badge variant="outline">{displayStatus}</Badge>;
  }
};

export function StatusCell({
  status,
  sourceId,
  onRefreshStatus,
}: StatusCellProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (onRefreshStatus && !isRefreshing) {
      setIsRefreshing(true);
      try {
        await onRefreshStatus(sourceId);
      } catch (error) {
        console.error("Error refreshing status:", error);
      } finally {
        setIsRefreshing(false);
      }
    }
  };

  return (
    <div className="flex items-center gap-2">
      {getStatusBadge(status)}
      {onRefreshStatus && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={handleRefresh}
          disabled={isRefreshing}
          title="Refresh status"
        >
          <RefreshCw
            className={`h-3 w-3 ${isRefreshing ? "animate-spin" : ""}`}
          />
        </Button>
      )}
    </div>
  );
}
