"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReCAPTCHA from "react-google-recaptcha";
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
import {
  ArrowLeft,
  Mail,
  Lock,
  Building2,
  Phone,
  User,
  CheckCircle2,
  Sparkles,
  CreditCard,
  FileText,
  ArrowRight,
  Globe,
  MapPin,
  Car,
  X,
  AlertCircle,
  Copy,
  Check,
  Shield,
  Tag,
  Calendar,
  Store,
  Languages,
  Award,
} from "lucide-react";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  dealershipSignup,
  dealershipUpdateDetails,
  generateOTP,
  type DealershipSignupRequest,
  type DealershipUpdateDetailsRequest,
  ApiError,
} from "@/lib/api";

export default function DealerSignup() {
  const router = useRouter();
  const [phase, setPhase] = useState<
    "registration" | "verification" | "success"
  >("registration");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [errorDetails, setErrorDetails] = useState<string | null>(null);
  const [signupResponse, setSignupResponse] = useState<any>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [recaptchaToken, setRecaptchaToken] = useState<string | null>(null);
  const recaptchaRef = useRef<ReCAPTCHA>(null);
  const [phoneOtpToken, setPhoneOtpToken] = useState<string | null>(null);
  const [phoneOtp, setPhoneOtp] = useState("");
  const [emailOtpToken, setEmailOtpToken] = useState<string | null>(null);
  const [emailOtp, setEmailOtp] = useState("");
  const [isGeneratingOtp, setIsGeneratingOtp] = useState(false);
  const [isGeneratingEmailOtp, setIsGeneratingEmailOtp] = useState(false);
  const [otpError, setOtpError] = useState("");

  // Get reCAPTCHA site key from environment
  const recaptchaSiteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || "";
  const isRecaptchaEnabled = Boolean(recaptchaSiteKey);

  // Registration data
  const [registrationData, setRegistrationData] = useState({
    dealershipName: "",
    legalName: "",
    fullName: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    region: "south-india",
    vehicleType: "Passenger vehicles",
    dealershipType: "Multi Brand" as "Single Brand" | "Multi Brand",
    languages: [] as string[],
    brands: [] as string[],
    website: "",
    panNumber: "",
    gstin: "",
  });

  // Verification data
  const [verificationData, setVerificationData] = useState({
    gstin: "",
    panCard: "",
    address: "",
    city: "",
    state: "",
  });

  const handleGenerateOTP = async () => {
    if (!registrationData.phone) {
      setOtpError("Please enter a phone number first");
      return;
    }
    if (!registrationData.email) {
      setOtpError("Please enter an email address first");
      return;
    }

    setIsGeneratingOtp(true);
    setOtpError("");
    setPhoneOtpToken(null);
    setEmailOtpToken(null);

    try {
      // Generate phone OTP
      const phoneResponse = await generateOTP(
        registrationData.phone,
        "whatsapp"
      );
      if (!phoneResponse.token) {
        setOtpError("Failed to generate phone OTP. Please try again.");
        return;
      }
      setPhoneOtpToken(phoneResponse.token);

      // Generate email OTP automatically
      try {
        const emailResponse = await generateOTP(
          registrationData.email,
          "email"
        );
        if (emailResponse.token) {
          setEmailOtpToken(emailResponse.token);
        }
      } catch (emailErr) {
        // If email OTP fails, we'll use phone OTP token as fallback
        console.error("Failed to generate email OTP:", emailErr);
        setEmailOtpToken(phoneResponse.token); // Fallback to phone token
      }

      setOtpError("");
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : "Failed to generate OTP. Please try again.";
      setOtpError(errorMessage);
    } finally {
      setIsGeneratingOtp(false);
    }
  };

  const handleRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate passwords match
    if (registrationData.password !== registrationData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Validate password requirements
    if (registrationData.password.length < 8) {
      setError("Password must be at least 8 characters long");
      return;
    }
    if (!/[a-zA-Z]/.test(registrationData.password)) {
      setError("Password must contain at least one letter");
      return;
    }

    // Validate required fields
    if (!registrationData.dealershipName) {
      setError("Dealership name is required");
      return;
    }
    if (!registrationData.fullName) {
      setError("Admin name is required");
      return;
    }
    if (!registrationData.email) {
      setError("Email is required");
      return;
    }
    if (!registrationData.phone) {
      setError("Phone is required");
      return;
    }
    if (!phoneOtpToken) {
      setError("Please generate OTP for your phone number");
      return;
    }
    if (!phoneOtp) {
      setError("Please enter the OTP sent to your phone number");
      return;
    }
    if (registrationData.brands.length === 0) {
      setError("Please select at least one brand");
      return;
    }
    if (registrationData.languages.length === 0) {
      setError("Please select at least one language");
      return;
    }

    // Validate reCAPTCHA if enabled
    if (isRecaptchaEnabled && !recaptchaToken) {
      setError("Please complete the reCAPTCHA verification");
      return;
    }

    setIsLoading(true);

    try {
      // Prepare aliases
      const aliases: string[] = [];
      if (registrationData.dealershipName)
        aliases.push(registrationData.dealershipName);
      if (
        registrationData.legalName &&
        registrationData.legalName !== registrationData.dealershipName
      ) {
        aliases.push(registrationData.legalName);
      }

      // Map brand names to API format (slug format)
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

      const brandSlugs = registrationData.brands
        .map(
          (brand) =>
            brandSlugMap[brand] || brand.toLowerCase().replace(/\s+/g, "-")
        )
        .filter(Boolean);

      // Prepare API request
      const signupRequest: DealershipSignupRequest = {
        args: [registrationData.dealershipName, registrationData.region],
        kwargs: {
          primary_contact_name: registrationData.fullName,
          primary_contact_email: registrationData.email,
          primary_contact_phone: registrationData.phone,
          password: registrationData.password,
          confirm_password: registrationData.confirmPassword,
          email_otp: emailOtp || phoneOtp, // Use email OTP if available, fallback to phone OTP
          email_otp_token: emailOtpToken || phoneOtpToken, // Use email OTP token if available
          phone_number_otp: phoneOtp,
          phone_number_otp_token: phoneOtpToken,
          ...(registrationData.vehicleType && {
            vehicle_type: registrationData.vehicleType,
          }),
          ...(registrationData.dealershipType && {
            dealership_type: registrationData.dealershipType,
          }),
          ...(registrationData.languages.length > 0 && {
            languages: registrationData.languages,
          }),
          ...(brandSlugs.length > 0 && {
            brands: brandSlugs,
          }),
          ...(aliases.length > 0 && { aliases }),
          ...(registrationData.website && {
            website: registrationData.website,
          }),
          ...(registrationData.panNumber && {
            pan_number: registrationData.panNumber,
          }),
          ...(registrationData.gstin && {
            gstin: registrationData.gstin,
          }),
        },
        _timeout: 600,
      };

      // Call the dealership signup API
      const response = await dealershipSignup(signupRequest);

      // Store the response data
      setSignupResponse(response);

      // Update dealership details after successful signup
      // Use dealership_id from response if available, otherwise construct from name and region
      const dealershipId =
        response.dealership_id ||
        response.dealership_slug ||
        `${registrationData.dealershipName.toLowerCase().replace(/\s+/g, "-")}-${registrationData.region}`;

      try {
        const updateRequest: DealershipUpdateDetailsRequest = {
          args: [dealershipId],
          kwargs: {
            ...(registrationData.dealershipType && {
              dealership_type: registrationData.dealershipType,
            }),
            ...(registrationData.languages.length > 0 && {
              languages: registrationData.languages,
            }),
            ...(brandSlugs.length > 0 && {
              supported_brands: brandSlugs,
            }),
            ...(aliases.length > 0 && { aliases }),
            ...(registrationData.panNumber && {
              pan_number: registrationData.panNumber,
            }),
            ...(registrationData.gstin && {
              gstin: registrationData.gstin,
            }),
            ...(registrationData.website && {
              website: registrationData.website,
            }),
          },
        };

        // Call update details API (don't fail signup if this fails)
        await dealershipUpdateDetails(updateRequest);
      } catch (updateError) {
        // Log error but don't fail the signup process
        console.error("Failed to update dealership details:", updateError);
      }

      // Reset reCAPTCHA on successful registration
      if (isRecaptchaEnabled) {
        recaptchaRef.current?.reset();
        setRecaptchaToken(null);
      }

      // On success, show success with initial credits
      setPhase("success");
    } catch (err) {
      // Reset reCAPTCHA on error
      if (isRecaptchaEnabled) {
        recaptchaRef.current?.reset();
        setRecaptchaToken(null);
      }
      if (err instanceof ApiError) {
        // Extract clean error message
        let cleanErrorMessage = err.message;
        let details: string | null = null;

        // Try to parse and extract a cleaner error message
        if (err.error) {
          if (typeof err.error === "string") {
            // Try to parse if it's JSON string
            try {
              const parsed = JSON.parse(err.error);
              if (parsed.error) {
                cleanErrorMessage = parsed.error;
              } else if (parsed.message) {
                cleanErrorMessage = parsed.message;
              }
              // Store formatted JSON as details
              details = JSON.stringify(parsed, null, 2);
            } catch {
              // Not JSON, use as is
              cleanErrorMessage = err.error;
              // Only store details if it's different from the message
              if (err.error !== cleanErrorMessage) {
                details = err.error;
              } else {
                details = null;
              }
            }
          } else if (err.error.error) {
            cleanErrorMessage = err.error.error;
            details = JSON.stringify(err.error, null, 2);
          } else if (err.error.message) {
            cleanErrorMessage = err.error.message;
            details = JSON.stringify(err.error, null, 2);
          } else {
            // Store the full error object as details
            details = JSON.stringify(err.error, null, 2);
          }
        }

        // Clean up error message - remove any "API Error:" prefixes and status codes
        cleanErrorMessage = cleanErrorMessage
          .replace(/^API Error:\s*\d*\s*/gi, "")
          .replace(/^Request failed\s*\(\d+\)\s*/gi, "")
          .trim();

        // Try to extract JSON error if present in the message
        try {
          // Match JSON object (including multiline)
          const jsonMatch = cleanErrorMessage.match(/\{[\s\S]*?\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            if (parsed.error) {
              cleanErrorMessage = parsed.error;
              // Store the full JSON as details if not already set
              if (!details) {
                details = JSON.stringify(parsed, null, 2);
              }
            } else if (parsed.message) {
              cleanErrorMessage = parsed.message;
              if (!details) {
                details = JSON.stringify(parsed, null, 2);
              }
            }
          }
        } catch {
          // Not JSON, keep as is
        }

        // If message is empty or just whitespace, use a default message
        if (!cleanErrorMessage || cleanErrorMessage.trim() === "") {
          cleanErrorMessage = "Registration failed. Please try again.";
        }

        setError(cleanErrorMessage.trim());
        // Only set details if they exist and are different from the error message
        if (details && details.trim() && details !== cleanErrorMessage) {
          setErrorDetails(details);
        } else {
          setErrorDetails(null);
        }
      } else {
        const errorMessage =
          err instanceof Error
            ? err.message.replace(/^API Error: \d+\s*/i, "")
            : "Registration failed. Please try again.";
        setError(errorMessage);
        setErrorDetails(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerification = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setErrorDetails(null);
    setIsLoading(true);

    try {
      // Note: Verification API endpoint can be added later if needed
      // For now, we'll just redirect to dashboard after successful signup
      // The verification data (GSTIN, PAN) can be submitted separately

      // Redirect to dashboard
      router.push("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Verification failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen py-8">
      <div className="container mx-auto px-4 max-w-2xl">
        {/* Back to Login */}
        {phase === "registration" && (
          <div className="mb-6">
            <Link
              href="/login"
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Login
            </Link>
          </div>
        )}

        {/* Registration Phase */}
        {phase === "registration" && (
          <>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                <Building2 className="h-8 w-8 text-primary" />
              </div>
              <h1 className="text-4xl font-bold text-foreground mb-2">
                Dealer Registration
              </h1>
              <p className="text-lg text-muted-foreground">
                Create your account and get started in minutes
              </p>
            </div>

            <Card className="shadow-xl border-border/50">
              <CardHeader>
                <CardTitle className="text-2xl">Quick Registration</CardTitle>
                <CardDescription>
                  Enter your basic details to get started with 100 free credits
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleRegistration} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="dealershipName">
                      Dealership Name{" "}
                      <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="dealershipName"
                        placeholder="Enter dealership name"
                        value={registrationData.dealershipName}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            dealershipName: e.target.value,
                          })
                        }
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="legalName">Legal Name (Optional)</Label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="legalName"
                        placeholder="Enter legal business name"
                        value={registrationData.legalName}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            legalName: e.target.value,
                          })
                        }
                        className="pl-10"
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Legal name as per registration documents
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="fullName">
                      Your Full Name <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="fullName"
                        placeholder="Enter your name"
                        value={registrationData.fullName}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            fullName: e.target.value,
                          })
                        }
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="email">
                        Email <span className="text-destructive">*</span>
                      </Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="email"
                          type="email"
                          placeholder="you@dealership.com"
                          value={registrationData.email}
                          onChange={(e) =>
                            setRegistrationData({
                              ...registrationData,
                              email: e.target.value,
                            })
                          }
                          className="pl-10"
                          required
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone">
                        Phone <span className="text-destructive">*</span>
                      </Label>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                          <Input
                            id="phone"
                            type="tel"
                            placeholder="+91 98765 43210"
                            value={registrationData.phone}
                            onChange={(e) => {
                              setRegistrationData({
                                ...registrationData,
                                phone: e.target.value,
                              });
                              // Reset OTP token if phone number changes
                              if (phoneOtpToken) {
                                setPhoneOtpToken(null);
                                setPhoneOtp("");
                              }
                              setOtpError("");
                            }}
                            className="pl-10"
                            required
                          />
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={handleGenerateOTP}
                          disabled={isGeneratingOtp || !registrationData.phone}
                        >
                          {isGeneratingOtp ? "Generating..." : "Generate OTP"}
                        </Button>
                      </div>
                      {otpError && (
                        <p className="text-sm text-destructive">{otpError}</p>
                      )}
                      {phoneOtpToken && (
                        <p className="text-sm text-green-600">
                          OTP sent successfully! Please check your phone.
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Phone OTP Input */}
                  {phoneOtpToken && (
                    <div className="space-y-2">
                      <Label htmlFor="phoneOtp">
                        Phone OTP <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        id="phoneOtp"
                        type="text"
                        placeholder="Enter OTP"
                        value={phoneOtp}
                        onChange={(e) => {
                          // Only allow numbers and limit to 6 digits
                          const value = e.target.value
                            .replace(/\D/g, "")
                            .slice(0, 6);
                          setPhoneOtp(value);
                        }}
                        maxLength={6}
                        className="font-mono text-center text-lg tracking-widest"
                        required
                      />
                      <p className="text-xs text-muted-foreground">
                        Enter the 6-digit OTP sent to your phone number
                      </p>
                    </div>
                  )}

                  {/* Region Selection */}
                  <div className="space-y-2">
                    <Label htmlFor="region">
                      Region <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <select
                        id="region"
                        value={registrationData.region}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            region: e.target.value,
                          })
                        }
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 pl-10 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      >
                        <option value="south-india">South India</option>
                        <option value="north-india">North India</option>
                        <option value="east-india">East India</option>
                        <option value="west-india">West India</option>
                        <option value="central-india">Central India</option>
                      </select>
                    </div>
                  </div>

                  {/* Vehicle Type */}
                  <div className="space-y-2">
                    <Label htmlFor="vehicleType">
                      Vehicle Type <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                      <Car className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <select
                        id="vehicleType"
                        value={registrationData.vehicleType}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            vehicleType: e.target.value,
                          })
                        }
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 pl-10 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        required
                      >
                        <option value="Passenger vehicles">
                          Passenger vehicles
                        </option>
                        <option value="Commercial vehicles">
                          Commercial vehicles
                        </option>
                        <option value="Two-wheelers">Two-wheelers</option>
                        <option value="Electric vehicles">
                          Electric vehicles
                        </option>
                      </select>
                    </div>
                  </div>

                  {/* Dealership Type */}
                  <div className="space-y-3">
                    <Label className="text-base font-semibold">
                      Dealership Type{" "}
                      <span className="text-destructive">*</span>
                    </Label>
                    <RadioGroup
                      value={registrationData.dealershipType}
                      onValueChange={(value) =>
                        setRegistrationData({
                          ...registrationData,
                          dealershipType: value as
                            | "Single Brand"
                            | "Multi Brand",
                        })
                      }
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
                      Supported Brands{" "}
                      <span className="text-destructive">*</span>
                    </Label>
                    <div className="space-y-2">
                      <Select
                        value=""
                        onValueChange={(value) => {
                          if (
                            value &&
                            !registrationData.brands.includes(value)
                          ) {
                            setRegistrationData({
                              ...registrationData,
                              brands: [...registrationData.brands, value],
                            });
                          }
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select a brand to add" />
                        </SelectTrigger>
                        <SelectContent>
                          {[
                            "Toyota",
                            "Honda",
                            "Maruti Suzuki",
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
                                !registrationData.brands.includes(brand)
                            )
                            .map((brand) => (
                              <SelectItem key={brand} value={brand}>
                                {brand}
                              </SelectItem>
                            ))}
                          {registrationData.brands.length >= 10 && (
                            <SelectItem value="" disabled>
                              Maximum brands selected
                            </SelectItem>
                          )}
                        </SelectContent>
                      </Select>
                      {registrationData.brands.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-2 p-3 bg-muted/50 rounded-lg border">
                          {registrationData.brands.map((brand) => (
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
                                  setRegistrationData({
                                    ...registrationData,
                                    brands: registrationData.brands.filter(
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
                      {registrationData.brands.length === 0 && (
                        <p className="text-sm text-muted-foreground">
                          No brands selected. Please add at least one brand.
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Languages */}
                  <div className="space-y-3">
                    <Label className="text-base font-semibold">
                      Supported Languages{" "}
                      <span className="text-destructive">*</span>
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
                            registrationData.languages.includes(lang)
                              ? "default"
                              : "outline"
                          }
                          className="cursor-pointer px-3 py-2 text-sm capitalize"
                          onClick={() => {
                            if (registrationData.languages.includes(lang)) {
                              setRegistrationData({
                                ...registrationData,
                                languages: registrationData.languages.filter(
                                  (l) => l !== lang
                                ),
                              });
                            } else {
                              setRegistrationData({
                                ...registrationData,
                                languages: [
                                  ...registrationData.languages,
                                  lang,
                                ],
                              });
                            }
                          }}
                        >
                          {lang}
                          {registrationData.languages.includes(lang) && (
                            <X className="h-3 w-3 ml-2" />
                          )}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Website */}
                  <div className="space-y-2">
                    <Label htmlFor="website">Website (Optional)</Label>
                    <div className="relative">
                      <Globe className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="website"
                        type="url"
                        placeholder="https://www.yourdealership.com"
                        value={registrationData.website}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            website: e.target.value,
                          })
                        }
                        className="pl-10"
                      />
                    </div>
                  </div>

                  {/* PAN and GSTIN (Optional) */}
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="panNumber">PAN Number (Optional)</Label>
                      <Input
                        id="panNumber"
                        placeholder="ABCD1234567890"
                        value={registrationData.panNumber}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            panNumber: e.target.value.toUpperCase(),
                          })
                        }
                        maxLength={10}
                        className="font-mono uppercase"
                      />
                      <p className="text-xs text-muted-foreground">
                        Permanent Account Number
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="gstin">GSTIN (Optional)</Label>
                      <Input
                        id="gstin"
                        placeholder="ABCD1234567890"
                        value={registrationData.gstin}
                        onChange={(e) =>
                          setRegistrationData({
                            ...registrationData,
                            gstin: e.target.value.toUpperCase(),
                          })
                        }
                        maxLength={15}
                        className="font-mono uppercase"
                      />
                      <p className="text-xs text-muted-foreground">
                        15-digit GST Identification Number
                      </p>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="password">
                        Password <span className="text-destructive">*</span>
                      </Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="password"
                          type="password"
                          placeholder="Create password"
                          value={registrationData.password}
                          onChange={(e) =>
                            setRegistrationData({
                              ...registrationData,
                              password: e.target.value,
                            })
                          }
                          className="pl-10"
                          required
                          minLength={8}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Password must be at least 8 characters and contain at
                        least one letter
                      </p>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="confirmPassword">
                        Confirm Password{" "}
                        <span className="text-destructive">*</span>
                      </Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="confirmPassword"
                          type="password"
                          placeholder="Confirm password"
                          value={registrationData.confirmPassword}
                          onChange={(e) =>
                            setRegistrationData({
                              ...registrationData,
                              confirmPassword: e.target.value,
                            })
                          }
                          className="pl-10"
                          required
                          minLength={8}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Error Display at Bottom */}
                  {error && (
                    <Alert
                      variant="destructive"
                      className="border-red-500/50 bg-red-50/50 dark:bg-red-950/20"
                    >
                      <AlertDescription>
                        <div className="flex items-start gap-3">
                          <div className="flex-shrink-0 mt-0.5">
                            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-red-900 dark:text-red-100 mb-2">
                              Registration Failed
                            </div>
                            <div className="text-sm text-red-800 dark:text-red-200 leading-relaxed break-words">
                              {error}
                            </div>
                            {errorDetails && (
                              <details className="mt-3 group">
                                <summary className="cursor-pointer text-xs font-medium text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100 transition-colors list-none">
                                  <span className="inline-flex items-center gap-1">
                                    <span>View technical details</span>
                                    <svg
                                      className="w-3 h-3 transition-transform group-open:rotate-180"
                                      fill="none"
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M19 9l-7 7-7-7"
                                      />
                                    </svg>
                                  </span>
                                </summary>
                                <div className="mt-2 p-3 bg-red-100/50 dark:bg-red-950/30 rounded-md border border-red-200/50 dark:border-red-800/50">
                                  <pre className="text-xs overflow-auto max-h-40 font-mono text-red-900 dark:text-red-100 whitespace-pre-wrap break-words">
                                    {typeof errorDetails === "string"
                                      ? errorDetails
                                      : JSON.stringify(errorDetails, null, 2)}
                                  </pre>
                                </div>
                              </details>
                            )}
                          </div>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* reCAPTCHA */}
                  {isRecaptchaEnabled && (
                    <div className="space-y-2">
                      <ReCAPTCHA
                        ref={recaptchaRef}
                        sitekey={recaptchaSiteKey}
                        onChange={(token) => {
                          setRecaptchaToken(token);
                          if (token && error.includes("reCAPTCHA")) {
                            setError("");
                          }
                        }}
                        theme="light"
                        size="normal"
                      />
                    </div>
                  )}

                  <Button
                    type="submit"
                    className="w-full"
                    size="lg"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      "Creating Account..."
                    ) : (
                      <>
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Create Account & Get 100 Credits
                      </>
                    )}
                  </Button>

                  <p className="text-xs text-center text-muted-foreground">
                    By registering, you agree to our Terms of Service and
                    Privacy Policy
                  </p>
                </form>
              </CardContent>
            </Card>
          </>
        )}

        {/* Success with Verification Option */}
        {phase === "success" && signupResponse && (
          <>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 mb-4 animate-in zoom-in duration-500">
                <CheckCircle2 className="h-12 w-12 text-green-600" />
              </div>
              <h1 className="text-4xl font-bold text-foreground mb-2">
                Welcome Aboard!
              </h1>
              <p className="text-lg text-muted-foreground">
                Your dealership account has been created successfully
              </p>
            </div>

            {/* Dealership Information Card */}
            <Card className="shadow-xl border-primary/50 mb-6 bg-gradient-to-br from-primary/5 to-transparent">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <Building2 className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-2xl">
                      {signupResponse.dealer_name ||
                        signupResponse.dealership_legal_name}
                    </CardTitle>
                    <CardDescription>
                      Dealership ID: {signupResponse.dealership_id}
                    </CardDescription>
                  </div>
                  <Badge
                    variant={
                      signupResponse.dealer_status === "active"
                        ? "default"
                        : "secondary"
                    }
                    className="text-sm"
                  >
                    {signupResponse.dealer_status || "Lead"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <MapPin className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">Region</p>
                        <p className="text-sm text-muted-foreground">
                          {signupResponse.region_name ||
                            signupResponse.region_id}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <Store className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">Dealership Type</p>
                        <p className="text-sm text-muted-foreground">
                          {signupResponse.dealership_type}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <Car className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">Vehicle Category</p>
                        <p className="text-sm text-muted-foreground">
                          {signupResponse.vehicle_category}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="space-y-3">
                    {signupResponse.website && (
                      <div className="flex items-start gap-3">
                        <Globe className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Website</p>
                          <a
                            href={signupResponse.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm text-primary hover:underline"
                          >
                            {signupResponse.website}
                          </a>
                        </div>
                      </div>
                    )}
                    {signupResponse.gstin && (
                      <div className="flex items-start gap-3">
                        <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">GSTIN</p>
                          <p className="text-sm text-muted-foreground font-mono">
                            {signupResponse.gstin}
                          </p>
                        </div>
                      </div>
                    )}
                    {signupResponse.pan_number && (
                      <div className="flex items-start gap-3">
                        <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">PAN Number</p>
                          <p className="text-sm text-muted-foreground font-mono">
                            {signupResponse.pan_number}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Supported Brands */}
                {signupResponse.supported_brands &&
                  signupResponse.supported_brands.length > 0 && (
                    <div className="pt-4 border-t">
                      <div className="flex items-center gap-2 mb-3">
                        <Tag className="h-5 w-5 text-muted-foreground" />
                        <p className="text-sm font-medium">Supported Brands</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {signupResponse.supported_brands.map(
                          (brand: string, idx: number) => (
                            <Badge key={idx} variant="outline">
                              {brand
                                .replace(/-/g, " ")
                                .replace(/\b\w/g, (l: string) =>
                                  l.toUpperCase()
                                )}
                            </Badge>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Languages */}
                {signupResponse.languages &&
                  signupResponse.languages.length > 0 && (
                    <div className="pt-4 border-t">
                      <div className="flex items-center gap-2 mb-3">
                        <Languages className="h-5 w-5 text-muted-foreground" />
                        <p className="text-sm font-medium">
                          Supported Languages
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {signupResponse.languages.map(
                          (lang: string, idx: number) => (
                            <Badge key={idx} variant="secondary">
                              {lang.charAt(0).toUpperCase() + lang.slice(1)}
                            </Badge>
                          )
                        )}
                      </div>
                    </div>
                  )}

                {/* Aliases */}
                {signupResponse.aliases &&
                  signupResponse.aliases.length > 0 && (
                    <div className="pt-4 border-t">
                      <div className="flex items-center gap-2 mb-3">
                        <Award className="h-5 w-5 text-muted-foreground" />
                        <p className="text-sm font-medium">Aliases</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {signupResponse.aliases.map(
                          (alias: string, idx: number) => (
                            <Badge key={idx} variant="outline">
                              {alias}
                            </Badge>
                          )
                        )}
                      </div>
                    </div>
                  )}
              </CardContent>
            </Card>

            {/* Credits Card */}
            <Card className="shadow-xl border-green-500/50 mb-6 bg-gradient-to-br from-green-50 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-4 bg-green-500 rounded-full">
                    <Sparkles className="h-8 w-8 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-2xl font-bold text-foreground">
                      500 Testing Credits Added!
                    </h3>
                    <p className="text-muted-foreground">
                      Start exploring our platform with your testing credits
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Login Credentials Card */}
            {signupResponse.login_token && (
              <Card className="shadow-xl border-blue-500/50 mb-6 bg-gradient-to-br from-blue-50 to-transparent">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-500/10 rounded-lg">
                      <Shield className="h-6 w-6 text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <CardTitle className="text-xl">
                        Login Credentials
                      </CardTitle>
                      <CardDescription>
                        Save these credentials for future access
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="bg-background/50 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <User className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">User ID</p>
                          <p className="text-sm text-muted-foreground font-mono">
                            {signupResponse.login_token.user_id}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            signupResponse.login_token.user_id
                          );
                          setCopiedField("user_id");
                          setTimeout(() => setCopiedField(null), 2000);
                        }}
                      >
                        {copiedField === "user_id" ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Lock className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Session ID</p>
                          <p className="text-sm text-muted-foreground font-mono">
                            {signupResponse.login_token.session_id}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            signupResponse.login_token.session_id
                          );
                          setCopiedField("session_id");
                          setTimeout(() => setCopiedField(null), 2000);
                        }}
                      >
                        {copiedField === "session_id" ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Shield className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Token</p>
                          <p className="text-sm text-muted-foreground font-mono truncate max-w-xs">
                            {signupResponse.login_token.token}
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          navigator.clipboard.writeText(
                            signupResponse.login_token.token
                          );
                          setCopiedField("token");
                          setTimeout(() => setCopiedField(null), 2000);
                        }}
                      >
                        {copiedField === "token" ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <div className="flex items-center gap-3 pt-2 border-t">
                      <Award className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">Role</p>
                        <p className="text-sm text-muted-foreground">
                          {signupResponse.login_token.role}
                        </p>
                      </div>
                    </div>
                    {signupResponse.login_token.expiry && (
                      <div className="flex items-center gap-3 pt-2 border-t">
                        <Calendar className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">Token Expiry</p>
                          <p className="text-sm text-muted-foreground">
                            {new Date(
                              signupResponse.login_token.expiry * 1000
                            ).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Continue to Dashboard */}
            <Card className="shadow-xl border-primary/50 bg-gradient-to-br from-primary/5 to-transparent">
              <CardContent className="pt-6">
                <div className="text-center space-y-4">
                  <p className="text-muted-foreground">
                    You're all set! Start creating campaigns and managing your
                    dealership.
                  </p>
                  <Button
                    size="lg"
                    onClick={() => router.push("/")}
                    className="w-full md:w-auto"
                  >
                    Go to Dashboard
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {/* Verification Phase */}
        {phase === "verification" && (
          <>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
                <FileText className="h-8 w-8 text-primary" />
              </div>
              <h1 className="text-4xl font-bold text-foreground mb-2">
                Profile Verification
              </h1>
              <p className="text-lg text-muted-foreground">
                Complete verification to unlock 500 testing credits
              </p>
            </div>

            {/* Progress Indicator */}
            <Card className="mb-6 border-primary/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">
                    Verification Progress
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
                <CardTitle className="text-2xl">Business Details</CardTitle>
                <CardDescription>
                  Provide your business verification documents
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleVerification} className="space-y-4">
                  {error && (
                    <Alert variant="destructive">
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="gstin">
                      GSTIN <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="gstin"
                      placeholder="Enter 15-digit GSTIN"
                      value={verificationData.gstin}
                      onChange={(e) =>
                        setVerificationData({
                          ...verificationData,
                          gstin: e.target.value,
                        })
                      }
                      maxLength={15}
                      className="font-mono"
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      Goods and Services Tax Identification Number
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="panCard">
                      PAN Card <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="panCard"
                      placeholder="Enter PAN number"
                      value={verificationData.panCard}
                      onChange={(e) =>
                        setVerificationData({
                          ...verificationData,
                          panCard: e.target.value,
                        })
                      }
                      maxLength={10}
                      className="font-mono uppercase"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="address">
                      Business Address{" "}
                      <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="address"
                      placeholder="Enter complete business address"
                      value={verificationData.address}
                      onChange={(e) =>
                        setVerificationData({
                          ...verificationData,
                          address: e.target.value,
                        })
                      }
                      required
                    />
                  </div>

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="city">
                        City <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        id="city"
                        placeholder="City"
                        value={verificationData.city}
                        onChange={(e) =>
                          setVerificationData({
                            ...verificationData,
                            city: e.target.value,
                          })
                        }
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="state">
                        State <span className="text-destructive">*</span>
                      </Label>
                      <Input
                        id="state"
                        placeholder="State"
                        value={verificationData.state}
                        onChange={(e) =>
                          setVerificationData({
                            ...verificationData,
                            state: e.target.value,
                          })
                        }
                        required
                      />
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      Your documents will be verified within 24 hours. Once
                      approved, 500 testing credits will be added to your
                      account automatically.
                    </p>
                  </div>

                  <div className="grid md:grid-cols-2 gap-3 pt-4">
                    <Button
                      type="button"
                      variant="outline"
                      size="lg"
                      onClick={() => router.push("/")}
                    >
                      Skip & Go to Dashboard
                    </Button>
                    <Button type="submit" size="lg" disabled={isLoading}>
                      {isLoading ? (
                        "Submitting..."
                      ) : (
                        <>
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Submit for Verification
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </>
        )}
        
        {/* Made by Dave AI */}
        <div className="text-center mt-8 pb-8">
          <p className="text-sm text-muted-foreground flex items-center justify-center gap-1">
            Made by{" "}
            <a
              href="https://www.iamdave.ai/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-foreground hover:text-primary transition-colors"
            >
              Dave AI
            </a>{" "}
            with <span className="text-red-500">♥</span>
          </p>
        </div>
      </div>
    </div>
  );
}
