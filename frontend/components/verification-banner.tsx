"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { CheckCircle2, ShieldCheck, X, Sparkles, ArrowRight } from "lucide-react"
import { useAuth } from "@/lib/auth-context"

interface VerificationBannerProps {
  variant?: "inline" | "floating" | "compact"
  showDismiss?: boolean
}

export function VerificationBanner({ variant = "inline", showDismiss = true }: VerificationBannerProps) {
  const { user } = useAuth()
  const router = useRouter()
  const [isDismissed, setIsDismissed] = useState(false)

  // Don't show if user is already verified or banner is dismissed
  if (!user || user.isVerified || isDismissed) {
    return null
  }

  const handleVerifyClick = () => {
    router.push("/profile/verify")
  }

  if (variant === "compact") {
    return (
      <div className="flex items-center justify-between gap-4 px-4 py-2.5 bg-gradient-to-r from-amber-50/80 to-orange-50/80 dark:from-amber-950/30 dark:to-orange-950/30 border border-amber-300/70 dark:border-amber-800/70 rounded-lg shadow-sm">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="p-1.5 bg-amber-500/10 dark:bg-amber-500/20 rounded-md shrink-0">
            <ShieldCheck className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2 min-w-0 flex-1">
            <span className="text-sm font-semibold text-amber-900 dark:text-amber-100">
              Verify your profile
            </span>
            <span className="hidden sm:inline text-amber-600 dark:text-amber-400">•</span>
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs text-amber-700 dark:text-amber-300">
                Unlock <span className="font-bold text-amber-800 dark:text-amber-200">+500 credits</span>
              </span>
              <span className="hidden sm:inline text-xs text-amber-600 dark:text-amber-400">•</span>
              <span className="hidden sm:inline text-xs text-amber-700 dark:text-amber-300">
                Fast 24h approval
              </span>
            </div>
          </div>
        </div>
        <Button
          size="sm"
          onClick={handleVerifyClick}
          className="h-8 rounded-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 text-xs px-4 font-medium shadow-sm shrink-0"
        >
          Verify Now
          <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
        </Button>
      </div>
    )
  }

  if (variant === "floating") {
    return (
      <div className="fixed bottom-4 right-4 z-50 max-w-md animate-in slide-in-from-bottom-4 duration-500">
        <Alert className="shadow-2xl border-2 border-primary/20 bg-gradient-to-br from-background to-primary/5">
          {showDismiss && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-2 top-2 h-6 w-6"
              onClick={() => setIsDismissed(true)}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
          <Sparkles className="h-5 w-5 text-primary" />
          <AlertTitle className="text-lg font-bold mb-2">Unlock Testing Credits!</AlertTitle>
          <AlertDescription className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Complete profile verification and get 500 additional credits for testing campaigns.
            </p>
            <div className="flex items-center gap-2">
              <Button onClick={handleVerifyClick} size="sm" className="w-full">
                Start Verification
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  // Default inline variant
  return (
    <Alert className="border-2 border-amber-500/60 bg-gradient-to-r from-amber-50 via-orange-50 to-rose-50 dark:from-amber-950/20 dark:via-orange-950/20 dark:to-rose-950/20 shadow-lg rounded-xl">
      {showDismiss && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-2 top-2 h-7 w-7"
          onClick={() => setIsDismissed(true)}
        >
          <X className="h-4 w-4" />
        </Button>
      )}
      <div className="flex items-start gap-3">
        <div className="p-2.5 bg-amber-500 rounded-lg shrink-0 shadow-sm">
          <ShieldCheck className="h-5 w-5 text-white" />
        </div>
        <div className="flex-1">
          <AlertTitle className="text-xl font-bold text-amber-900 dark:text-amber-200 mb-2 flex items-center gap-2">
            Complete Your Profile Verification
            <span className="ml-1 inline-flex items-center rounded-full bg-amber-600/10 px-2 py-0.5 text-[11px] font-semibold text-amber-700 dark:text-amber-200 ring-1 ring-amber-600/20">
              +500 credits
            </span>
          </AlertTitle>
          <AlertDescription className="space-y-3">
            <p className="text-[0.925rem] text-amber-800 dark:text-amber-300 leading-relaxed">
              Unlock premium features and earn 500 additional testing credits by completing your profile verification.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-1.5 rounded-full bg-white/70 dark:bg-amber-900/30 px-3 py-1 text-[12px] text-amber-900 dark:text-amber-200 ring-1 ring-amber-300/60">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Fast approval within 24 hours</span>
              </div>
              <div className="inline-flex items-center gap-1.5 rounded-full bg-white/70 dark:bg-amber-900/30 px-3 py-1 text-[12px] text-amber-900 dark:text-amber-200 ring-1 ring-amber-300/60">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>500 testing credits</span>
              </div>
              <div className="inline-flex items-center gap-1.5 rounded-full bg-white/70 dark:bg-amber-900/30 px-3 py-1 text-[12px] text-amber-900 dark:text-amber-200 ring-1 ring-amber-300/60">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Enhanced features</span>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
              <Button
                onClick={handleVerifyClick}
                className="mt-2 h-10 rounded-full bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-700 hover:to-orange-700 shadow-md shadow-amber-200/50 px-5"
              >
                Verify Profile Now
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <span className="mt-2 sm:mt-0 text-xs text-amber-700/80 dark:text-amber-200/80">
                Takes ~2 minutes
              </span>
            </div>
          </AlertDescription>
        </div>
      </div>
    </Alert>
  )
}

export default VerificationBanner
