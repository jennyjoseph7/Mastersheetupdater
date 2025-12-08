"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Plus, Trash2 } from "lucide-react"
import type { DataSourceFormData, FieldMapping } from "../add-data-source-dialog"

interface MapFieldsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

export function MapFields({ formData, updateFormData }: MapFieldsProps) {
  const addFieldMapping = () => {
    const newMapping: FieldMapping = {
      id: `field_${Date.now()}`,
      sourceField: "",
      targetField: "",
      enabled: true,
    }
    updateFormData({
      fieldMappings: [...formData.fieldMappings, newMapping],
    })
  }

  const removeFieldMapping = (id: string) => {
    updateFormData({
      fieldMappings: formData.fieldMappings.filter((m) => m.id !== id),
    })
  }

  const updateFieldMapping = (id: string, updates: Partial<FieldMapping>) => {
    updateFormData({
      fieldMappings: formData.fieldMappings.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })
  }

  // Mock source fields - in real app, these would come from API/CSV
  const sourceFields = ["first_name", "last_name", "phone", "email_address", "preferred_language", "customer_tags"]

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Map Fields to Standard Fields</h3>
        <p className="text-sm text-muted-foreground">
          Map your source fields to standard audience fields. Disabled fields will be excluded.
        </p>
      </div>

      <div className="space-y-3">
        {formData.fieldMappings.map((mapping, index) => (
          <div
            key={mapping.id}
            className={`flex items-center gap-3 p-3 rounded-lg border ${
              !mapping.enabled ? "bg-muted/50 opacity-60" : "bg-background"
            }`}
          >
            <div className="flex items-center">
              <Switch
                checked={mapping.enabled}
                onCheckedChange={(enabled) => updateFieldMapping(mapping.id, { enabled })}
              />
            </div>

            <div className="flex-1 grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Source Field</Label>
                <Select
                  value={mapping.sourceField}
                  onValueChange={(value) => updateFieldMapping(mapping.id, { sourceField: value })}
                  disabled={!mapping.enabled}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select source field" />
                  </SelectTrigger>
                  <SelectContent>
                    {sourceFields.map((field) => (
                      <SelectItem key={field} value={field}>
                        {field}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Target Field</Label>
                <Input
                  value={mapping.targetField}
                  onChange={(e) => updateFieldMapping(mapping.id, { targetField: e.target.value })}
                  placeholder="Enter target field name"
                  disabled={!mapping.enabled}
                />
              </div>
            </div>

            {index >= 5 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeFieldMapping(mapping.id)}
                className="text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}
      </div>

      <Button variant="outline" onClick={addFieldMapping} className="w-full bg-transparent">
        <Plus className="h-4 w-4 mr-2" />
        Add Field Mapping
      </Button>
    </div>
  )
}
