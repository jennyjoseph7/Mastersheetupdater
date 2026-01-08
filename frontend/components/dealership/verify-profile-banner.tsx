"use client";

import { useRouter } from "next/navigation";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Shield, X, ArrowRight } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";

export function VerifyProfileBanner() {
  const router = useRouter();
  const { isDealershipSetupComplete } = useAuth();
  const [dismissed, setDismissed] = useState(false);

  // Don't show if setup is complete or banner is dismissed
  // Explicitly check for true to hide the banner
  if (dismissed) {
    return null;
  }

  // Hide if setup is complete (true)
  if (isDealershipSetupComplete === true) {
    console.log("[VerifyProfileBanner] Setup is complete, hiding banner");
    return null;
  }

  // Don't show if setup status is still loading (null means not checked yet)
  if (isDealershipSetupComplete === null) {
    console.log("[VerifyProfileBanner] Status is null (loading), hiding banner");
    return null;
  }

  // Also check localStorage as a fallback
  const cachedStatus = localStorage.getItem("dealership_setup_complete");
  if (cachedStatus === "true") {
    console.log("[VerifyProfileBanner] Cached status is true, hiding banner");
    return null;
  }

  // Only show if setup is explicitly false (incomplete)
  // This means setup has been checked and is incomplete
  if (isDealershipSetupComplete !== false) {
    return null;
  }
  
  console.log("[VerifyProfileBanner] Setup is incomplete, showing banner");

  return (
    <Alert className="border-amber-500/50 bg-amber-50 dark:bg-amber-950/20 mb-6">
      <Shield className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      <AlertDescription className="flex items-center justify-between gap-4">
        <div className="flex-1">
          <p className="font-medium text-amber-900 dark:text-amber-100">
            Verify Your Profile
          </p>
          <p className="text-sm text-amber-800 dark:text-amber-200 mt-1">
            Complete your dealership setup to unlock campaign creation and all
            features.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={() => router.push("/dealership/update-details")}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            Complete Setup
            <ArrowRight className="ml-2 h-3 w-3" />
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setDismissed(true)}
            className="h-8 w-8 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}
