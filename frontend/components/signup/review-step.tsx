"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Pencil, CheckCircle2 } from "lucide-react";
import type { DealershipData } from "@/types/dealership";
import { dealershipSignup, type DealershipSignupRequest } from "@/lib/api";
import React from "react";

interface ReviewStepProps {
  data: DealershipData;
  onEdit: (step: number) => void;
}

export function ReviewStep({ data, onEdit }: ReviewStepProps) {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // Map DealershipData to API request format
      const aliases: string[] = [];
      if (data.dealer_name) aliases.push(data.dealer_name);
      if (
        data.dealership_legal_name &&
        data.dealership_legal_name !== data.dealer_name
      ) {
        aliases.push(data.dealership_legal_name);
      }

      // Extract PAN number from pan_card_link if it's a number format
      // Otherwise use the link as-is or extract number
      let panNumber = data.pan_card_link || "";
      // If pan_card_link looks like a PAN number format (10 alphanumeric), use it directly
      if (
        panNumber &&
        panNumber.length === 10 &&
        /^[A-Z0-9]{10}$/.test(panNumber.toUpperCase())
      ) {
        // Already in correct format
      } else if (panNumber) {
        // Try to extract PAN from URL or other format
        const panMatch = panNumber.match(/[A-Z]{5}[0-9]{4}[A-Z]{1}/i);
        if (panMatch) {
          panNumber = panMatch[0].toUpperCase();
        }
      }

      // Convert brand names to API format (slug format)
      // Map common brand names to API slugs
      const brandSlugMap: Record<string, string> = {
        "Maruti Suzuki": "maruti-suzuki-arena",
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

      const brandSlugs = data.supported_brands
        .map(
          (brand) =>
            brandSlugMap[brand] || brand.toLowerCase().replace(/\s+/g, "-")
        )
        .filter(Boolean);

      // Prepare API request
      const signupRequest: DealershipSignupRequest = {
        args: [
          data.dealer_name || "",
          data.region_id || "south-india", // Default to south-india if not provided
          "Passenger vehicles", // Default vehicle type
          data.dealership_type === "Multi Brand"
            ? "Multi Brand"
            : "Single Brand",
          data.languages.length > 0 ? data.languages : ["english"], // Default to english if empty
          brandSlugs.length > 0 ? brandSlugs : [], // Use mapped brand slugs
          data.primary_contact_name || "",
          data.primary_contact_email || "",
          data.primary_contact_phone || "",
        ],
        kwargs: {
          ...(aliases.length > 0 && { aliases }),
          ...(panNumber && { pan_number: panNumber }),
          ...(data.gstin && { gstin: data.gstin }),
          ...(data.website && { website: data.website }),
        },
        _timeout: 600,
      };

      // Call the dealership signup API
      await dealershipSignup(signupRequest);

      // Redirect to success page or dashboard
      window.location.href = "/onboarding/success";
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "An error occurred"
      );
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
        <div>
          <p className="font-medium text-green-900">Almost there!</p>
          <p className="text-sm text-green-800 mt-1">
            Review your information below and submit to complete onboarding.
          </p>
        </div>
      </div>

      {/* Basic Information */}
      <div className="border rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Basic Information</h3>
          <Button variant="ghost" size="sm" onClick={() => onEdit(1)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Dealership Name</p>
            <p className="font-medium">{data.dealer_name || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Legal Name</p>
            <p className="font-medium">{data.dealership_legal_name || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Type</p>
            <p className="font-medium">{data.dealership_type}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Brands</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {data.supported_brands.map((brand) => (
                <Badge key={brand} variant="secondary">
                  {brand}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Legal Documents */}
      <div className="border rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Legal Documents</h3>
          <Button variant="ghost" size="sm" onClick={() => onEdit(2)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">GSTIN</p>
            <p className="font-medium font-mono">{data.gstin || "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">GST Certificate</p>
            <p className="font-medium">
              {data.gst_certificate ? "✓ Uploaded" : "—"}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">PAN Card</p>
            <p className="font-medium">
              {data.pan_card_link ? "✓ Provided" : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Contact Information */}
      <div className="border rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Contact Information</h3>
          <Button variant="ghost" size="sm" onClick={() => onEdit(3)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Primary Contact</p>
            <p className="font-medium">{data.primary_contact_name || "—"}</p>
            <p className="text-xs text-muted-foreground">
              {data.primary_contact_email}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">Billing Address</p>
            <p className="font-medium">{data.billing_address || "—"}</p>
          </div>
        </div>
      </div>

      {/* Operational Details */}
      <div className="border rounded-lg p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Operational Details</h3>
          <Button variant="ghost" size="sm" onClick={() => onEdit(4)}>
            <Pencil className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Channels</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {data.channels.map((channel) => (
                <Badge key={channel} variant="outline">
                  {channel}
                </Badge>
              ))}
            </div>
          </div>
          <div>
            <p className="text-muted-foreground">Languages</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {data.languages.map((lang) => (
                <Badge key={lang} variant="outline" className="capitalize">
                  {lang}
                </Badge>
              ))}
            </div>
          </div>
          <div>
            <p className="text-muted-foreground">Total Centers</p>
            <p className="font-medium">
              {data.showroom_center_count +
                data.workshop_center_count +
                data.buyback_center_count}
            </p>
          </div>
        </div>
      </div>

      {submitError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-800">
          {submitError}
        </div>
      )}

      <div className="flex gap-3 pt-4">
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="flex-1"
        >
          {isSubmitting ? "Submitting..." : "Submit & Complete Onboarding"}
        </Button>
      </div>
    </div>
  );
}
