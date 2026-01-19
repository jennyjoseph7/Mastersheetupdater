import { getDealershipDetails, type DealershipDetailsResponse, getWorkshopsForDealership } from "./api";

/**
 * Check if dealership setup is completed
 * Setup is considered complete if essential fields are filled:
 * - dealership_type
 * - languages (at least one)
 * - supported_brands (at least one)
 * - pan_number or gstin or website (at least one verification field)
 * - at least one workshop exists
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
    // Dealership type must exist and not be empty
    const hasDealershipType = 
      Boolean(details.dealership_type) && 
      String(details.dealership_type).trim() !== "";
    
    // Languages must be an array with at least one non-empty item
    const hasLanguages =
      Array.isArray(details.languages) && 
      details.languages.length > 0 &&
      details.languages.some((lang: any) => lang && String(lang).trim() !== "");
    
    // Supported brands must be an array with at least one non-empty item
    const hasSupportedBrands =
      Array.isArray(details.supported_brands) &&
      details.supported_brands.length > 0 &&
      details.supported_brands.some((brand: any) => brand && String(brand).trim() !== "");
    
    // Accept website, pan_number, or gstin as verification (must be non-empty)
    const panNumber = details.pan_number ? String(details.pan_number).trim() : "";
    const gstin = details.gstin ? String(details.gstin).trim() : "";
    const website = details.website ? String(details.website).trim() : "";
    
    const hasVerification = panNumber !== "" || gstin !== "" || website !== "";

    // Check if at least one workshop exists
    let hasWorkshop = false;
    try {
      const dealershipId = details.dealership_id || details.dealership_slug || "";
      if (dealershipId) {
        const workshops = await getWorkshopsForDealership(dealershipId);
        hasWorkshop = Array.isArray(workshops) && workshops.length > 0;
        console.log("[Dealership Utils] Workshops found:", workshops.length);
      }
    } catch (workshopError) {
      console.error("[Dealership Utils] Error checking workshops:", workshopError);
      // If we can't check workshops, don't fail the entire check
      // but log it for debugging
    }

    const isComplete =
      hasDealershipType &&
      hasLanguages &&
      hasSupportedBrands &&
      hasVerification &&
      hasWorkshop;

    console.log("[Dealership Utils] Setup completion check:", {
      hasDealershipType,
      hasLanguages,
      hasSupportedBrands,
      hasVerification,
      hasWorkshop,
      isComplete,
    });

    return isComplete;
  } catch (error) {
    console.error("[Dealership Utils] Error checking setup status:", error);
    // If we can't fetch details, assume not complete
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

    // Check for workshops
    try {
      const dealershipId = details.dealership_id || details.dealership_slug || "";
      if (dealershipId) {
        const workshops = await getWorkshopsForDealership(dealershipId);
        if (!Array.isArray(workshops) || workshops.length === 0) {
          missingFields.push("Workshop Details");
        }
      } else {
        missingFields.push("Workshop Details");
      }
    } catch (workshopError) {
      console.error("[Dealership Utils] Error checking workshops:", workshopError);
      missingFields.push("Workshop Details");
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
