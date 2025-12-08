"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import type { DataSourceFormData } from "../add-data-source-dialog"
import { useState } from "react"

interface AssignAudienceDetailsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
}

const predefinedTags = [
  "Active Customers",
  "Premium Leads",
  "Test Audience",
  "Inactive Users",
  "VIP Customers",
]

export function AssignAudienceDetails({ formData, updateFormData }: AssignAudienceDetailsProps) {
  const [customTagInput, setCustomTagInput] = useState("")
  const [showCustomTagInput, setShowCustomTagInput] = useState(false)

  const handleTagToggle = (tag: string) => {
    const currentTags = formData.tags || []
    if (currentTags.includes(tag)) {
      updateFormData({ tags: currentTags.filter((t) => t !== tag) })
    } else {
      updateFormData({ tags: [...currentTags, tag] })
    }
  }

  const handleAddCustomTag = () => {
    if (customTagInput.trim() && !formData.tags?.includes(customTagInput.trim())) {
      updateFormData({ tags: [...(formData.tags || []), customTagInput.trim()] })
      setCustomTagInput("")
      setShowCustomTagInput(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Select Category & Add Audience Details</h3>
        <p className="text-sm text-muted-foreground">
          Choose category, name your audience, and add tags to organize them.
        </p>
      </div>

      <div className="space-y-6">
        {/* Category Section */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">
            Category <span className="text-destructive">*</span>
          </Label>
          <RadioGroup
            value={formData.category}
            onValueChange={(value) => updateFormData({ category: value })}
            className="flex gap-4"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="pre_sales" id="pre_sales" />
              <Label htmlFor="pre_sales" className="cursor-pointer font-normal">
                Pre-Sales
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="post_sales" id="post_sales" />
              <Label htmlFor="post_sales" className="cursor-pointer font-normal">
                Post-Sales
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Audience Name Section */}
        <div className="space-y-2">
          <Label htmlFor="audienceName" className="text-sm font-medium">
            Audience Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="audienceName"
            placeholder="e.g., Premium Customers - CRM Q4 Leads"
            value={formData.audienceName}
            onChange={(e) => updateFormData({ audienceName: e.target.value })}
          />
        </div>

        {/* Tags Section */}
        <div className="space-y-3">
          <div>
            <Label className="text-sm font-medium">Tags (Optional)</Label>
            <p className="text-xs text-muted-foreground mt-1">
              Select a tag to organize your audience
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {predefinedTags.map((tag) => {
              const isSelected = formData.tags?.includes(tag) || false
              return (
                <Badge
                  key={tag}
                  variant={isSelected ? "default" : "outline"}
                  className={`cursor-pointer transition-colors ${
                    isSelected
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-accent hover:text-accent-foreground"
                  }`}
                  onClick={() => handleTagToggle(tag)}
                >
                  {tag}
                </Badge>
              )
            })}
            {!showCustomTagInput ? (
              <Button
                type="button"
                variant="outline"
                className="border-dashed"
                onClick={() => setShowCustomTagInput(true)}
              >
                <Plus className="h-4 w-4 mr-1" />
                Custom Tag
              </Button>
            ) : (
              <div className="flex gap-2 items-center">
                <Input
                  placeholder="Enter tag name"
                  value={customTagInput}
                  onChange={(e) => setCustomTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault()
                      handleAddCustomTag()
                    }
                    if (e.key === "Escape") {
                      setShowCustomTagInput(false)
                      setCustomTagInput("")
                    }
                  }}
                  className="w-32"
                  autoFocus
                />
                <Button
                  type="button"
                  size="sm"
                  onClick={handleAddCustomTag}
                >
                  Add
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setShowCustomTagInput(false)
                    setCustomTagInput("")
                  }}
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
          {formData.tags && formData.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {formData.tags.map((tag) => (
                <Badge
                  key={tag}
                  variant="default"
                  className="bg-primary text-primary-foreground"
                >
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
