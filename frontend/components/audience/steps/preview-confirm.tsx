"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertTriangle,
  FileDown,
  Loader2,
  ServerCog,
  CheckCircle2,
  XCircle,
  Database,
} from "lucide-react";
import type { DataSourceFormData } from "../add-data-source-dialog";
import { APP_BASE_URL } from "@/utils/headers";
import { triggerGlobalLogout } from "@/lib/auth-context"; // 👈 Import global logout

const getCookie = (name: string) => {
  if (typeof document === "undefined") return null;

  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));

  return match ? match.split("=")[1] : null;
};

// Configuration
const BASE_URL = APP_BASE_URL;

// Get credentials from browser cookies
let token = getCookie("gryd_token");
let sessionId = getCookie("gryd_session_id");
let applicationId = getCookie("gryd_application_id");

// CRITICAL FIX: Always use "autocrm", never "gryd"
if (applicationId === "gryd" || !applicationId) {
  applicationId = "autocrm";
}

// --- UPDATED: No Hardcoded Fallback ---
if (!token || !sessionId) {
  console.warn("[PreviewConfirm] Missing credentials. API calls may fail 401.");
}

const API_HEADERS = {
  "Content-Type": "application/json",
  "Accept": "application/json",
  "X-GRYD-ENTERPRISE-ID": "autocrm",
  "X-GRYD-TOKEN": token || "", // Ensure string
  "X-GRYD-SESSION-ID": sessionId || "", // Ensure string
  "X-GRYD-APPLICATION-ID": applicationId || "autocrm",
  "X-GRYD-ROLE": "agent",
};

interface PreviewConfirmProps {
  formData: DataSourceFormData;
  updateFormData: (updates: Partial<DataSourceFormData>) => void;
}

export function PreviewConfirm({ formData, updateFormData }: PreviewConfirmProps) {
  const [pollingStatus, setPollingStatus] = useState<string>("Checking status...");

  // Logic to determine if we need to poll
  const shouldPoll =
    formData.taskId &&
    formData.taskStatus !== "completed" &&
    formData.taskStatus !== "success" &&
    formData.taskStatus !== "error";

  // --- 1. Fetch Result (Once Success) ---
  const fetchResult = async (taskId: string) => {
    setPollingStatus("Fetching final results...");
    try {
      const response = await fetch(`${BASE_URL}/gryd/result/${taskId}`, {
        headers: API_HEADERS,
      });

      // 🚨 Auto-Logout Check
      if (response.status === 401) {
        triggerGlobalLogout();
        return;
      }

      const data = await response.json();
      console.log("Preview Result:", data);

      const resultObj = data.result || data;

      // Map specific counts from the result object as per user requirement
      const total = resultObj.total || 0;
      const processed = resultObj.processed || 0;
      const errorCount = resultObj.error || 0;
      
      const errorUrl = resultObj.error_csv_url || resultObj.error_csv || null;
      const previewRows = resultObj.preview_rows || resultObj.data || [];

      updateFormData({
        taskStatus: "completed",
        audienceSize: total,
        processedCount: processed,
        errorCount: errorCount,
        sampleData: previewRows.slice(0, 10),
        errorCsvUrl: errorUrl,
      });
    } catch (err) {
      console.error("Error fetching result:", err);
      updateFormData({ taskStatus: "error" });
    }
  };

  // --- 2. Poll Status ---
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;
    let isMounted = true;

    const checkStatus = async () => {
      if (!shouldPoll || !formData.taskId) return;

      try {
        const response = await fetch(
          `${BASE_URL}/gryd/status/${formData.taskId}`,
          { headers: API_HEADERS }
        );

        // 🚨 Auto-Logout Check
        if (response.status === 401) {
          triggerGlobalLogout();
          return;
        }

        const data = await response.json();

        if (!isMounted) return;

        // Check for specific error array/object
        if (
          data.status === "error" ||
          data.state === "FAILURE" ||
          data.state === "REVOKED"
        ) {
          updateFormData({ taskStatus: "error" });
          return;
        }

        // Check for success
        if (
          data.status === "success" ||
          data.state === "SUCCESS" ||
          data.status === "completed"
        ) {
          fetchResult(formData.taskId);
          return;
        }

        // Still processing
        setPollingStatus(
          `Processing... ${data.status || data.state || ""}`
        );
        
        // Poll again
        timeoutId = setTimeout(checkStatus, 2000);
      } catch (err) {
        console.error("Polling error:", err);
        // Don't kill the loop immediately on one network error, maybe retry
        timeoutId = setTimeout(checkStatus, 3000);
      }
    };

    if (shouldPoll) {
      checkStatus();
    }

    return () => {
      isMounted = false;
      clearTimeout(timeoutId);
    };
  }, [shouldPoll, formData.taskId]); // Removed updateFormData from deps to avoid loop

  // --- Render Helpers ---
  const hasRealData = formData.sampleData && formData.sampleData.length > 0;
  const displayData = hasRealData ? formData.sampleData : [];
  const headers = hasRealData
    ? Object.keys(displayData[0])
    : ["Name", "Email", "Phone"];
  
  const isProcessing = formData.taskStatus !== "completed" && formData.taskStatus !== "error" && formData.taskId;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold mb-2">Preview & Confirm</h3>
          <p className="text-sm text-muted-foreground">
            Review the processed data below.
          </p>
        </div>
      </div>

      {/* 1. PROCESSING STATE */}
      {isProcessing && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-8 flex flex-col items-center justify-center text-center space-y-4">
          <div className="relative">
            <div className="absolute inset-0 bg-blue-400/30 blur-xl rounded-full animate-pulse" />
            <div className="bg-background dark:bg-card p-4 rounded-full relative shadow-sm border border-blue-100 dark:border-blue-800">
              <ServerCog className="h-8 w-8 text-blue-600 dark:text-blue-400 animate-spin-slow" />
            </div>
          </div>
          <div>
            <h4 className="text-lg font-semibold text-blue-950 dark:text-blue-100">
              Processing Data
            </h4>
            <p className="text-blue-600 dark:text-blue-300 mt-1">
              {pollingStatus}
            </p>
          </div>
          <Badge variant="outline" className="font-mono text-xs bg-background/50">
            Task ID: {formData.taskId}
          </Badge>
        </div>
      )}

      {/* 2. ERROR STATE (System Error) */}
      {formData.taskStatus === "error" && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-6 text-center text-destructive">
            <AlertTriangle className="h-10 w-10 mx-auto mb-3" />
            <h4 className="font-semibold">Processing Failed</h4>
            <p className="text-sm mt-1">The server encountered an error processing your file.</p>
        </div>
      )}

      {/* 3. COMPLETED STATE (Success) */}
      {!isProcessing && formData.taskStatus === "completed" && (
        <>
          {/* Detailed Statistics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Total Records */}
            <Card className="bg-card">
              <CardContent className="pt-6 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Total Rows
                  </p>
                  <div className="text-3xl font-bold mt-1">
                    {formData.audienceSize?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="bg-primary/10 p-3 rounded-full">
                  <Database className="h-5 w-5 text-primary" />
                </div>
              </CardContent>
            </Card>

            {/* Processed Successfully */}
            <Card className="bg-green-50/50 dark:bg-green-900/10 border-green-200/50 dark:border-green-900/50">
              <CardContent className="pt-6 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-green-700 dark:text-green-400 uppercase tracking-wider">
                    Processed
                  </p>
                  <div className="text-3xl font-bold text-green-700 dark:text-green-400 mt-1">
                    {formData.processedCount?.toLocaleString() || 0}
                  </div>
                </div>
                <div className="bg-green-100 dark:bg-green-900/40 p-3 rounded-full">
                  <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
              </CardContent>
            </Card>

            {/* Errors */}
            <Card className={`${(formData.errorCount || 0) > 0 ? "bg-red-50/50 dark:bg-red-900/10 border-red-200/50 dark:border-red-900/50" : "bg-card"}`}>
              <CardContent className="pt-6 flex items-center justify-between">
                <div>
                  <p className={`text-xs font-medium uppercase tracking-wider ${(formData.errorCount || 0) > 0 ? "text-red-700 dark:text-red-400" : "text-muted-foreground"}`}>
                    Errors
                  </p>
                  <div className={`text-3xl font-bold mt-1 ${(formData.errorCount || 0) > 0 ? "text-red-700 dark:text-red-400" : ""}`}>
                    {formData.errorCount?.toLocaleString() || 0}
                  </div>
                </div>
                <div className={`${(formData.errorCount || 0) > 0 ? "bg-red-100 dark:bg-red-900/40" : "bg-muted"} p-3 rounded-full`}>
                  <XCircle className={`h-5 w-5 ${(formData.errorCount || 0) > 0 ? "text-red-600 dark:text-red-400" : "text-muted-foreground"}`} />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Validation Error Banner */}
          {formData.errorCsvUrl && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-900 rounded-lg p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-yellow-100 dark:bg-yellow-900/40 rounded-full shrink-0">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-500" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-yellow-800 dark:text-yellow-500">
                    Validation Issues Found
                  </h4>
                  <p className="text-xs text-yellow-700 dark:text-yellow-400 mt-1">
                    Some records could not be processed. Download the error report
                    to fix them.
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="border-yellow-300 bg-yellow-100 text-yellow-900 hover:bg-yellow-200 shrink-0"
                onClick={() => window.open(formData.errorCsvUrl, "_blank")}
              >
                <FileDown className="h-4 w-4 mr-2" />
                Download Report
              </Button>
            </div>
          )}

          {/* Data Preview Table */}
          <Card>
            <CardContent className="pt-6">
              <div className="mb-4">
                <h4 className="text-base font-semibold mb-1">Data Preview</h4>
                <p className="text-xs text-muted-foreground">
                  Showing first {displayData.length} valid records.
                </p>
              </div>

              <div className="rounded-md border overflow-x-auto max-w-[calc(100vw-4rem)] sm:max-w-none">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {headers.map((key) => (
                        <TableHead key={key} className="capitalize whitespace-nowrap">
                          {key.replace(/_/g, " ")}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {hasRealData ? (
                      displayData.map((row, index) => (
                        <TableRow key={index}>
                          {headers.map((key, i) => (
                            <TableCell
                              key={i}
                              className="whitespace-nowrap max-w-[200px] truncate"
                              title={String(row[key])}
                            >
                              {String(row[key])}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell
                          colSpan={headers.length}
                          className="text-center h-24 text-muted-foreground"
                        >
                          No preview data available.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}