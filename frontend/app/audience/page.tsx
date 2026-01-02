"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Plus, RefreshCcw } from "lucide-react";
import { DataSourcesDataTable } from "@/components/audience/data-sources-datatable";
import { AddDataSourceDialog } from "@/components/audience/add-data-source-dialog";
// Ensure updateAudienceTask is imported
import { fetchAudienceTasks, getTaskStatus, getTaskResult, updateAudienceTask } from "@/utils/api";

export interface DataSource {
  id: string;          
  taskId: string;      
  sourceName: string;
  audienceName: string;
  type: string;
  audienceSize: number;
  lastSynced: string;
  status: "Connected" | "Error" | "Expired" | "Pending" | "Processing" | "Completed" | "Failed";
  tags?: string[];
  errorDetails?: any[]; 
}

export default function AudiencePage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Map backend string to frontend badge status
  const mapBackendStatus = (status: string): DataSource["status"] => {
    if (!status) return "Pending";
    const s = status.toLowerCase();
    
    // Explicitly mapping success/completed to "Connected"
    if (s === "completed" || s === "success" || s === "connected") return "Connected";
    if (s === "started" || s === "processing" || s === "in_progress") return "Processing";
    if (s === "error" || s === "failed" || s === "failure") return "Error";
    if (s === "expired") return "Expired";
    
    return "Pending";
  };

  const loadData = async () => {
    setIsLoading(true);
    try {
      const { items } = await fetchAudienceTasks();
      
      const mappedData: DataSource[] = items.map((item: any) => ({
        id: item.audience_task_id || item._id, 
        taskId: item.task_id, 
        sourceName: item.source_name || "Unknown Source",
        audienceName: item.audience_name || "Untitled Audience",
        type: item.source_type || "File", 
        audienceSize: item.process_size || item.audience_size_csv || 0,
        lastSynced: item.updated ? new Date(item.updated * 1000).toISOString() : new Date().toISOString(), 
        status: mapBackendStatus(item.csv_status),
        tags: item.tags || [],
        errorDetails: item.error_details || [] 
      }));

      setDataSources(mappedData);
    } catch (error) {
      console.error("Failed to load audience tasks", error);
    } finally {
      setIsLoading(false);
    }
  };

  // --- REFRESH LOGIC (Sync Status) ---
  const handleRefreshRow = async (rowId: string) => {
    const row = dataSources.find((d) => d.id === rowId);
    
    // We need the UUID (taskId) for the Status API calls
    if (!row || !row.taskId) {
      console.error("No Task ID found for row", rowId);
      return;
    }

    try {
      // 1. Fetch Status from Task Queue
      const statusData = await getTaskStatus(row.taskId);
      
      let newStatus: DataSource["status"] = "Pending";
      let backendStatusString = "pending";
      let errorList: any[] = [];

      // 2. Logic: Check for Errors First
      if (
          (statusData.error && Array.isArray(statusData.error) && statusData.error.length > 0) ||
          statusData.status === "error" || 
          statusData.state === "FAILURE" || 
          statusData.state === "REVOKED"
      ) {
         newStatus = "Error";
         backendStatusString = "error";
         if (statusData.error) {
            errorList = Array.isArray(statusData.error) ? statusData.error : [statusData.error];
         }
      } 
      else if (statusData.status === "success" || statusData.state === "SUCCESS") {
         newStatus = "Connected"; 
         backendStatusString = "connected"; 
      } 
      else {
         newStatus = "Processing";
         backendStatusString = (statusData.status || statusData.state || "processing").toLowerCase();
      }

      let newSize = row.audienceSize;
      let errorCsvLink = "";

      // 3. If Connected, fetch result details
      if (newStatus === "Connected") {
          try {
             const resultData = await getTaskResult(row.taskId);
             const result = resultData.result || resultData;
             
             if (result.processed !== undefined) newSize = result.processed;
             else if (result.total !== undefined) newSize = result.total;
             
             if (result.error_csv || result.error_csv_url) {
                errorCsvLink = result.error_csv || result.error_csv_url;
             }
          } catch (resError) {
             console.error("Failed to fetch result details", resError);
          }
      }

      // 4. UPDATE DB (Using updateAudienceTask PATCH)
      const updatePayload: any = {
          csv_status: backendStatusString,
          process_size: newSize,
      };

      // Also update model audience_size if connected
      if (newStatus === "Connected") {
        updatePayload.audience_size = newSize;
      }
      
      if (errorCsvLink) updatePayload.error_csv_link = errorCsvLink;

      try {
        // Using the imported PATCH function
        await updateAudienceTask(row.id, updatePayload);
      } catch (dbError) {
        console.error("Failed to update audience task in DB", dbError);
      }

      // 5. Update Local UI State
      setDataSources((prev) => 
        prev.map((item) => {
          if (item.id === rowId) {
            return { 
                ...item, 
                status: newStatus,
                audienceSize: newSize,
                lastSynced: newStatus === "Connected" ? new Date().toISOString() : item.lastSynced,
                errorDetails: errorList 
            };
          }
          return item;
        })
      );
    } catch (error) {
      console.error(`Failed to refresh row ${rowId}`, error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // --- SAVE LOGIC (Using updateAudienceTask PATCH) ---
  // Updated to accept taskId and the data payload
  const handleSaveDataSource = async (taskId?: string, updatedValues?: any) => {
    setIsDialogOpen(false);

    // Only attempt PATCH if we have an ID and data
    if (taskId && updatedValues) {
      try {
        await updateAudienceTask(taskId, updatedValues);
      } catch (error) {
        console.error("Failed to patch audience task", error);
        // You might want to show a toast error here
      }
    }
    
    // Refresh to show changes
    setTimeout(() => loadData(), 500); 
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audience Data Sources</h1>
          <p className="text-muted-foreground">
            Manage your connected data sources and audience lists.
          </p>
        </div>
        <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={loadData} title="Refresh List">
                <RefreshCcw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={() => setIsDialogOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Data Source
            </Button>
        </div>
      </div>

      {isLoading && dataSources.length === 0 ? (
         <div className="flex items-center justify-center h-64 border rounded-lg bg-card">
            <p className="text-muted-foreground">Loading audiences...</p>
         </div>
      ) : (
        <DataSourcesDataTable
          data={dataSources}
          onRemove={(id) => console.log("Remove", id)}
          onResync={(id) => console.log("Resync", id)}
          onRefreshStatus={handleRefreshRow} 
        />
      )}

      <AddDataSourceDialog
        isOpen={isDialogOpen}
        onClose={() => { handleSaveDataSource(); setIsDialogOpen(false); }}
        onSave={() => handleSaveDataSource()}
      />
    </div>
  );
}