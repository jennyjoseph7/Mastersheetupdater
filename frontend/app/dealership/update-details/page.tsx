"use client";

import type React from "react";

import { useState, useEffect } from "react";
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
} from "@/lib/api";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";
import { isDealershipSetupComplete } from "@/lib/dealership-utils";

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

  // Physical Locations state - unified for all location types
  type LocationType = "workshop" | "showroom" | "buyback_center";
  const [selectedLocationType, setSelectedLocationType] = useState<LocationType | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState("");
  const [locationSuccess, setLocationSuccess] = useState("");
  
  // Location lists
  const [workshops, setWorkshops] = useState<any[]>([]);
  const [showrooms, setShowrooms] = useState<any[]>([]);
  const [buybackCenters, setBuybackCenters] = useState<any[]>([]);
  const [loadingLocations, setLoadingLocations] = useState(false);
  const [dealershipId, setDealershipId] = useState<string>("");

  // Workshop form data
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

  // Showroom form data
  const [showroomFormData, setShowroomFormData] = useState({
    showroom_name: "",
    showroom_full_name: "",
    showroom_type: "Main Showroom",
    showroom_status: "active",
    manager_name: "",
    email: "",
    contact_number: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    region_name: "",
    opening_time: "09:00",
    closing_time: "19:00",
    days_open: [] as string[],
    supported_brands: [] as string[],
    parking_capacity: "",
    daily_walkin_capacity: "",
    display_vehicle_count: "",
    total_sales_executives: "",
  });

  // Buyback Center form data
  const [buybackCenterFormData, setBuybackCenterFormData] = useState({
    buyback_center_id: "",
    manager_name: "",
    email: "",
    contact_number: "",
    address: "",
    city: "",
    state: "",
    pincode: "",
    opening_time: "09:00",
    closing_time: "18:00",
    days_open: [] as string[],
    parking_capacity: "",
    daily_walkin_capacity: "",
    display_vehicle_count: "",
    total_sales_executives: "",
  });

  // Set dealership ID from localStorage on client side
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedDealershipId = localStorage.getItem("dealership_id");
      setDealershipId(storedDealershipId || user?.id || "");
    }
  }, [user?.id]);

  // Fetch all existing locations on component mount
  useEffect(() => {
    const fetchAllLocations = async () => {
      const storedDealershipId = typeof window !== "undefined" 
        ? localStorage.getItem("dealership_id") 
        : null;
      const currentDealershipId = storedDealershipId || user?.id || "";
      
      if (!currentDealershipId) {
        return;
      }

      setLoadingLocations(true);
      try {
        // Fetch all location types in parallel
        const [fetchedWorkshops, fetchedShowrooms, fetchedBuybackCenters] = await Promise.all([
          getWorkshopsForDealership(currentDealershipId).catch(() => []),
          getShowroomsForDealership(currentDealershipId).catch(() => []),
          getBuybackCentersForDealership(currentDealershipId).catch(() => []),
        ]);
        
        setWorkshops(Array.isArray(fetchedWorkshops) ? fetchedWorkshops : []);
        setShowrooms(Array.isArray(fetchedShowrooms) ? fetchedShowrooms : []);
        setBuybackCenters(Array.isArray(fetchedBuybackCenters) ? fetchedBuybackCenters : []);
      } catch (error) {
        console.error("[Dealership Update] Error fetching locations:", error);
        setWorkshops([]);
        setShowrooms([]);
        setBuybackCenters([]);
      } finally {
        setLoadingLocations(false);
      }
    };

    fetchAllLocations();
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
        const locationsSection = document.getElementById("physical-locations-section");
        if (locationsSection) {
          locationsSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 100);
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

  // Generic location submit handler - routes to appropriate handler based on type
  const handleLocationSubmit = async (e: React.FormEvent, locationType: LocationType) => {
    e.preventDefault();
    setLocationError("");
    setLocationSuccess("");

    if (locationType === "workshop") {
      await handleWorkshopSubmit(e);
    } else if (locationType === "showroom") {
      await handleShowroomSubmit(e);
    } else if (locationType === "buyback_center") {
      await handleBuybackCenterSubmit(e);
    }
  };

  const handleWorkshopSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocationError("");
    setLocationSuccess("");

    // Validate required fields
    if (!workshopFormData.workshop_name.trim()) {
      setLocationError("Workshop name is required");
      return;
    }
    if (!workshopFormData.manager_name.trim()) {
      setLocationError("Manager name is required");
      return;
    }
    if (!workshopFormData.email.trim()) {
      setLocationError("Email is required");
      return;
    }
    if (!workshopFormData.contact_number.trim()) {
      setLocationError("Contact number is required");
      return;
    }

    // Validate phone number format
    const phoneValue = workshopFormData.contact_number.trim();
    if (!phoneValue || phoneValue.length < 10) {
      setLocationError("Please enter a valid phone number with country code");
      return;
    }
    if (!phoneValue.startsWith("+")) {
      setLocationError("Please select a country code for the phone number");
      return;
    }
    if (!workshopFormData.address.trim()) {
      setLocationError("Address is required");
      return;
    }
    if (!workshopFormData.city.trim()) {
      setLocationError("City is required");
      return;
    }
    if (!workshopFormData.state.trim()) {
      setLocationError("State is required");
      return;
    }
    if (!workshopFormData.pincode.trim()) {
      setLocationError("Pincode is required");
      return;
    }
    if (workshopFormData.days_open.length === 0) {
      setLocationError("Please select at least one day the workshop is open");
      return;
    }
    if (workshopFormData.supported_brands.length === 0) {
      setLocationError("Please select at least one supported brand");
      return;
    }
    if (workshopFormData.services_offered.length === 0) {
      setLocationError("Please select at least one service offered");
      return;
    }
    if (!workshopFormData.total_technicians.trim()) {
      setLocationError("Total technicians is required");
      return;
    }
    if (!workshopFormData.total_service_bays.trim()) {
      setLocationError("Total service bays is required");
      return;
    }
    if (!workshopFormData.daily_service_capacity.trim()) {
      setLocationError("Daily service capacity is required");
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(workshopFormData.email)) {
      setLocationError("Please enter a valid email address");
      return;
    }

    setLocationLoading(true);

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

      // Refresh workshops list
      const fetchedWorkshops = await getWorkshopsForDealership(dealershipId);
      setWorkshops(Array.isArray(fetchedWorkshops) ? fetchedWorkshops : []);

      setLocationSuccess(
        `Workshop "${workshopFormData.workshop_name}" added successfully! You can add more locations below.`
      );

      // Reset form for next entry (keep form visible)
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

      // Keep form visible for adding more locations
      setSelectedLocationType("workshop");
      
      // Clear success message after 5 seconds
      setTimeout(() => {
        setLocationSuccess("");
      }, 5000);

      // Check if both dealership details and workshop are now complete
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

      // Refresh dealership setup status (locations are optional)
      await checkDealershipSetup();
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
        setLocationError(cleanErrorMessage);
      } else {
        setLocationError(
          err instanceof Error
            ? err.message
            : "Failed to create workshop. Please try again."
        );
      }
    } finally {
      setLocationLoading(false);
    }
  };

  // Showroom submit handler
  const handleShowroomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocationError("");
    setLocationSuccess("");

    // Validate required fields
    if (!showroomFormData.showroom_name.trim()) {
      setLocationError("Showroom name is required");
      return;
    }
    if (!showroomFormData.manager_name.trim()) {
      setLocationError("Manager name is required");
      return;
    }
    if (!showroomFormData.email.trim()) {
      setLocationError("Email is required");
      return;
    }
    if (!showroomFormData.contact_number.trim()) {
      setLocationError("Contact number is required");
      return;
    }

    const phoneValue = showroomFormData.contact_number.trim();
    if (!phoneValue || phoneValue.length < 10 || !phoneValue.startsWith("+")) {
      setLocationError("Please enter a valid phone number with country code");
      return;
    }
    if (!showroomFormData.address.trim()) {
      setLocationError("Address is required");
      return;
    }
    if (!showroomFormData.city.trim()) {
      setLocationError("City is required");
      return;
    }
    if (!showroomFormData.state.trim()) {
      setLocationError("State is required");
      return;
    }
    if (!showroomFormData.pincode.trim()) {
      setLocationError("Pincode is required");
      return;
    }
    if (showroomFormData.days_open.length === 0) {
      setLocationError("Please select at least one day the showroom is open");
      return;
    }
    if (showroomFormData.supported_brands.length === 0) {
      setLocationError("Please select at least one supported brand");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(showroomFormData.email)) {
      setLocationError("Please enter a valid email address");
      return;
    }

    setLocationLoading(true);

    try {
      const storedDealershipId = localStorage.getItem("dealership_id");
      const dealershipId = storedDealershipId || user?.id || "";

      if (!dealershipId) {
        throw new Error("Dealership ID not found. Please ensure you're logged in.");
      }

      let dealerName = dealershipId;
      try {
        const dealershipDetails = await getDealershipDetails();
        dealerName =
          dealershipDetails.dealership_name ||
          dealershipDetails.dealership_legal_name ||
          dealershipId;
      } catch {
        dealerName = dealershipId;
      }

      // Generate showroom_id from showroom_name and dealership_id
      const showroomId = `${dealershipId.replace(/-/g, "_")}---${showroomFormData.showroom_name
        .toLowerCase()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9-]/g, "")}-${showroomFormData.city.toLowerCase()}`;

      const showroomData: CreateShowroomRequest = {
        showroom_id: showroomId,
        showroom_name: showroomFormData.showroom_name.trim(),
        showroom_full_name: showroomFormData.showroom_full_name.trim() || showroomFormData.showroom_name.trim(),
        showroom_type: showroomFormData.showroom_type,
        showroom_status: showroomFormData.showroom_status,
        dealership_id: dealershipId,
        dealership_name: dealerName,
        manager_name: showroomFormData.manager_name.trim(),
        email: showroomFormData.email.trim(),
        contact_number: showroomFormData.contact_number.trim(),
        address: showroomFormData.address.trim(),
        city: showroomFormData.city.trim(),
        state: showroomFormData.state.trim(),
        pincode: showroomFormData.pincode.trim(),
        region_name: showroomFormData.region_name || "",
        geolocation: [0, 0],
        operating_hours: {
          opening_time: showroomFormData.opening_time,
          closing_time: showroomFormData.closing_time,
        },
        days_open: showroomFormData.days_open,
        supported_brands: showroomFormData.supported_brands,
        parking_capacity: parseInt(showroomFormData.parking_capacity || "0", 10),
        daily_walkin_capacity: parseInt(showroomFormData.daily_walkin_capacity || "0", 10),
        display_vehicle_count: parseInt(showroomFormData.display_vehicle_count || "0", 10),
        total_sales_executives: parseInt(showroomFormData.total_sales_executives || "0", 10),
      };

      await createShowroom(showroomData);

      // Refresh showrooms list
      const fetchedShowrooms = await getShowroomsForDealership(dealershipId);
      setShowrooms(Array.isArray(fetchedShowrooms) ? fetchedShowrooms : []);

      setLocationSuccess(
        `Showroom "${showroomFormData.showroom_name}" added successfully! You can add more locations below.`
      );

      // Reset form
      setShowroomFormData({
        showroom_name: "",
        showroom_full_name: "",
        showroom_type: "Main Showroom",
        showroom_status: "active",
        manager_name: "",
        email: "",
        contact_number: "",
        address: "",
        city: "",
        state: "",
        pincode: "",
        region_name: "",
        opening_time: "09:00",
        closing_time: "19:00",
        days_open: [],
        supported_brands: [],
        parking_capacity: "",
        daily_walkin_capacity: "",
        display_vehicle_count: "",
        total_sales_executives: "",
      });

      setSelectedLocationType("showroom");
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
              cleanErrorMessage =
                parsed.error || parsed.message || cleanErrorMessage;
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
            : "Failed to create showroom. Please try again."
        );
      }
    } finally {
      setLocationLoading(false);
    }
  };

  // Buyback Center submit handler
  const handleBuybackCenterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocationError("");
    setLocationSuccess("");

    // Validate required fields
    if (!buybackCenterFormData.buyback_center_id.trim()) {
      setLocationError("Buyback Center ID is required");
      return;
    }
    if (!buybackCenterFormData.manager_name.trim()) {
      setLocationError("Manager name is required");
      return;
    }
    if (!buybackCenterFormData.email.trim()) {
      setLocationError("Email is required");
      return;
    }
    if (!buybackCenterFormData.contact_number.trim()) {
      setLocationError("Contact number is required");
      return;
    }

    const phoneValue = buybackCenterFormData.contact_number.trim();
    if (!phoneValue || phoneValue.length < 10 || !phoneValue.startsWith("+")) {
      setLocationError("Please enter a valid phone number with country code");
      return;
    }
    if (!buybackCenterFormData.address.trim()) {
      setLocationError("Address is required");
      return;
    }
    if (!buybackCenterFormData.city.trim()) {
      setLocationError("City is required");
      return;
    }
    if (!buybackCenterFormData.state.trim()) {
      setLocationError("State is required");
      return;
    }
    if (!buybackCenterFormData.pincode.trim()) {
      setLocationError("Pincode is required");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(buybackCenterFormData.email)) {
      setLocationError("Please enter a valid email address");
      return;
    }

    setLocationLoading(true);

    try {
      const storedDealershipId = localStorage.getItem("dealership_id");
      const dealershipId = storedDealershipId || user?.id || "";

      if (!dealershipId) {
        throw new Error("Dealership ID not found. Please ensure you're logged in.");
      }

      let dealerName = dealershipId;
      try {
        const dealershipDetails = await getDealershipDetails();
        dealerName =
          dealershipDetails.dealership_name ||
          dealershipDetails.dealership_legal_name ||
          dealershipId;
      } catch {
        dealerName = dealershipId;
      }

      const buybackCenterData: CreateBuybackCenterRequest = {
        buyback_center_id: buybackCenterFormData.buyback_center_id.trim(),
        dealership_id: dealershipId,
        dealership_name: dealerName,
        manager_name: buybackCenterFormData.manager_name.trim(),
        email: buybackCenterFormData.email.trim(),
        contact_number: buybackCenterFormData.contact_number.trim(),
        address: buybackCenterFormData.address.trim(),
        city: buybackCenterFormData.city.trim(),
        state: buybackCenterFormData.state.trim(),
        pincode: buybackCenterFormData.pincode.trim(),
        geolocation: [0, 0],
        operating_hours: {
          opening_time: buybackCenterFormData.opening_time,
          closing_time: buybackCenterFormData.closing_time,
        },
        days_open: buybackCenterFormData.days_open.length > 0 
          ? buybackCenterFormData.days_open 
          : {},
        parking_capacity: parseInt(buybackCenterFormData.parking_capacity || "0", 10),
        daily_walkin_capacity: parseInt(buybackCenterFormData.daily_walkin_capacity || "0", 10),
        display_vehicle_count: parseInt(buybackCenterFormData.display_vehicle_count || "0", 10),
        total_sales_executives: parseInt(buybackCenterFormData.total_sales_executives || "0", 10),
      };

      await createBuybackCenter(buybackCenterData);

      // Refresh buyback centers list
      const fetchedBuybackCenters = await getBuybackCentersForDealership(dealershipId);
      setBuybackCenters(Array.isArray(fetchedBuybackCenters) ? fetchedBuybackCenters : []);

      setLocationSuccess(
        `Buyback Center "${buybackCenterFormData.buyback_center_id}" added successfully! You can add more locations below.`
      );

      // Reset form
      setBuybackCenterFormData({
        buyback_center_id: "",
        manager_name: "",
        email: "",
        contact_number: "",
        address: "",
        city: "",
        state: "",
        pincode: "",
        opening_time: "09:00",
        closing_time: "18:00",
        days_open: [],
        parking_capacity: "",
        daily_walkin_capacity: "",
        display_vehicle_count: "",
        total_sales_executives: "",
      });

      setSelectedLocationType("buyback_center");
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
              cleanErrorMessage =
                parsed.error || parsed.message || cleanErrorMessage;
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
            : "Failed to create buyback center. Please try again."
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
                  {(workshops.length > 0 || showrooms.length > 0 || buybackCenters.length > 0) ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-amber-600" />
                  )}
                  <span className={workshops.length > 0 || showrooms.length > 0 || buybackCenters.length > 0 ? "text-foreground" : "text-muted-foreground"}>
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

              </form>
            </CardContent>
          </Card>

          {/* Physical Locations Section */}
          <Card id="physical-locations-section" className="shadow-xl border-border/50 mt-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    <MapPin className="h-6 w-6 text-primary" />
                    Physical Locations
                    {(workshops.length > 0 || showrooms.length > 0 || buybackCenters.length > 0) && (
                      <Badge variant="secondary" className="ml-2">
                        {workshops.length + showrooms.length + buybackCenters.length} Total
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription className="mt-2">
                    Manage workshops, showrooms, and buyback centers for your dealership. At least one physical location is required to save dealership details.
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
              {(workshops.length > 0 || showrooms.length > 0 || buybackCenters.length > 0) && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-4">Existing Locations</h3>
                  
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
                                      <span className="font-medium">Manager: </span>
                                      {workshop.manager_name}
                                    </div>
                                  )}
                                  {workshop.email && (
                                    <div>
                                      <span className="font-medium">Email: </span>
                                      {workshop.email}
                                    </div>
                                  )}
                                  {workshop.contact_number && (
                                    <div>
                                      <span className="font-medium">Contact: </span>
                                      {workshop.contact_number}
                                    </div>
                                  )}
                                  {workshop.city && workshop.state && (
                                    <div>
                                      <span className="font-medium">Location: </span>
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
                                      <span className="font-medium">Manager: </span>
                                      {showroom.manager_name}
                                    </div>
                                  )}
                                  {showroom.email && (
                                    <div>
                                      <span className="font-medium">Email: </span>
                                      {showroom.email}
                                    </div>
                                  )}
                                  {showroom.contact_number && (
                                    <div>
                                      <span className="font-medium">Contact: </span>
                                      {showroom.contact_number}
                                    </div>
                                  )}
                                  {showroom.city && showroom.state && (
                                    <div>
                                      <span className="font-medium">Location: </span>
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
                                      <span className="font-medium">Manager: </span>
                                      {center.manager_name}
                                    </div>
                                  )}
                                  {center.email && (
                                    <div>
                                      <span className="font-medium">Email: </span>
                                      {center.email}
                                    </div>
                                  )}
                                  {center.contact_number && (
                                    <div>
                                      <span className="font-medium">Contact: </span>
                                      {center.contact_number}
                                    </div>
                                  )}
                                  {center.city && center.state && (
                                    <div>
                                      <span className="font-medium">Location: </span>
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

              {/* Location Type Selection Tabs */}
              <Tabs 
                value={selectedLocationType || undefined} 
                onValueChange={(value) => setSelectedLocationType(value as LocationType)}
                className="w-full"
              >
                <TabsList className="grid w-full grid-cols-3 mb-6">
                  <TabsTrigger value="workshop" className="flex items-center gap-2">
                    <Wrench className="h-4 w-4" />
                    Workshop
                  </TabsTrigger>
                  <TabsTrigger value="showroom" className="flex items-center gap-2">
                    <Store className="h-4 w-4" />
                    Showroom
                  </TabsTrigger>
                  <TabsTrigger value="buyback_center" className="flex items-center gap-2">
                    <RotateCcw className="h-4 w-4" />
                    Buyback Center
                  </TabsTrigger>
                </TabsList>

                {/* Workshop Form */}
                <TabsContent value="workshop">
                  <form onSubmit={(e) => handleLocationSubmit(e, "workshop")} className="space-y-6">
                  {locationError && selectedLocationType === "workshop" && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{locationError}</AlertDescription>
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
                            const currentDealershipId = dealershipId || user?.id || "";
                            // Try to extract dealer name from dealership_id
                            if (currentDealershipId.includes("-")) {
                              const parts = currentDealershipId.split("-");
                              return parts
                                .slice(0, -1)
                                .join(" ")
                                .replace(/\b\w/g, (l) => l.toUpperCase());
                            }
                            return currentDealershipId;
                          })()}
                          disabled
                          className="bg-background"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="dealership_id">Dealership ID</Label>
                        <Input
                          id="dealership_id"
                          value={dealershipId || user?.id || ""}
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

                    <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
                      <Button type="submit" size="lg" disabled={locationLoading} className="w-full sm:flex-1">
                        {locationLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Creating Workshop...
                          </>
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                            Add Workshop
                      </>
                    )}
                  </Button>
                      {workshops.length > 0 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="lg"
                          onClick={() => {
                            // Reset form but keep it visible for adding another
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
                            setLocationError("");
                            setLocationSuccess("");
                            setSelectedLocationType("workshop");
                          }}
                          className="w-full sm:w-auto"
                        >
                          <Wrench className="mr-2 h-4 w-4" />
                          Add Another Workshop
                        </Button>
                      )}
                </div>
              </form>
                </TabsContent>

                {/* Showroom Form */}
                <TabsContent value="showroom">
                  <form onSubmit={(e) => handleLocationSubmit(e, "showroom")} className="space-y-6">
                    {/* Auto-filled Dealership Information */}
                    <div className="space-y-4 p-4 bg-muted/50 rounded-lg border">
                      <h3 className="text-lg font-semibold">Dealership Information</h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="showroom_dealership_id">Dealership ID</Label>
                          <Input
                            id="showroom_dealership_id"
                            value={dealershipId || user?.id || ""}
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
                          <Label htmlFor="showroom_name">Showroom Name *</Label>
                          <Input
                            id="showroom_name"
                            placeholder="e.g., NEXA Delhi South - Main Showroom"
                            value={showroomFormData.showroom_name}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                showroom_name: e.target.value,
                                showroom_full_name: e.target.value || showroomFormData.showroom_full_name,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_type">Showroom Type *</Label>
                          <Select
                            value={showroomFormData.showroom_type}
                            onValueChange={(value) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                showroom_type: value,
                              })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Main Showroom">Main Showroom</SelectItem>
                              <SelectItem value="Satellite Showroom">Satellite Showroom</SelectItem>
                              <SelectItem value="Authorized Showroom">Authorized Showroom</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="showroom_manager_name">Manager Name *</Label>
                          <Input
                            id="showroom_manager_name"
                            placeholder="Enter manager name"
                            value={showroomFormData.manager_name}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                manager_name: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_status">Showroom Status</Label>
                          <Select
                            value={showroomFormData.showroom_status}
                            onValueChange={(value) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                showroom_status: value,
                              })
                            }
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="active">Active</SelectItem>
                              <SelectItem value="inactive">Inactive</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                    </div>

                    {/* Contact Information */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Contact Information</h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="showroom_email" className="flex items-center gap-2">
                            <Mail className="h-4 w-4" />
                            Email *
                          </Label>
                          <Input
                            id="showroom_email"
                            type="email"
                            placeholder="showroom@example.com"
                            value={showroomFormData.email}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                email: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_contact_number" className="flex items-center gap-2">
                            <Phone className="h-4 w-4" />
                            Contact Number *
                          </Label>
                          <PhoneInput
                            value={showroomFormData.contact_number}
                            onChange={(phone) =>
                              setShowroomFormData({
                                ...showroomFormData,
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
                        <Label htmlFor="showroom_address">Address *</Label>
                        <Textarea
                          id="showroom_address"
                          placeholder="Enter full address"
                          value={showroomFormData.address}
                          onChange={(e) =>
                            setShowroomFormData({
                              ...showroomFormData,
                              address: e.target.value,
                            })
                          }
                          required
                        />
                      </div>
                      <div className="grid md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="showroom_city">City *</Label>
                          <Input
                            id="showroom_city"
                            placeholder="City"
                            value={showroomFormData.city}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                city: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_state">State *</Label>
                          <Input
                            id="showroom_state"
                            placeholder="State"
                            value={showroomFormData.state}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                state: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_pincode">Pincode *</Label>
                          <Input
                            id="showroom_pincode"
                            placeholder="110001"
                            value={showroomFormData.pincode}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
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
                          <Label htmlFor="showroom_opening_time">Opening Time *</Label>
                          <Input
                            id="showroom_opening_time"
                            type="time"
                            value={showroomFormData.opening_time}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                opening_time: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_closing_time">Closing Time *</Label>
                          <Input
                            id="showroom_closing_time"
                            type="time"
                            value={showroomFormData.closing_time}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
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
                          {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((day) => (
                            <div key={day} className="flex items-center space-x-2">
                              <Checkbox
                                id={`showroom-day-${day}`}
                                checked={showroomFormData.days_open.includes(day)}
                                onCheckedChange={(checked) => {
                                  if (checked) {
                                    setShowroomFormData({
                                      ...showroomFormData,
                                      days_open: [...showroomFormData.days_open, day],
                                    });
                                  } else {
                                    setShowroomFormData({
                                      ...showroomFormData,
                                      days_open: showroomFormData.days_open.filter((d) => d !== day),
                                    });
                                  }
                                }}
                              />
                              <Label htmlFor={`showroom-day-${day}`} className="text-sm font-normal cursor-pointer">
                                {day}
                              </Label>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Supported Brands */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Supported Brands *</h3>
                      <div className="flex flex-wrap gap-2">
                        {["NEXA", "Maruti Suzuki", "Hyundai", "Toyota", "Honda", "Tata Motors", "Mahindra", "Kia", "MG Motor", "Ford", "Volkswagen"].map((brand) => (
                          <Badge
                            key={brand}
                            variant={showroomFormData.supported_brands.includes(brand) ? "default" : "outline"}
                            className="cursor-pointer px-3 py-2 text-sm"
                            onClick={() => {
                              if (showroomFormData.supported_brands.includes(brand)) {
                                setShowroomFormData({
                                  ...showroomFormData,
                                  supported_brands: showroomFormData.supported_brands.filter((b) => b !== brand),
                                });
                              } else {
                                setShowroomFormData({
                                  ...showroomFormData,
                                  supported_brands: [...showroomFormData.supported_brands, brand],
                                });
                              }
                            }}
                          >
                            {brand}
                            {showroomFormData.supported_brands.includes(brand) && <X className="h-3 w-3 ml-2" />}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    {/* Capacity Information (Optional) */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Capacity Information (Optional)
                      </h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="showroom_parking_capacity">Parking Capacity</Label>
                          <Input
                            id="showroom_parking_capacity"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={showroomFormData.parking_capacity}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                parking_capacity: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_daily_walkin_capacity">Daily Walk-in Capacity</Label>
                          <Input
                            id="showroom_daily_walkin_capacity"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={showroomFormData.daily_walkin_capacity}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                daily_walkin_capacity: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_display_vehicle_count">Display Vehicle Count</Label>
                          <Input
                            id="showroom_display_vehicle_count"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={showroomFormData.display_vehicle_count}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                display_vehicle_count: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="showroom_total_sales_executives">Total Sales Executives</Label>
                          <Input
                            id="showroom_total_sales_executives"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={showroomFormData.total_sales_executives}
                            onChange={(e) =>
                              setShowroomFormData({
                                ...showroomFormData,
                                total_sales_executives: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
                      <Button type="submit" size="lg" disabled={locationLoading} className="w-full sm:flex-1">
                        {locationLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Creating Showroom...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            Add Showroom
                          </>
                        )}
                      </Button>
                      {showrooms.length > 0 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="lg"
                          onClick={() => {
                            // Reset form but keep it visible for adding another
                            setShowroomFormData({
                              showroom_name: "",
                              showroom_full_name: "",
                              showroom_type: "Main Showroom",
                              showroom_status: "active",
                              manager_name: "",
                              email: "",
                              contact_number: "",
                              address: "",
                              city: "",
                              state: "",
                              pincode: "",
                              region_name: "",
                              opening_time: "09:00",
                              closing_time: "19:00",
                              days_open: [],
                              supported_brands: [],
                              parking_capacity: "",
                              daily_walkin_capacity: "",
                              display_vehicle_count: "",
                              total_sales_executives: "",
                            });
                            setLocationError("");
                            setLocationSuccess("");
                            setSelectedLocationType("showroom");
                          }}
                          className="w-full sm:w-auto"
                        >
                          <Store className="mr-2 h-4 w-4" />
                          Add Another Showroom
                        </Button>
                      )}
                    </div>
                  </form>
                </TabsContent>

                {/* Buyback Center Form */}
                <TabsContent value="buyback_center">
                  <form onSubmit={(e) => handleLocationSubmit(e, "buyback_center")} className="space-y-6">
                    {/* Auto-filled Dealership Information */}
                    <div className="space-y-4 p-4 bg-muted/50 rounded-lg border">
                      <h3 className="text-lg font-semibold">Dealership Information</h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="buyback_dealership_id">Dealership ID</Label>
                          <Input
                            id="buyback_dealership_id"
                            value={dealershipId || user?.id || ""}
                            disabled
                            className="bg-background font-mono"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Basic Information */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Basic Information</h3>
                      <div className="space-y-2">
                        <Label htmlFor="buyback_center_id">Buyback Center ID *</Label>
                        <Input
                          id="buyback_center_id"
                          placeholder="e.g., delhi"
                          value={buybackCenterFormData.buyback_center_id}
                          onChange={(e) =>
                            setBuybackCenterFormData({
                              ...buybackCenterFormData,
                              buyback_center_id: e.target.value.trim(),
                            })
                          }
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="buyback_manager_name">Manager Name *</Label>
                        <Input
                          id="buyback_manager_name"
                          placeholder="Enter manager name"
                          value={buybackCenterFormData.manager_name}
                          onChange={(e) =>
                            setBuybackCenterFormData({
                              ...buybackCenterFormData,
                              manager_name: e.target.value,
                            })
                          }
                          required
                        />
                      </div>
                    </div>

                    {/* Contact Information */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold">Contact Information</h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="buyback_email" className="flex items-center gap-2">
                            <Mail className="h-4 w-4" />
                            Email *
                          </Label>
                          <Input
                            id="buyback_email"
                            type="email"
                            placeholder="buyback@example.com"
                            value={buybackCenterFormData.email}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                email: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_contact_number" className="flex items-center gap-2">
                            <Phone className="h-4 w-4" />
                            Contact Number *
                          </Label>
                          <PhoneInput
                            value={buybackCenterFormData.contact_number}
                            onChange={(phone) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
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
                        <Label htmlFor="buyback_address">Address *</Label>
                        <Textarea
                          id="buyback_address"
                          placeholder="Enter full address"
                          value={buybackCenterFormData.address}
                          onChange={(e) =>
                            setBuybackCenterFormData({
                              ...buybackCenterFormData,
                              address: e.target.value,
                            })
                          }
                          required
                        />
                      </div>
                      <div className="grid md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="buyback_city">City *</Label>
                          <Input
                            id="buyback_city"
                            placeholder="City"
                            value={buybackCenterFormData.city}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                city: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_state">State *</Label>
                          <Input
                            id="buyback_state"
                            placeholder="State"
                            value={buybackCenterFormData.state}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                state: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_pincode">Pincode *</Label>
                          <Input
                            id="buyback_pincode"
                            placeholder="110001"
                            value={buybackCenterFormData.pincode}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
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
                          <Label htmlFor="buyback_opening_time">Opening Time *</Label>
                          <Input
                            id="buyback_opening_time"
                            type="time"
                            value={buybackCenterFormData.opening_time}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                opening_time: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_closing_time">Closing Time *</Label>
                          <Input
                            id="buyback_closing_time"
                            type="time"
                            value={buybackCenterFormData.closing_time}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                closing_time: e.target.value,
                              })
                            }
                            required
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>Days Open (Optional)</Label>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map((day) => (
                            <div key={day} className="flex items-center space-x-2">
                              <Checkbox
                                id={`buyback-day-${day}`}
                                checked={buybackCenterFormData.days_open.includes(day)}
                                onCheckedChange={(checked) => {
                                  if (checked) {
                                    setBuybackCenterFormData({
                                      ...buybackCenterFormData,
                                      days_open: [...buybackCenterFormData.days_open, day],
                                    });
                                  } else {
                                    setBuybackCenterFormData({
                                      ...buybackCenterFormData,
                                      days_open: buybackCenterFormData.days_open.filter((d) => d !== day),
                                    });
                                  }
                                }}
                              />
                              <Label htmlFor={`buyback-day-${day}`} className="text-sm font-normal cursor-pointer">
                                {day}
                              </Label>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Capacity Information (Optional) */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Users className="h-5 w-5" />
                        Capacity Information (Optional)
                      </h3>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="buyback_parking_capacity">Parking Capacity</Label>
                          <Input
                            id="buyback_parking_capacity"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={buybackCenterFormData.parking_capacity}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                parking_capacity: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_daily_walkin_capacity">Daily Walk-in Capacity</Label>
                          <Input
                            id="buyback_daily_walkin_capacity"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={buybackCenterFormData.daily_walkin_capacity}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                daily_walkin_capacity: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_display_vehicle_count">Display Vehicle Count</Label>
                          <Input
                            id="buyback_display_vehicle_count"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={buybackCenterFormData.display_vehicle_count}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                display_vehicle_count: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="buyback_total_sales_executives">Total Sales Executives</Label>
                          <Input
                            id="buyback_total_sales_executives"
                            type="number"
                            min="0"
                            placeholder="0"
                            value={buybackCenterFormData.total_sales_executives}
                            onChange={(e) =>
                              setBuybackCenterFormData({
                                ...buybackCenterFormData,
                                total_sales_executives: e.target.value.replace(/\D/g, ""),
                              })
                            }
                          />
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t">
                      <Button type="submit" size="lg" disabled={locationLoading} className="w-full sm:flex-1">
                        {locationLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Creating Buyback Center...
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="mr-2 h-4 w-4" />
                            Add Buyback Center
                          </>
                        )}
                      </Button>
                      {buybackCenters.length > 0 && (
                        <Button
                          type="button"
                          variant="outline"
                          size="lg"
                          onClick={() => {
                            // Reset form but keep it visible for adding another
                            setBuybackCenterFormData({
                              buyback_center_id: "",
                              manager_name: "",
                              email: "",
                              contact_number: "",
                              address: "",
                              city: "",
                              state: "",
                              pincode: "",
                              opening_time: "09:00",
                              closing_time: "18:00",
                              days_open: [],
                              parking_capacity: "",
                              daily_walkin_capacity: "",
                              display_vehicle_count: "",
                              total_sales_executives: "",
                            });
                            setLocationError("");
                            setLocationSuccess("");
                            setSelectedLocationType("buyback_center");
                          }}
                          className="w-full sm:w-auto"
                        >
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Add Another Buyback Center
                        </Button>
                      )}
                    </div>
                  </form>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Sticky Footer with Save Button */}
          <div className="sticky bottom-0 left-0 right-0 bg-background border-t shadow-lg mt-8 mb-8 z-50">
            <div className="container mx-auto px-4 max-w-2xl py-4">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-sm text-muted-foreground text-center sm:text-left">
                  {workshops.length === 0 && showrooms.length === 0 && buybackCenters.length === 0 ? (
                    <span className="text-amber-600 font-medium">
                      <AlertCircle className="inline h-4 w-4 mr-1" />
                      Please add at least one physical location to continue
                    </span>
                  ) : (
                    <span>
                      {workshops.length + showrooms.length + buybackCenters.length} location(s) added
                    </span>
                  )}
                </div>
                <Button
                  type="button"
                  size="lg"
                  disabled={isLoading || (workshops.length === 0 && showrooms.length === 0 && buybackCenters.length === 0)}
                  onClick={(e) => {
                    e.preventDefault();
                    // Create a proper synthetic event for form submission
                    const form = document.querySelector('form') as HTMLFormElement;
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
                        type: 'submit',
                      } as React.FormEvent<HTMLFormElement>;
                      handleSubmit(syntheticEvent);
                    } else {
                      // Fallback: call handleSubmit with minimal event
                      handleSubmit({ preventDefault: () => {} } as React.FormEvent);
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
