"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ChevronLeft, ChevronRight, Upload, X, FileText } from "lucide-react"
import { cn } from "@/lib/utils"
import * as XLSX from "xlsx"

interface UploadAudienceDialogProps {
  isOpen: boolean
  onClose: () => void
  onSave: (audienceData: AudienceData) => void
}

export interface AudienceData {
  file: File | null
  fileName: string
  contactCount: number
  fieldMappings: {
    name: string
    email: string
    phone: string
    company: string
    city: string
  }
  audienceName: string
  category: string
}

const categories = [
  { value: "general", label: "General Customers" },
  { value: "premium", label: "Premium Leads" },
  { value: "test", label: "Test Audience" },
  { value: "vip", label: "VIP Customers" },
  { value: "inactive", label: "Inactive Users" },
]

export function UploadAudienceDialog({ isOpen, onClose, onSave }: UploadAudienceDialogProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<AudienceData>({
    file: null,
    fileName: "",
    contactCount: 0,
    fieldMappings: {
      name: "",
      email: "",
      phone: "",
      company: "",
      city: "",
    },
    audienceName: "",
    category: "",
  })

  const updateFormData = (updates: Partial<AudienceData>) => {
    setFormData((prev) => ({ ...prev, ...updates }))
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return;

    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    let finalFile = file;

    if (fileExtension === 'xls' || fileExtension === 'xlsx') {
      try {
        const data = await file.arrayBuffer();
        const workbook = XLSX.read(data);
        const worksheet = workbook.Sheets[workbook.SheetNames[0]];
        const csvContent = XLSX.utils.sheet_to_csv(worksheet);
        
        const csvBlob = new Blob([csvContent], { type: 'text/csv' });
        const csvFileName = file.name.replace(/\.(xls|xlsx)$/i, '.csv');
        finalFile = new File([csvBlob], csvFileName, { type: 'text/csv' });
      } catch (error) {
        console.error("Excel conversion error:", error);
      }
    }

    // Simulate contact count (in real app, parse CSV)
    const mockContactCount = Math.floor(Math.random() * 5000) + 100
    updateFormData({
      file: finalFile,
      fileName: finalFile.name,
      contactCount: mockContactCount,
    })
  }

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSave = () => {
    onSave(formData)
    handleClose()
  }

  const handleClose = () => {
    setCurrentStep(1)
    setFormData({
      file: null,
      fileName: "",
      contactCount: 0,
      fieldMappings: {
        name: "",
        email: "",
        phone: "",
        company: "",
        city: "",
      },
      audienceName: "",
      category: "",
    })
    onClose()
  }

  const isStepValid = () => {
    switch (currentStep) {
      case 1:
        return formData.file !== null
      case 2:
        return formData.fieldMappings.name && formData.fieldMappings.email && formData.fieldMappings.phone
      case 3:
        return formData.audienceName && formData.category
      case 4:
        return true
      default:
        return false
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle>Upload Audience – Step {currentStep} of 4</DialogTitle>
              <DialogDescription className="mt-1">
                {currentStep === 1 && "Add your audience data to target specific customers."}
                {currentStep === 2 && "Map your CSV or Excel columns to the required fields."}
                {currentStep === 3 && "Name and categorize your audience."}
                {currentStep === 4 && "Review your audience configuration."}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {/* Stepper */}
        <div className="flex items-center justify-center gap-2 py-4 border-b">
          {[1, 2, 3, 4].map((step) => (
            <div key={step} className="flex items-center">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors",
                  step === currentStep
                    ? "bg-primary text-primary-foreground"
                    : step < currentStep
                      ? "bg-primary/20 text-primary"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {step}
              </div>
              {step < 4 && <div className="w-12 h-0.5 bg-muted mx-1" />}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Step 1: Upload CSV */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="border-2 border-dashed rounded-lg p-12 text-center hover:border-primary/50 transition-colors">
                <Upload className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-sm font-medium mb-2">Upload CSV or Excel File</p>
                <p className="text-xs text-muted-foreground mb-4">Drag and drop or click to upload (Max 10MB)</p>
                <Input type="file" accept=".csv,.xls,.xlsx" onChange={handleFileUpload} className="hidden" id="csv-upload" />
                <Button variant="outline" size="sm" onClick={() => document.getElementById("csv-upload")?.click()}>
                  Choose File
                </Button>
              </div>
              {formData.file && (
                <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
                  <FileText className="h-5 w-5 text-primary" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">{formData.fileName}</p>
                    <p className="text-xs text-muted-foreground">{formData.contactCount.toLocaleString()} contacts</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => updateFormData({ file: null, fileName: "", contactCount: 0 })}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Map Data Fields */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="map-name">
                    Name <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={formData.fieldMappings.name}
                    onValueChange={(value) =>
                      updateFormData({
                        fieldMappings: { ...formData.fieldMappings, name: value },
                      })
                    }
                  >
                    <SelectTrigger id="map-name">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="first_name">First Name</SelectItem>
                      <SelectItem value="full_name">Full Name</SelectItem>
                      <SelectItem value="customer_name">Customer Name</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="map-email">
                    Email <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={formData.fieldMappings.email}
                    onValueChange={(value) =>
                      updateFormData({
                        fieldMappings: { ...formData.fieldMappings, email: value },
                      })
                    }
                  >
                    <SelectTrigger id="map-email">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="email">Email Address</SelectItem>
                      <SelectItem value="email_id">Email ID</SelectItem>
                      <SelectItem value="contact_email">Contact Email</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="map-phone">
                    Phone <span className="text-destructive">*</span>
                  </Label>
                  <Select
                    value={formData.fieldMappings.phone}
                    onValueChange={(value) =>
                      updateFormData({
                        fieldMappings: { ...formData.fieldMappings, phone: value },
                      })
                    }
                  >
                    <SelectTrigger id="map-phone">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="phone">Phone Number</SelectItem>
                      <SelectItem value="mobile">Mobile</SelectItem>
                      <SelectItem value="contact_number">Contact Number</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="map-company">Company</Label>
                  <Select
                    value={formData.fieldMappings.company}
                    onValueChange={(value) =>
                      updateFormData({
                        fieldMappings: { ...formData.fieldMappings, company: value },
                      })
                    }
                  >
                    <SelectTrigger id="map-company">
                      <SelectValue placeholder="Select column (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="company">Company</SelectItem>
                      <SelectItem value="organization">Organization</SelectItem>
                      <SelectItem value="business_name">Business Name</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="map-city">City</Label>
                  <Select
                    value={formData.fieldMappings.city}
                    onValueChange={(value) =>
                      updateFormData({
                        fieldMappings: { ...formData.fieldMappings, city: value },
                      })
                    }
                  >
                    <SelectTrigger id="map-city">
                      <SelectValue placeholder="Select column (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="city">City</SelectItem>
                      <SelectItem value="location">Location</SelectItem>
                      <SelectItem value="address_city">Address City</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Audience Configuration */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="audience-name">
                  Audience Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="audience-name"
                  placeholder="e.g., Q1 2025 Leads"
                  value={formData.audienceName}
                  onChange={(e) => updateFormData({ audienceName: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">
                  Category <span className="text-destructive">*</span>
                </Label>
                <Select value={formData.category} onValueChange={(value) => updateFormData({ category: value })}>
                  <SelectTrigger id="category">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  This helps organize your audiences for better campaign targeting.
                </p>
              </div>
            </div>
          )}

          {/* Step 4: Preview & Confirm */}
          {currentStep === 4 && (
            <div className="space-y-6">
              <div className="space-y-3">
                <h4 className="font-semibold text-sm">File Summary</h4>
                <div className="bg-muted rounded-lg p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">File Name:</span>
                    <span className="font-medium">{formData.fileName}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Contact Count:</span>
                    <span className="font-medium">{formData.contactCount.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="font-semibold text-sm">Audience Details</h4>
                <div className="bg-muted rounded-lg p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Audience Name:</span>
                    <span className="font-medium">{formData.audienceName}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Category:</span>
                    <span className="font-medium">{categories.find((c) => c.value === formData.category)?.label}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <h4 className="font-semibold text-sm">Field Mapping Summary</h4>
                <div className="bg-muted rounded-lg p-4 space-y-2">
                  {formData.fieldMappings.name && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Name:</span>
                      <span className="font-medium">{formData.fieldMappings.name}</span>
                    </div>
                  )}
                  {formData.fieldMappings.email && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Email:</span>
                      <span className="font-medium">{formData.fieldMappings.email}</span>
                    </div>
                  )}
                  {formData.fieldMappings.phone && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Phone:</span>
                      <span className="font-medium">{formData.fieldMappings.phone}</span>
                    </div>
                  )}
                  {formData.fieldMappings.company && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Company:</span>
                      <span className="font-medium">{formData.fieldMappings.company}</span>
                    </div>
                  )}
                  {formData.fieldMappings.city && (
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">City:</span>
                      <span className="font-medium">{formData.fieldMappings.city}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t bg-muted/30">
          <Button variant="outline" onClick={handlePrevious} disabled={currentStep === 1}>
            <ChevronLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div className="text-sm text-muted-foreground">Step {currentStep} of 4</div>
          {currentStep < 4 ? (
            <Button onClick={handleNext} disabled={!isStepValid()}>
              Next
              <ChevronRight className="h-4 w-4 ml-2" />
            </Button>
          ) : (
            <Button onClick={handleSave}>Complete Setup</Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
