"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, Database, Loader2 } from "lucide-react";
import { DataSourcesDataTable } from "@/components/audience/data-sources-datatable";
import { AddDataSourceDialog } from "@/components/audience/add-data-source-dialog";
// Using Next.js API route instead of direct external API call to avoid CORS issues

export interface DataSource {
  id: string;
  sourceName: string;
  audienceName: string;
  tags?: string[];
  type: "API" | "File" | "CSV";
  audienceSize: number;
  lastSynced: string;
  status: "Connected" | "Error" | "Expired" | string; // Allow any status string for csv_status
}

// Mock data for demonstration
const mockDataSources: DataSource[] = [
  {
    id: "1",
    sourceName: "Salesforce",
    audienceName: "Premium Customers - CRM",
    tags: ["Active Customers", "Premium Leads", "VIP Customers"],
    type: "API",
    audienceSize: 1250,
    lastSynced: "2025-01-10T20:00:00Z",
    status: "Connected",
  },
  {
    id: "2",
    sourceName: "Google Sheets",
    audienceName: "Q4 Leads",
    tags: ["Test Audience", "Premium Leads"],
    type: "File",
    audienceSize: 850,
    lastSynced: "2025-01-09T15:45:00Z",
    status: "Connected",
  },
  {
    id: "3",
    sourceName: "HubSpot",
    audienceName: "Active Subscribers",
    tags: ["Inactive Users", "Active Customers"],
    type: "API",
    audienceSize: 3200,
    lastSynced: "2025-01-08T22:15:00Z",
    status: "Error",
  },
];

// Transform API audience_task objects to DataSource format
function transformAudienceTaskToDataSource(
  task: any,
  index: number
): DataSource {
  // Map the API response fields to DataSource format
  // Adjust field mappings based on actual API response structure
  const id = task.id || task._id || task.task_id || `task_${index}`;
  const sourceName =
    task.source_name || task.sourceName || task.source || "Unknown Source";
  const audienceName =
    task.audience_name ||
    task.audienceName ||
    task.name ||
    `Audience ${index + 1}`;
  // Always set type to CSV for now
  const type: "API" | "File" | "CSV" = "CSV";

  const audienceSize =
    task.audience_size || task.audienceSize || task.total || task.size || 0;
  const lastSynced =
    task.last_synced ||
    task.lastSynced ||
    task.updated_at ||
    task.updatedAt ||
    task.created_at ||
    new Date().toISOString();

  // Use csv_status for status, fallback to other status fields
  const status = task.csv_status || task.status || "Connected";

  // Extract tags if available
  const tags = task.tags || task.tag || [];
  const tagsArray = Array.isArray(tags) ? tags : tags ? [tags] : [];

  return {
    id: String(id),
    sourceName,
    audienceName,
    tags: tagsArray,
    type,
    audienceSize: Number(audienceSize),
    lastSynced,
    status,
  };
}

export default function AudiencePage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleAddDataSource = (
    newSource: Omit<DataSource, "id" | "lastSynced" | "status">
  ) => {
    const dataSource: DataSource = {
      ...newSource,
      id: `ds_${Date.now()}`,
      lastSynced: new Date().toISOString(),
      status: "Connected",
    };
    setDataSources([...dataSources, dataSource]);
    setIsAddDialogOpen(false);
  };

  const handleRemove = (id: string) => {
    setDataSources(dataSources.filter((ds) => ds.id !== id));
  };

  const handleResync = (id: string) => {
    setDataSources(
      dataSources.map((ds) =>
        ds.id === id
          ? {
              ...ds,
              lastSynced: new Date().toISOString(),
              status: "Connected" as const,
            }
          : ds
      )
    );
  };

  // Fetch data from API
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        // Use Next.js API route proxy to avoid CORS issues
        const response = await fetch("/api/audience-task");
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(
            errorData.error || `HTTP error! status: ${response.status}`
          );
        }
        const responseData = await response.json();

        // Handle different response structures
        // The API might return { data: [...] } or directly an array
        const tasks =
          responseData.data || responseData.items || responseData || [];

        if (Array.isArray(tasks)) {
          const transformed = tasks.map((task: any, index: number) =>
            transformAudienceTaskToDataSource(task, index)
          );
          setDataSources(transformed);
        } else {
          // If response is not an array, try to extract data
          console.warn("Unexpected API response structure:", responseData);
          // Fallback to mock data if structure is unexpected
          setDataSources(mockDataSources);
        }
      } catch (err) {
        console.error("Error fetching audience task:", err);
        setError(err instanceof Error ? err.message : "Failed to load data");
        // Fallback to mock data on error
        setDataSources(mockDataSources);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <div>
        <div className="flex h-20 items-center justify-between px-6 md:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Audience Data Sources
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Connect and manage your audience data sources
            </p>
          </div>
          <Button onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Data Source
          </Button>
        </div>
      </div>

      <main className="flex-1 p-6 md:p-8">
        {isLoading ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground">
                Loading data sources...
              </p>
            </CardContent>
          </Card>
        ) : error ? (
          <Card className="border-destructive">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <div className="rounded-full bg-destructive/10 p-6 mb-4">
                <Database className="h-12 w-12 text-destructive" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Error loading data</h3>
              <p className="text-sm text-muted-foreground mb-6 text-center max-w-md">
                {error}
              </p>
              <Button onClick={() => window.location.reload()}>Retry</Button>
            </CardContent>
          </Card>
        ) : dataSources.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <div className="rounded-full bg-muted p-6 mb-4">
                <Database className="h-12 w-12 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold mb-2">
                No audience sources connected yet
              </h3>
              <p className="text-sm text-muted-foreground mb-6 text-center max-w-md">
                Connect your first data source to start building targeted
                audience segments for your campaigns
              </p>
              <Button onClick={() => setIsAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Data Source
              </Button>
            </CardContent>
          </Card>
        ) : (
          <DataSourcesDataTable
            data={dataSources}
            onRemove={handleRemove}
            onResync={handleResync}
          />
        )}
      </main>

      <AddDataSourceDialog
        isOpen={isAddDialogOpen}
        onClose={() => setIsAddDialogOpen(false)}
        onSave={handleAddDataSource}
      />
    </div>
  );
}
