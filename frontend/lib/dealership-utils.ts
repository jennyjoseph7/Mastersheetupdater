import { 
  getDealershipDetails, 
  type DealershipDetailsResponse, 
  getWorkshopsForDealership,
  getShowroomsForDealership, //
  getBuybackCentersForDealership //
} from "./api";

/**
 * Check if dealership setup is completed
 * Setup is considered complete if essential fields are filled:
 * - dealership_type
 * - languages (at least one)
 * - supported_brands (at least one)
 * - pan_number or gstin or website (at least one verification field)
 * - AND at least one facility exists (Workshop OR Showroom OR Buyback Center)
 */
export async function isDealershipSetupComplete(): Promise<boolean> {
  try {
    const details: DealershipDetailsResponse = await getDealershipDetails();

    console.log("[Dealership Utils] Checking setup completion with details:", {
      dealership_type: details.dealership_type,
      languages: details.languages,
      supported_brands: details.supported_brands,
      pan_number: details.pan_number,
      gstin: details.gstin,
      website: details.website,
    });

    // Check if essential fields are present
    const hasDealershipType = 
      Boolean(details.dealership_type) && 
      String(details.dealership_type).trim() !== "";
    
    const hasLanguages =
      Array.isArray(details.languages) && 
      details.languages.length > 0 &&
      details.languages.some((lang: any) => lang && String(lang).trim() !== "");
    
    const hasSupportedBrands =
      Array.isArray(details.supported_brands) &&
      details.supported_brands.length > 0 &&
      details.supported_brands.some((brand: any) => brand && String(brand).trim() !== "");
    
    const panNumber = details.pan_number ? String(details.pan_number).trim() : "";
    const gstin = details.gstin ? String(details.gstin).trim() : "";
    const website = details.website ? String(details.website).trim() : "";
    
    const hasVerification = panNumber !== "" || gstin !== "" || website !== "";

    const dealershipId = details.dealership_id || details.dealership_slug || "";

    // 1. Check for Workshop
    let hasWorkshop = false;
    try {
      if (dealershipId) {
        const workshops = await getWorkshopsForDealership(dealershipId);
        hasWorkshop = Array.isArray(workshops) && workshops.length > 0;
      }
    } catch (e) {
      console.error("[Dealership Utils] Error checking workshops:", e);
    }

    // 2. Check for Showroom
    let hasShowroom = false;
    try {
      if (dealershipId) {
        const showrooms = await getShowroomsForDealership(dealershipId);
        hasShowroom = Array.isArray(showrooms) && showrooms.length > 0;
      }
    } catch (e) {
      console.error("[Dealership Utils] Error checking showrooms:", e);
    }

    // 3. Check for Buyback Center (New Requirement)
    let hasBuybackCenter = false;
    try {
      if (dealershipId) {
        const buybackCenters = await getBuybackCentersForDealership(dealershipId);
        hasBuybackCenter = Array.isArray(buybackCenters) && buybackCenters.length > 0;
      }
    } catch (e) {
      console.error("[Dealership Utils] Error checking buyback centers:", e);
    }

    // Combine checks: ANY facility is sufficient
    const hasAnyFacility = hasWorkshop || hasShowroom || hasBuybackCenter;

    const isComplete =
      hasDealershipType &&
      hasLanguages &&
      hasSupportedBrands &&
      hasVerification &&
      hasAnyFacility;

    console.log("[Dealership Utils] Setup completion check:", {
      hasDealershipType,
      hasLanguages,
      hasSupportedBrands,
      hasVerification,
      hasWorkshop,
      hasShowroom,
      hasBuybackCenter,
      hasAnyFacility,
      isComplete,
    });

    return isComplete;
  } catch (error) {
    console.error("[Dealership Utils] Error checking setup status:", error);
    return false;
  }
}

/**
 * Get dealership setup completion status with details
 */
export async function getDealershipSetupStatus(): Promise<{
  isComplete: boolean;
  missingFields: string[];
}> {
  const missingFields: string[] = [];

  try {
    const details: DealershipDetailsResponse = await getDealershipDetails();

    if (!details.dealership_type) {
      missingFields.push("Dealership Type");
    }
    if (!Array.isArray(details.languages) || details.languages.length === 0) {
      missingFields.push("Languages");
    }
    if (
      !Array.isArray(details.supported_brands) ||
      details.supported_brands.length === 0
    ) {
      missingFields.push("Supported Brands");
    }
    if (!details.pan_number && !details.gstin && !details.website) {
      missingFields.push("PAN Number, GSTIN, or Website");
    }

    const dealershipId = details.dealership_id || details.dealership_slug || "";
    let hasAnyFacility = false;

    // Check all three facilities
    if (dealershipId) {
      const [workshops, showrooms, buybackCenters] = await Promise.all([
        getWorkshopsForDealership(dealershipId).catch(() => []),
        getShowroomsForDealership(dealershipId).catch(() => []),
        getBuybackCentersForDealership(dealershipId).catch(() => [])
      ]);

      const hasWorkshop = Array.isArray(workshops) && workshops.length > 0;
      const hasShowroom = Array.isArray(showrooms) && showrooms.length > 0;
      const hasBuybackCenter = Array.isArray(buybackCenters) && buybackCenters.length > 0;

      hasAnyFacility = hasWorkshop || hasShowroom || hasBuybackCenter;
    }

    if (!hasAnyFacility) {
      missingFields.push("At least one facility (Workshop, Showroom, or Buyback Center)");
    }

    return {
      isComplete: missingFields.length === 0,
      missingFields,
    };
  } catch (error) {
    console.error("[Dealership Utils] Error getting setup status:", error);
    return {
      isComplete: false,
      missingFields: ["Unable to verify setup status"],
    };
  }
}