"use client";

import type React from "react";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
} from "lucide-react";
import {
  dealershipUpdateDetails,
  type DealershipUpdateDetailsRequest,
  ApiError,
} from "@/lib/api";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";

const urlRegex =
  /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

export default function DealershipUpdateDetails() {
  const router = useRouter();
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [websiteError, setWebsiteError] = useState("");
  const [panError, setPanError] = useState("");
  const [gstinError, setGstinError] = useState("");

  const [dealershipDetails, setDealershipDetails] = useState({
    dealershipType: "Multi Brand" as "Single Brand" | "Multi Brand",
    languages: [] as string[],
    brands: [] as string[],
    aliases: [] as string[],
    panNumber: "",
    gstin: "",
    website: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate business verification - all fields are mandatory
    if (!dealershipDetails.website || dealershipDetails.website.trim() === "") {
      setWebsiteError("Website URL is required");
      setError("Please enter your website URL");
      return;
    }
    if (!urlRegex.test(dealershipDetails.website)) {
      setWebsiteError("Please enter a valid website URL");
      setError("Please enter a valid website URL");
      return;
    }

    if (
      !dealershipDetails.panNumber ||
      dealershipDetails.panNumber.trim() === ""
    ) {
      setPanError("PAN Number is required");
      setError("Please enter your PAN Number");
      return;
    }
    if (!panRegex.test(dealershipDetails.panNumber)) {
      setPanError("Please enter a valid PAN number (Format: ABCDE1234F)");
      setError("Please enter a valid PAN number");
      return;
    }

    // GSTIN is optional, but if provided, validate format
    if (
      dealershipDetails.gstin &&
      dealershipDetails.gstin.trim() !== "" &&
      !gstinRegex.test(dealershipDetails.gstin)
    ) {
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

      // Build kwargs object
      const kwargs: Record<string, any> = {
        aliases:
          dealershipDetails.aliases.length > 0 ? dealershipDetails.aliases : [],
        gstin: dealershipDetails.gstin || "",
      };

      if (dealershipDetails.dealershipType) {
        kwargs.dealership_type = dealershipDetails.dealershipType;
      }

      if (dealershipDetails.languages.length > 0) {
        kwargs.languages = dealershipDetails.languages;
      }

      if (brandSlugs.length > 0) {
        kwargs.supported_brands = brandSlugs;
      }

      // Include all verification fields
      kwargs.website = dealershipDetails.website;
      kwargs.pan_number = dealershipDetails.panNumber;
      kwargs.gstin = dealershipDetails.gstin;

      const updateRequest: DealershipUpdateDetailsRequest = {
        args: [dealershipId],
        kwargs,
        _timeout: 600,
      };

      // Call the dealership update details API
      await dealershipUpdateDetails(updateRequest);

      // On success, redirect to success page or dashboard
      router.push("/dealership/update-details/success");
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
              Complete Your Profile
            </h1>
            <p className="text-lg text-muted-foreground">
              Add additional details about your dealership
            </p>
          </div>

          {/* Progress Indicator */}
          <Card className="mb-6 border-primary/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">
                  Onboarding Progress
                </span>
                <span className="text-sm text-muted-foreground">
                  Step 2 of 2
                </span>
              </div>
              <Progress value={100} className="h-2" />
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
                      <RadioGroupItem
                        value="Single Brand"
                        id="single-brand"
                      />
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
                            (brand) =>
                              !dealershipDetails.brands.includes(brand)
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
                              languages: [
                                ...dealershipDetails.languages,
                                lang,
                              ],
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

                {/* Aliases */}
                <div className="space-y-2">
                  <Label htmlFor="alias">Aliases (Optional)</Label>
                  <div className="flex gap-2">
                    <Input
                      id="alias"
                      placeholder="Enter alias name"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          const input = e.currentTarget;
                          const value = input.value.trim();
                          if (
                            value &&
                            !dealershipDetails.aliases.includes(value)
                          ) {
                            setDealershipDetails({
                              ...dealershipDetails,
                              aliases: [...dealershipDetails.aliases, value],
                            });
                            input.value = "";
                          }
                        }
                      }}
                    />
                  </div>
                  {dealershipDetails.aliases.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {dealershipDetails.aliases.map((alias) => (
                        <Badge key={alias} variant="outline">
                          {alias}
                          <button
                            type="button"
                            onClick={() => {
                              setDealershipDetails({
                                ...dealershipDetails,
                                aliases: dealershipDetails.aliases.filter(
                                  (a) => a !== alias
                                ),
                              });
                            }}
                            className="ml-2"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                {/* Business Verification */}
                <div className="space-y-4">
                  <Label className="text-base font-semibold">
                    Business Verification{" "}
                    <span className="text-destructive">*</span>
                  </Label>

                  {/* Website */}
                  <div className="space-y-2">
                    <Label htmlFor="website">
                      Website URL <span className="text-destructive">*</span>
                    </Label>
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
                          if (!value || value.trim() === "") {
                            setWebsiteError("Website URL is required");
                          } else if (!urlRegex.test(value)) {
                            setWebsiteError(
                              "Please enter a valid website URL"
                            );
                          } else {
                            setWebsiteError("");
                          }
                        }}
                        required
                        className="pl-10"
                      />
                    </div>
                    {websiteError && (
                      <p className="text-sm text-destructive">
                        {websiteError}
                      </p>
                    )}
                  </div>

                  {/* PAN and GSTIN */}
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="panNumber">
                        PAN Number <span className="text-destructive">*</span>
                      </Label>
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
                          if (!value || value.trim() === "") {
                            setPanError("PAN Number is required");
                          } else if (!panRegex.test(value)) {
                            setPanError(
                              "Please enter a valid PAN number (Format: ABCDE1234F)"
                            );
                          } else {
                            setPanError("");
                          }
                        }}
                        maxLength={10}
                        className="font-mono uppercase"
                        required
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
                        <p className="text-sm text-destructive">
                          {gstinError}
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-3 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    size="lg"
                    onClick={() => router.push("/")}
                  >
                    Skip for Now
                  </Button>
                  <Button type="submit" size="lg" disabled={isLoading}>
                    {isLoading ? (
                      "Saving..."
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Save & Continue
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  );
}

