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
    null
  );

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

      const res = await fetch(
        `${APP_BASE_URL}/gryd/result/${taskId}`,
        { headers: apiHeaders! }
      );

      if (res.status === 401) {
        triggerGlobalLogout();
        return;
      }

      const data = await res.json();
      const result = data.result || data;

      updateFormData({
        taskStatus: "completed",
        audienceSize: result.total || 0,
        processedCount: result.processed || 0,
        errorCount: result.error || 0,
        uniqueCount: result.unique || 0,
        sampleData: (result.preview_rows || result.data || []).slice(0, 10),
        errorCsvUrl: result.error_csv_url || null,
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
          { headers: apiHeaders! }
        );

        if (res.status === 401) {
          triggerGlobalLogout();
          return;
        }

        const data = await res.json();

        if (["FAILURE", "REVOKED", "error"].includes(data.state || data.status)) {
          updateFormData({ taskStatus: "error" });
          return;
        }

        if (["SUCCESS", "success", "completed"].includes(data.state || data.status)) {
          fetchResult(formData.taskId!);
          return;
        }

        setPollingStatus(`Processing… ${data.state || data.status}`);
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
  const headers = hasData
    ? Object.keys(formData.sampleData![0])
    : [];

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
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard label="Total Rows" value={formData.audienceSize} icon={Database} />
            <StatCard label="Processed" value={formData.processedCount} icon={CheckCircle2} />
            <StatCard label="Unique" value={formData.uniqueCount} icon={Fingerprint} />
            <StatCard label="Errors" value={formData.errorCount} icon={XCircle} />
          </div>

          {formData.errorCsvUrl && (
            <Button
              variant="outline"
              onClick={() => window.open(formData.errorCsvUrl!, "_blank")}
            >
              <FileDown className="mr-2 h-4 w-4" />
              Download Error Report
            </Button>
          )}

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
        </>
      )}
    </div>
  );
}

/* ---------------- SMALL STAT CARD ---------------- */
function StatCard({ label, value, icon: Icon }: any) {
  return (
    <Card>
      <CardContent className="pt-6 flex justify-between items-center">
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-3xl font-bold">{value || 0}</p>
        </div>
        <Icon className="h-6 w-6 text-muted-foreground" />
      </CardContent>
    </Card>
  );
}
