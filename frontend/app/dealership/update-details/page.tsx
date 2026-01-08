"use client";

import type React from "react";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PhoneInput } from "react-international-phone";
import "react-international-phone/style.css";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft,
  Building2,
  Globe,
  X,
  AlertCircle,
  CheckCircle2,
  Wrench,
  MapPin,
  Clock,
  Users,
  Phone,
  Mail,
} from "lucide-react";
import {
  type DealershipUpdateDetailsRequest,
  type CreateWorkshopRequest,
  ApiError,
  createWorkshop,
  getDealershipDetails,
  getWorkshopsForDealership,
  dealershipUpdateDetails,
} from "@/lib/api";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";
import { isDealershipSetupComplete } from "@/lib/dealership-utils";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";

const urlRegex = /^(https?:\/\/)?.+\..+/;
const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

export default function DealershipUpdateDetails() {
  const router = useRouter();
  const { user, checkDealershipSetup } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [websiteError, setWebsiteError] = useState("");
  const [panError, setPanError] = useState("");
  const [gstinError, setGstinError] = useState("");

  const [dealershipDetails, setDealershipDetails] = useState({
    dealershipType: "Multi Brand" as "Single Brand" | "Multi Brand",
    languages: [] as string[],
    brands: [] as string[],
    panNumber: "",
    gstin: "",
    website: "",
  });

  // Workshop form state
  const [workshopLoading, setWorkshopLoading] = useState(false);
  const [workshopError, setWorkshopError] = useState("");
  const [workshopSuccess, setWorkshopSuccess] = useState("");
  const [showWorkshopForm, setShowWorkshopForm] = useState(false);
  const [workshopFormData, setWorkshopFormData] = useState({
    workshop_name: "",
    workshop_type: "Main Workshop",
    workshop_status: "Active",
    manager_name: "",
    email: "",
    contact_number: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    region_id: "",
    region_name: "",
    opening_time: "08:00",
    closing_time: "18:00",
    days_open: [] as string[],
    supported_brands: [] as string[],
    services_offered: [] as string[],
    total_technicians: "",
    total_service_bays: "",
    daily_service_capacity: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate business verification - at least one field must be provided
    const hasWebsite =
      dealershipDetails.website && dealershipDetails.website.trim() !== "";
    const hasPan =
      dealershipDetails.panNumber && dealershipDetails.panNumber.trim() !== "";
    const hasGstin =
      dealershipDetails.gstin && dealershipDetails.gstin.trim() !== "";

    if (!hasWebsite && !hasPan && !hasGstin) {
      setError(
        "Please provide at least one business verification detail (Website URL, PAN Number, or GSTIN)"
      );
      return;
    }

    // Validate format only if field is provided
    if (hasWebsite && !urlRegex.test(dealershipDetails.website)) {
      setWebsiteError("Please enter a valid website URL");
      setError("Please enter a valid website URL");
      return;
    }

    if (hasPan && !panRegex.test(dealershipDetails.panNumber)) {
      setPanError("Please enter a valid PAN number (Format: ABCDE1234F)");
      setError("Please enter a valid PAN number");
      return;
    }

    if (hasGstin && !gstinRegex.test(dealershipDetails.gstin)) {
      setGstinError("Please enter a valid GSTIN (15 characters)");
      setError("Please enter a valid GSTIN");
      return;
    }

    setIsLoading(true);

    try {
      // Get dealership ID from localStorage (stored during signup) or user context
      const storedDealershipId = localStorage.getItem("dealership_id");
      const dealershipId = storedDealershipId || user?.id || "";

      if (!dealershipId) {
        throw new Error(
          "Dealership ID not found. Please ensure you're logged in and have completed signup."
        );
      }

      // Map brand names to API format (slug format)
      const brandSlugMap: Record<string, string> = {
        "Maruti Suzuki": "maruti-suzuki-arena",
        "Maruti Suzuki NEXA": "maruti-suzuki-nexa",
        Hyundai: "hyundai",
        Toyota: "toyota",
        Honda: "honda",
        "Tata Motors": "tata-motors",
        Mahindra: "mahindra",
        Kia: "kia",
        "MG Motor": "mg-motor",
        Ford: "ford",
        Volkswagen: "volkswagen",
      };

      const brandSlugs = dealershipDetails.brands
        .map(
          (brand) =>
            brandSlugMap[brand] || brand.toLowerCase().replace(/\s+/g, "-")
        )
        .filter(Boolean);

      // Extract legal name from dealership_id (remove region suffix if present)
      // e.g., "logintest2-south-india" -> "logintest2"
      let dealershipLegalName = dealershipId;
      const lastDashIndex = dealershipId.lastIndexOf("-");
      if (lastDashIndex > 0) {
        // Check if it looks like a region suffix pattern (e.g., "-south-india")
        const potentialRegion = dealershipId.substring(lastDashIndex + 1);
        const commonRegions = [
          "south-india",
          "north-india",
          "east-india",
          "west-india",
          "central-india",
        ];
        if (
          commonRegions.includes(potentialRegion.toLowerCase()) ||
          dealershipId.includes("-india")
        ) {
          dealershipLegalName = dealershipId.substring(0, lastDashIndex);
        }
      }

      // Ensure dealership_legal_name is never empty
      if (!dealershipLegalName || dealershipLegalName.trim() === "") {
        dealershipLegalName = dealershipId; // Fallback to full dealership_id
      }

      // Build kwargs object - only include fields with values
      // Match the exact format from the curl command that works
      const kwargs: Record<string, any> = {
        dealership_type: dealershipDetails.dealershipType || "Multi Brand",
        dealership_legal_name: dealershipLegalName,
      };

      // Only include arrays if they have values
      if (dealershipDetails.languages.length > 0) {
        kwargs.languages = dealershipDetails.languages;
      } else {
        kwargs.languages = []; // Include empty array for languages
      }

      if (brandSlugs.length > 0) {
        kwargs.supported_brands = brandSlugs;
      } else {
        kwargs.supported_brands = []; // Include empty array for supported_brands
      }

      // Always include aliases as empty array (matches curl format)
      kwargs.aliases = [];

      // Only include verification fields if they have values (not empty strings)
      const websiteValue = dealershipDetails.website?.trim();
      if (websiteValue) {
        kwargs.website = websiteValue;
      } else {
        kwargs.website = ""; // Include empty string if validation requires at least one field
      }

      const panValue = dealershipDetails.panNumber?.trim();
      if (panValue) {
        kwargs.pan_number = panValue;
      } else {
        kwargs.pan_number = ""; // Include empty string
      }

      const gstinValue = dealershipDetails.gstin?.trim();
      if (gstinValue) {
        kwargs.gstin = gstinValue;
      } else {
        kwargs.gstin = ""; // Include empty string
      }

      const updateRequest: DealershipUpdateDetailsRequest = {
        args: [dealershipId],
        kwargs,
        _timeout: 600,
      };

      // Call the dealership update details API function (uses API route proxy)
      console.log("[Dealership Update Details] Calling API function");
      console.log(
        "[Dealership Update Details] Request body:",
        JSON.stringify(updateRequest, null, 2)
      );

      const responseData = await dealershipUpdateDetails(updateRequest);
      console.log("[Dealership Update Details] Response:", responseData);

      // After successful update, check if setup is now complete based on the response
      try {
        console.log(
          "[Dealership Update] Checking setup status after update..."
        );

        // Check completion based on the response data we just received
        const hasDealershipType = Boolean(responseData.dealership_type);
        const hasLanguages =
          Array.isArray(responseData.languages) &&
          responseData.languages.length > 0 &&
          responseData.languages.some(
            (lang: any) => lang && String(lang).trim() !== ""
          );
        const hasSupportedBrands =
          Array.isArray(responseData.supported_brands) &&
          responseData.supported_brands.length > 0 &&
          responseData.supported_brands.some(
            (brand: any) => brand && String(brand).trim() !== ""
          );
        const panNumber = responseData.pan_number
          ? String(responseData.pan_number).trim()
          : "";
        const gstin = responseData.gstin
          ? String(responseData.gstin).trim()
          : "";
        const website = responseData.website
          ? String(responseData.website).trim()
          : "";
        const hasVerification =
          panNumber !== "" || gstin !== "" || website !== "";

        // Check for workshops - BOTH dealership details AND workshops must be complete
        let hasWorkshop = false;
        try {
          if (dealershipId) {
            const workshops = await getWorkshopsForDealership(dealershipId);
            hasWorkshop = Array.isArray(workshops) && workshops.length > 0;
            console.log(
              "[Dealership Update] Workshops found:",
              workshops.length
            );
          }
        } catch (workshopError) {
          console.error(
            "[Dealership Update] Error checking workshops:",
            workshopError
          );
        }

        const setupComplete =
          hasDealershipType &&
          hasLanguages &&
          hasSupportedBrands &&
          hasVerification &&
          hasWorkshop;

        console.log(
          "[Dealership Update] Setup completion check from response:",
          {
            hasDealershipType,
            hasLanguages,
            hasSupportedBrands,
            hasVerification,
            hasWorkshop,
            setupComplete,
          }
        );

        // Update auth context with the new status
        if (setupComplete) {
          // Mark as complete immediately - this is critical
          localStorage.setItem("dealership_setup_complete", "true");
          // Set flag to indicate we just completed setup (for dashboard refresh)
          sessionStorage.setItem("just_completed_setup", "true");
          // Clear any modal dismissal flag since setup is now complete
          sessionStorage.removeItem("setup_modal_dismissed");

          // Force refresh auth context - wait for it to complete
          console.log("[Dealership Update] Refreshing auth context...");
          await checkDealershipSetup();

          // Wait a bit more to ensure state propagation
          await new Promise((resolve) => setTimeout(resolve, 500));

          console.log(
            "[Dealership Update] Setup complete, redirecting to dashboard"
          );
          router.push("/");
        } else {
          // Still incomplete - show message about what's missing
          console.log("[Dealership Update] Setup still incomplete. Missing:", {
            hasDealershipType,
            hasLanguages,
            hasSupportedBrands,
            hasVerification,
            hasWorkshop,
            responseData,
          });
          localStorage.setItem("dealership_setup_complete", "false");
          await checkDealershipSetup(); // Refresh auth context

          // Show message that workshop is still needed
          if (!hasWorkshop) {
            setError(
              "Dealership details saved! Please add workshop details below to complete the setup."
            );
            setShowWorkshopForm(true); // Show workshop form
          }
          // Don't redirect - stay on page to complete workshop
        }
      } catch (error) {
        console.error(
          "[Dealership Update] Failed to check setup status:",
          error
        );
        router.push("/dealership/update-details/success");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        let cleanErrorMessage = err.message;
        if (err.error) {
          if (typeof err.error === "string") {
            try {
              const parsed = JSON.parse(err.error);
              cleanErrorMessage =
                parsed.error || parsed.message || cleanErrorMessage;
            } catch {
              cleanErrorMessage = err.error;
            }
          }
        }
        setError(cleanErrorMessage);
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to update dealership details. Please try again."
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleWorkshopSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setWorkshopError("");
    setWorkshopSuccess("");

    // Validate required fields
    if (!workshopFormData.workshop_name.trim()) {
      setWorkshopError("Workshop name is required");
      return;
    }
    if (!workshopFormData.manager_name.trim()) {
      setWorkshopError("Manager name is required");
      return;
    }
    if (!workshopFormData.email.trim()) {
      setWorkshopError("Email is required");
      return;
    }
    if (!workshopFormData.contact_number.trim()) {
      setWorkshopError("Contact number is required");
      return;
    }

    // Validate phone number format (PhoneInput provides validated format with country code)
    // PhoneInput returns phone in E.164 format (e.g., +919876543401)
    const phoneValue = workshopFormData.contact_number.trim();
    if (!phoneValue || phoneValue.length < 10) {
      setWorkshopError("Please enter a valid phone number with country code");
      return;
    }
    // PhoneInput ensures the format is correct, but we can add additional validation
    if (!phoneValue.startsWith("+")) {
      setWorkshopError("Please select a country code for the phone number");
      return;
    }
    if (!workshopFormData.address.trim()) {
      setWorkshopError("Address is required");
      return;
    }
    if (!workshopFormData.city.trim()) {
      setWorkshopError("City is required");
      return;
    }
    if (!workshopFormData.state.trim()) {
      setWorkshopError("State is required");
      return;
    }
    if (!workshopFormData.pincode.trim()) {
      setWorkshopError("Pincode is required");
      return;
    }
    if (workshopFormData.days_open.length === 0) {
      setWorkshopError("Please select at least one day the workshop is open");
      return;
    }
    if (workshopFormData.supported_brands.length === 0) {
      setWorkshopError("Please select at least one supported brand");
      return;
    }
    if (workshopFormData.services_offered.length === 0) {
      setWorkshopError("Please select at least one service offered");
      return;
    }
    if (!workshopFormData.total_technicians.trim()) {
      setWorkshopError("Total technicians is required");
      return;
    }
    if (!workshopFormData.total_service_bays.trim()) {
      setWorkshopError("Total service bays is required");
      return;
    }
    if (!workshopFormData.daily_service_capacity.trim()) {
      setWorkshopError("Daily service capacity is required");
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(workshopFormData.email)) {
      setWorkshopError("Please enter a valid email address");
      return;
    }

    setWorkshopLoading(true);

    try {
      // Get dealership ID and name
      const storedDealershipId = localStorage.getItem("dealership_id");
      const dealershipId = storedDealershipId || user?.id || "";

      if (!dealershipId) {
        throw new Error(
          "Dealership ID not found. Please ensure you're logged in."
        );
      }

      // Get dealership name - try to extract from dealership_id or use a default
      let dealerName = dealershipId;
      // Try to get from dealership details if available
      try {
        const dealershipDetails = await getDealershipDetails();
        dealerName =
          dealershipDetails.dealership_name ||
          dealershipDetails.dealership_legal_name ||
          dealershipId;
      } catch {
        // Use dealership_id as fallback
        dealerName = dealershipId;
      }

      // Extract region info from dealership_id if available
      let regionId = workshopFormData.region_id;
      let regionName = workshopFormData.region_name;

      if (!regionId && dealershipId.includes("-")) {
        const parts = dealershipId.split("-");
        const potentialRegion = parts[parts.length - 1];
        const commonRegions = [
          "north-india",
          "south-india",
          "east-india",
          "west-india",
          "central-india",
        ];
        if (commonRegions.includes(potentialRegion)) {
          regionId = potentialRegion;
          regionName = potentialRegion
            .split("-")
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
            .join(" ");
        }
      }

      const workshopData: CreateWorkshopRequest = {
        dealer_name: dealerName,
        dealership_id: dealershipId,
        workshop_name: workshopFormData.workshop_name.trim(),
        workshop_type: workshopFormData.workshop_type,
        workshop_status: workshopFormData.workshop_status,
        email: workshopFormData.email.trim(),
        contact_number: workshopFormData.contact_number.trim(),
        manager_name: workshopFormData.manager_name.trim(),
        address: workshopFormData.address.trim(),
        city: workshopFormData.city.trim(),
        state: workshopFormData.state.trim(),
        pincode: workshopFormData.pincode.trim(),
        region_id: regionId || "",
        region_name: regionName || "",
        geolocation: [0, 0], // Default geolocation - can be updated later
        operating_hours: {
          opening_time: workshopFormData.opening_time,
          closing_time: workshopFormData.closing_time,
          days_open: workshopFormData.days_open,
        },
        supported_brands: workshopFormData.supported_brands,
        services_offered: workshopFormData.services_offered,
        total_technicians: parseInt(workshopFormData.total_technicians, 10),
        total_service_bays: parseInt(workshopFormData.total_service_bays, 10),
        daily_service_capacity: parseInt(
          workshopFormData.daily_service_capacity,
          10
        ),
      };

      await createWorkshop(workshopData);

      setWorkshopSuccess("Workshop added successfully!");

      // Check if both dealership details and workshop are now complete
      // Reuse dealershipId from above
      // Verify dealership details are also complete
      let dealershipDetailsComplete = false;
      try {
        const details = await getDealershipDetails();
        const hasDealershipType = Boolean(details.dealership_type);
        const hasLanguages =
          Array.isArray(details.languages) && details.languages.length > 0;
        const hasSupportedBrands =
          Array.isArray(details.supported_brands) &&
          details.supported_brands.length > 0;
        const hasVerification = Boolean(
          details.pan_number || details.gstin || details.website
        );
        dealershipDetailsComplete =
          hasDealershipType &&
          hasLanguages &&
          hasSupportedBrands &&
          hasVerification;
      } catch (error) {
        console.error(
          "[Workshop Submit] Error checking dealership details:",
          error
        );
      }

      if (dealershipDetailsComplete) {
        // Both are complete - mark setup as complete
        localStorage.setItem("dealership_setup_complete", "true");
        sessionStorage.setItem("just_completed_setup", "true");
        sessionStorage.removeItem("setup_modal_dismissed");

        // Refresh auth context
        await checkDealershipSetup();

        // Wait a bit for state propagation
        await new Promise((resolve) => setTimeout(resolve, 500));

        // Redirect to dashboard
        router.push("/");
      } else {
        // Workshop added but dealership details incomplete
        setWorkshopSuccess(
          "Workshop added! Please complete dealership details above to finish setup."
        );
        setShowWorkshopForm(false);

        // Reset form
        setWorkshopFormData({
          workshop_name: "",
          workshop_type: "Main Workshop",
          workshop_status: "Active",
          manager_name: "",
          email: "",
          contact_number: "",
          address: "",
          city: "",
          state: "",
          pincode: "",
          region_id: "",
          region_name: "",
          opening_time: "08:00",
          closing_time: "18:00",
          days_open: [],
          supported_brands: [],
          services_offered: [],
          total_technicians: "",
          total_service_bays: "",
          daily_service_capacity: "",
        });

        // Refresh dealership setup status
        await checkDealershipSetup();
      }
    } catch (err) {
      if (err instanceof ApiError) {
        let cleanErrorMessage = err.message;
        if (err.error) {
          if (typeof err.error === "string") {
            try {
              const parsed = JSON.parse(err.error);
              cleanErrorMessage =
                parsed.error || parsed.message || cleanErrorMessage;
            } catch {
              cleanErrorMessage = err.error;
            }
          }
        }
        setWorkshopError(cleanErrorMessage);
      } else {
        setWorkshopError(
          err instanceof Error
            ? err.message
            : "Failed to create workshop. Please try again."
        );
      }
    } finally {
      setWorkshopLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen py-8">
        <div className="container mx-auto px-4 max-w-2xl">
          {/* Back Button */}
          <div className="mb-6">
            <Link
              href="/"
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Link>
          </div>

          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
              <Building2 className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-4xl font-bold text-foreground mb-2">
              Complete Your Dealership Basic Setup
            </h1>
            <p className="text-lg text-muted-foreground">
              Add additional details about your dealership
            </p>
          </div>

          {/* Progress Indicator */}
          <Card className="mb-6 border-primary/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Onboarding Progress</span>
                <span className="text-sm text-muted-foreground">
                  Both steps required
                </span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    Step 1: Dealership Details
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    Step 2: Workshop Details
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-xl border-border/50">
            <CardHeader>
              <CardTitle className="text-2xl">Dealership Details</CardTitle>
              <CardDescription>
                Provide additional information about your dealership
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* Dealership Type */}
                <div className="space-y-3">
                  <Label className="text-base font-semibold">
                    Dealership Type
                  </Label>
                  <RadioGroup
                    value={dealershipDetails.dealershipType}
                    onValueChange={(value) => {
                      const newType = value as "Single Brand" | "Multi Brand";
                      // If switching to Single Brand and multiple brands are selected, keep only the first one
                      const updatedBrands =
                        newType === "Single Brand" &&
                        dealershipDetails.brands.length > 1
                          ? [dealershipDetails.brands[0]]
                          : dealershipDetails.brands;
                      setDealershipDetails({
                        ...dealershipDetails,
                        dealershipType: newType,
                        brands: updatedBrands,
                      });
                    }}
                  >
                    <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                      <RadioGroupItem value="Single Brand" id="single-brand" />
                      <Label
                        htmlFor="single-brand"
                        className="flex-1 cursor-pointer"
                      >
                        <div className="font-medium">Single Brand</div>
                        <div className="text-sm text-muted-foreground">
                          Exclusive partnership with one manufacturer
                        </div>
                      </Label>
                    </div>
                    <div className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-gray-50 transition-colors">
                      <RadioGroupItem value="Multi Brand" id="multi-brand" />
                      <Label
                        htmlFor="multi-brand"
                        className="flex-1 cursor-pointer"
                      >
                        <div className="font-medium">Multi Brand</div>
                        <div className="text-sm text-muted-foreground">
                          Multiple brand partnerships
                        </div>
                      </Label>
                    </div>
                  </RadioGroup>
                </div>

                {/* Supported Brands */}
                <div className="space-y-3">
                  <Label className="text-base font-semibold">
                    Supported Brands
                    {dealershipDetails.dealershipType === "Single Brand" && (
                      <span className="text-sm font-normal text-muted-foreground ml-2">
                        (Select one brand)
                      </span>
                    )}
                  </Label>
                  <div className="space-y-2">
                    <Select
                      value=""
                      onValueChange={(value) => {
                        if (value) {
                          // If Single Brand is selected, replace existing brand with new one
                          if (
                            dealershipDetails.dealershipType === "Single Brand"
                          ) {
                            setDealershipDetails({
                              ...dealershipDetails,
                              brands: [value],
                            });
                          } else if (
                            !dealershipDetails.brands.includes(value)
                          ) {
                            // Multi Brand: add if not already selected
                            setDealershipDetails({
                              ...dealershipDetails,
                              brands: [...dealershipDetails.brands, value],
                            });
                          }
                        }
                      }}
                      disabled={
                        dealershipDetails.dealershipType === "Single Brand" &&
                        dealershipDetails.brands.length >= 1
                      }
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue
                          placeholder={
                            dealershipDetails.dealershipType ===
                              "Single Brand" &&
                            dealershipDetails.brands.length >= 1
                              ? "One brand selected (change by selecting another)"
                              : "Select a brand to add"
                          }
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {[
                          "Toyota",
                          "Honda",
                          "Maruti Suzuki",
                          "Maruti Suzuki NEXA",
                          "Hyundai",
                          "Tata Motors",
                          "Mahindra",
                          "Kia",
                          "MG Motor",
                          "Ford",
                          "Volkswagen",
                        ]
                          .filter(
                            (brand) => !dealershipDetails.brands.includes(brand)
                          )
                          .map((brand) => (
                            <SelectItem key={brand} value={brand}>
                              {brand}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                    {dealershipDetails.brands.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2 p-3 bg-muted/50 rounded-lg border">
                        {dealershipDetails.brands.map((brand) => (
                          <Badge
                            key={brand}
                            variant="secondary"
                            className="flex items-center gap-1.5 px-3 py-1.5"
                          >
                            {brand}
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                e.preventDefault();
                                setDealershipDetails({
                                  ...dealershipDetails,
                                  brands: dealershipDetails.brands.filter(
                                    (b) => b !== brand
                                  ),
                                });
                              }}
                              className="ml-1.5 rounded-sm hover:bg-destructive/20 p-0.5 -mr-0.5 opacity-70 hover:opacity-100 transition-opacity"
                              aria-label={`Remove ${brand}`}
                            >
                              <X className="h-3.5 w-3.5 cursor-pointer hover:text-destructive transition-colors" />
                            </button>
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Languages */}
                <div className="space-y-3">
                  <Label className="text-base font-semibold">
                    Supported Languages
                  </Label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "english",
                      "hindi",
                      "kannada",
                      "telugu",
                      "tamil",
                      "malayalam",
                      "odia",
                      "bengali",
                      "marathi",
                      "gujarati",
                    ].map((lang) => (
                      <Badge
                        key={lang}
                        variant={
                          dealershipDetails.languages.includes(lang)
                            ? "default"
                            : "outline"
                        }
                        className="cursor-pointer px-3 py-2 text-sm capitalize"
                        onClick={() => {
                          if (dealershipDetails.languages.includes(lang)) {
                            setDealershipDetails({
                              ...dealershipDetails,
                              languages: dealershipDetails.languages.filter(
                                (l) => l !== lang
                              ),
                            });
                          } else {
                            setDealershipDetails({
                              ...dealershipDetails,
                              languages: [...dealershipDetails.languages, lang],
                            });
                          }
                        }}
                      >
                        {lang}
                        {dealershipDetails.languages.includes(lang) && (
                          <X className="h-3 w-3 ml-2" />
                        )}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* Business Verification */}
                <div className="space-y-4">
                  <Label className="text-base font-semibold">
                    Business Verification{" "}
                    <span className="text-sm font-normal text-muted-foreground">
                      (At least one field is required)
                    </span>
                  </Label>

                  {/* Website */}
                  <div className="space-y-2">
                    <Label htmlFor="website">Website URL (Optional)</Label>
                    <div className="relative">
                      <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="website"
                        type="url"
                        placeholder="Enter your website URL"
                        value={dealershipDetails.website}
                        onChange={(e) => {
                          const value = e.target.value;
                          setDealershipDetails({
                            ...dealershipDetails,
                            website: value,
                          });
                          // Only validate format if value is provided
                          if (
                            value &&
                            value.trim() !== "" &&
                            !urlRegex.test(value)
                          ) {
                            setWebsiteError("Please enter a valid website URL");
                          } else {
                            setWebsiteError("");
                          }
                        }}
                        className="pl-10"
                      />
                    </div>
                    {websiteError && (
                      <p className="text-sm text-destructive">{websiteError}</p>
                    )}
                  </div>

                  {/* PAN and GSTIN */}
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="panNumber">PAN Number (Optional)</Label>
                      <Input
                        id="panNumber"
                        placeholder="Enter your PAN Number"
                        value={dealershipDetails.panNumber}
                        onChange={(e) => {
                          const value = e.target.value
                            .toUpperCase()
                            .replace(/[^A-Z0-9]/g, "");
                          setDealershipDetails({
                            ...dealershipDetails,
                            panNumber: value,
                          });
                          // Only validate format if value is provided
                          if (
                            value &&
                            value.trim() !== "" &&
                            !panRegex.test(value)
                          ) {
                            setPanError(
                              "Please enter a valid PAN number (Format: ABCDE1234F)"
                            );
                          } else {
                            setPanError("");
                          }
                        }}
                        maxLength={10}
                        className="font-mono uppercase"
                      />
                      {panError && (
                        <p className="text-sm text-destructive">{panError}</p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="gstin">GSTIN Number (Optional)</Label>
                      <Input
                        id="gstin"
                        placeholder="Enter your GSTIN Number"
                        value={dealershipDetails.gstin}
                        onChange={(e) => {
                          const value = e.target.value
                            .toUpperCase()
                            .replace(/[^A-Z0-9]/g, "");
                          setDealershipDetails({
                            ...dealershipDetails,
                            gstin: value,
                          });
                          // Only validate format if value is provided
                          if (value && !gstinRegex.test(value)) {
                            setGstinError(
                              "Please enter a valid GSTIN (15 characters)"
                            );
                          } else {
                            setGstinError("");
                          }
                        }}
                        maxLength={15}
                        className="font-mono uppercase"
                      />
                      {gstinError && (
                        <p className="text-sm text-destructive">{gstinError}</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="pt-4">
                  <Button
                    type="submit"
                    size="lg"
                    disabled={isLoading}
                    className="w-full"
                  >
                    {isLoading ? (
                      "Saving..."
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Save Dealership Details
                      </>
                    )}
                  </Button>
                  <p className="text-sm text-muted-foreground text-center mt-3">
                    Note: Both Dealership Details and Workshop Details must be
                    completed to finish setup.
                  </p>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Workshop Details Section */}
          <Card className="shadow-xl border-border/50 mt-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <Wrench className="h-6 w-6 text-primary" />
                    Workshop Details
                  </CardTitle>
                  <CardDescription className="mt-2">
                    Add workshop information for your dealership
                  </CardDescription>
                </div>
                {workshopSuccess && (
                  <Alert className="border-green-500 bg-green-50">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-green-800">
                      {workshopSuccess}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {!showWorkshopForm ? (
                <div className="text-center py-8">
                  <Wrench className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground mb-4">
                    Add your workshop details to complete the dealership setup
                  </p>
                  <Button onClick={() => setShowWorkshopForm(true)} size="lg">
                    Add Workshop Details
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleWorkshopSubmit} className="space-y-6">
                  {workshopError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{workshopError}</AlertDescription>
                    </Alert>
                  )}

                  {/* Auto-filled Dealership Information */}
                  <div className="space-y-4 p-4 bg-muted/50 rounded-lg border">
                    <h3 className="text-lg font-semibold">
                      Dealership Information
                    </h3>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="dealer_name">Dealer Name</Label>
                        <Input
                          id="dealer_name"
                          value={(() => {
                            const storedDealershipId =
                              localStorage.getItem("dealership_id");
                            const dealershipId =
                              storedDealershipId || user?.id || "";
                            // Try to extract dealer name from dealership_id
                            if (dealershipId.includes("-")) {
                              const parts = dealershipId.split("-");
                              return parts
                                .slice(0, -1)
                                .join(" ")
                                .replace(/\b\w/g, (l) => l.toUpperCase());
                            }
                            return dealershipId;
                          })()}
                          disabled
                          className="bg-background"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="dealership_id">Dealership ID</Label>
                        <Input
                          id="dealership_id"
                          value={
                            localStorage.getItem("dealership_id") ||
                            user?.id ||
                            ""
                          }
                          disabled
                          className="bg-background font-mono"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Basic Information */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">Basic Information</h3>

                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="workshop_name">Workshop Name *</Label>
                        <Input
                          id="workshop_name"
                          placeholder="e.g., NEXA Delhi South - Service Center"
                          value={workshopFormData.workshop_name}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              workshop_name: e.target.value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="workshop_type">Workshop Type *</Label>
                        <Select
                          value={workshopFormData.workshop_type}
                          onValueChange={(value) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              workshop_type: value,
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Main Workshop">
                              Main Workshop
                            </SelectItem>
                            <SelectItem value="Express Service Center">
                              Express Service Center
                            </SelectItem>
                            <SelectItem value="Authorized Service Center">
                              Authorized Service Center
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="manager_name">Manager Name *</Label>
                        <Input
                          id="manager_name"
                          placeholder="Enter manager name"
                          value={workshopFormData.manager_name}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              manager_name: e.target.value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="workshop_status">Workshop Status</Label>
                        <Select
                          value={workshopFormData.workshop_status}
                          onValueChange={(value) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              workshop_status: value,
                            })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Active">Active</SelectItem>
                            <SelectItem value="Inactive">Inactive</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

                  {/* Contact Information */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">
                      Contact Information
                    </h3>

                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label
                          htmlFor="workshop_email"
                          className="flex items-center gap-2"
                        >
                          <Mail className="h-4 w-4" />
                          Email *
                        </Label>
                        <Input
                          id="workshop_email"
                          type="email"
                          placeholder="workshop@example.com"
                          value={workshopFormData.email}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              email: e.target.value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label
                          htmlFor="contact_number"
                          className="flex items-center gap-2"
                        >
                          <Phone className="h-4 w-4" />
                          Contact Number *
                        </Label>
                        <PhoneInput
                          value={workshopFormData.contact_number}
                          onChange={(phone) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              contact_number: phone,
                            })
                          }
                          defaultCountry="in"
                          inputClassName="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                          countrySelectorStyleProps={{
                            buttonClassName:
                              "flex h-10 items-center justify-center rounded-l-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                          }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Address Information */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <MapPin className="h-5 w-5" />
                      Address Information
                    </h3>

                    <div className="space-y-2">
                      <Label htmlFor="address">Address *</Label>
                      <Textarea
                        id="address"
                        placeholder="Enter full address"
                        value={workshopFormData.address}
                        onChange={(e) =>
                          setWorkshopFormData({
                            ...workshopFormData,
                            address: e.target.value,
                          })
                        }
                        required
                      />
                    </div>

                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="city">City *</Label>
                        <Input
                          id="city"
                          placeholder="City"
                          value={workshopFormData.city}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              city: e.target.value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="state">State *</Label>
                        <Input
                          id="state"
                          placeholder="State"
                          value={workshopFormData.state}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              state: e.target.value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="pincode">Pincode *</Label>
                        <Input
                          id="pincode"
                          placeholder="110001"
                          value={workshopFormData.pincode}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              pincode: e.target.value.replace(/\D/g, ""),
                            })
                          }
                          maxLength={6}
                          required
                        />
                      </div>
                    </div>
                  </div>

                  {/* Operating Hours */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Clock className="h-5 w-5" />
                      Operating Hours
                    </h3>

                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="opening_time">Opening Time *</Label>
                        <Input
                          id="opening_time"
                          type="time"
                          value={workshopFormData.opening_time}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              opening_time: e.target.value,
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="closing_time">Closing Time *</Label>
                        <Input
                          id="closing_time"
                          type="time"
                          value={workshopFormData.closing_time}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              closing_time: e.target.value,
                            })
                          }
                          required
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>Days Open *</Label>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                          "Monday",
                          "Tuesday",
                          "Wednesday",
                          "Thursday",
                          "Friday",
                          "Saturday",
                          "Sunday",
                        ].map((day) => (
                          <div
                            key={day}
                            className="flex items-center space-x-2"
                          >
                            <Checkbox
                              id={`day-${day}`}
                              checked={workshopFormData.days_open.includes(day)}
                              onCheckedChange={(checked) => {
                                if (checked) {
                                  setWorkshopFormData({
                                    ...workshopFormData,
                                    days_open: [
                                      ...workshopFormData.days_open,
                                      day,
                                    ],
                                  });
                                } else {
                                  setWorkshopFormData({
                                    ...workshopFormData,
                                    days_open:
                                      workshopFormData.days_open.filter(
                                        (d) => d !== day
                                      ),
                                  });
                                }
                              }}
                            />
                            <Label
                              htmlFor={`day-${day}`}
                              className="text-sm font-normal cursor-pointer"
                            >
                              {day}
                            </Label>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Supported Brands */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">
                      Supported Brands *
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {[
                        "NEXA",
                        "Maruti Suzuki",
                        "Hyundai",
                        "Toyota",
                        "Honda",
                        "Tata Motors",
                        "Mahindra",
                        "Kia",
                        "MG Motor",
                        "Ford",
                        "Volkswagen",
                      ].map((brand) => (
                        <Badge
                          key={brand}
                          variant={
                            workshopFormData.supported_brands.includes(brand)
                              ? "default"
                              : "outline"
                          }
                          className="cursor-pointer px-3 py-2 text-sm"
                          onClick={() => {
                            if (
                              workshopFormData.supported_brands.includes(brand)
                            ) {
                              setWorkshopFormData({
                                ...workshopFormData,
                                supported_brands:
                                  workshopFormData.supported_brands.filter(
                                    (b) => b !== brand
                                  ),
                              });
                            } else {
                              setWorkshopFormData({
                                ...workshopFormData,
                                supported_brands: [
                                  ...workshopFormData.supported_brands,
                                  brand,
                                ],
                              });
                            }
                          }}
                        >
                          {brand}
                          {workshopFormData.supported_brands.includes(
                            brand
                          ) && <X className="h-3 w-3 ml-2" />}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Services Offered */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">
                      Services Offered *
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {[
                        "General Service",
                        "Repair",
                        "Body Shop",
                        "Car Wash",
                        "Tire Service",
                        "Battery Service",
                        "AC Service",
                        "Brake Service",
                      ].map((service) => (
                        <Badge
                          key={service}
                          variant={
                            workshopFormData.services_offered.includes(service)
                              ? "default"
                              : "outline"
                          }
                          className="cursor-pointer px-3 py-2 text-sm"
                          onClick={() => {
                            if (
                              workshopFormData.services_offered.includes(
                                service
                              )
                            ) {
                              setWorkshopFormData({
                                ...workshopFormData,
                                services_offered:
                                  workshopFormData.services_offered.filter(
                                    (s) => s !== service
                                  ),
                              });
                            } else {
                              setWorkshopFormData({
                                ...workshopFormData,
                                services_offered: [
                                  ...workshopFormData.services_offered,
                                  service,
                                ],
                              });
                            }
                          }}
                        >
                          {service}
                          {workshopFormData.services_offered.includes(
                            service
                          ) && <X className="h-3 w-3 ml-2" />}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Capacity Information */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                      <Users className="h-5 w-5" />
                      Capacity Information
                    </h3>

                    <div className="grid md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="total_technicians">
                          Total Technicians *
                        </Label>
                        <Input
                          id="total_technicians"
                          type="number"
                          min="1"
                          placeholder="5"
                          value={workshopFormData.total_technicians}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              total_technicians: e.target.value.replace(
                                /\D/g,
                                ""
                              ),
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="total_service_bays">
                          Total Service Bays *
                        </Label>
                        <Input
                          id="total_service_bays"
                          type="number"
                          min="1"
                          placeholder="4"
                          value={workshopFormData.total_service_bays}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              total_service_bays: e.target.value.replace(
                                /\D/g,
                                ""
                              ),
                            })
                          }
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="daily_service_capacity">
                          Daily Service Capacity *
                        </Label>
                        <Input
                          id="daily_service_capacity"
                          type="number"
                          min="1"
                          placeholder="20"
                          value={workshopFormData.daily_service_capacity}
                          onChange={(e) =>
                            setWorkshopFormData({
                              ...workshopFormData,
                              daily_service_capacity: e.target.value.replace(
                                /\D/g,
                                ""
                              ),
                            })
                          }
                          required
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      size="lg"
                      onClick={() => {
                        setShowWorkshopForm(false);
                        setWorkshopError("");
                        setWorkshopSuccess("");
                      }}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" size="lg" disabled={workshopLoading}>
                      {workshopLoading ? (
                        "Creating Workshop..."
                      ) : (
                        <>
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Create Workshop
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  );
}
