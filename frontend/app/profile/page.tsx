"use client";
import {
  Store,
  User,
  Upload,
  Loader2,
  AlertCircle,
  Building2,
  Globe,
  MapPin,
  CreditCard,
  FileText,
  Tag,
  Edit,
  Save,
  X,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useEffect, useState } from "react";
import {
  getDealershipDetails,
  type DealershipDetailsResponse,
  type DealershipUpdateDetailsRequest,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getCookie } from "@/lib/cookies";

export default function ProfilePage() {
  const [dealershipData, setDealershipData] =
    useState<DealershipDetailsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    dealership_type: "",
    dealership_legal_name: "",
    languages: [] as string[],
    supported_brands: [] as string[],
    aliases: [] as string[],
    pan_number: "",
    gstin: "",
    website: "",
  });

  useEffect(() => {
    const fetchDealership = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await getDealershipDetails();
        setDealershipData(data);
        // Initialize form data
        setFormData({
          dealership_type: data.dealership_type || "",
          dealership_legal_name: data.dealership_legal_name || "",
          languages: data.languages || [],
          supported_brands: data.supported_brands || [],
          aliases: data.aliases || [],
          pan_number: data.pan_number || "",
          gstin: data.gstin || "",
          website: data.website || "",
        });
        console.log("[Profile Page] Dealership data loaded:", data);
      } catch (err) {
        console.error("[Profile Page] Failed to fetch dealership:", err);
        setError(
          err instanceof Error ? err.message : "Failed to load dealership data"
        );
      } finally {
        setIsLoading(false);
      }
    };

    fetchDealership();
  }, []);

  const handleSave = async () => {
    if (!dealershipData?.dealership_id) {
      setError("Dealership ID not found");
      return;
    }

    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updateRequest: DealershipUpdateDetailsRequest = {
        args: [dealershipData.dealership_id],
        kwargs: {
          dealership_type: formData.dealership_type,
          dealership_legal_name: formData.dealership_legal_name,
          languages: formData.languages,
          supported_brands: formData.supported_brands,
          aliases: formData.aliases,
          pan_number: formData.pan_number,
          gstin: formData.gstin,
          website: formData.website,
        },
        _timeout: 600,
      };

      // Call API directly from page.tsx
      // Use hardcoded token and session_id for dealership update API
      const backendUrl = `https://autobot-webapp-dev.gryd.in/gryd/api/autocrm-core/dealership_update_details`;
      const token = "53014452-7df1-351c-9b79-af13d3d6b92f";
      const sessionId = "94b970d4-5c2b-3762-bf65-272901d0ad53";

      console.log("[Profile Page] Calling backend:", backendUrl);
      console.log(
        "[Profile Page] Request body:",
        JSON.stringify(updateRequest, null, 2)
      );

      // Headers must match the curl command exactly
      const headers = {
        "Content-Type": "application/json",
        "X-GRYD-ENTERPRISE-ID": "autocrm",
        "X-GRYD-TOKEN": token,
        "X-GRYD-SESSION-ID": sessionId,
        Accept: "application/json",
        "X-GRYD-ROLE": "agent",
      };

      console.log(
        "[Profile Page] Request headers:",
        JSON.stringify(headers, null, 2)
      );

      const res = await fetch(backendUrl, {
        method: "POST",
        headers: headers,
        body: JSON.stringify(updateRequest),
        cache: "no-store",
        mode: "cors",
        credentials: "omit",
      });

      console.log(`[Profile Page] Response status: ${res.status}`);

      if (!res.ok) {
        const errorText = await res.text();
        console.error(`[Profile Page] Error response:`, errorText);
        let errorMessage = `Failed to update dealership details (${res.status})`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage =
            errorData?.error || errorData?.message || errorText || errorMessage;
        } catch {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const updatedData = await res.json();
      console.log("[Profile Page] Update successful:", updatedData);
      setDealershipData(updatedData);
      setIsEditing(false);
      setSuccessMessage("Dealership details updated successfully!");

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error("[Profile Page] Failed to update dealership:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to update dealership details"
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (dealershipData) {
      setFormData({
        dealership_type: dealershipData.dealership_type || "",
        dealership_legal_name: dealershipData.dealership_legal_name || "",
        languages: dealershipData.languages || [],
        supported_brands: dealershipData.supported_brands || [],
        aliases: dealershipData.aliases || [],
        pan_number: dealershipData.pan_number || "",
        gstin: dealershipData.gstin || "",
        website: dealershipData.website || "",
      });
    }
    setIsEditing(false);
    setError(null);
  };
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="text-muted-foreground">
            Loading dealership information...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background">
        <div className="space-y-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Profile Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your personal and business information
          </p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800 dark:text-green-200">
              {successMessage}
            </AlertDescription>
          </Alert>
        )}

        {/* Dealership Information Display */}
        {dealershipData && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5" />
                    Dealership Information
                  </CardTitle>
                  <CardDescription>
                    Your dealership details from the system
                  </CardDescription>
                </div>
                {!isEditing && (
                  <Button
                    onClick={() => setIsEditing(true)}
                    variant="outline"
                    className="gap-2"
                  >
                    <Edit className="h-4 w-4" />
                    Update
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {isEditing ? (
                <form className="space-y-6">
                  {/* Error Alert */}
                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Dealership Type */}
                    <div className="space-y-2">
                      <Label htmlFor="dealership_type">
                        Dealership Type{" "}
                        <span className="text-destructive">*</span>
                      </Label>
                      <Select
                        value={formData.dealership_type}
                        onValueChange={(value) =>
                          setFormData({ ...formData, dealership_type: value })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Single Brand">
                            Single Brand
                          </SelectItem>
                          <SelectItem value="Multi Brand">
                            Multi Brand
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Legal Name */}
                    <div className="space-y-2">
                      <Label htmlFor="dealership_legal_name">
                        Legal Name <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        id="dealership_legal_name"
                        value={formData.dealership_legal_name}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            dealership_legal_name: e.target.value,
                          })
                        }
                        placeholder="Enter legal name"
                      />
                    </div>
                  </div>

                  {/* Website */}
                  <div className="space-y-2">
                    <Label htmlFor="website">Website</Label>
                    <Input
                      id="website"
                      type="url"
                      value={formData.website}
                      onChange={(e) =>
                        setFormData({ ...formData, website: e.target.value })
                      }
                      placeholder="https://example.com"
                    />
                  </div>

                  {/* PAN Number and GSTIN */}
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="pan_number">PAN Number</Label>
                      <Input
                        id="pan_number"
                        value={formData.pan_number}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            pan_number: e.target.value,
                          })
                        }
                        placeholder="ABCDE1234F"
                        maxLength={10}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="gstin">GSTIN</Label>
                      <Input
                        id="gstin"
                        value={formData.gstin}
                        onChange={(e) =>
                          setFormData({ ...formData, gstin: e.target.value })
                        }
                        placeholder="29AAXCS6043H1ZO"
                        maxLength={15}
                      />
                    </div>
                  </div>

                  {/* Languages */}
                  <div className="space-y-2">
                    <Label>Languages</Label>
                    <div className="flex flex-wrap gap-2">
                      {[
                        "english",
                        "hindi",
                        "kannada",
                        "gujarati",
                        "tamil",
                        "telugu",
                      ].map((lang) => (
                        <Badge
                          key={lang}
                          variant={
                            formData.languages.includes(lang)
                              ? "default"
                              : "outline"
                          }
                          className="cursor-pointer"
                          onClick={() => {
                            if (formData.languages.includes(lang)) {
                              setFormData({
                                ...formData,
                                languages: formData.languages.filter(
                                  (l) => l !== lang
                                ),
                              });
                            } else {
                              setFormData({
                                ...formData,
                                languages: [...formData.languages, lang],
                              });
                            }
                          }}
                        >
                          {lang}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Supported Brands */}
                  <div className="space-y-2">
                    <Label>Supported Brands</Label>
                    <div className="flex flex-wrap gap-2">
                      {[
                        "hyundai",
                        "maruti",
                        "tata",
                        "mahindra",
                        "honda",
                        "toyota",
                      ].map((brand) => (
                        <Badge
                          key={brand}
                          variant={
                            formData.supported_brands.includes(brand)
                              ? "default"
                              : "outline"
                          }
                          className="cursor-pointer"
                          onClick={() => {
                            if (formData.supported_brands.includes(brand)) {
                              setFormData({
                                ...formData,
                                supported_brands:
                                  formData.supported_brands.filter(
                                    (b) => b !== brand
                                  ),
                              });
                            } else {
                              setFormData({
                                ...formData,
                                supported_brands: [
                                  ...formData.supported_brands,
                                  brand,
                                ],
                              });
                            }
                          }}
                        >
                          {brand}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Aliases */}
                  <div className="space-y-2">
                    <Label htmlFor="aliases">Aliases (comma-separated)</Label>
                    <Input
                      id="aliases"
                      value={formData.aliases.join(", ")}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          aliases: e.target.value
                            .split(",")
                            .map((a) => a.trim())
                            .filter((a) => a),
                        })
                      }
                      placeholder="Alias 1, Alias 2, Alias 3"
                    />
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-end gap-3 pt-4 border-t">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleCancel}
                      disabled={isSaving}
                    >
                      <X className="mr-2 h-4 w-4" />
                      Cancel
                    </Button>
                    <Button
                      type="button"
                      onClick={handleSave}
                      disabled={isSaving}
                      className="gap-2"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="mr-2 h-4 w-4" />
                          Save Changes
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              ) : (
                <>
                  <div className="grid md:grid-cols-2 gap-6">
                    {/* Basic Information */}
                    <div className="space-y-4">
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Dealership Name
                        </Label>
                        <p className="text-lg font-medium mt-1">
                          {dealershipData.dealer_name || "N/A"}
                        </p>
                      </div>
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Legal Name
                        </Label>
                        <p className="text-lg font-medium mt-1">
                          {dealershipData.dealership_legal_name || "N/A"}
                        </p>
                      </div>
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Dealership ID
                        </Label>
                        <p className="text-sm font-mono text-muted-foreground mt-1">
                          {dealershipData.dealership_id || "N/A"}
                        </p>
                      </div>
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Status
                        </Label>
                        <div className="mt-1">
                          <Badge
                            variant={
                              dealershipData.dealer_status === "lead"
                                ? "secondary"
                                : "default"
                            }
                          >
                            {dealershipData.dealer_status || "N/A"}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {/* Contact & Location */}
                    <div className="space-y-4">
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                          <Globe className="h-4 w-4" />
                          Website
                        </Label>
                        {dealershipData.website ? (
                          <a
                            href={dealershipData.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline mt-1 block"
                          >
                            {dealershipData.website}
                          </a>
                        ) : (
                          <p className="text-muted-foreground mt-1">N/A</p>
                        )}
                      </div>
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                          <MapPin className="h-4 w-4" />
                          Region
                        </Label>
                        <p className="text-lg font-medium mt-1">
                          {dealershipData.region_name ||
                            dealershipData.region_id ||
                            "N/A"}
                        </p>
                      </div>
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                          <CreditCard className="h-4 w-4" />
                          Credits Balance
                        </Label>
                        <p className="text-lg font-medium mt-1">
                          {dealershipData.credits_balance ?? 0}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Additional Details */}
                  <div className="mt-6 pt-6 border-t space-y-4">
                    <div className="grid md:grid-cols-2 gap-6">
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Dealership Type
                        </Label>
                        <p className="text-lg font-medium mt-1">
                          {dealershipData.dealership_type || "N/A"}
                        </p>
                      </div>
                      <div>
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Vehicle Category
                        </Label>
                        <p className="text-lg font-medium mt-1">
                          {dealershipData.vehicle_category || "N/A"}
                        </p>
                      </div>
                    </div>

                    {dealershipData.supported_brands &&
                      dealershipData.supported_brands.length > 0 && (
                        <div>
                          <Label className="text-sm font-semibold text-muted-foreground">
                            Supported Brands
                          </Label>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {dealershipData.supported_brands.map(
                              (brand: string, index: number) => (
                                <Badge key={index} variant="outline">
                                  {brand}
                                </Badge>
                              )
                            )}
                          </div>
                        </div>
                      )}

                    {dealershipData.languages &&
                      dealershipData.languages.length > 0 && (
                        <div>
                          <Label className="text-sm font-semibold text-muted-foreground">
                            Languages
                          </Label>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {dealershipData.languages.map(
                              (lang: string, index: number) => (
                                <Badge key={index} variant="secondary">
                                  {lang}
                                </Badge>
                              )
                            )}
                          </div>
                        </div>
                      )}

                    {dealershipData.aliases &&
                      dealershipData.aliases.length > 0 && (
                        <div>
                          <Label className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                            <Tag className="h-4 w-4" />
                            Aliases
                          </Label>
                          <div className="flex flex-wrap gap-2 mt-2">
                            {dealershipData.aliases.map(
                              (alias: string, index: number) => (
                                <Badge key={index} variant="outline">
                                  {alias}
                                </Badge>
                              )
                            )}
                          </div>
                        </div>
                      )}

                    <div className="grid md:grid-cols-2 gap-6">
                      {dealershipData.pan_number && (
                        <div>
                          <Label className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            PAN Number
                          </Label>
                          <p className="text-lg font-medium mt-1 font-mono">
                            {dealershipData.pan_number}
                          </p>
                        </div>
                      )}
                      {dealershipData.gstin && (
                        <div>
                          <Label className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            GSTIN
                          </Label>
                          <p className="text-lg font-medium mt-1 font-mono">
                            {dealershipData.gstin}
                          </p>
                        </div>
                      )}
                    </div>


                    {dealershipData.auth && (
                      <div className="pt-4 border-t">
                        <Label className="text-sm font-semibold text-muted-foreground">
                          Authentication Info
                        </Label>
                        <div className="mt-2 space-y-1 text-sm">
                          <p>
                            <span className="font-medium">Role:</span>{" "}
                            {dealershipData.auth.role}
                          </p>
                          <p>
                            <span className="font-medium">Dealership ID:</span>{" "}
                            {dealershipData.dealership_id || "N/A"}
                          </p>
                          <p>
                            <span className="font-medium">Enterprise ID:</span>{" "}
                            {dealershipData.auth.enterprise_id}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        )}

        <Tabs defaultValue="basics" className="space-y-6">
          <TabsList className="bg-muted/50">
            <TabsTrigger value="basics" className="gap-2">
              <Store className="h-4 w-4" />
              Dealership Basics
            </TabsTrigger>
            <TabsTrigger value="identity" className="gap-2">
              <User className="h-4 w-4" />
              Dealership Identity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="basics" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Dealership Basics</CardTitle>
                <CardDescription>
                  Let's start with the essential details about your dealership
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full-name">
                      Full Name <span className="text-destructive">*</span>
                    </Label>
                    <Input id="full-name" placeholder="User" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="dealership-name">
                      Dealership Name{" "}
                      <span className="text-destructive">*</span>
                    </Label>
                    <Input id="dealership-name" placeholder="user Auto Sales" />
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">
                      Email <span className="text-destructive">*</span>
                    </Label>
                    <Input id="email" type="email" placeholder="user@g" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="contact-number">
                      Contact Number <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="contact-number"
                      type="tel"
                      placeholder="Business contact number"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="address">
                    Address <span className="text-destructive">*</span>
                  </Label>
                  <Textarea
                    id="address"
                    placeholder="Complete business address"
                    className="min-h-[80px]"
                  />
                </div>

                <div className="space-y-2">
                  <Label>
                    Upload Logo <span className="text-destructive">*</span>
                  </Label>
                  <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                    <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      Drop your logo here or click to browse
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      No file chosen
                    </p>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button size="lg" className="bg-primary hover:bg-primary/90">
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="identity" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Dealership Identity</CardTitle>
                <CardDescription>
                  Tell us what makes your dealership unique
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="usp-tagline">
                    USP/Tagline <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="usp-tagline"
                    placeholder="Tell customers in one line why they should choose your dealership"
                  />
                  <p className="text-xs text-muted-foreground">
                    e.g., "Trusted for quality cars and excellent service"
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="business-timings">Business Timings</Label>
                  <Input
                    id="business-timings"
                    placeholder="e.g., Mon-Sat: 9:00 AM - 7:00 PM, Sun: 10:00 AM - 6:00 PM"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Upload Documents (Optional)</Label>
                  <p className="text-sm text-muted-foreground">
                    Brochures, certifications, product PDFs, etc.
                  </p>
                  <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-primary/50 transition-colors cursor-pointer">
                    <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      Drop documents here or click to browse
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      No files chosen
                    </p>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button size="lg" className="bg-primary hover:bg-primary/90">
                    Save Changes
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
