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
  ServerCog,
  CheckCircle2,
  XCircle,
  Database,
  Fingerprint,
} from "lucide-react";
import type { DataSourceFormData } from "../add-data-source-dialog";
import { APP_BASE_URL } from "@/utils/headers";
import { triggerGlobalLogout } from "@/lib/auth-context";

/* ---------------- COOKIE HELPER ---------------- */
const getCookie = (name: string) => {
  if (typeof document === "undefined") return null;

  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));

  return match ? decodeURIComponent(match.split("=")[1]) : null;
};

interface PreviewConfirmProps {
  formData: DataSourceFormData;
  updateFormData: (updates: Partial<DataSourceFormData>) => void;
}

export function PreviewConfirm({
  formData,
  updateFormData,
}: PreviewConfirmProps) {
  const [pollingStatus, setPollingStatus] = useState("Initializing...");
  const [apiHeaders, setApiHeaders] = useState<Record<string, string> | null>(
    null,
  );
  const [apiErrors, setApiErrors] = useState<any[]>([]);

  /* ---------------- LOAD COOKIES SAFELY ---------------- */
  useEffect(() => {
    const token = getCookie("gryd_token");
    const sessionId = getCookie("gryd_session_id");
    let applicationId = getCookie("gryd_application_id");

    if (!applicationId || applicationId === "gryd") {
      applicationId = "autocrm";
    }

    if (!token || !sessionId) {
      console.warn("[PreviewConfirm] Missing cookies → logging out");
      triggerGlobalLogout();
      return;
    }

    setApiHeaders({
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-GRYD-ENTERPRISE-ID": "autocrm",
      "X-GRYD-TOKEN": token,
      "X-GRYD-SESSION-ID": sessionId,
      "X-GRYD-APPLICATION-ID": applicationId,
      "X-GRYD-ROLE": "agent",
    });
  }, []);

  /* ---------------- POLLING LOGIC ---------------- */
  const shouldPoll =
    apiHeaders &&
    formData.taskId &&
    !["completed", "success", "error"].includes(formData.taskStatus || "");

  const fetchResult = async (taskId: string) => {
    try {
      setPollingStatus("Fetching final results...");

      const res = await fetch(`${APP_BASE_URL}/gryd/result/${taskId}`, {
        headers: apiHeaders!,
      });

      if (res.status === 401) {
        triggerGlobalLogout();
        return;
      }

      const rawData = await res.json();
      
      // Extract the result object from rawData (supporting single objects or arrays of responses)
      let resultObj: any = {};
      let errorsList: any[] = [];
      let csvUrl: string | null = null;

      if (Array.isArray(rawData)) {
        // Look for items with a valid result object
        const itemWithObjResult = rawData.find(
          (item) => item && typeof item.result === "object" && item.result !== null
        );
        if (itemWithObjResult) {
          resultObj = itemWithObjResult.result;
        } else {
          const itemWithResult = rawData.find((item) => item && item.result);
          if (itemWithResult) {
            resultObj = { status: itemWithResult.result };
          }
        }

        // Extract errors and CSV URLs from all items in the array
        for (const item of rawData) {
          if (!item) continue;
          if (Array.isArray(item.error)) {
            errorsList.push(...item.error);
          }
          const itemResult = item.result;
          if (itemResult) {
            if (Array.isArray(itemResult.error)) {
              errorsList.push(...itemResult.error);
            } else if (Array.isArray(itemResult.errors)) {
              errorsList.push(...itemResult.errors);
            }
            if (itemResult.error_csv_url) {
              csvUrl = itemResult.error_csv_url;
            }
          }
        }
      } else {
        resultObj = rawData.result || rawData;
        if (Array.isArray(rawData.error)) {
          errorsList = rawData.error;
        } else if (resultObj && Array.isArray(resultObj.error)) {
          errorsList = resultObj.error;
        } else if (resultObj && Array.isArray(resultObj.errors)) {
          errorsList = resultObj.errors;
        }
        if (resultObj && resultObj.error_csv_url) {
          csvUrl = resultObj.error_csv_url;
        }
      }

      if (errorsList.length > 0) {
        setApiErrors(errorsList);
      }

      const total = resultObj.total || 0;
      const processed = resultObj.processed || 0;
      const unique = resultObj.unique || 0;
      const errorCount = typeof resultObj.error === "number" 
        ? resultObj.error 
        : (errorsList.length || 0);

      updateFormData({
        taskStatus: "completed",
        audienceSize: total,
        processedCount: processed,
        errorCount: errorCount,
        uniqueCount: unique,
        sampleData: (resultObj.preview_rows || resultObj.data || []).slice(0, 10),
        errorCsvUrl: csvUrl || resultObj.error_csv_url || null,
      });
    } catch (e) {
      console.error(e);
      updateFormData({ taskStatus: "error" });
    }
  };

  useEffect(() => {
    if (!shouldPoll) return;

    let timeoutId: NodeJS.Timeout;

    const poll = async () => {
      try {
        const res = await fetch(
          `${APP_BASE_URL}/gryd/status/${formData.taskId}`,
          { headers: apiHeaders! },
        );

        if (res.status === 401) {
          triggerGlobalLogout();
          return;
        }

        const rawData = await res.json();
        
        // Find state/status and errors in potentially array responses
        let stateVal = "";
        let statusVal = "";
        let errorsList: any[] = [];

        if (Array.isArray(rawData)) {
          const activeItem = rawData.find(item => item && (item.state || item.status));
          if (activeItem) {
            stateVal = activeItem.state || "";
            statusVal = activeItem.status || "";
          }
          for (const item of rawData) {
            if (item && Array.isArray(item.error)) {
              errorsList.push(...item.error);
            }
          }
        } else {
          stateVal = rawData.state || "";
          statusVal = rawData.status || "";
          if (Array.isArray(rawData.error)) {
            errorsList = rawData.error;
          }
        }

        if (errorsList.length > 0) {
          setApiErrors(errorsList);
        }

        const currentStatus = stateVal || statusVal;

        if (
          ["FAILURE", "REVOKED", "error"].includes(currentStatus)
        ) {
          updateFormData({ taskStatus: "error" });
          return;
        }

        if (
          ["SUCCESS", "success", "completed"].includes(currentStatus)
        ) {
          fetchResult(formData.taskId!);
          return;
        }

        setPollingStatus(`Processing… ${currentStatus}`);
        timeoutId = setTimeout(poll, 2000);
      } catch {
        timeoutId = setTimeout(poll, 3000);
      }
    };

    poll();
    return () => clearTimeout(timeoutId);
  }, [shouldPoll, formData.taskId, apiHeaders]);

  /* ---------------- UI STATES ---------------- */
  if (!apiHeaders) {
    return (
      <div className="flex items-center justify-center py-16 text-muted-foreground">
        Loading session…
      </div>
    );
  }

  const isProcessing =
    formData.taskId &&
    !["completed", "error"].includes(formData.taskStatus || "");

  const hasData = formData.sampleData?.length > 0;
  const headers = hasData ? Object.keys(formData.sampleData![0]) : [];

  return (
    <div className="space-y-6">
      {isProcessing && (
        <div className="border rounded-lg p-10 text-center space-y-4">
          <ServerCog className="h-10 w-10 mx-auto animate-spin text-primary" />
          <p className="font-medium">{pollingStatus}</p>
          <Badge variant="outline">{formData.taskId}</Badge>
        </div>
      )}

      {formData.taskStatus === "error" && (
        <div className="p-6 border rounded-lg text-center text-destructive">
          <AlertTriangle className="h-10 w-10 mx-auto mb-2" />
          Processing failed.
        </div>
      )}

      {formData.taskStatus === "completed" && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total Rows"
            value={formData.audienceSize}
            icon={Database}
            variant="indigo"
          />
          <StatCard
            label="Processed"
            value={formData.processedCount}
            icon={CheckCircle2}
            variant="emerald"
          />
          <StatCard
            label="Unique"
            value={formData.uniqueCount}
            icon={Fingerprint}
            variant="violet"
          />
          <StatCard
            label="Errors"
            value={formData.errorCount}
            icon={XCircle}
            variant="rose"
          />
        </div>
      )}

      {apiErrors.length > 0 && (
        <Card className="border-destructive/30 bg-destructive/5 dark:bg-destructive/10">
          <div className="p-4 border-b border-destructive/20 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive animate-pulse" />
              <h3 className="font-semibold text-destructive">
                Row Validation Errors ({apiErrors.length})
              </h3>
            </div>
            {formData.errorCsvUrl && (
              <Button
                size="sm"
                variant="destructive"
                className="h-8 text-xs gap-1.5"
                onClick={() => window.open(formData.errorCsvUrl!, "_blank")}
              >
                <FileDown className="h-3.5 w-3.5" />
                Download Error CSV
              </Button>
            )}
          </div>
          <CardContent className="p-0">
            <div className="max-h-72 overflow-y-auto divide-y divide-destructive/10">
              {apiErrors.map((err, idx) => {
                const errMsg = err._error || "Unknown validation error";
                const rowNum = err.line_num || idx + 1;
                // Exclude system fields to only show relevant attributes
                const metadataFields = Object.entries(err).filter(
                  ([k]) => !["_error", "line_num", "campaign_id", "showroom_id", "dealership_id", "campaign_objective_id", "ddid", "role", "task", "job_id", "service", "task_id", "user_id", "publisher", "status_to", "end_timestamp", "enterprise_id", "start_timestamp", "expiry_timestamp", "published_timestamp", "result_to", "role_service"].includes(k)
                );

                return (
                  <div key={idx} className="p-4 text-sm space-y-2 hover:bg-destructive/5 transition-colors">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-destructive">
                        Row {rowNum}
                      </span>
                      {err.person_name && (
                        <span className="text-xs text-muted-foreground font-medium">
                          {err.person_name} {err.phone_number ? `(${err.phone_number})` : ""}
                        </span>
                      )}
                    </div>
                    <pre className="text-xs font-mono bg-background/50 p-2.5 rounded border border-destructive/10 text-foreground whitespace-pre-wrap leading-relaxed">
                      {errMsg.trim()}
                    </pre>
                    {metadataFields.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {metadataFields.map(([key, val]) => (
                          <span key={key} className="text-[10px] bg-muted px-2 py-0.5 rounded text-muted-foreground font-mono">
                            {key}: {String(val)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {formData.taskStatus === "completed" && (
        <>
          {formData.errorCsvUrl && apiErrors.length === 0 && (
            <Button
              variant="outline"
              onClick={() => window.open(formData.errorCsvUrl!, "_blank")}
            >
              <FileDown className="mr-2 h-4 w-4" />
              Download Error Report
            </Button>
          )}

          {hasData && (
            <Card>
              <CardContent className="pt-6 overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {headers.map((h) => (
                        <TableHead key={h}>{h}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {formData.sampleData?.map((row, i) => (
                      <TableRow key={i}>
                        {headers.map((h) => (
                          <TableCell key={h}>{String(row[h])}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/* ---------------- SMALL STAT CARD ---------------- */
interface StatCardProps {
  label: string;
  value: number | string | undefined;
  icon: any;
  variant?: "indigo" | "emerald" | "violet" | "rose";
}

function StatCard({ label, value, icon: Icon, variant = "indigo" }: StatCardProps) {
  const themes = {
    indigo: {
      bg: "bg-indigo-50/40 dark:bg-indigo-950/10",
      border: "border-indigo-100/80 dark:border-indigo-900/20",
      iconBg: "bg-indigo-100 dark:bg-indigo-900/40",
      iconColor: "text-indigo-600 dark:text-indigo-400",
      glow: "shadow-indigo-100/30 dark:shadow-indigo-950/5",
    },
    emerald: {
      bg: "bg-emerald-50/40 dark:bg-emerald-950/10",
      border: "border-emerald-100/80 dark:border-emerald-900/20",
      iconBg: "bg-emerald-100 dark:bg-emerald-900/40",
      iconColor: "text-emerald-600 dark:text-emerald-400",
      glow: "shadow-emerald-100/30 dark:shadow-emerald-950/5",
    },
    violet: {
      bg: "bg-violet-50/40 dark:bg-violet-950/10",
      border: "border-violet-100/80 dark:border-violet-900/20",
      iconBg: "bg-violet-100 dark:bg-violet-900/40",
      iconColor: "text-violet-600 dark:text-violet-400",
      glow: "shadow-violet-100/30 dark:shadow-violet-950/5",
    },
    rose: {
      bg: "bg-rose-50/40 dark:bg-rose-950/10",
      border: "border-rose-100/80 dark:border-rose-900/20",
      iconBg: "bg-rose-100 dark:bg-rose-900/40",
      iconColor: "text-rose-600 dark:text-rose-400",
      glow: "shadow-rose-100/30 dark:shadow-rose-950/5",
    },
  };

  const theme = themes[variant];

  return (
    <Card className={`overflow-hidden transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 border ${theme.bg} ${theme.border} shadow-sm ${theme.glow}`}>
      <CardContent className="p-6 flex justify-between items-center">
        <div className="space-y-1">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</p>
          <p className="text-3xl font-extrabold tracking-tight">{value !== undefined ? value : 0}</p>
        </div>
        <div className={`p-3 rounded-xl ${theme.iconBg} ${theme.iconColor} transition-transform duration-300 hover:scale-110`}>
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}
