"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import PageHeader from "@/components/page-header";
import { AudienceDatatable } from "@/components/audience-datatable";
import type { AudienceMember } from "@/types/audience";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

// Audience metadata for header
const audienceMetadata: Record<string, { name: string; description: string }> =
  {
    "car-buyers": {
      name: "Car Buyers",
      description: "Customers who have purchased vehicles",
    },
    "service-customers": {
      name: "Service Customers",
      description: "Regular service and maintenance customers",
    },
    "test-drive": {
      name: "Test Drive Requests",
      description: "Leads who requested test drives",
    },
    financing: {
      name: "Financing Inquiries",
      description: "Customers interested in financing options",
    },
    "trade-in": {
      name: "Trade-In Leads",
      description: "Customers looking to trade in vehicles",
    },
    vip: {
      name: "VIP Customers",
      description: "High-value and premium customers",
    },
  };

export default function AudienceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const audienceId = params.id as string;

  const [audienceData, setAudienceData] = useState<AudienceMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const audienceInfo = audienceMetadata[audienceId] || {
    name: "Unknown Audience",
    description: "Audience details not found",
  };

  useEffect(() => {
    const fetchAudienceData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/audience/${audienceId}`);
        const result = await response.json();

        if (result.success) {
          setAudienceData(result.data);
        } else {
          setError(result.message || "Failed to load audience data");
        }
      } catch (err) {
        console.error("Error fetching audience data:", err);
        setError("An error occurred while loading audience data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAudienceData();
  }, [audienceId]);

  const handleBack = () => {
    router.push("/audiences");
  };

  return (
    <div className="flex min-h-screen flex-col">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          {audienceInfo.name}
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {audienceInfo.description}
        </p>
      </div>

      <main className="flex-1 space-y-6 p-6 md:p-8 w-full">
        <div className="mb-6">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Audiences
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
              <p className="text-muted-foreground">Loading audience data...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <p className="text-destructive mb-4">{error}</p>
              <Button onClick={handleBack}>Return to Audiences</Button>
            </div>
          </div>
        ) : (
          <AudienceDatatable
            data={audienceData}
            audienceName={audienceInfo.name}
            onBack={handleBack}
          />
        )}
      </main>
    </div>
  );
}
