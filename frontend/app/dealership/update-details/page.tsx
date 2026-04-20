"use client";

import type React from "react";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PhoneInput } from "react-international-phone";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
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
  Loader2,
  Plus,
  Store,
  RotateCcw,
} from "lucide-react";
import {
  type DealershipUpdateDetailsRequest,
  type CreateWorkshopRequest,
  type CreateShowroomRequest,
  type CreateBuybackCenterRequest,
  ApiError,
  createWorkshop,
  createShowroom,
  createBuybackCenter,
  getDealershipDetails,
  getWorkshopsForDealership,
  getShowroomsForDealership,
  getBuybackCentersForDealership,
  dealershipUpdateDetails,
  // getBrands,
} from "@/lib/api";
import { getBrands } from "@/utils/api";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";
import { isDealershipSetupComplete } from "@/lib/dealership-utils";

const urlRegex = /^(https?:\/\/)?.+\..+/;
const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

const DEFAULT_BRANDS = [
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
];

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

  const [availableBrands, setAvailableBrands] = useState<any[]>([]);

  // Physical Locations state - unified for all location types
  type LocationType = "workshop" | "showroom" | "buyback_center";
  const [selectedLocationTypes, setSelectedLocationTypes] = useState<
    LocationType[]
  >([]);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [locationSuccess, setLocationSuccess] = useState("");

  // Location lists
  const [workshops, setWorkshops] = useState<any[]>([]);
  const [showrooms, setShowrooms] = useState<any[]>([]);
  const [buybackCenters, setBuybackCenters] = useState<any[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);
  const [dealershipId, setDealershipId] = useState<string>("");

  // Unified Physical Location form data
  const [locationFormData, setLocationFormData] = useState({
    locationName: "",
    contactNumber: "",
    emailAddress: "",
    address: "",
    pincode: "",
    openingTime: "09:00",
    closingTime: "18:00",
    daysOpen: [] as string[],
  });

  // Set dealership ID from localStorage on client side
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedDealershipId = localStorage.getItem("dealership_id");
      setDealershipId(storedDealershipId || user?.id || "");
    }
  }, [user?.id]);

  // Fetch all existing locations and available brands on component mount
  useEffect(() => {
    const fetchAllData = async () => {
      const storedDealershipId =
        typeof window !== "undefined"
          ? localStorage.getItem("dealership_id")
          : null;
      const currentDealershipId = storedDealershipId || user?.id || "";

      if (!currentDealershipId) {
        return;
      }

      setLoadingLocations(true);
      try {
        // 1. Fetch Locations
        const [fetchedWorkshops, fetchedShowrooms, fetchedBuybackCenters] =
          await Promise.all([
            getWorkshopsForDealership(currentDealershipId).catch(() => []),
            getShowroomsForDealership(currentDealershipId).catch(() => []),
            getBuybackCentersForDealership(currentDealershipId).catch(() => []),
          ]);

        setWorkshops(Array.isArray(fetchedWorkshops) ? fetchedWorkshops : []);
        setShowrooms(Array.isArray(fetchedShowrooms) ? fetchedShowrooms : []);
        setBuybackCenters(
          Array.isArray(fetchedBuybackCenters) ? fetchedBuybackCenters : []
        );

        // 2. Fetch Available Brands based on Region
        try {
          // Get dealership details to find region info
          // const details = await getDealershipDetails(currentDealershipId);
          const details = await getDealershipDetails();

          let regionId = details?.region_id;

          // If region_id is not directly available, try to infer from region_name
          if (!regionId && details?.region_name) {
            regionId = details.region_name.toLowerCase().replace(/\s+/g, "-");
          }

          // Fallback: try to extract from dealership ID string (e.g. "dealer-south-india")
          if (!regionId && currentDealershipId.includes("-")) {
            const commonRegions = [
              "south-india",
              "north-india",
              "east-india",
              "west-india",
              "central-india",
            ];
            for (const region of commonRegions) {
              if (currentDealershipId.toLowerCase().endsWith(region)) {
                regionId = region;
                break;
              }
            }
          }

          if (regionId) {
            const brandsData = await getBrands(regionId);
            if (Array.isArray(brandsData) && brandsData.length > 0) {
              setAvailableBrands(brandsData);
            }
          }
        } catch (err) {
          console.warn(
            "[Dealership Update] Failed to fetch dynamic brands, using defaults.",
            err
          );
        }
      } catch (error) {
        console.error(
          "[Dealership Update] Error fetching initial data:",
          error
        );
      } finally {
        setLoadingLocations(false);
      }
    };

    fetchAllData();
  }, [user?.id]);

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

    // Validate that at least one physical location exists
    const hasWorkshop = workshops.length > 0;
    const hasShowroom = showrooms.length > 0;
    const hasBuybackCenter = buybackCenters.length > 0;

    if (!hasWorkshop && !hasShowroom && !hasBuybackCenter) {
      setError(
        "Please add at least one physical location (workshop, showroom, or buyback center) before saving dealership details."
      );
      // Scroll to physical locations section
      setTimeout(() => {
        const locationsSection = document.getElementById(
          "physical-locations-section"
        );
        if (locationsSection) {
          locationsSection.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
      }, 100);
      return;
    }

    setIsLoading(true);

    try {
      // Get dealership ID from localStorage (stored during signup) or user context
      const storedDealershipId = localStorage.getItem("dealership_id");
      const dealershipId = storedDealershipId || user?.id || "";
      // const credit_balance = localStorage.getItem("dealership"); // Default credit balance for testing
      const credit_balance =JSON.parse(localStorage.getItem("dealership_details") || "{}").credits_balance || 0;

      if (!dealershipId) {
        throw new Error(
          "Dealership ID not found. Please ensure you're logged in and have completed signup."
        );
      }

      // Map brand names to API format (slug format)
      // We keep this as a fallback if dynamic mapping fails
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

      // Construct brand IDs by looking up the full brand object from API response
      const brandIds = dealershipDetails.brands
        .map((name) => {
          // 1. Try to find the matching brand object in the fetched list
          const brandObj = availableBrands.find(
            (b: any) => b.brand_name === name
          );

          // 2. If found, use the official brand_id from the database
          if (brandObj && brandObj.brand_id) {
            return brandObj.brand_id;
          }

          // 3. Fallback: Use slug map or basic slugification if not found in API list
          // (This handles the case where DEFAULT_BRANDS are used due to API failure)
          return (
            brandSlugMap[name] || name.toLowerCase().replace(/\s+/g, "-")
          );
        })
        .filter(Boolean);

      // Extract legal name from dealership_id (remove region suffix if present)
      // e.g., "logintest2-south-india" -> "logintest2"
      let dealershipLegalName = dealershipId;
      const lastDashIndex = dealershipId.lastIndexOf("-");
      if (lastDashIndex > 0) {
        // Check if it looks like a region suffix pattern (e.g., "-south-india")
        const potentialRegion = dealershipId.substring(lastDashIndex + 1);
        const commonRegions = [
          "India",
          "United States",
          "United Arab Emirates",
          "Saudi Arabia",
          // "south-india",
          // "north-india",
          // "east-india",
          // "west-india",
          // "central-india",
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

      if (brandIds.length > 0) {
        kwargs.supported_brands = brandIds;
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
      kwargs.credits_balance = Number(credit_balance + 500)  ; // Add default credit balance for testing
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

        // Locations are optional - setup can be complete without them
        // Dealers can add locations later
        const setupComplete =
          hasDealershipType &&
          hasLanguages &&
          hasSupportedBrands &&
          hasVerification;

        console.log(
          "[Dealership Update] Setup completion check from response:",
          {
            hasDealershipType,
            hasLanguages,
            hasSupportedBrands,
            hasVerification,
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
            responseData,
          });
          localStorage.setItem("dealership_setup_complete", "false");
          await checkDealershipSetup(); // Refresh auth context
          // Don't redirect - stay on page to complete missing details
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

  // Unified location submit handler - creates all selected location types
  const handleLocationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocationError("");
    setLocationSuccess("");

    // Validate location types selected
    if (selectedLocationTypes.length === 0) {
      setLocationError("Please select at least one location type");
      return;
    }

    // Validate required fields
    if (!locationFormData.locationName.trim()) {
      setLocationError("Location name is required");
      return;
    }
    if (!locationFormData.contactNumber.trim()) {
      setLocationError("Contact number is required");
      return;
    }
    if (!locationFormData.contactNumber.startsWith("+")) {
      setLocationError("Please select a country code for the phone number");
      return;
    }
    if (!locationFormData.emailAddress.trim()) {
      setLocationError("Email address is required");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(locationFormData.emailAddress)) {
      setLocationError("Please enter a valid email address");
      return;
    }
    if (!locationFormData.address.trim()) {
      setLocationError("Address is required");
      return;
    }
    if (!locationFormData.pincode.trim()) {
      setLocationError("Pincode is required");
      return;
    }
    if (locationFormData.pincode.length !== 6) {
      setLocationError("Pincode must be 6 digits");
      return;
    }
    if (locationFormData.daysOpen.length === 0) {
      setLocationError("Please select at least one day");
      return;
    }

    setLocationLoading(true);

    try {
      const storedDealershipId = localStorage.getItem("dealership_id");
      const currentDealershipId = storedDealershipId || user?.id || "";

      if (!currentDealershipId) {
        throw new Error(
          "Dealership ID not found. Please ensure you're logged in."
        );
      }

      // Get dealership details for supported brands
      let dealerName = currentDealershipId;
      let supportedBrands: string[] = [];
      try {
        const dealershipDetails = await getDealershipDetails();
        dealerName =
          dealershipDetails.dealership_name ||
          dealershipDetails.dealership_legal_name ||
          currentDealershipId;
        if (Array.isArray(dealershipDetails.supported_brands)) {
          supportedBrands = dealershipDetails.supported_brands;
        }
      } catch {
        dealerName = currentDealershipId;
      }

      // Parse address into city, state (pincode is separate field)
      const addressParts = locationFormData.address
        .split(",")
        .map((s) => s.trim());
      const city =
        addressParts.length > 1
          ? addressParts[addressParts.length - 2] || ""
          : "";
      const state =
        addressParts.length > 0
          ? addressParts[addressParts.length - 1] || ""
          : "";
      const pincode = locationFormData.pincode.trim();

      // All services for workshop
      const allServices = [
        "General Service",
        "Repair",
        "Body Shop",
        "Paint",
        "Tyre Alignment",
        "Wheel Balancing",
        "AC Service",
        "Battery Service",
        "Electrical Work",
        "Detailing",
        "Car Wash",
        "Pickup & Drop",
        "Roadside Assistance",
      ];

      // Create locations for each selected type
      const createPromises: Promise<any>[] = [];

      if (selectedLocationTypes.includes("workshop")) {
        const workshopData: CreateWorkshopRequest = {
          dealer_name: dealerName,
          dealership_id: currentDealershipId,
          workshop_name: locationFormData.locationName.trim(),
          workshop_type: "Main Workshop",
          workshop_status: "Active",
          email: locationFormData.emailAddress.trim(),
          contact_number: locationFormData.contactNumber.trim(),
          manager_name: "", // Removed from form
          address: locationFormData.address.trim(),
          city: city,
          state: state,
          pincode: pincode,
          region_id: "",
          region_name: "",
          geolocation: [0, 0],
          operating_hours: {
            opening_time: locationFormData.openingTime,
            closing_time: locationFormData.closingTime,
            days_open: locationFormData.daysOpen,
          },
          supported_brands: supportedBrands,
          services_offered: allServices,
          total_technicians: 0,
          total_service_bays: 0,
          daily_service_capacity: 0,
        };
        createPromises.push(createWorkshop(workshopData));
      }

      if (selectedLocationTypes.includes("showroom")) {
        const showroomId = `${currentDealershipId.replace(
          /-/g,
          "_"
        )}---${locationFormData.locationName
          .toLowerCase()
          .replace(/\s+/g, "-")
          .replace(/[^a-z0-9-]/g, "")}-${city.toLowerCase()}`;

        const showroomData: CreateShowroomRequest = {
          showroom_id: showroomId,
          showroom_name: locationFormData.locationName.trim(),
          showroom_full_name: locationFormData.locationName.trim(),
          showroom_type: "Main Showroom",
          showroom_status: "active",
          dealership_id: currentDealershipId,
          dealership_name: dealerName,
          manager_name: "", // Removed from form
          email: locationFormData.emailAddress.trim(),
          contact_number: locationFormData.contactNumber.trim(),
          address: locationFormData.address.trim(),
          city: city,
          state: state,
          pincode: pincode,
          region_name: "",
          geolocation: [0, 0],
          operating_hours: {
            opening_time: locationFormData.openingTime,
            closing_time: locationFormData.closingTime,
          },
          days_open: locationFormData.daysOpen,
          supported_brands: supportedBrands,
          parking_capacity: 0,
          daily_walkin_capacity: 0,
          display_vehicle_count: 0,
          total_sales_executives: 0,
        };
        createPromises.push(createShowroom(showroomData));
      }

      if (selectedLocationTypes.includes("buyback_center")) {
        const buybackCenterData: CreateBuybackCenterRequest = {
          buyback_center_id: locationFormData.locationName
            .toLowerCase()
            .replace(/\s+/g, "-"),
          dealership_id: currentDealershipId,
          dealership_name: dealerName,
          manager_name: "", // Removed from form
          email: locationFormData.emailAddress.trim(),
          contact_number: locationFormData.contactNumber.trim(),
          address: locationFormData.address.trim(),
          city: city,
          state: state,
          pincode: pincode,
          geolocation: [0, 0],
          operating_hours: {
            opening_time: locationFormData.openingTime,
            closing_time: locationFormData.closingTime,
          },
          days_open:
            locationFormData.daysOpen.length > 0
              ? locationFormData.daysOpen
              : {},
          parking_capacity: 0,
          daily_walkin_capacity: 0,
          display_vehicle_count: 0,
          total_sales_executives: 0,
        };
        createPromises.push(createBuybackCenter(buybackCenterData));
      }

      // Create all selected locations
      await Promise.all(createPromises);

      // Refresh all location lists
      const [fetchedWorkshops, fetchedShowrooms, fetchedBuybackCenters] =
        await Promise.all([
          getWorkshopsForDealership(currentDealershipId).catch(() => []),
          getShowroomsForDealership(currentDealershipId).catch(() => []),
          getBuybackCentersForDealership(currentDealershipId).catch(() => []),
        ]);

      setWorkshops(Array.isArray(fetchedWorkshops) ? fetchedWorkshops : []);
      setShowrooms(Array.isArray(fetchedShowrooms) ? fetchedShowrooms : []);
      setBuybackCenters(
        Array.isArray(fetchedBuybackCenters) ? fetchedBuybackCenters : []
      );

      const locationTypeNames = selectedLocationTypes
        .map((type) => {
          if (type === "buyback_center") return "Buyback Center";
          return type.charAt(0).toUpperCase() + type.slice(1);
        })
        .join(", ");

      setLocationSuccess(
        `Location "${locationFormData.locationName}" added successfully as ${locationTypeNames}! You can add more locations below.`
      );

      // Reset form
      setLocationFormData({
        locationName: "",
        contactNumber: "",
        emailAddress: "",
        address: "",
        pincode: "",
        openingTime: "09:00",
        closingTime: "18:00",
        daysOpen: [],
      });
      setSelectedLocationTypes([]);

      setTimeout(() => {
        setLocationSuccess("");
      }, 5000);

      await checkDealershipSetup();
    } catch (err) {
      if (err instanceof ApiError) {
        let cleanErrorMessage = err.message;
        if (err.error) {
          if (typeof err.error === "string") {
            try {
              const parsed = JSON.parse(err.error);
              cleanErrorMessage = parsed.message || parsed.error || err.message;
            } catch {
              cleanErrorMessage = err.error;
            }
          }
        }
        setLocationError(cleanErrorMessage);
      } else {
        setLocationError(
          err instanceof Error
            ? err.message
            : "Failed to create location(s). Please try again."
        );
      }
    } finally {
      setLocationLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background py-8">
        <div className="container mx-auto px-4 max-w-2xl">
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
                  {workshops.length > 0 ||
                  showrooms.length > 0 ||
                  buybackCenters.length > 0 ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                  )}
                  <span
                    className={
                      workshops.length > 0 ||
                      showrooms.length > 0 ||
                      buybackCenters.length > 0
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }
                  >
                    Step 2: Physical Locations (Required - Add at least one)
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
                        {(availableBrands.length > 0
                          ? availableBrands
                          : DEFAULT_BRANDS.map((name) => ({
                              brand_name: name,
                            }))
                        )
                          .filter(
                            (brand: any) =>
                              !dealershipDetails.brands.includes(
                                brand.brand_name
                              )
                          )
                          .map((brand: any) => (
                            <SelectItem
                              key={brand.brand_name}
                              value={brand.brand_name}
                            >
                              {brand.brand_name}
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
              </form>
            </CardContent>
          </Card>

          {/* Physical Locations Section */}
          <Card
            id="physical-locations-section"
            className="shadow-xl border-border/50 mt-6"
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <MapPin className="h-6 w-6 text-primary" />
                    Physical Locations
                    {(workshops.length > 0 ||
                      showrooms.length > 0 ||
                      buybackCenters.length > 0) && (
                      <Badge variant="secondary" className="ml-2">
                        {workshops.length +
                          showrooms.length +
                          buybackCenters.length}{" "}
                        Total
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription className="mt-2">
                    Manage workshops, showrooms, and buyback centers for your
                    dealership. At least one physical location is required to
                    save dealership details.
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Success/Error Messages */}
              {locationSuccess && (
                <Alert className="mb-6 border-green-500 bg-green-50 dark:bg-green-950/20">
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <AlertDescription className="text-green-800 dark:text-green-200">
                    {locationSuccess}
                  </AlertDescription>
                </Alert>
              )}

              {locationError && (
                <Alert variant="destructive" className="mb-6">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{locationError}</AlertDescription>
                </Alert>
              )}

              {loadingLocations && (
                <div className="text-center py-4 text-muted-foreground mb-6">
                  Loading locations...
                </div>
              )}

              {/* Display All Existing Locations */}
              {(workshops.length > 0 ||
                showrooms.length > 0 ||
                buybackCenters.length > 0) && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">
                    Existing Locations
                  </h3>

                  {/* Workshops */}
                  {workshops.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-md font-medium mb-2 flex items-center gap-2">
                        <Wrench className="h-4 w-4" />
                        Workshops ({workshops.length})
                      </h4>
                      <div className="space-y-3">
                        {workshops.map((workshop, index) => (
                          <div
                            key={workshop.workshop_id || index}
                            className="p-4 border rounded-lg bg-muted/30"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="font-semibold text-lg">
                                    {workshop.workshop_name}
                                  </h4>
                                  <Badge variant="outline">
                                    {workshop.workshop_type}
                                  </Badge>
                                  <Badge
                                    variant={
                                      workshop.workshop_status === "Active"
                                        ? "default"
                                        : "secondary"
                                    }
                                  >
                                    {workshop.workshop_status}
                                  </Badge>
                                </div>
                                <div className="grid md:grid-cols-2 gap-2 text-sm text-muted-foreground">
                                  {workshop.manager_name && (
                                    <div>
                                      <span className="font-medium">
                                        Manager:{" "}
                                      </span>
                                      {workshop.manager_name}
                                    </div>
                                  )}
                                  {workshop.email && (
                                    <div>
                                      <span className="font-medium">
                                        Email:{" "}
                                      </span>
                                      {workshop.email}
                                    </div>
                                  )}
                                  {workshop.contact_number && (
                                    <div>
                                      <span className="font-medium">
                                        Contact:{" "}
                                      </span>
                                      {workshop.contact_number}
                                    </div>
                                  )}
                                  {workshop.city && workshop.state && (
                                    <div>
                                      <span className="font-medium">
                                        Location:{" "}
                                      </span>
                                      {workshop.city}, {workshop.state}
                                    </div>
                                  )}
                                </div>
                                {workshop.supported_brands &&
                                  workshop.supported_brands.length > 0 && (
                                    <div className="mt-2 flex flex-wrap gap-1">
                                      {workshop.supported_brands.map(
                                        (brand: string) => (
                                          <Badge
                                            key={brand}
                                            variant="secondary"
                                            className="text-xs"
                                          >
                                            {brand}
                                          </Badge>
                                        )
                                      )}
                                    </div>
                                  )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Showrooms */}
                  {showrooms.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-md font-medium mb-2 flex items-center gap-2">
                        <Store className="h-4 w-4" />
                        Showrooms ({showrooms.length})
                      </h4>
                      <div className="space-y-3">
                        {showrooms.map((showroom, index) => (
                          <div
                            key={showroom.showroom_id || index}
                            className="p-4 border rounded-lg bg-muted/30"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="font-semibold text-lg">
                                    {showroom.showroom_name}
                                  </h4>
                                  <Badge variant="outline">
                                    {showroom.showroom_type}
                                  </Badge>
                                  <Badge
                                    variant={
                                      showroom.showroom_status === "active"
                                        ? "default"
                                        : "secondary"
                                    }
                                  >
                                    {showroom.showroom_status}
                                  </Badge>
                                </div>
                                <div className="grid md:grid-cols-2 gap-2 text-sm text-muted-foreground">
                                  {showroom.manager_name && (
                                    <div>
                                      <span className="font-medium">
                                        Manager:{" "}
                                      </span>
                                      {showroom.manager_name}
                                    </div>
                                  )}
                                  {showroom.email && (
                                    <div>
                                      <span className="font-medium">
                                        Email:{" "}
                                      </span>
                                      {showroom.email}
                                    </div>
                                  )}
                                  {showroom.contact_number && (
                                    <div>
                                      <span className="font-medium">
                                        Contact:{" "}
                                      </span>
                                      {showroom.contact_number}
                                    </div>
                                  )}
                                  {showroom.city && showroom.state && (
                                    <div>
                                      <span className="font-medium">
                                        Location:{" "}
                                      </span>
                                      {showroom.city}, {showroom.state}
                                    </div>
                                  )}
                                </div>
                                {showroom.supported_brands &&
                                  showroom.supported_brands.length > 0 && (
                                    <div className="mt-2 flex flex-wrap gap-1">
                                      {showroom.supported_brands.map(
                                        (brand: string) => (
                                          <Badge
                                            key={brand}
                                            variant="secondary"
                                            className="text-xs"
                                          >
                                            {brand}
                                          </Badge>
                                        )
                                      )}
                                    </div>
                                  )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Buyback Centers */}
                  {buybackCenters.length > 0 && (
                    <div className="mb-4">
                      <h4 className="text-md font-medium mb-2 flex items-center gap-2">
                        <RotateCcw className="h-4 w-4" />
                        Buyback Centers ({buybackCenters.length})
                      </h4>
                      <div className="space-y-3">
                        {buybackCenters.map((center, index) => (
                          <div
                            key={center.buyback_center_id || index}
                            className="p-4 border rounded-lg bg-muted/30"
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <h4 className="font-semibold text-lg">
                                    {center.buyback_center_id}
                                  </h4>
                                </div>
                                <div className="grid md:grid-cols-2 gap-2 text-sm text-muted-foreground">
                                  {center.manager_name && (
                                    <div>
                                      <span className="font-medium">
                                        Manager:{" "}
                                      </span>
                                      {center.manager_name}
                                    </div>
                                  )}
                                  {center.email && (
                                    <div>
                                      <span className="font-medium">
                                        Email:{" "}
                                      </span>
                                      {center.email}
                                    </div>
                                  )}
                                  {center.contact_number && (
                                    <div>
                                      <span className="font-medium">
                                        Contact:{" "}
                                      </span>
                                      {center.contact_number}
                                    </div>
                                  )}
                                  {center.city && center.state && (
                                    <div>
                                      <span className="font-medium">
                                        Location:{" "}
                                      </span>
                                      {center.city}, {center.state}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Unified Physical Location Form */}
              <form onSubmit={handleLocationSubmit} className="space-y-6">
                {locationError && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{locationError}</AlertDescription>
                  </Alert>
                )}

                {/* Location Type Selection - Horizontal Checkboxes */}
                <div className="space-y-2">
                  <Label>
                    Location Type <span className="text-destructive">*</span>
                  </Label>
                  <div className="flex flex-wrap gap-4 p-4 border rounded-md">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="location-type-workshop"
                        checked={selectedLocationTypes.includes("workshop")}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedLocationTypes([
                              ...selectedLocationTypes,
                              "workshop",
                            ]);
                          } else {
                            setSelectedLocationTypes(
                              selectedLocationTypes.filter(
                                (t) => t !== "workshop"
                              )
                            );
                          }
                        }}
                      />
                      <Label
                        htmlFor="location-type-workshop"
                        className="text-sm font-normal cursor-pointer"
                      >
                        Workshop
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="location-type-showroom"
                        checked={selectedLocationTypes.includes("showroom")}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedLocationTypes([
                              ...selectedLocationTypes,
                              "showroom",
                            ]);
                          } else {
                            setSelectedLocationTypes(
                              selectedLocationTypes.filter(
                                (t) => t !== "showroom"
                              )
                            );
                          }
                        }}
                      />
                      <Label
                        htmlFor="location-type-showroom"
                        className="text-sm font-normal cursor-pointer"
                      >
                        Showroom
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="location-type-buyback"
                        checked={selectedLocationTypes.includes(
                          "buyback_center"
                        )}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedLocationTypes([
                              ...selectedLocationTypes,
                              "buyback_center",
                            ]);
                          } else {
                            setSelectedLocationTypes(
                              selectedLocationTypes.filter(
                                (t) => t !== "buyback_center"
                              )
                            );
                          }
                        }}
                      />
                      <Label
                        htmlFor="location-type-buyback"
                        className="text-sm font-normal cursor-pointer"
                      >
                        Buyback Center
                      </Label>
                    </div>
                  </div>
                </div>

                {/* Basic Information */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Basic Information</h3>

                  <div className="space-y-2">
                    <Label htmlFor="locationName">
                      Location Name <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="locationName"
                      placeholder="e.g., Main Showroom"
                      value={locationFormData.locationName}
                      onChange={(e) =>
                        setLocationFormData({
                          ...locationFormData,
                          locationName: e.target.value,
                        })
                      }
                      required
                    />
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="contactNumber">
                        Phone Number <span className="text-destructive">*</span>
                      </Label>
                      <PhoneInput
                        defaultCountry="in"
                        value={locationFormData.contactNumber}
                        onChange={(value) =>
                          setLocationFormData({
                            ...locationFormData,
                            contactNumber: value,
                          })
                        }
                        inputClassName="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        countrySelectorStyleProps={{
                          buttonClassName:
                            "flex h-10 items-center justify-center rounded-l-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                        }}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="emailAddress">
                        Email Address{" "}
                        <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        id="emailAddress"
                        type="email"
                        placeholder="location@dealership.com"
                        value={locationFormData.emailAddress}
                        onChange={(e) =>
                          setLocationFormData({
                            ...locationFormData,
                            emailAddress: e.target.value,
                          })
                        }
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="address">
                      Full Address <span className="text-destructive">*</span>
                    </Label>
                    <Textarea
                      id="address"
                      placeholder="Street address, area, landmark, city, state"
                      value={locationFormData.address}
                      onChange={(e) =>
                        setLocationFormData({
                          ...locationFormData,
                          address: e.target.value,
                        })
                      }
                      rows={3}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="pincode">
                      Pincode <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="pincode"
                      placeholder="110001"
                      value={locationFormData.pincode}
                      onChange={(e) =>
                        setLocationFormData({
                          ...locationFormData,
                          pincode: e.target.value.replace(/\D/g, ""),
                        })
                      }
                      maxLength={6}
                      required
                    />
                  </div>
                </div>

                {/* Operating Hours */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Operating Hours</h3>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="openingTime">Open Time</Label>
                      <Input
                        id="openingTime"
                        type="time"
                        value={locationFormData.openingTime}
                        onChange={(e) =>
                          setLocationFormData({
                            ...locationFormData,
                            openingTime: e.target.value,
                          })
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="closingTime">Close Time</Label>
                      <Input
                        id="closingTime"
                        type="time"
                        value={locationFormData.closingTime}
                        onChange={(e) =>
                          setLocationFormData({
                            ...locationFormData,
                            closingTime: e.target.value,
                          })
                        }
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>
                      Days Open <span className="text-destructive">*</span>
                    </Label>
                    <div className="flex flex-wrap gap-3 p-3 border rounded-md">
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
                          className="flex items-center space-x-2 min-w-[100px]"
                        >
                          <Checkbox
                            id={`day-${day}`}
                            checked={locationFormData.daysOpen.includes(day)}
                            onCheckedChange={(checked) => {
                              if (checked) {
                                setLocationFormData({
                                  ...locationFormData,
                                  daysOpen: [...locationFormData.daysOpen, day],
                                });
                              } else {
                                setLocationFormData({
                                  ...locationFormData,
                                  daysOpen: locationFormData.daysOpen.filter(
                                    (d) => d !== day
                                  ),
                                });
                              }
                            }}
                            className="flex-shrink-0"
                          />
                          <Label
                            htmlFor={`day-${day}`}
                            className="text-sm font-normal cursor-pointer whitespace-nowrap"
                          >
                            {day}
                          </Label>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Submit Button */}
                <div className="flex justify-end gap-4 pt-4 border-t">
                  <Button
                    type="submit"
                    disabled={locationLoading}
                    className="min-w-[120px]"
                  >
                    {locationLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Add Location
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Sticky Footer with Save Button */}
          <div className="sticky bottom-0 left-0 right-0 bg-background border-t shadow-lg mt-8 mb-8 z-50">
            <div className="container mx-auto px-4 max-w-2xl py-4">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-sm text-muted-foreground text-center sm:text-left">
                  {workshops.length === 0 &&
                  showrooms.length === 0 &&
                  buybackCenters.length === 0 ? (
                    <span className="text-amber-600 font-medium">
                      <AlertCircle className="inline h-4 w-4 mr-1" />
                      Please add at least one physical location to continue
                    </span>
                  ) : (
                    <span>
                      {workshops.length +
                        showrooms.length +
                        buybackCenters.length}{" "}
                      location(s) added
                    </span>
                  )}
                </div>
                <Button
                  type="button"
                  size="lg"
                  disabled={
                    isLoading ||
                    (workshops.length === 0 &&
                      showrooms.length === 0 &&
                      buybackCenters.length === 0)
                  }
                  onClick={(e) => {
                    e.preventDefault();
                    // Create a proper synthetic event for form submission
                    const form = document.querySelector(
                      "form"
                    ) as HTMLFormElement;
                    if (form) {
                      const syntheticEvent = {
                        preventDefault: () => {},
                        stopPropagation: () => {},
                        nativeEvent: e.nativeEvent,
                        currentTarget: form,
                        target: form,
                        bubbles: false,
                        cancelable: false,
                        defaultPrevented: false,
                        eventPhase: 0,
                        isTrusted: false,
                        timeStamp: Date.now(),
                        type: "submit",
                        isDefaultPrevented: () => false,
                        isPropagationStopped: () => false,
                        persist: () => {},
                      } as unknown as React.FormEvent<HTMLFormElement>;
                      handleSubmit(syntheticEvent);
                    } else {
                      // Fallback: call handleSubmit with minimal event
                      handleSubmit({
                        preventDefault: () => {},
                      } as unknown as React.FormEvent);
                    }
                  }}
                  className="w-full sm:w-auto min-w-[200px]"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Save Dealership Details
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}