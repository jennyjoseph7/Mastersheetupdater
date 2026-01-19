// audience/add-data-source-dialog.tsx
"use client";

import { useState, useEffect } from "react";
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
import { startImportTask, createAudienceTask, updateAudienceTask } from "@/utils/api";

// NEW PROP: prefilledData
interface AddDataSourceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    dataSource: Omit<DataSource, "id" | "lastSynced" | "status"> & {
      [key: string]: any;
    }
  ) => void;
  prefilledData?: {
    category?: string;
    objectiveId?: string;
    campaignId?: string;
  };
}

export interface FieldMapping {
  id: string;
  sourceField: string;
  targetField: string;
  enabled: boolean;
}

export interface DataSourceFormData {
  sourceType: "API" | "csv" | null;
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
  audienceTaskId?: string; // [Changed] Added to store DB ID
  audienceName: string;
  category: string;
  campaignObjectiveId?: string;
  campaignId?: string; // Storing the draft campaign ID
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
  prefilledData, // Destructure prop
}: AddDataSourceDialogProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [isStartingImport, setIsStartingImport] = useState(false);
  const [isSaving, setIsSaving] = useState(false); // [Changed] Added saving state

  // Initialize with prefilled data
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
    audienceTaskId: undefined, // [Changed] Initialize
    errorCsvUrl: undefined,
    audienceName: "",
    category: prefilledData?.category || "",
    campaignObjectiveId: prefilledData?.objectiveId || "",
    campaignId: prefilledData?.campaignId || "", // Initialize with draft ID
    tags: [],
    sampleData: [],
    audienceSize: 0,
    processedCount: 0,
    errorCount: 0,
  });

  // Re-sync props if dialog is reused without unmounting
  useEffect(() => {
    if (isOpen && prefilledData) {
        setFormData(prev => ({
            ...prev,
            category: prefilledData.category || prev.category,
            campaignObjectiveId: prefilledData.objectiveId || prev.campaignObjectiveId,
            campaignId: prefilledData.campaignId || prev.campaignId,
        }));
    }
  }, [isOpen, prefilledData]);

  const updateFormData = (updates: Partial<DataSourceFormData>) => {
    setFormData((prev) => ({ ...prev, ...updates }));
  };

  const triggerImportTask = async () => {
    setIsStartingImport(true);
    try {
      const mappingPayload: Record<string, string> = {};
      formData.fieldMappings.forEach(m => {
        if (m.enabled && m.sourceField && m.targetField) {
          mappingPayload[m.sourceField] = m.targetField;
        }
      });

      // Use the prefilled Draft Campaign ID if available, otherwise fallback to Objective ID
      const targetCampaignId = formData.campaignId || formData.campaignObjectiveId;
      
      const data = await startImportTask(
        formData.category,
        formData.audienceName,
        formData.fileUrl,
        formData.tags,
        formData.sourceName,
        mappingPayload,
        targetCampaignId 
      );

      const taskId = data.job?.task_id;
      if (!taskId) throw new Error("No Task ID returned");

      // [Changed] Capture response to get the DB ID
      const newTask = await createAudienceTask({
        task_id: taskId,
        campaign_type: formData.category,
        campaign_objective_id: formData.campaignObjectiveId, 
        campaign_id: targetCampaignId,
        campaign_objective_name: "",
        audience_name: formData.audienceName,
        tags: formData.tags || [],
        csv_file_url: formData.fileUrl,
        error_csv_link: "", 
        field_mapping: formData.fieldMappings.map(m => ({
          source_field: m.sourceField,
          target_field: m.targetField,
          enabled: m.enabled
        })),
        source_name: formData.sourceName || "Uploaded via csv",
        source_type: formData.sourceType || "csv",
        csv_status: "pending"
      });

      // [Changed] Store audienceTaskId
      updateFormData({ 
        taskId: taskId, 
        taskStatus: "started",
        audienceTaskId: newTask?.audience_task_id || newTask?._id || newTask?.id
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

  // [Changed] Updated handleSave to call updateAudienceTask
  const handleSave = async () => {
    setIsSaving(true);
    
    // Update status and size in DB
    if (formData.audienceTaskId) {
      try {
        await updateAudienceTask(formData.audienceTaskId, {
          csv_status: "connected",
          audience_size: formData.audienceSize,
          process_size: formData.processedCount
        });
      } catch (error) {
        console.error("Failed to update audience task status:", error);
        // Optional: Show an error toast here
      }
    }

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
    setIsSaving(false);
    handleClose();
  };

  const handleClose = () => {
    setCurrentStep(1);
    setCompletedSteps([]);
    onClose();
  };

  const isStepValid = () => {
    switch (currentStep) {
      case 1:
        return !!(formData.audienceName && formData.category && formData.campaignObjectiveId);
      case 2:
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

  const isPrefilled = !!(prefilledData?.category && prefilledData?.objectiveId);

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="w-[80%] max-w-none sm:max-w-[80%] max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {currentStep === 1
              ? (isPrefilled ? "Add Audience Details" : "Select Category & Add Audience Details")
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
              isPrefilled={isPrefilled} 
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
            disabled={currentStep === 1 || isStartingImport || isSaving}
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
            <Button onClick={handleSave} disabled={formData.taskStatus !== "completed" || isSaving}>
              {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {formData.taskStatus === "completed" 
                ? (isSaving ? "Saving..." : "Save & Connect") 
                : "Processing..."}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}