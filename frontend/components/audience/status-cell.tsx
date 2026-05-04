"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RefreshCw, Info, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { DataSource } from "@/app/audience/page";

interface StatusCellProps {
  status: DataSource["status"];
  sourceId: string;
  errorDetails?: any[];
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
        <Badge className="bg-emerald-500 hover:bg-emerald-600">Connected</Badge>
      );
    default:
      const displayStatus = status
        ? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
        : "Unknown";
      return <Badge variant="outline">{displayStatus}</Badge>;
  }
};

export function StatusCell({
  status,
  sourceId,
  errorDetails,
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

  const hasErrors = errorDetails && errorDetails.length > 0;

  return (
    <div className="flex items-center gap-2">
      {getStatusBadge(status)}
      
      {onRefreshStatus && (status === "Processing" || status === "Pending") && (
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
          onClick={handleRefresh}
          disabled={isRefreshing}
          title="Refresh status"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`}
          />
        </Button>
      )}

      {hasErrors && (
        <Dialog>
          <DialogTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0 text-amber-500 hover:text-amber-600 hover:bg-amber-50"
              title="View Issues"
            >
              <Info className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] flex flex-col">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-5 w-5" />
                Processing Issues Found
              </DialogTitle>
            </DialogHeader>
            <div className="flex-1 overflow-y-auto mt-2 p-4 bg-muted/30 rounded-md border text-sm font-mono whitespace-pre-wrap">
              {errorDetails?.map((err, idx) => {
                if (typeof err === "string") return <div key={idx} className="mb-4 pb-4 border-b last:border-0">{err}</div>;
                
                const errorMsg = err._error || err.message || JSON.stringify(err, null, 2);
                const lineInfo = err.line_num ? `Row ${err.line_num}: ` : "";
                
                return (
                  <div key={idx} className="mb-4 pb-4 border-b border-border/50 last:border-0 last:mb-0 last:pb-0">
                    <div className="font-semibold text-destructive mb-1">
                      {lineInfo}Issue Detected
                    </div>
                    <div className="text-muted-foreground">{errorMsg}</div>
                    {err.dealership_id && <div className="text-xs mt-1 text-muted-foreground/70">Dealership ID: {err.dealership_id}</div>}
                  </div>
                );
              })}
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}