"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Database, FileSpreadsheet, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import type { DataSourceFormData } from "../add-data-source-dialog"

interface SelectSourceTypeProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

export function SelectSourceType({ formData, updateFormData }: SelectSourceTypeProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Select Source Type</h3>
        <p className="text-sm text-muted-foreground">Choose how you want to connect your audience data</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* API Connection - Disabled / Coming Soon */}
        <Card
          className={cn(
            "relative border-muted bg-muted/20", // Muted background
            "cursor-not-allowed opacity-60" // Disabled visuals
          )}
        >
          <CardContent className="flex flex-col items-center justify-center p-8 relative">
            {/* Coming Soon Badge */}
            <div className="absolute top-3 right-3">
              <span className="inline-flex items-center rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-xs font-semibold text-neutral-950 dark:border-neutral-800 dark:bg-neutral-950 dark:text-neutral-50">
                Coming Soon
              </span>
            </div>

            <div className="rounded-full bg-muted p-4 mb-4 grayscale">
              <Database className="h-8 w-8 text-muted-foreground" />
            </div>
            <h4 className="font-semibold mb-2 text-muted-foreground">API Connection</h4>
            <p className="text-sm text-muted-foreground text-center">
              Connect to external APIs like Salesforce, HubSpot, or custom endpoints
            </p>
          </CardContent>
        </Card>

        {/* CSV Upload - Active */}
        <Card
          className={cn(
            "cursor-pointer transition-all hover:shadow-md",
            formData.sourceType === "File" && "border-primary ring-2 ring-primary ring-offset-2",
          )}
          onClick={() => updateFormData({ sourceType: "File" })}
        >
          <CardContent className="flex flex-col items-center justify-center p-8 relative">
            {formData.sourceType === "File" && (
              <div className="absolute top-3 right-3 flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Check className="h-4 w-4" />
              </div>
            )}
            <div className="rounded-full bg-primary/10 p-4 mb-4">
              <FileSpreadsheet className="h-8 w-8 text-primary" />
            </div>
            <h4 className="font-semibold mb-2">CSV Upload</h4>
            <p className="text-sm text-muted-foreground text-center">
              Upload a CSV file with your audience data directly
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}