"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReCAPTCHA from "react-google-recaptcha";
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
  Eye,
  EyeOff,
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
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
import { REGEXP_ONLY_DIGITS } from "input-otp";
import {
  API_BASE_URL,
  dealershipUpdateDetails,
  generateOTP,
  type DealershipSignupRequest,
  type DealershipUpdateDetailsRequest,
  ApiError,
} from "@/lib/api";

const urlRegex =
  /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

export default function DealerSignup() {
  const router = useRouter();
  const [phase, setPhase] = useState<"registration" | "success">(
    "registration"
  );
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
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);
  const [successDealershipId, setSuccessDealershipId] = useState("");

  // Get reCAPTCHA site key from environment
  const recaptchaSiteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || "";
  const isRecaptchaEnabled = Boolean(recaptchaSiteKey);

  // Registration data - only required fields
  const [registrationData, setRegistrationData] = useState({
    dealershipName: "",
    fullName: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    region: "south-india",
  });

  // Additional dealership details (step 2)
  const [dealershipDetails, setDealershipDetails] = useState({
    dealershipType: "Multi Brand" as "Single Brand" | "Multi Brand",
    languages: [] as string[],
    brands: [] as string[],
    panNumber: "",
    gstin: "",
    website: "",
  });
  const [websiteError, setWebsiteError] = useState("");
  const [panError, setPanError] = useState("");
  const [gstinError, setGstinError] = useState("");

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
    // Don't clear tokens immediately - keep forms visible while generating
    // setPhoneOtpToken(null);
    // setEmailOtpToken(null);

    try {
      // Generate phone OTP
      const phoneResponse = await generateOTP(
        registrationData.phone,
        "whatsapp"
      );
      if (!phoneResponse.token) {
        setOtpError("Failed to generate phone OTP. Please try again.");
        setPhoneOtpToken(null);
        setEmailOtpToken(null);
        return;
      }
      setPhoneOtpToken(phoneResponse.token);

      // Generate email OTP automatically
      try {
        const emailResponse = await generateOTP(
          registrationData.email,
          "email"
        );
        if (!emailResponse.token) {
          setOtpError("Failed to generate email OTP. Please try again.");
          setPhoneOtpToken(null);
          setEmailOtpToken(null);
          return;
        }
        setEmailOtpToken(emailResponse.token);
      } catch (emailErr) {
        // If email OTP fails, clear phone OTP token and show error
        console.error("Failed to generate email OTP:", emailErr);
        setPhoneOtpToken(null);
        setEmailOtpToken(null);
        const errorMessage =
          emailErr instanceof ApiError
            ? emailErr.message
            : "Failed to generate email OTP. Please try again.";
        setOtpError(errorMessage);
        return;
      }

      setOtpError("");
    } catch (err) {
      const errorMessage =
        err instanceof ApiError
          ? err.message
          : "Failed to generate OTP. Please try again.";
      setOtpError(errorMessage);
      setPhoneOtpToken(null);
      setEmailOtpToken(null);
    } finally {
      setIsGeneratingOtp(false);
    }
  };

  const handleRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setErrorDetails(null);

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
    if (!emailOtpToken) {
      setError("Please generate OTP for your email address");
      return;
    }
    if (!emailOtp) {
      setError("Please enter the OTP sent to your email address");
      return;
    }

    // Validate reCAPTCHA if enabled
    if (isRecaptchaEnabled && !recaptchaToken) {
      setError("Please complete the reCAPTCHA verification");
      return;
    }

    setIsLoading(true);

    try {
      // Step 1: Prepare API request with only required fields for signup
      const signupRequest: DealershipSignupRequest = {
        args: [registrationData.dealershipName, registrationData.region],
        kwargs: {
          primary_contact_name: registrationData.fullName,
          primary_contact_email: registrationData.email,
          primary_contact_phone: registrationData.phone,
          password: registrationData.password,
          confirm_password: registrationData.confirmPassword,
          email_otp: emailOtp,
          email_otp_token: emailOtpToken,
          phone_number_otp: phoneOtp,
          phone_number_otp_token: phoneOtpToken,
        },
        _timeout: 600,
      };

      // Call the dealership signup API directly - same pattern as generateOTP
      const backendUrl = `${API_BASE_URL}/dealership_signup`;
      
      console.log("[Signup Page] Calling backend directly:", backendUrl);
      console.log("[Signup Page] API_BASE_URL:", API_BASE_URL);
      console.log("[Signup Page] Request body:", JSON.stringify(signupRequest, null, 2));

      const res = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-GRYD-ENTERPRISE-ID": "autocrm",
          "X-GRYD-SIGNUP-TOKEN": "YXV0b2NybTE3NjI2MTAzOTUgMjY0NTI0",
        },
        body: JSON.stringify(signupRequest),
        cache: "no-store",
        mode: "cors",
        credentials: "omit",
      });

      console.log(`[Signup Page] Response status: ${res.status}`);
      console.log(
        `[Signup Page] Response headers:`,
        Object.fromEntries(res.headers.entries())
      );

      // Check content-type to detect HTML responses
      const contentType = res.headers.get("content-type") || "";
      const isHTML = contentType.includes("text/html");

      if (!res.ok) {
        let errorMessage = `Request failed (${res.status})`;
        let errorData: any = null;

        try {
          const errorText = await res.text();

          console.log(
            `[Signup Page] Error response content-type: ${contentType}`
          );
          console.log(
            `[Signup Page] Error response body: ${errorText.substring(0, 500)}`
          );

          // If response is HTML, it's likely a CORS error or redirect
          if (
            isHTML ||
            errorText.trim().startsWith("<!DOCTYPE") ||
            errorText.trim().startsWith("<html")
          ) {
            console.error(
              "[Signup Page] Received HTML response instead of JSON. This usually indicates:"
            );
            console.error("  1. CORS is not properly configured on the backend");
            console.error("  2. The endpoint is redirecting to an HTML page");
            console.error("  3. The endpoint doesn't exist (404 HTML page)");
            console.error("Response preview:", errorText.substring(0, 500));
            errorMessage = `Server returned HTML instead of JSON (Status: ${res.status}). This usually indicates a CORS issue or the endpoint doesn't exist. Check browser console for details.`;
          } else {
            // Try to parse JSON error response
            if (errorText && errorText.trim()) {
              try {
                errorData = JSON.parse(errorText);

                // Extract error message from various possible formats
                if (errorData && typeof errorData === "object") {
                  if (errorData.error) {
                    errorMessage = String(errorData.error);
                  } else if (errorData.message) {
                    errorMessage = String(errorData.message);
                  } else if (errorData.detail) {
                    errorMessage = String(errorData.detail);
                  } else {
                    // If it's an object but no standard error field, try to extract useful info
                    const errorStr = JSON.stringify(errorData);
                    // Check if it contains the Python error message
                    if (
                      errorStr.includes("'NoneType' object has no attribute 'get'")
                    ) {
                      // This is a backend bug - try to extract the original error if available
                      errorMessage =
                        "An error occurred while processing your request. Please check if the dealership already exists or try again.";
                    } else {
                      errorMessage = errorStr;
                    }
                  }
                } else if (typeof errorData === "string") {
                  errorMessage = errorData;
                }
              } catch (parseError) {
                // Not JSON, use errorText as is
                console.log(
                  `[Signup Page] Error response is not JSON, using raw text`
                );
                errorMessage = errorText || errorMessage;
              }
            }
          }
        } catch (readError) {
          // Failed to read response, use default message
          console.error(
            "[Signup Page] Failed to read error response:",
            readError
          );
          errorMessage = `Request failed (${res.status})`;
        }

        // Clean up any "API Error:" prefixes
        errorMessage = errorMessage.replace(/^API Error:\s*\d*\s*/gi, "").trim();

        // Handle Python traceback errors - replace with user-friendly message
        if (errorMessage.includes("'NoneType' object has no attribute 'get'")) {
          errorMessage =
            "An error occurred while processing your request. The dealership may already exist or there was a server error. Please try again.";
        }

        // If message is empty after cleanup, use a default
        if (!errorMessage || errorMessage === "") {
          errorMessage = `Request failed (${res.status})`;
        }

        console.log(`[Signup Page] Returning error: ${errorMessage}`);
        throw new ApiError(res.status, errorMessage);
      }

      // Check if successful response is also HTML (shouldn't happen, but handle it)
      const responseClone = res.clone();
      const responseText = await responseClone.text();

      if (
        isHTML ||
        responseText.trim().startsWith("<!DOCTYPE") ||
        responseText.trim().startsWith("<html")
      ) {
        console.error(
          "[Signup Page] Received HTML response for successful request!"
        );
        console.error("Response status:", res.status);
        console.error("Response URL:", res.url);
        console.error(
          "Response headers:",
          Object.fromEntries(res.headers.entries())
        );
        console.error("Response preview:", responseText.substring(0, 1000));
        throw new ApiError(
          500,
          `Server returned HTML instead of JSON (Status: ${res.status}). This usually indicates:
1. CORS is not properly configured on the backend
2. The endpoint URL is incorrect
3. The backend is redirecting to an HTML page
Check browser console and Network tab for more details.`
        );
      }

      // Try to parse as JSON
      let response;
      try {
        response = JSON.parse(responseText);
      } catch (parseError) {
        console.error("[Signup Page] Failed to parse response as JSON");
        console.error("Response text:", responseText.substring(0, 500));
        throw new ApiError(
          500,
          `Server returned invalid JSON. Response preview: ${responseText.substring(
            0,
            200
          )}...`
        );
      }

      console.log("[Signup Page] Response:", response);

      // Store the response data
      setSignupResponse(response);

      // Get dealership ID from signup response and store in localStorage
      const dealershipId =
        response?.dealership_id ||
        response?.dealership_slug ||
        `${registrationData.dealershipName
          .toLowerCase()
          .replace(/\s+/g, "-")}-${registrationData.region}`;

      if (dealershipId) {
        localStorage.setItem("dealership_id", dealershipId);
      }

      // Reset reCAPTCHA on successful registration
      if (isRecaptchaEnabled) {
        recaptchaRef.current?.reset();
        setRecaptchaToken(null);
      }

      // Show success dialog with dealership ID
      setSuccessDealershipId(dealershipId);
      setShowSuccessDialog(true);
      
      // After successful signup, redirect to login page
      // The success dialog will handle the redirect when user clicks "Go to Login"
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
                      <Label>
                        Phone <span className="text-destructive">*</span>
                      </Label>
                      <div className="flex gap-2">
                        <div className="flex-1">
                          <PhoneInput
                            value={registrationData.phone}
                            onChange={(phone) => {
                              setRegistrationData({
                                ...registrationData,
                                phone: phone,
                              });
                              // Reset OTP token if phone number changes
                              if (phoneOtpToken) {
                                setPhoneOtpToken(null);
                                setPhoneOtp("");
                              }
                              setOtpError("");
                            }}
                            defaultCountry="in"
                            inputClassName="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            countrySelectorStyleProps={{
                              buttonClassName:
                                "flex h-10 items-center justify-center rounded-l-md border border-input bg-background px-3 py-2 text-sm text-foreground ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
                            }}
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
                    </div>
                  </div>

                  {/* OTP Status Alerts - Full Width */}
                  {otpError && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{otpError}</AlertDescription>
                    </Alert>
                  )}
                  {phoneOtpToken && emailOtpToken && (
                    <Alert className="border-green-200 bg-green-50 dark:bg-green-950/20 dark:border-green-800/50">
                      <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                      <AlertDescription className="text-green-800 dark:text-green-200">
                        <div className="flex items-start gap-2">
                          <span className="font-medium">
                            OTPs sent successfully!
                          </span>
                          <span className="text-sm">
                            Please check your phone and email for the
                            verification codes.
                          </span>
                        </div>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* OTP Inputs - Phone and Email in a single row */}
                  {/* Show forms immediately when Generate OTP is clicked or when tokens exist */}
                  {(isGeneratingOtp || phoneOtpToken || emailOtpToken) && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Email OTP */}
                      <div className="space-y-2">
                        <Label
                          htmlFor="emailOtp"
                          className="flex items-center gap-2"
                        >
                          <Mail className="h-4 w-4" />
                          Email OTP <span className="text-destructive">*</span>
                          {isGeneratingOtp && !emailOtpToken && (
                            <span className="text-xs text-muted-foreground ml-auto">
                              Sending...
                            </span>
                          )}
                        </Label>
                        <div className="flex flex-col gap-2">
                          <InputOTP
                            maxLength={6}
                            pattern={REGEXP_ONLY_DIGITS}
                            value={emailOtp}
                            onChange={(value) => setEmailOtp(value)}
                            disabled={isGeneratingOtp && !emailOtpToken}
                          >
                            <InputOTPGroup>
                              <InputOTPSlot index={0} />
                              <InputOTPSlot index={1} />
                              <InputOTPSlot index={2} />
                              <InputOTPSlot index={3} />
                              <InputOTPSlot index={4} />
                              <InputOTPSlot index={5} />
                            </InputOTPGroup>
                          </InputOTP>
                          <p className="text-xs text-muted-foreground">
                            {isGeneratingOtp && !emailOtpToken
                              ? "Generating OTP..."
                              : "Enter the 6-digit OTP sent to your email address"}
                          </p>
                        </div>
                      </div>

                      {/* Phone OTP */}
                      <div className="space-y-2">
                        <Label
                          htmlFor="phoneOtp"
                          className="flex items-center gap-2"
                        >
                          <Phone className="h-4 w-4" />
                          Phone OTP <span className="text-destructive">*</span>
                          {isGeneratingOtp && !phoneOtpToken && (
                            <span className="text-xs text-muted-foreground ml-auto">
                              Sending...
                            </span>
                          )}
                        </Label>
                        <div className="flex flex-col gap-2">
                          <InputOTP
                            maxLength={6}
                            pattern={REGEXP_ONLY_DIGITS}
                            value={phoneOtp}
                            onChange={(value) => setPhoneOtp(value)}
                            disabled={isGeneratingOtp && !phoneOtpToken}
                          >
                            <InputOTPGroup>
                              <InputOTPSlot index={0} />
                              <InputOTPSlot index={1} />
                              <InputOTPSlot index={2} />
                              <InputOTPSlot index={3} />
                              <InputOTPSlot index={4} />
                              <InputOTPSlot index={5} />
                            </InputOTPGroup>
                          </InputOTP>
                          <p className="text-xs text-muted-foreground">
                            {isGeneratingOtp && !phoneOtpToken
                              ? "Generating OTP..."
                              : "Enter the 6-digit OTP sent to your phone number"}
                          </p>
                        </div>
                      </div>
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

                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="password">
                        Password <span className="text-destructive">*</span>
                      </Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="password"
                          type={showPassword ? "text" : "password"}
                          placeholder="Create password"
                          value={registrationData.password}
                          onChange={(e) =>
                            setRegistrationData({
                              ...registrationData,
                              password: e.target.value,
                            })
                          }
                          className="pl-10 pr-10"
                          required
                          minLength={8}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                          aria-label={
                            showPassword ? "Hide password" : "Show password"
                          }
                        >
                          {showPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
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
                          type={showConfirmPassword ? "text" : "password"}
                          placeholder="Confirm password"
                          value={registrationData.confirmPassword}
                          onChange={(e) =>
                            setRegistrationData({
                              ...registrationData,
                              confirmPassword: e.target.value,
                            })
                          }
                          className="pl-10 pr-10"
                          required
                          minLength={8}
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setShowConfirmPassword(!showConfirmPassword)
                          }
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                          aria-label={
                            showConfirmPassword
                              ? "Hide password"
                              : "Show password"
                          }
                        >
                          {showConfirmPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
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
                Dealer Registered Successfully!
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

            {/* Complete Verification Card */}
            <Card className="shadow-xl border-amber-500/50 mb-6 bg-gradient-to-br from-amber-50 to-transparent dark:from-amber-950/20">
              <CardContent className="pt-6">
                <div className="text-center space-y-4">
                  <div className="flex items-center justify-center gap-2 mb-2">
                    <Shield className="h-6 w-6 text-amber-600" />
                    <h3 className="text-xl font-semibold">
                      Complete Your Profile Verification
                    </h3>
                  </div>
                  <p className="text-muted-foreground">
                    Add dealership details, business verification, and unlock
                    additional features
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3 justify-center">
                    <Button
                      size="lg"
                      onClick={() => router.push("/dealership/update-details")}
                      className="bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700"
                    >
                      <Shield className="mr-2 h-4 w-4" />
                      Complete Verification
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                    <Button
                      size="lg"
                      variant="outline"
                      onClick={() => router.push("/")}
                      className="w-full sm:w-auto"
                    >
                      Skip for Now
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

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
                      onClick={() => router.push("/login")}
                      className="w-full md:w-auto"
                    >
                      Go to Login
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                </div>
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

      {/* Success Dialog */}
      <AlertDialog open={showSuccessDialog} onOpenChange={setShowSuccessDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <div className="flex items-center justify-center mb-4">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
            </div>
            <AlertDialogTitle className="text-center text-2xl">
              Dealer Registered Successfully!
            </AlertDialogTitle>
            <AlertDialogDescription className="text-center pt-4">
              <div className="space-y-2">
                <p className="text-base font-medium text-foreground">
                  Dealership ID:
                </p>
                <p className="text-lg font-mono font-semibold text-primary">
                  {successDealershipId}
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="sm:justify-center">
            <AlertDialogAction
              onClick={() => {
                setShowSuccessDialog(false);
                router.push("/login");
              }}
              className="w-full sm:w-auto"
            >
              Go to Login
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
