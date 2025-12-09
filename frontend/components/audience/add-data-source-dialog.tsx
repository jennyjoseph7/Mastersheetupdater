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
// Import the new createAudienceTask function
import { startImportTask, createAudienceTask } from "@/utils/api";

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
  sourceField: string;
  targetField: string;
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
  extractedHeaders: string[]; 
  fieldMappings: FieldMapping[];
  errorCsvUrl?: string;
  taskId?: string; 
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
      // 1. Prepare Mapping
      const mappingPayload: Record<string, string> = {};
      formData.fieldMappings.forEach(m => {
        if (m.enabled && m.sourceField && m.targetField) {
          mappingPayload[m.sourceField] = m.targetField;
        }
      });

      // 2. Start Import Task
      const data = await startImportTask(
        formData.category,
        formData.audienceName,
        formData.fileUrl,
        formData.tags,
        formData.sourceName,
        mappingPayload
      );

      const taskId = data.job?.task_id;
      if (!taskId) throw new Error("No Task ID returned");

      // 3. Create Audience Task Record in DB
      // We use the same campaign_id as used in startImportTask (hardcoded in api.js)
      const campaignId = "74f260b8-e8dc-3c52-ab8d-31bd0fc49943"; 

      await createAudienceTask({
        task_id: taskId,
        campaign_type: formData.category,
        campaign_objective_id: campaignId, // Using Campaign ID as placeholder for Objective ID
        campaign_id: campaignId,
        audience_name: formData.audienceName,
        tags: formData.tags || [],
        csv_file_url: formData.fileUrl,
        error_csv_link: "", // Will be updated later if errors occur
        field_mapping: formData.fieldMappings.map(m => ({
          source_field: m.sourceField,
          target_field: m.targetField,
          enabled: m.enabled
        })),
        source_name: formData.sourceName || "Uploaded via csv",
        source_type: formData.sourceType || "File",
        csv_status: "pending"
      });

      // 4. Update State & Move to Next Step
      updateFormData({ 
        taskId: taskId, 
        taskStatus: "started" 
      });
      
      setCompletedSteps([...completedSteps, currentStep]);
      setCurrentStep(currentStep + 1);

    } catch (error) {
      console.error("Failed to start import or create task record:", error);
      alert("Failed to initiate import task. Please try again.");
    } finally {
      setIsStartingImport(false);
    }
  };

  const handleNext = () => {
    if (currentStep === 3) {
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
    if (completedSteps.includes(step) || step === currentStep) {
      setCurrentStep(step);
    }
  };

  const handleSave = () => {
    // Just pass basic info back to parent, the real data is already in the DB via createAudienceTask
    const dataSource = {
      sourceName: formData.sourceName,
      audienceName: formData.audienceName,
      type: formData.sourceType!,
      audienceSize: formData.audienceSize,
      category: formData.category,
      tags: formData.tags,
      connectionDetails: {
        taskId: formData.taskId,
      },
    };
    onSave(dataSource as any);
    handleClose();
  };

  const handleClose = () => {
    setCurrentStep(1);
    setCompletedSteps([]);
    // Reset data logic...
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
          formData.extractedHeaders.length > 0
        );
      case 3: 
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