"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Sparkles, ArrowRight, Home } from "lucide-react";
import { ProtectedRoute } from "@/components/protected-route";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function DealershipUpdateSuccess() {
  const router = useRouter();
  const { checkDealershipSetup } = useAuth();
  const [countdown, setCountdown] = useState(5);

  // Refresh setup status when page loads
  useEffect(() => {
    const refreshStatus = async () => {
      console.log("[Success Page] Refreshing setup status...");
      // Set flag to indicate we just completed setup (for dashboard refresh)
      sessionStorage.setItem("just_completed_setup", "true");
      // Clear any modal dismissal flag since setup might be complete now
      sessionStorage.removeItem("setup_modal_dismissed");
      await checkDealershipSetup();
      // Wait for state to update
      await new Promise((resolve) => setTimeout(resolve, 500));
      console.log("[Success Page] Setup status refreshed");
    };
    refreshStatus();
  }, [checkDealershipSetup]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          router.push("/");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [router]);

  return (
    <ProtectedRoute>
      <div className="min-h-screen py-8">
        <div className="container mx-auto px-4 max-w-2xl">
          <div className="text-center space-y-8">
            {/* Success Icon */}
            <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-green-100 dark:bg-green-900/20 animate-in zoom-in duration-500">
              <CheckCircle2 className="h-16 w-16 text-green-600 dark:text-green-400" />
            </div>

            {/* Success Message */}
            <div className="space-y-4">
              <h1 className="text-4xl md:text-5xl font-bold">
                Dealership Details Updated!
              </h1>
              <p className="text-lg text-muted-foreground max-w-md mx-auto">
                Your dealership information has been successfully updated and
                verified.
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
                    <p className="text-sm text-muted-foreground">
                      Profile verification complete
                    </p>
                    <p className="text-3xl font-bold text-green-600 dark:text-green-400">
                      Verified ✓
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center">
              <Button
                size="lg"
                onClick={() => router.push("/")}
                className="gap-2"
              >
                <Home className="h-5 w-5" />
                Go to Dashboard
                <ArrowRight className="h-5 w-5" />
              </Button>
            </div>

            {/* Auto redirect message */}
            <p className="text-sm text-muted-foreground">
              Redirecting to dashboard in {countdown} seconds...
            </p>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
