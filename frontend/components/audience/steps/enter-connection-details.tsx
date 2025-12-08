"use client"

import type React from "react"
import { useState, useRef } from "react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent } from "@/components/ui/card"
import { Upload, FileText, X, AlertCircle, Loader2, CheckCircle2 } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DataSourceFormData } from "../add-data-source-dialog"

// Defined based on your JSON response
interface GrydFileUploadResponse {
  cdn_url: string
  file_id: string
  file_name: string
  // ... other fields if needed
}

interface EnterConnectionDetailsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

export function EnterConnectionDetails({ formData, updateFormData }: EnterConnectionDetailsProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [jsonError, setJsonError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // --- API Upload Logic ---
  const uploadFileToGryd = async (file: File) => {
    setIsUploading(true)

    const uploadData = new FormData()
    uploadData.append("file", file)

    try {
      const response = await fetch("https://file-prod.gryd.in/media/document", {
        method: "POST",
        headers: {
          "X-I2CE-ENTERPRISE-ID": "gryd_file_system",
          "X-I2CE-USER-ID": "abhishek+file-gryd@iamdave.ai",
          "X-I2CE-API-KEY": "4bd3fe53-02bf-3918-8e27-53095dd0e32b",
          // Note: Do NOT set Content-Type here; fetch sets it automatically with the boundary for FormData
        },
        body: uploadData,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const data: GrydFileUploadResponse = await response.json()

      // Success: Store the File object (for display) AND the cdn_url (for logic)
      updateFormData({ 
        file: file, 
        fileUrl: data.cdn_url // We assume your form data interface has this field
      })

    } catch (error) {
      console.error("Upload error:", error)
      alert("Failed to upload file. Please try again.")
      updateFormData({ file: null, fileUrl: undefined })
    } finally {
      setIsUploading(false)
    }
  }

  // --- File Event Handlers ---
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      uploadFileToGryd(file)
    }
    e.target.value = "" // Reset input
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    if (!isUploading) setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    if (isUploading) return

    const file = e.dataTransfer.files?.[0]
    // Validate CSV
    if (file && (file.type === "text/csv" || file.name.endsWith(".csv"))) {
      uploadFileToGryd(file)
    } else {
      alert("Please upload a valid CSV file.")
    }
  }

  const removeFile = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    // Clear both the file object and the uploaded URL
    updateFormData({ file: null, fileUrl: undefined })
  }

  // --- JSON Validation Logic (Existing) ---
  const handleHeadersChange = (value: string) => {
    updateFormData({ headers: value })
    if (!value.trim()) {
      setJsonError(null); return
    }
    try {
      JSON.parse(value)
      setJsonError(null)
    } catch (e) {
      setJsonError("Invalid JSON format")
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Enter Connection Details</h3>
        <p className="text-sm text-muted-foreground">
          {formData.sourceType === "API"
            ? "Provide the API credentials and endpoint information"
            : "Upload your CSV file with audience data"}
        </p>
      </div>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="sourceName">Source Name *</Label>
          <Input
            id="sourceName"
            placeholder={formData.sourceType === "API" ? "e.g., Salesforce, HubSpot" : "e.g., Q4 Leads CSV"}
            value={formData.sourceName}
            onChange={(e) => updateFormData({ sourceName: e.target.value })}
          />
        </div>

        {formData.sourceType === "API" ? (
          /* API FORM FIELDS (Unchanged) */
          <>
            <div className="space-y-2">
              <Label htmlFor="baseUrl">Base URL *</Label>
              <Input
                id="baseUrl"
                placeholder="https://api.example.com/v1"
                value={formData.baseUrl}
                onChange={(e) => updateFormData({ baseUrl: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="authType">Authentication Type *</Label>
              <Select value={formData.authType} onValueChange={(value) => updateFormData({ authType: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="api-key">API Key</SelectItem>
                  <SelectItem value="bearer">Bearer Token</SelectItem>
                  <SelectItem value="oauth">OAuth 2.0</SelectItem>
                  <SelectItem value="basic">Basic Auth</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="apiKey">
                 {formData.authType === 'bearer' ? 'Token' : 'API Key / Secret'} *
              </Label>
              <Input
                id="apiKey"
                type="password"
                placeholder="Enter your credentials"
                value={formData.apiKey}
                onChange={(e) => updateFormData({ apiKey: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label htmlFor="headers">Custom Headers (Optional)</Label>
                {jsonError && <span className="text-xs text-destructive flex items-center gap-1"><AlertCircle className="w-3 h-3"/> {jsonError}</span>}
              </div>
              <Textarea
                id="headers"
                placeholder={'{\n  "Content-Type": "application/json"\n}'}
                rows={4}
                value={formData.headers}
                onChange={(e) => handleHeadersChange(e.target.value)}
                className={cn("font-mono text-sm", jsonError && "border-destructive focus-visible:ring-destructive")}
              />
            </div>
          </>
        ) : (
          /* CSV UPLOAD SECTION */
          <div className="space-y-2">
            <Label htmlFor="file">Upload CSV File *</Label>
            
            {!formData.file && !isUploading ? (
              /* 1. Empty State (Ready to Upload) */
              <Card 
                className={cn(
                  "border-2 border-dashed transition-colors", 
                  isDragging ? "border-primary bg-primary/5" : "border-border"
                )}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <CardContent className="p-6">
                  <label htmlFor="file" className="flex flex-col items-center justify-center cursor-pointer w-full h-full">
                    <div className={cn("rounded-full p-4 mb-3 transition-colors", isDragging ? "bg-primary/20" : "bg-muted")}>
                      <Upload className={cn("h-6 w-6", isDragging ? "text-primary" : "text-muted-foreground")} />
                    </div>
                    <p className="text-sm font-medium mb-1">
                      Click to upload or drag and drop
                    </p>
                    <p className="text-xs text-muted-foreground">CSV files up to 10MB</p>
                    <input 
                      id="file" 
                      ref={fileInputRef}
                      type="file" 
                      accept=".csv" 
                      className="hidden" 
                      onChange={handleFileChange} 
                    />
                  </label>
                </CardContent>
              </Card>
            ) : (
              /* 2. Uploading or Completed State */
              <Card className="border border-border">
                <CardContent className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("rounded-full p-2", isUploading ? "bg-muted" : "bg-green-100 dark:bg-green-900/30")}>
                      {isUploading ? (
                        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                      ) : (
                        <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {formData.file?.name || "Uploading..."}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {isUploading 
                          ? "Uploading to secure server..." 
                          : `${(formData.file!.size / 1024).toFixed(1)} KB • Upload complete`
                        }
                      </p>
                    </div>
                  </div>
                  
                  {!isUploading && (
                    <button 
                      onClick={removeFile}
                      className="text-muted-foreground hover:text-destructive transition-colors p-1"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}