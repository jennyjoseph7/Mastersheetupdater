"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, Database, Loader2 } from "lucide-react";
import { DataSourcesDataTable } from "@/components/audience/data-sources-datatable";
import { AddDataSourceDialog } from "@/components/audience/add-data-source-dialog";
import { fetchPersonObjects } from "@/lib/api";

export interface DataSource {
  id: string;
  sourceName: string;
  audienceName: string;
  type: "API" | "File";
  audienceSize: number;
  lastSynced: string;
  status: "Connected" | "Error" | "Expired";
}

// Mock data for demonstration
const mockDataSources: DataSource[] = [
  {
    id: "1",
    sourceName: "Salesforce",
    audienceName: "Premium Customers – CRM",
    type: "API",
    audienceSize: 1250,
    lastSynced: "2025-01-10T14:30:00Z",
    status: "Connected",
  },
  {
    id: "2",
    sourceName: "Google Sheets",
    audienceName: "Q4 Leads",
    type: "File",
    audienceSize: 850,
    lastSynced: "2025-01-09T10:15:00Z",
    status: "Connected",
  },
  {
    id: "3",
    sourceName: "HubSpot",
    audienceName: "Active Subscribers",
    type: "API",
    audienceSize: 3200,
    lastSynced: "2025-01-08T16:45:00Z",
    status: "Error",
  },
];

// Transform API person objects to DataSource format
// Adjust this based on your actual API response structure
function transformPersonToDataSource(person: any, index: number): DataSource {
  // This is a sample transformation - adjust based on your actual API response
  return {
    id: person.id || person._id || `person_${index}`,
    sourceName: person.sourceName || person.source_name || person.source || "Unknown Source",
    audienceName: person.audienceName || person.audience_name || person.name || `Audience ${index + 1}`,
    type: (person.type === "File" || person.type === "file") ? "File" : "API",
    audienceSize: person.audienceSize || person.audience_size || person.size || 0,
    lastSynced: person.lastSynced || person.last_synced || person.updatedAt || person.updated_at || new Date().toISOString(),
    status: person.status === "error" ? "Error" : person.status === "expired" ? "Expired" : "Connected",
  };
}

export default function AudiencePage() {
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleAddDataSource = (
    newSource: Omit<DataSource, "id" | "lastSynced" | "status">,
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
          : ds,
      ),
    );
  };

  // Fetch data from API on component mount
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetchPersonObjects();
        // Handle different response structures
        const persons = response.data || response.items || response || [];
        
        if (Array.isArray(persons)) {
          const transformed = persons.map((person: any, index: number) =>
            transformPersonToDataSource(person, index)
          );
          setDataSources(transformed);
        } else {
          // If response is not an array, try to extract data
          console.warn("Unexpected API response structure:", response);
          setDataSources([]);
        }
      } catch (err) {
        console.error("Error fetching person objects:", err);
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
              <p className="text-sm text-muted-foreground">Loading data sources...</p>
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
              <Button onClick={() => window.location.reload()}>
                Retry
              </Button>
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
