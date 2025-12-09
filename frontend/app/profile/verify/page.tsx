"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { ProtectedRoute } from "@/components/protected-route"
import { useAuth } from "@/lib/auth-context"
import { CheckCircle2, ArrowLeft, ShieldCheck, Clock, Sparkles, Building2, CreditCard } from "lucide-react"
import Link from "next/link"

export default function ProfileVerification() {
  const router = useRouter()
  const { user, updateVerificationStatus, updateCredits } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [verificationData, setVerificationData] = useState({
    gstin: "",
    panCard: "",
    address: "",
    city: "",
    state: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setIsLoading(true)

    try {
      const response = await fetch("/api/dealer/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: user?.email,
          ...verificationData,
        }),
      })

      if (!response.ok) {
        throw new Error("Verification submission failed")
      }

      // Update verification status
      updateVerificationStatus(true, "pending")
      // Add credits immediately for demo purposes
      if (user) {
        updateCredits(user.credits + 500)
      }

      router.push("/profile/verify/success")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen py-8">
        <div className="container mx-auto px-4 max-w-3xl">
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
              <ShieldCheck className="h-8 w-8 text-primary" />
            </div>
            <h1 className="text-4xl font-bold mb-2">Profile Verification</h1>
            <p className="text-lg text-muted-foreground">
              Complete verification to unlock 500 testing credits and premium features
            </p>
          </div>

          {/* Benefits Banner */}
          <Card className="mb-6 border-primary/50 bg-gradient-to-br from-primary/5 to-transparent shadow-lg">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 mb-4">
                <Sparkles className="h-6 w-6 text-primary" />
                <h3 className="text-xl font-bold">Verification Benefits</h3>
              </div>
              <div className="grid md:grid-cols-3 gap-4">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-sm">500 Credits</p>
                    <p className="text-xs text-muted-foreground">Additional testing credits</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-sm">24hr Approval</p>
                    <p className="text-xs text-muted-foreground">Fast verification process</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-sm">Premium Access</p>
                    <p className="text-xs text-muted-foreground">Enhanced features</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Progress Indicator */}
          <Card className="mb-6">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Verification Progress</span>
                <Badge variant="outline">Step 1 of 1</Badge>
              </div>
              <Progress value={100} className="h-2" />
            </CardContent>
          </Card>

          {/* Verification Form */}
          <Card className="shadow-xl">
            <CardHeader>
              <CardTitle className="text-2xl">Business Verification Details</CardTitle>
              <CardDescription>Provide your business documents for verification</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                {/* GSTIN */}
                <div className="space-y-2">
                  <Label htmlFor="gstin" className="flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
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

                {/* PAN Card */}
                <div className="space-y-2">
                  <Label htmlFor="panCard" className="flex items-center gap-2">
                    <CreditCard className="h-4 w-4" />
                    PAN Card <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="panCard"
                    placeholder="Enter PAN number"
                    value={verificationData.panCard}
                    onChange={(e) =>
                      setVerificationData({ ...verificationData, panCard: e.target.value.toUpperCase() })
                    }
                    maxLength={10}
                    className="font-mono uppercase"
                    required
                  />
                </div>

                {/* Business Address */}
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

                {/* City & State */}
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

                {/* Info Alert */}
                <Alert className="bg-blue-50 border-blue-200 dark:bg-blue-950/20 dark:border-blue-800">
                  <Clock className="h-4 w-4 text-blue-600" />
                  <AlertDescription className="text-sm text-blue-800 dark:text-blue-200">
                    Your documents will be verified within 24 hours. Once approved, 500 testing credits will be added to
                    your account automatically.
                  </AlertDescription>
                </Alert>

                {/* Submit Button */}
                <Button type="submit" size="lg" className="w-full" disabled={isLoading}>
                  {isLoading ? (
                    "Submitting..."
                  ) : (
                    <>
                      <CheckCircle2 className="mr-2 h-5 w-5" />
                      Submit for Verification
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}
