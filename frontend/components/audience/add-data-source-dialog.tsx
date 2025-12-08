"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Stepper } from "@/components/campaign/stepper";
import { EnterConnectionDetails } from "./steps/enter-connection-details";
// import { MapFields } from "./steps/map-fields"; // Commented out for now
import { AssignAudienceDetails } from "./steps/assign-audience-details";
import { PreviewConfirm } from "./steps/preview-confirm";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import type { DataSource } from "@/app/audience/page";

interface AddDataSourceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    dataSource: Omit<DataSource, "id" | "lastSynced" | "status">
  ) => void;
}

export interface FieldMapping {
  id: string;
  sourceField: string;
  targetField: string;
  enabled: boolean;
}

export interface DataSourceFormData {
  sourceType: "API" | "File" | null;
  sourceName: string;
  // API fields
  baseUrl: string;
  authType: string;
  apiKey: string;
  headers: string;
  // File fields
  file: File | null;
  fileUrl?: string; // <--- Added: Stores the CDN URL after upload
  // Field mapping
  fieldMappings: FieldMapping[];
  // Audience details
  audienceName: string;
  category: string;
  tags: string[];
  // Preview
  sampleData: any[];
  audienceSize: number;
}

const steps = [
  { number: 1, title: "Details", completed: false },
  { number: 2, title: "Connection", completed: false },
  // { number: 3, title: "Map Fields", completed: false }, // Commented out for now
  { number: 3, title: "Preview", completed: false },
];

export function AddDataSourceDialog({
  isOpen,
  onClose,
  onSave,
}: AddDataSourceDialogProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  const [formData, setFormData] = useState<DataSourceFormData>({
    sourceType: null,
    sourceName: "",
    baseUrl: "",
    authType: "api-key",
    apiKey: "",
    headers: "",
    file: null,
    fileUrl: undefined, // <--- Added: Initial state
    fieldMappings: [
      { id: "1", sourceField: "", targetField: "Name", enabled: true },
      { id: "2", sourceField: "", targetField: "Mobile Number", enabled: true },
      { id: "3", sourceField: "", targetField: "Email", enabled: true },
      { id: "4", sourceField: "", targetField: "Language", enabled: true },
      { id: "5", sourceField: "", targetField: "Tags", enabled: true },
    ],
    audienceName: "",
    category: "",
    tags: [],
    sampleData: [],
    audienceSize: 0,
  });

  const updateFormData = (updates: Partial<DataSourceFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const handleNext = () => {
    if (currentStep < 3) {
      setCompletedSteps([...completedSteps, currentStep]);
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleStepClick = (step: number) => {
    if (completedSteps.includes(step) || step === currentStep) {
      setCurrentStep(step);
    }
  };

  const handleSave = () => {
    const dataSource: Omit<DataSource, "id" | "lastSynced" | "status"> = {
      sourceName: formData.sourceName,
      audienceName: formData.audienceName,
      type: formData.sourceType!,
      audienceSize: formData.audienceSize,
    };
    // Note: You might want to pass formData.fileUrl to the onSave handler here as well
    // depending on how your backend expects to receive the file reference.
    onSave(dataSource);
    handleClose();
  };

  const handleClose = () => {
    setCurrentStep(1);
    setCompletedSteps([]);
    setFormData({
      sourceType: null,
      sourceName: "",
      baseUrl: "",
      authType: "api-key",
      apiKey: "",
      headers: "",
      file: null,
      fileUrl: undefined, // <--- Reset state
      fieldMappings: [
        { id: "1", sourceField: "", targetField: "Name", enabled: true },
        {
          id: "2",
          sourceField: "",
          targetField: "Mobile Number",
          enabled: true,
        },
        { id: "3", sourceField: "", targetField: "Email", enabled: true },
        { id: "4", sourceField: "", targetField: "Language", enabled: true },
        { id: "5", sourceField: "", targetField: "Tags", enabled: true },
      ],
      audienceName: "",
      category: "",
      tags: [],
      sampleData: [],
      audienceSize: 0,
    });
    onClose();
  };

  const isStepValid = () => {
    switch (currentStep) {
      case 1:
        return !!(formData.audienceName && formData.category);
      case 2:
        if (formData.sourceType === "API") {
          return !!(formData.sourceName && formData.baseUrl && formData.apiKey);
        }
        // For File type: We need the name, the file object, AND the uploaded URL.
        // This effectively disables the 'Continue' button while uploading.
        return !!(
          formData.sourceName &&
          formData.file !== null &&
          formData.fileUrl
        );
      // case 3: // Map Fields step - commented out
      //   return formData.fieldMappings.some(
      //     (m) => m.enabled && m.sourceField && m.targetField
      //   );
      case 3:
        return true;
      default:
        return false;
    }
  };

  const stepsWithCompletion = steps.map((step) => ({
    ...step,
    completed: completedSteps.includes(step.number),
  }));

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="w-[80%] max-w-none sm:max-w-[80%] max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {currentStep === 1
              ? "Select Category & Add Audience Details"
              : currentStep === 3
              ? "Preview & Confirm Audience Data"
              : "Add Data Source"}
          </DialogTitle>
        </DialogHeader>

        <div className="px-6 py-6 border-b border-border/30">
          <Stepper
            steps={stepsWithCompletion}
            currentStep={currentStep}
            onStepClick={handleStepClick}
          />
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          {currentStep === 1 && (
            <AssignAudienceDetails
              formData={formData}
              updateFormData={updateFormData}
            />
          )}
          {currentStep === 2 && (
            <EnterConnectionDetails
              formData={formData}
              updateFormData={updateFormData}
            />
          )}
          {/* {currentStep === 3 && (
            <MapFields formData={formData} updateFormData={updateFormData} />
          )} */}
          {currentStep === 3 && <PreviewConfirm formData={formData} />}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t bg-muted/30">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 1}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="text-sm text-muted-foreground">
            Step {currentStep} of {steps.length}
          </div>
          {currentStep < 3 ? (
            <Button onClick={handleNext} disabled={!isStepValid()}>
              Continue
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button onClick={handleSave}>Save & Connect</Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
