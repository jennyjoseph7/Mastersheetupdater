"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Building2, ArrowRight, Shield } from "lucide-react";

interface CompleteSetupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  preventClose?: boolean; // If true, modal cannot be closed without action
}

export function CompleteSetupModal({
  open,
  onOpenChange,
  preventClose = false,
}: CompleteSetupModalProps) {
  const router = useRouter();

  const handleCompleteSetup = () => {
    onOpenChange(false);
    router.push("/dealership/update-details");
  };

  const handleSkip = () => {
    onOpenChange(false);
    // Mark modal as dismissed in this session so it doesn't show again
    sessionStorage.setItem("setup_modal_dismissed", "true");
    // Allow user to continue but they'll see the banner
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(newOpen) => {
        // Prevent closing if preventClose is true
        if (!preventClose || !newOpen) {
          onOpenChange(newOpen);
        }
      }}
    >
      <DialogContent
        className="sm:max-w-[500px]"
        onInteractOutside={(e) => {
          // Prevent closing by clicking outside if preventClose is true
          if (preventClose) {
            e.preventDefault();
          }
        }}
        onEscapeKeyDown={(e) => {
          // Prevent closing with Escape key if preventClose is true
          if (preventClose) {
            e.preventDefault();
          }
        }}
      >
        <DialogHeader>
          <div className="flex items-center justify-center mb-4">
            <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center">
              <Shield className="h-8 w-8 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
          <DialogTitle className="text-2xl text-center">
            Complete Your Dealership Basic Setup
          </DialogTitle>
          <DialogDescription className="text-center pt-2">
            <p className="text-base">
              To unlock all features and create campaigns, please complete your
              dealership profile verification.
            </p>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <div className="flex items-start gap-3">
              <Building2 className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <p className="font-medium">Add Business Details</p>
                <p className="text-sm text-muted-foreground">
                  Complete your dealership information, verification documents,
                  and preferences
                </p>
              </div>
            </div>
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            onClick={handleSkip}
            className="w-full sm:w-auto"
          >
            Skip for Now
          </Button>
          <Button onClick={handleCompleteSetup} className="w-full sm:w-auto">
            Complete Setup
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
