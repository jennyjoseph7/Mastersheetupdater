"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { CheckCircle2, Sparkles, ArrowRight, Home } from "lucide-react"
import { ProtectedRoute } from "@/components/protected-route"
import { useAuth } from "@/lib/auth-context"

export default function VerificationSuccess() {
  const router = useRouter()
  const { user } = useAuth()
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          router.push("/")
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [router])

  return (
    <ProtectedRoute>
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-2xl w-full text-center space-y-8">
          {/* Success Icon */}
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-100 dark:bg-green-900/20 animate-in zoom-in duration-500">
            <CheckCircle2 className="h-16 w-16 text-green-600 dark:text-green-400" />
          </div>

          {/* Success Message */}
          <div className="space-y-4">
            <h1 className="text-4xl md:text-5xl font-bold">Verification Submitted!</h1>
            <p className="text-lg text-muted-foreground max-w-md mx-auto">
              Your verification documents have been submitted successfully. We'll review them within 24 hours.
            </p>
          </div>

          {/* Credits Card */}
          <Card className="max-w-md mx-auto border-green-500/50 bg-gradient-to-br from-green-50 to-transparent dark:from-green-950/20 shadow-lg">
            <CardContent className="pt-6">
              <div className="flex items-center justify-center gap-4">
                <div className="p-4 bg-green-500 rounded-full">
                  <Sparkles className="h-8 w-8 text-white" />
                </div>
                <div className="text-left">
                  <p className="text-sm text-muted-foreground">Credits to be added</p>
                  <p className="text-3xl font-bold text-green-600 dark:text-green-400">+500 Credits</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
            <Button size="lg" onClick={() => router.push("/")} className="gap-2">
              <Home className="h-5 w-5" />
              Go to Dashboard
              <ArrowRight className="h-5 w-5" />
            </Button>
          </div>

          {/* Auto redirect message */}
          <p className="text-sm text-muted-foreground">Redirecting to dashboard in {countdown} seconds...</p>
        </div>
      </div>
    </ProtectedRoute>
  )
}
