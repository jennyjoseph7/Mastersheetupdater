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
import { AssignAudienceDetails } from "./steps/assign-audience-details";
import { PreviewConfirm } from "./steps/preview-confirm";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { DataSource } from "@/app/audience/page";

interface AddDataSourceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    dataSource: Omit<DataSource, "id" | "lastSynced" | "status"> & {
      [key: string]: any;
    }
  ) => void;
}

export interface DataSourceFormData {
  sourceType: "API" | "File" | null;
  sourceName: string;
  baseUrl: string;
  authType: string;
  apiKey: string;
  headers: string;
  file: File | null;
  fileUrl?: string;
  errorCsvUrl?: string;
  taskId?: string;
  taskStatus?: string;
  fieldMappings: any[];
  audienceName: string;
  category: string;
  tags: string[];
  sampleData: any[];
  audienceSize: number;
  // Added specific counters
  processedCount?: number;
  errorCount?: number;
}

const steps = [
  { number: 1, title: "Details", completed: false },
  { number: 2, title: "Connection", completed: false },
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
    fileUrl: undefined,
    taskId: undefined,
    taskStatus: undefined,
    errorCsvUrl: undefined,
    fieldMappings: [],
    audienceName: "",
    category: "",
    tags: [],
    sampleData: [],
    audienceSize: 0,
    processedCount: 0,
    errorCount: 0,
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
    const dataSource = {
      sourceName: formData.sourceName,
      audienceName: formData.audienceName,
      type: formData.sourceType!,
      audienceSize: formData.audienceSize,
      category: formData.category,
      tags: formData.tags,
      connectionDetails: {
        fileUrl: formData.fileUrl,
        errorCsvUrl: formData.errorCsvUrl,
        taskId: formData.taskId,
        baseUrl: formData.baseUrl,
        authType: formData.authType,
        apiKey: formData.apiKey,
        headers: formData.headers,
      },
    };
    onSave(dataSource as any);
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
      fileUrl: undefined,
      taskId: undefined,
      taskStatus: undefined,
      errorCsvUrl: undefined,
      fieldMappings: [],
      audienceName: "",
      category: "",
      tags: [],
      sampleData: [],
      audienceSize: 0,
      processedCount: 0,
      errorCount: 0,
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
        return !!(
          formData.sourceName &&
          formData.file !== null &&
          formData.fileUrl &&
          (formData.audienceSize > 0 || formData.errorCsvUrl || formData.taskId)
        );
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
          {currentStep === 3 && (
            <PreviewConfirm
              formData={formData}
              updateFormData={updateFormData} // <--- Added this prop
            />
          )}
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
            <Button onClick={handleSave} disabled={formData.taskStatus !== "completed"}>
              {/* Disable Save until processing completes */}
              {formData.taskStatus === "completed" ? "Save & Connect" : "Processing..."}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}