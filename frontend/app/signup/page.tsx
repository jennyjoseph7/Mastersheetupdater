"use client"

import type React from "react"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
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
} from "lucide-react"

export default function DealerSignup() {
  const router = useRouter()
  const [phase, setPhase] = useState<"registration" | "verification" | "success">("registration")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  // Registration data
  const [registrationData, setRegistrationData] = useState({
    dealershipName: "",
    fullName: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
  })

  // Verification data
  const [verificationData, setVerificationData] = useState({
    gstin: "",
    panCard: "",
    address: "",
    city: "",
    state: "",
  })

  const handleRegistration = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    // Validate passwords match
    if (registrationData.password !== registrationData.confirmPassword) {
      setError("Passwords do not match")
      return
    }

    setIsLoading(true)

    try {
      // API call to register dealer
      const response = await fetch("/api/dealer/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(registrationData),
      })

      if (!response.ok) {
        throw new Error("Registration failed")
      }

      // On success, show success with initial credits
      setPhase("success")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerification = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setIsLoading(true)

    try {
      // API call to submit verification
      const response = await fetch("/api/dealer/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: registrationData.email,
          ...verificationData,
        }),
      })

      if (!response.ok) {
        throw new Error("Verification failed")
      }

      // Redirect to dashboard
      router.push("/")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

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
              <h1 className="text-4xl font-bold text-foreground mb-2">Dealer Registration</h1>
              <p className="text-lg text-muted-foreground">Create your account and get started in minutes</p>
            </div>

            <Card className="shadow-xl border-border/50">
              <CardHeader>
                <CardTitle className="text-2xl">Quick Registration</CardTitle>
                <CardDescription>Enter your basic details to get started with 100 free credits</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleRegistration} className="space-y-4">
                  {error && (
                    <Alert variant="destructive">
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="space-y-2">
                    <Label htmlFor="dealershipName">
                      Dealership Name <span className="text-destructive">*</span>
                    </Label>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="dealershipName"
                        placeholder="Enter dealership name"
                        value={registrationData.dealershipName}
                        onChange={(e) => setRegistrationData({ ...registrationData, dealershipName: e.target.value })}
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
                        onChange={(e) => setRegistrationData({ ...registrationData, fullName: e.target.value })}
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
                          onChange={(e) => setRegistrationData({ ...registrationData, email: e.target.value })}
                          className="pl-10"
                          required
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone">
                        Phone <span className="text-destructive">*</span>
                      </Label>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="phone"
                          type="tel"
                          placeholder="+91 98765 43210"
                          value={registrationData.phone}
                          onChange={(e) => setRegistrationData({ ...registrationData, phone: e.target.value })}
                          className="pl-10"
                          required
                        />
                      </div>
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
                          onChange={(e) => setRegistrationData({ ...registrationData, password: e.target.value })}
                          className="pl-10"
                          required
                          minLength={8}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="confirmPassword">
                        Confirm Password <span className="text-destructive">*</span>
                      </Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="confirmPassword"
                          type="password"
                          placeholder="Confirm password"
                          value={registrationData.confirmPassword}
                          onChange={(e) =>
                            setRegistrationData({ ...registrationData, confirmPassword: e.target.value })
                          }
                          className="pl-10"
                          required
                          minLength={8}
                        />
                      </div>
                    </div>
                  </div>

                  <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
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
                    By registering, you agree to our Terms of Service and Privacy Policy
                  </p>
                </form>
              </CardContent>
            </Card>
          </>
        )}

        {/* Success with Verification Option */}
        {phase === "success" && (
          <>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-green-100 mb-4 animate-in zoom-in duration-500">
                <CheckCircle2 className="h-12 w-12 text-green-600" />
              </div>
              <h1 className="text-4xl font-bold text-foreground mb-2">Welcome Aboard!</h1>
              <p className="text-lg text-muted-foreground">Your account has been created successfully</p>
            </div>

            {/* Initial Credits Card */}
            <Card className="shadow-xl border-green-500/50 mb-6 bg-gradient-to-br from-green-50 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-4 bg-green-500 rounded-full">
                    <Sparkles className="h-8 w-8 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-2xl font-bold text-foreground">100 Credits Added!</h3>
                    <p className="text-muted-foreground">Start exploring our platform with your welcome credits</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Verification CTA */}
            <Card className="shadow-xl border-primary/50 bg-gradient-to-br from-primary/5 to-transparent">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <CreditCard className="h-6 w-6 text-primary" />
                  </div>
                  <div className="flex-1">
                    <CardTitle className="text-xl">Unlock Testing Credits</CardTitle>
                    <CardDescription>Complete verification to get 500 additional testing credits</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-background/50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center gap-3 text-sm">
                    <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />
                    <span>Submit GST and business details</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />
                    <span>Get verified within 24 hours</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />
                    <span>Receive 500 testing credits instantly</span>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-3">
                  <Button variant="outline" size="lg" onClick={() => router.push("/")}>
                    Skip for Now
                  </Button>
                  <Button size="lg" onClick={() => setPhase("verification")}>
                    <FileText className="mr-2 h-4 w-4" />
                    Verify Now
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
              <h1 className="text-4xl font-bold text-foreground mb-2">Profile Verification</h1>
              <p className="text-lg text-muted-foreground">Complete verification to unlock 500 testing credits</p>
            </div>

            {/* Progress Indicator */}
            <Card className="mb-6 border-primary/50">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Verification Progress</span>
                  <span className="text-sm text-muted-foreground">Step 2 of 2</span>
                </div>
                <Progress value={100} className="h-2" />
              </CardContent>
            </Card>

            <Card className="shadow-xl border-border/50">
              <CardHeader>
                <CardTitle className="text-2xl">Business Details</CardTitle>
                <CardDescription>Provide your business verification documents</CardDescription>
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
                      onChange={(e) => setVerificationData({ ...verificationData, gstin: e.target.value })}
                      maxLength={15}
                      className="font-mono"
                      required
                    />
                    <p className="text-xs text-muted-foreground">Goods and Services Tax Identification Number</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="panCard">
                      PAN Card <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="panCard"
                      placeholder="Enter PAN number"
                      value={verificationData.panCard}
                      onChange={(e) => setVerificationData({ ...verificationData, panCard: e.target.value })}
                      maxLength={10}
                      className="font-mono uppercase"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="address">
                      Business Address <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id="address"
                      placeholder="Enter complete business address"
                      value={verificationData.address}
                      onChange={(e) => setVerificationData({ ...verificationData, address: e.target.value })}
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
                        onChange={(e) => setVerificationData({ ...verificationData, city: e.target.value })}
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
                        onChange={(e) => setVerificationData({ ...verificationData, state: e.target.value })}
                        required
                      />
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      Your documents will be verified within 24 hours. Once approved, 500 testing credits will be added
                      to your account automatically.
                    </p>
                  </div>

                  <div className="grid md:grid-cols-2 gap-3 pt-4">
                    <Button type="button" variant="outline" size="lg" onClick={() => router.push("/")}>
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
      </div>
    </div>
  )
}
