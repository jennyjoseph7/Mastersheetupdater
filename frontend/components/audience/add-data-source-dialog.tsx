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
import { MapFields } from "./steps/map-fields";  
import { PreviewConfirm } from "./steps/preview-confirm";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import type { DataSource } from "@/app/audience/page";
import { startImportTask } from "@/utils/api";

interface AddDataSourceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    dataSource: Omit<DataSource, "id" | "lastSynced" | "status"> & {
      [key: string]: any;
    }
  ) => void;
}

export interface FieldMapping {
  id: string;
  sourceField: string; // From CSV
  targetField: string; // To System
  enabled: boolean;
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
  
  // Headers extracted from the CSV in Step 2
  extractedHeaders: string[]; 
  
  // Mappings created in Step 3
  fieldMappings: FieldMapping[];

  errorCsvUrl?: string;
  taskId?: string; // This is the IMPORT task ID
  taskStatus?: string;
  
  audienceName: string;
  category: string;
  tags: string[];
  sampleData: any[];
  audienceSize: number;
  processedCount?: number;
  errorCount?: number;
}

const steps = [
  { number: 1, title: "Details", completed: false },
  { number: 2, title: "Connection", completed: false },
  { number: 3, title: "Mapping", completed: false },
  { number: 4, title: "Preview", completed: false },
];

export function AddDataSourceDialog({
  isOpen,
  onClose,
  onSave,
}: AddDataSourceDialogProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [isStartingImport, setIsStartingImport] = useState(false);

  const [formData, setFormData] = useState<DataSourceFormData>({
    sourceType: null,
    sourceName: "",
    baseUrl: "",
    authType: "api-key",
    apiKey: "",
    headers: "",
    file: null,
    fileUrl: undefined,
    extractedHeaders: [],
    fieldMappings: [],
    taskId: undefined,
    taskStatus: undefined,
    errorCsvUrl: undefined,
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

  const triggerImportTask = async () => {
    setIsStartingImport(true);
    try {
      // Create a mapping object { "csv_header": "db_field" }
      const mappingPayload: Record<string, string> = {};
      formData.fieldMappings.forEach(m => {
        if (m.enabled && m.sourceField && m.targetField) {
          mappingPayload[m.sourceField] = m.targetField;
        }
      });

      const data = await startImportTask(
        formData.category,
        formData.audienceName,
        formData.fileUrl,
        formData.tags,
        formData.sourceName,
        mappingPayload // Pass the mapping
      );

      const taskId = data.job?.task_id;
      if (!taskId) throw new Error("No Task ID returned");

      updateFormData({ 
        taskId: taskId, 
        taskStatus: "started" 
      });
      
      // Move to next step (Preview)
      setCompletedSteps([...completedSteps, currentStep]);
      setCurrentStep(currentStep + 1);

    } catch (error) {
      console.error("Failed to start import:", error);
      alert("Failed to initiate import task. Please try again.");
    } finally {
      setIsStartingImport(false);
    }
  };

  const handleNext = () => {
    if (currentStep === 3) {
      // If finishing Mapping step, trigger import
      triggerImportTask();
    } else if (currentStep < 4) {
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
    // Only allow clicking strictly previous completed steps to avoid skipping logic
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
        mapping: formData.fieldMappings,
      },
    };
    onSave(dataSource as any);
    handleClose();
  };

  const handleClose = () => {
    setCurrentStep(1);
    setCompletedSteps([]);
    // Reset data ... (simplified for brevity)
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
        // File type: Need file, url, and EXTRACTED HEADERS
        return !!(
          formData.sourceName &&
          formData.file !== null &&
          formData.fileUrl &&
          formData.extractedHeaders.length > 0
        );
      case 3: 
        // Mapping: At least one field enabled and mapped
        return formData.fieldMappings.some(m => m.enabled && m.sourceField && m.targetField);
      case 4:
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
              : currentStep === 2
              ? "Upload & Connection"
              : currentStep === 3
              ? "Map Fields"
              : "Preview & Confirm"}
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
            <MapFields
              formData={formData}
              updateFormData={updateFormData}
            />
          )}
          {currentStep === 4 && (
            <PreviewConfirm
              formData={formData}
              updateFormData={updateFormData}
            />
          )}
        </div>

        <div className="flex items-center justify-between px-6 py-4 border-t bg-muted/30">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 1 || isStartingImport}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          
          <div className="text-sm text-muted-foreground">
            Step {currentStep} of {steps.length}
          </div>

          {currentStep < 4 ? (
            <Button onClick={handleNext} disabled={!isStepValid() || isStartingImport}>
              {isStartingImport && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {currentStep === 3 ? "Import & Preview" : "Continue"}
              {!isStartingImport && <ChevronRight className="h-4 w-4 ml-2" />}
            </Button>
          ) : (
            <Button onClick={handleSave} disabled={formData.taskStatus !== "completed"}>
              {formData.taskStatus === "completed" ? "Save & Connect" : "Processing..."}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}