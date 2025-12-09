"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { AlertCircle } from "lucide-react"
import type { DataSourceFormData, FieldMapping } from "../add-data-source-dialog"

interface MapFieldsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

export function MapFields({ formData, updateFormData }: MapFieldsProps) {
  
  const updateFieldMapping = (id: string, updates: Partial<FieldMapping>) => {
    updateFormData({
      fieldMappings: formData.fieldMappings.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })
  }

  // Pre-defined target fields in your system (optional suggestion list)
  const systemTargets = [
    "Name", "Mobile Number", "Email", "Vehicle Model", "Registration Number", "Last Service Date", "City"
  ];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Map CSV Columns</h3>
        <p className="text-sm text-muted-foreground">
          Match the columns from your uploaded CSV to the fields in the CRM.
        </p>
      </div>

      {formData.fieldMappings.length === 0 ? (
         <div className="p-4 border border-dashed rounded-lg text-center text-muted-foreground">
            <AlertCircle className="h-6 w-6 mx-auto mb-2 opacity-50"/>
            No headers found. Please go back and ensure your CSV is valid.
         </div>
      ) : (
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
            <div className="grid grid-cols-12 gap-3 mb-2 px-2 text-xs font-semibold text-muted-foreground">
                <div className="col-span-1 text-center">Import</div>
                <div className="col-span-5">CSV Header (Source)</div>
                <div className="col-span-6">System Field (Target)</div>
            </div>

            {formData.fieldMappings.map((mapping) => (
            <div
                key={mapping.id}
                className={`grid grid-cols-12 gap-3 items-center p-3 rounded-lg border transition-colors ${
                !mapping.enabled ? "bg-muted/40 opacity-70 border-dashed" : "bg-card border-solid"
                }`}
            >
                {/* Enable/Disable Toggle */}
                <div className="col-span-1 flex justify-center">
                <Switch
                    checked={mapping.enabled}
                    onCheckedChange={(enabled) => updateFieldMapping(mapping.id, { enabled })}
                    className="scale-75"
                />
                </div>

                {/* Source Field (Read Only) */}
                <div className="col-span-5">
                    <div className="text-sm font-medium truncate" title={mapping.sourceField}>
                        {mapping.sourceField}
                    </div>
                </div>

                {/* Target Field Input */}
                <div className="col-span-6">
                    <Input
                        value={mapping.targetField}
                        onChange={(e) => updateFieldMapping(mapping.id, { targetField: e.target.value })}
                        placeholder="Map to..."
                        disabled={!mapping.enabled}
                        className="h-8 text-sm"
                        list={`suggestions-${mapping.id}`}
                    />
                    {/* Native Datalist for suggestions */}
                    <datalist id={`suggestions-${mapping.id}`}>
                        {systemTargets.map(t => <option key={t} value={t} />)}
                    </datalist>
                </div>
            </div>
            ))}
        </div>
      )}
    </div>
  )
}