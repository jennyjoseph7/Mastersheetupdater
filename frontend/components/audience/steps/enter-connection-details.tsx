"use client";

import type React from "react";
import { useState, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import {
  Upload,
  X,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { DataSourceFormData } from "../add-data-source-dialog";
import { 
  uploadFileToGryd, 
  startImportTask, 
  getTaskStatus, 
  getTaskResult 
} from "@/utils/api";

interface EnterConnectionDetailsProps {
  formData: DataSourceFormData;
  updateFormData: (updates: Partial<DataSourceFormData>) => void;
}

export function EnterConnectionDetails({
  formData,
  updateFormData,
}: EnterConnectionDetailsProps) {
  const [isDragging, setIsDragging] = useState(false);
  
  const [status, setStatus] = useState<
    "idle" | "uploading" | "starting_task" | "polling" | "fetching_result" | "success" | "error"
  >("idle");
  
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isReadyForNextStep = status === "success" || status === "polling" || status === "fetching_result";

  // --- Step 3: Get Final Result ---
  const fetchTaskResult = async (taskId: string, file: File, fileUrl: string) => {
    setStatus("fetching_result");
    setStatusMessage("Finalizing data processing...");

    try {
      const data = await getTaskResult(taskId);
      
      const resultObj = data.result || data; 
      const errorUrl = resultObj.error_csv_url || resultObj.error_csv || null;
      const validRows = resultObj.preview_rows || resultObj.data || [];
      const totalCount = resultObj.total_records || resultObj.count || validRows.length;

      updateFormData({
        file: file,
        fileUrl: fileUrl,
        sourceType: "File",
        audienceSize: totalCount,
        sampleData: validRows.slice(0, 10),
        errorCsvUrl: errorUrl,
        taskId: taskId,
        taskStatus: "completed"
      });

      setStatus("success");
      setStatusMessage(errorUrl ? "Processed with warnings." : "File processed successfully!");

    } catch (error) {
      console.error("Result fetch error:", error);
      setStatus("error");
      setStatusMessage("Failed to retrieve final data.");
    }
  };

  // --- Step 2: Poll Status ---
  const pollTaskStatus = async (taskId: string, file: File, fileUrl: string) => {
    setStatus("polling");
    
    const checkStatus = async () => {
      try {
        const data = await getTaskStatus(taskId);
        console.log("Poll Status:", data); 
        
        if (data.status === "error" || data.state === "FAILURE" || data.state === "REVOKED") {
          setStatus("error");
          let errorMsg = "Task failed on server.";
          if (Array.isArray(data.error) && data.error.length > 0) {
             const firstError = data.error[0];
             if (typeof firstError === 'string') errorMsg = firstError;
             else if (typeof firstError === 'object') errorMsg = firstError._error || firstError.message || "Validation errors found.";
          } else if (typeof data.error === "string") {
            errorMsg = data.error;
          }
          setStatusMessage(errorMsg);
          return; 
        }

        if (data.status === "success" || data.state === "SUCCESS" || data.status === "completed") {
          await fetchTaskResult(taskId, file, fileUrl);
          return; 
        }

        updateFormData({ 
          taskId: taskId, 
          taskStatus: data.status || data.state || "processing" 
        });

        const currentStatus = (data.status || data.state || "").toLowerCase();
        
        if (currentStatus.includes("started") || currentStatus.includes("queued")) {
           setStatusMessage(`Task ${currentStatus}... (You can continue)`);
        } else {
           setStatusMessage(`Processing... ${currentStatus}`);
        }
        
        setTimeout(checkStatus, 2000);

      } catch (error) {
        console.error("Polling error:", error);
        setStatus("error");
        setStatusMessage("Lost connection to status server.");
      }
    };

    checkStatus();
  };

  // --- Step 1: Start Task ---
  const handleStartImportTask = async (fileUrl: string, file: File) => {
    setStatus("starting_task");
    setStatusMessage("Initiating import task...");

    try {
      // Updated to pass tags and sourceName
      const data = await startImportTask(
        formData.category,
        formData.audienceName,
        fileUrl,
        formData.tags,        // Passed to kwargs.tags
        formData.sourceName   // Passed to kwargs.source_name
      );
      
      const taskId = data.job?.task_id;

      if (!taskId) throw new Error("No Task ID returned");

      updateFormData({ 
        taskId: taskId, 
        taskStatus: "started",
        file: file,
        fileUrl: fileUrl
      });

      pollTaskStatus(taskId, file, fileUrl);

    } catch (error: any) {
      console.error("Start Task Exception:", error);
      setStatus("error");
      setStatusMessage(error.message || "Failed to start processing task.");
    }
  };

  // --- Step 0: Upload File ---
  const handleUploadFile = async (file: File) => {
    setStatus("uploading");
    setStatusMessage("Uploading file to storage...");

    try {
      const data = await uploadFileToGryd(file);

      if (data.cdn_url) {
        handleStartImportTask(data.cdn_url, file);
      } else {
        throw new Error("No CDN URL received.");
      }

    } catch (error: any) {
      console.error("Upload error:", error);
      setStatus("error");
      setStatusMessage(error.message || "Failed to upload file.");
      updateFormData({ file: null, fileUrl: undefined });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUploadFile(file);
    e.target.value = "";
  };

  const removeFile = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setStatus("idle");
    setStatusMessage(null);
    updateFormData({ file: null, fileUrl: undefined, sampleData: [], audienceSize: 0, errorCsvUrl: undefined, taskId: undefined });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Enter Connection Details</h3>
        <p className="text-sm text-muted-foreground">
          {formData.sourceType === "API" ? "API credentials" : "Upload your CSV file to import audience data"}
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="sourceName">Source Name *</Label>
          <Input
            id="sourceName"
            placeholder={formData.sourceType === "API" ? "e.g., Salesforce" : "e.g., Q4 Leads CSV"}
            value={formData.sourceName}
            onChange={(e) => updateFormData({ sourceName: e.target.value })}
          />
        </div>

        {formData.sourceType === "API" ? (
             <div className="p-4 border border-dashed rounded text-center text-muted-foreground">API Form Fields Here</div>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="file">Upload CSV File *</Label>

            {status === "idle" || status === "error" ? (
              <div className="space-y-2">
                <Card
                  className={cn("border-2 border-dashed transition-colors", status === "error" ? "border-destructive/50 bg-destructive/5" : "border-border")}
                >
                  <CardContent className="p-6">
                    <label htmlFor="file" className="flex flex-col items-center justify-center cursor-pointer w-full h-full">
                      <div className={cn("rounded-full p-4 mb-3 transition-colors", "bg-muted")}>
                        <Upload className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <p className="text-sm font-medium mb-1">Click to upload CSV</p>
                      <input id="file" ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
                    </label>
                  </CardContent>
                </Card>
                {status === "error" && (
                  <div className="text-xs text-destructive flex items-center gap-2 mt-2 font-medium">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span className="break-all">{statusMessage}</span>
                  </div>
                )}
              </div>
            ) : (
              <Card className={cn("border border-border", isReadyForNextStep && "border-green-500/50 bg-green-50/10")}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("rounded-full p-2", status === "success" ? "bg-green-100" : "bg-muted")}>
                      {status === "success" ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{formData.file?.name || "Processing..."}</p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {status === "uploading" && <span>Uploading...</span>}
                        {(status === "polling" || status === "starting_task") && (
                           <span className="flex items-center gap-1 text-primary">
                             <Clock className="w-3 h-3" /> {statusMessage}
                           </span>
                        )}
                        {status === "success" && (
                          <span className={formData.errorCsvUrl ? "text-yellow-600 font-medium" : "text-green-600"}>
                             {statusMessage || "Ready"}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {status === "success" && (
                    <button onClick={removeFile} className="text-muted-foreground hover:text-destructive p-1">
                      <X className="h-5 w-5" />
                    </button>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}