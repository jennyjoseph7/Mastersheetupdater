"use client";

import type React from "react";
import { useState, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import {
  Upload,
  AlertCircle,
  Loader2,
  CheckCircle2,
  FileJson,
  FileSpreadsheet,
} from "lucide-react";
import * as XLSX from "xlsx";
import { cn } from "@/lib/utils";
import type { DataSourceFormData } from "../add-data-source-dialog";
import { 
  uploadFileToGryd, 
  extractCsvHeadersAPI, 
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
  const [status, setStatus] = useState<
    "idle" | "uploading" | "extracting" | "polling" | "success" | "error"
  >("idle");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Step 3: Get Headers Result ---
  const fetchHeadersResult = async (taskId: string, file: File, fileUrl: string) => {
    try {
      const data = await getTaskResult(taskId);
      const rawResult = data.result || data;
      const headers = Array.isArray(rawResult) ? rawResult : (rawResult.headers || []);

      if (!headers || headers.length === 0) throw new Error("No headers found in CSV.");

      updateFormData({
        file: file,
        fileUrl: fileUrl,
        sourceType: "csv",
        extractedHeaders: headers,
        fieldMappings: headers.map((h: string, i: number) => ({
            id: `map_${i}`,
            sourceField: h,
            targetField: h,
            enabled: true
        }))
      });

      setStatus("success");
      setStatusMessage("Headers extracted successfully!");

    } catch (error: any) {
      console.error("Header fetch error:", error);
      setStatus("error");
      setStatusMessage(error.message || "Failed to retrieve CSV headers.");
    }
  };

  // --- Step 2: Poll Header Extraction ---
  const pollHeaderStatus = async (taskId: string, file: File, fileUrl: string) => {
    setStatus("polling");
    
    const checkStatus = async () => {
      try {
        const data = await getTaskStatus(taskId);
        
        // --- SAFE ERROR HANDLING FIX ---
        if (data.status === "error" || data.state === "FAILURE" || data.state === "REVOKED") {
          setStatus("error");
          
          let errorMsg = "Header extraction failed.";
          
          // Check if error is in an array
          if (Array.isArray(data.error) && data.error.length > 0) {
             const firstErr = data.error[0];
             if (typeof firstErr === 'string') {
               errorMsg = firstErr;
             } else if (typeof firstErr === 'object' && firstErr !== null) {
               // Safely access properties: _error, message, error
               errorMsg = (firstErr as any)._error || (firstErr as any).message || (firstErr as any).error || "Validation error in CSV.";
             }
          } 
          // Check if error is a direct object
          else if (typeof data.error === 'object' && data.error !== null) {
             errorMsg = (data.error as any)._error || (data.error as any).message || "Unknown error object.";
          }
          // Check if error is a string
          else if (typeof data.error === 'string') {
             errorMsg = data.error;
          }

          // Truncate if message is too long
          if (errorMsg.length > 120) errorMsg = errorMsg.substring(0, 120) + "...";

          setStatusMessage(errorMsg);
          return;
        }

        if (data.status === "success" || data.state === "SUCCESS") {
          await fetchHeadersResult(taskId, file, fileUrl);
          return; 
        }

        setStatusMessage(`Extracting headers...`);
        setTimeout(checkStatus, 1500);

      } catch (error) {
        console.error("Polling error:", error);
        setStatus("error");
        setStatusMessage("Connection lost.");
      }
    };
    checkStatus();
  };

  // --- Step 1: Start Header Extraction ---
  const handleExtractHeaders = async (fileUrl: string, file: File) => {
    setStatus("extracting");
    setStatusMessage("Analyzing CSV file...");

    try {
      const data = await extractCsvHeadersAPI(fileUrl);
      const taskId = data.job?.task_id;

      if (!taskId) throw new Error("No Task ID returned for header extraction");

      pollHeaderStatus(taskId, file, fileUrl);

    } catch (error: any) {
      console.error("Extraction start error:", error);
      setStatus("error");
      setStatusMessage(error.message || "Failed to start analysis.");
    }
  };

  // --- Step 0: Upload File ---
  const handleUploadFile = async (file: File) => {
    setStatus("uploading");
    setStatusMessage("Uploading file...");

    try {
      const data = await uploadFileToGryd(file);
      if (data.cdn_url) {
        handleExtractHeaders(data.cdn_url, file);
      } else {
        throw new Error("No CDN URL received.");
      }
    } catch (error: any) {
      console.error("Upload error:", error);
      setStatus("error");
      setStatusMessage(error.message || "Upload failed.");
      updateFormData({ file: null, fileUrl: undefined });
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    
    if (fileExtension === 'xls' || fileExtension === 'xlsx') {
      setStatus("uploading");
      setStatusMessage("Converting Excel to CSV...");
      try {
        const data = await file.arrayBuffer();
        const workbook = XLSX.read(data);
        const worksheet = workbook.Sheets[workbook.SheetNames[0]];
        const csvContent = XLSX.utils.sheet_to_csv(worksheet);
        
        // Create a new File object from the CSV content
        const csvBlob = new Blob([csvContent], { type: 'text/csv' });
        const csvFileName = file.name.replace(/\.(xls|xlsx)$/i, '.csv');
        const csvFile = new File([csvBlob], csvFileName, { type: 'text/csv' });
        
        handleUploadFile(csvFile);
      } catch (error: any) {
        console.error("Excel conversion error:", error);
        setStatus("error");
        setStatusMessage("Failed to convert Excel file.");
      }
    } else {
      handleUploadFile(file);
    }
    
    e.target.value = "";
  };

  const removeFile = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setStatus("idle");
    setStatusMessage(null);
    updateFormData({ 
        file: null, 
        fileUrl: undefined, 
        extractedHeaders: [],
        fieldMappings: []
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Upload Data Source</h3>
        <p className="text-sm text-muted-foreground">
          Upload your CSV or Excel file. We will analyze the headers for mapping.
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
            <Label htmlFor="sourceName">Source Name *</Label>
            <Input
            id="sourceName"
            placeholder="e.g., Q4 Leads CSV"
            value={formData.sourceName}
            onChange={(e) => updateFormData({ sourceName: e.target.value })}
            />
        </div>

        <div className="space-y-2">
            <Label htmlFor="file">Upload CSV or Excel File *</Label>
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
                      <p className="text-sm font-medium mb-1">Click to upload CSV or Excel</p>
                      <input id="file" ref={fileInputRef} type="file" accept=".csv,.xls,.xlsx" className="hidden" onChange={handleFileChange} />
                    </label>
                  </CardContent>
                </Card>
                {status === "error" && (
                  <div className="text-xs text-destructive flex items-start gap-2 mt-2 font-medium">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span className="break-all">{statusMessage}</span>
                  </div>
                )}
              </div>
            ) : (
              <Card className={cn("border border-border", status === "success" && "border-green-500/50 bg-green-50/10")}>
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
                        {status !== "success" && (
                           <span className="flex items-center gap-1 text-primary">
                             <FileSpreadsheet className="w-3 h-3" /> {statusMessage}
                           </span>
                        )}
                        {status === "success" && (
                          <span className="text-green-600 font-medium">
                             Analysis Complete. {formData.extractedHeaders.length} columns found.
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {status === "success" && (
                    <button onClick={removeFile} className="text-muted-foreground hover:text-destructive p-1">
                      <AlertCircle className="w-5 h-5" />
                    </button>
                  )}
                </CardContent>
              </Card>
            )}
        </div>
      </div>
    </div>
  );
}