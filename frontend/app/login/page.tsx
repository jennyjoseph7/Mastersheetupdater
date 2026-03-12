"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ReCAPTCHA from "react-google-recaptcha";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Loader2,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  UserPlus,
  ArrowRight,
} from "lucide-react";
import Image from "next/image";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("user@iamdave.ai");
  const [password, setPassword] = useState("12345678");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [recaptchaToken, setRecaptchaToken] = useState<string | null>(null);
  const recaptchaRef = useRef<ReCAPTCHA>(null);
  const [validationErrors, setValidationErrors] = useState<{
    email?: string;
    password?: string;
    recaptcha?: string;
  }>({});

  // Get reCAPTCHA site key from environment
  const recaptchaSiteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || "";
  console.log("[autoNgage] reCAPTCHA site key status:", recaptchaSiteKey ? "Loaded" : "Not found" ,recaptchaSiteKey);
  const isRecaptchaEnabled = Boolean(recaptchaSiteKey);

  // Debug: Log the site key status (remove in production)
  useEffect(() => {
    if (isRecaptchaEnabled) {
      console.log(
        // "[reCAPTCHA] Site key loaded:",
        // recaptchaSiteKey.substring(0, 10) + "..."
      );
      console.log(
        // "[reCAPTCHA] Current domain:",
        // typeof window !== "undefined" ? window.location.hostname : "server"
      );
    } else {
      console.warn(
        // "[reCAPTCHA] Site key not found. Add NEXT_PUBLIC_RECAPTCHA_SITE_KEY to .env.local"
      );
    }
  }, [recaptchaSiteKey, isRecaptchaEnabled]);

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validateForm = () => {
    const errors: { email?: string; password?: string; recaptcha?: string } =
      {};

    if (!email) {
      errors.email = "Email is required";
    } else if (!validateEmail(email)) {
      errors.email = "Please enter a valid email address";
    }

    if (!password) {
      errors.password = "Password is required";
    } else if (password.length < 6) {
      errors.password = "Password must be at least 6 characters";
    }

    // Only validate reCAPTCHA if it's enabled
    if (isRecaptchaEnabled && !recaptchaToken) {
      errors.recaptcha = "Please complete the reCAPTCHA verification";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      await login(email, password);
      // Reset reCAPTCHA on successful login
      if (isRecaptchaEnabled) {
        recaptchaRef.current?.reset();
        setRecaptchaToken(null);
      }
      // Redirect to dashboard - modal will be shown there if setup is incomplete
      // The dashboard will check setup status and show modal automatically
      router.push("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Invalid email or password. Please try again."
      );
      // Reset reCAPTCHA on error
      if (isRecaptchaEnabled) {
        recaptchaRef.current?.reset();
        setRecaptchaToken(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRecaptchaChange = (token: string | null) => {
    setRecaptchaToken(token);
    if (token && validationErrors.recaptcha) {
      setValidationErrors((prev) => ({ ...prev, recaptcha: undefined }));
    }
  };

  const handleFieldChange = (field: "email" | "password", value: string) => {
    if (field === "email") {
      setEmail(value);
      if (validationErrors.email) {
        setValidationErrors((prev) => ({ ...prev, email: undefined }));
      }
    } else {
      setPassword(value);
      if (validationErrors.password) {
        setValidationErrors((prev) => ({ ...prev, password: undefined }));
      }
    }
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo and Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Image
              src="/images/logo.png"
              alt="autoNgage Logo"
              width={230}
              height={56}
              className="w-auto h-10 "
            />
          </div>
          <h1 className="text-3xl font-bold text-foreground">Welcome back</h1>
          <p className="text-muted-foreground mt-2">
            Sign in to your account to continue
          </p>
        </div>

        {/* Login Card */}
        <Card className="shadow-2xl border-border/50">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-semibold">Sign in</CardTitle>
            <CardDescription>
              Enter your credentials to access your account
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Global Error Alert */}
              {error && (
                <Alert
                  variant="destructive"
                  className="animate-in fade-in slide-in-from-top-2 duration-300"
                >
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Email Field */}
              <div className="space-y-2">
                <Label htmlFor="email" className="text-sm font-medium">
                  Email address
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => handleFieldChange("email", e.target.value)}
                    className={`pl-10 ${
                      validationErrors.email
                        ? "border-destructive focus-visible:ring-destructive"
                        : ""
                    }`}
                    disabled={isLoading}
                    autoComplete="email"
                  />
                </div>
                {validationErrors.email && (
                  <p className="text-sm text-destructive animate-in fade-in slide-in-from-top-1 duration-200">
                    {validationErrors.email}
                  </p>
                )}
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-sm font-medium">
                    Password
                  </Label>
                  <Link
                    href="/forgot-password"
                    className="text-sm text-primary hover:text-primary/80 font-medium transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) =>
                      handleFieldChange("password", e.target.value)
                    }
                    className={`pl-10 pr-10 ${
                      validationErrors.password
                        ? "border-destructive focus-visible:ring-destructive"
                        : ""
                    }`}
                    disabled={isLoading}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    disabled={isLoading}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
                {validationErrors.password && (
                  <p className="text-sm text-destructive animate-in fade-in slide-in-from-top-1 duration-200">
                    {validationErrors.password}
                  </p>
                )}
              </div>

              {/* reCAPTCHA */}
              <div className="space-y-2">
                <ReCAPTCHA
                  ref={recaptchaRef}
                  sitekey={process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || ""}
                  onChange={handleRecaptchaChange}
                  theme="light"
                  size="normal"
                />
                {validationErrors.recaptcha && (
                  <p className="text-sm text-destructive animate-in fade-in slide-in-from-top-1 duration-200">
                    {validationErrors.recaptcha}
                  </p>
                )}
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Sign in
                  </>
                )}
              </Button>
            </form>

            {/* Dealer Registration CTA Card */}
            <div className="mt-6">
              <Separator className="mb-6" />

              <div className="bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border-2 border-primary/20 rounded-lg p-6 space-y-4 hover:border-primary/30 transition-all duration-300">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <UserPlus className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-foreground text-lg">
                      New to our platform?
                    </h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      Join our network of dealers and start managing your
                      campaigns with AI-powered tools
                    </p>
                  </div>
                </div>

                <Button
                  variant="default"
                  size="lg"
                  className="w-full shadow-lg hover:shadow-xl transition-all duration-300 group"
                  onClick={() => router.push("/signup")}
                  type="button"
                >
                  <UserPlus className="mr-2 h-5 w-5" />
                  Register / Sign Up with Us as Dealer
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        {/* <p className="text-center text-sm text-muted-foreground mt-6">
          By signing in, you agree to our{" "}
          <Link
            href="/terms"
            className="underline hover:text-foreground transition-colors"
          >
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link
            href="/privacy"
            className="underline hover:text-foreground transition-colors"
          >
            Privacy Policy
          </Link>
        </p> */}
 <p className="text-center text-sm text-muted-foreground mt-6">
        By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
        {/* Made by Dave AI */}
        <div className="text-center mt-8">
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
