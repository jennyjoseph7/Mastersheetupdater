"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import PageHeader from "@/components/page-header";
import { AudienceDatatable } from "@/components/audience-datatable";
import type { AudienceMember } from "@/types/audience";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

// Audience metadata for header - maps data source IDs to audience info
const audienceMetadata: Record<string, { name: string; description: string }> =
  {
    "1": {
      name: "Premium Customers - CRM",
      description: "Premium customers from Salesforce CRM",
    },
    "2": {
      name: "Q4 Leads",
      description: "Leads from Q4 campaign",
    },
    "3": {
      name: "Active Subscribers",
      description: "Active subscribers from HubSpot",
    },
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

  // Mock data with person_name, vehicle_model, phone_number, and city
  const mockAudienceData: AudienceMember[] = [
    {
      id: "1",
      person_name: "Rajesh Kumar",
      phone_number: "+91-98765-43210",
      vehicle_model: "Maruti Swift",
      city: "Mumbai",
    },
    {
      id: "2",
      person_name: "Priya Sharma",
      phone_number: "+91-98765-43211",
      vehicle_model: "Hyundai Creta",
      city: "Delhi",
    },
    {
      id: "3",
      person_name: "Amit Patel",
      phone_number: "+91-98765-43212",
      vehicle_model: "Tata Nexon",
      city: "Bangalore",
    },
    {
      id: "4",
      person_name: "Sneha Reddy",
      phone_number: "+91-98765-43213",
      vehicle_model: "Honda City",
      city: "Chennai",
    },
    {
      id: "5",
      person_name: "Vikram Singh",
      phone_number: "+91-98765-43214",
      vehicle_model: "Mahindra XUV700",
      city: "Pune",
    },
    {
      id: "6",
      person_name: "Anjali Desai",
      phone_number: "+91-98765-43215",
      vehicle_model: "Toyota Innova",
      city: "Mumbai",
    },
    {
      id: "7",
      person_name: "Rahul Mehta",
      phone_number: "+91-98765-43216",
      vehicle_model: "Maruti Baleno",
      city: "Jaipur",
    },
    {
      id: "8",
      person_name: "Kavita Nair",
      phone_number: "+91-98765-43217",
      vehicle_model: "Kia Seltos",
      city: "Kolkata",
    },
    {
      id: "9",
      person_name: "Suresh Iyer",
      phone_number: "+91-98765-43218",
      vehicle_model: "Volkswagen Polo",
      city: "Kochi",
    },
    {
      id: "10",
      person_name: "Meera Joshi",
      phone_number: "+91-98765-43219",
      vehicle_model: "Nissan Magnite",
      city: "Indore",
    },
    {
      id: "11",
      person_name: "Arjun Malhotra",
      phone_number: "+91-98765-43220",
      vehicle_model: "MG Hector",
      city: "Gurgaon",
    },
    {
      id: "12",
      person_name: "Divya Rao",
      phone_number: "+91-98765-43221",
      vehicle_model: "Skoda Kushaq",
      city: "Hyderabad",
    },
    {
      id: "13",
      person_name: "Ramesh Gupta",
      phone_number: "+91-98765-43222",
      vehicle_model: "Maruti Swift",
      city: "Mumbai",
    },
    {
      id: "14",
      person_name: "Sunita Verma",
      phone_number: "+91-98765-43223",
      vehicle_model: "Hyundai i20",
      city: "Delhi",
    },
    {
      id: "15",
      person_name: "Nikhil Agarwal",
      phone_number: "+91-98765-43224",
      vehicle_model: "Tata Harrier",
      city: "Ahmedabad",
    },
  ];

  useEffect(() => {
    // Simulate loading delay
    setIsLoading(true);
    setTimeout(() => {
      setAudienceData(mockAudienceData);
      setIsLoading(false);
    }, 500);
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
