"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { 
  Plus, 
  Target, 
  Users, 
  CheckCircle2, 
  Tag, 
  X,
  Type,
} from "lucide-react"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
import type { DataSourceFormData } from "../add-data-source-dialog"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { fetchCampaignObjectives } from "@/utils/api"

interface AssignAudienceDetailsProps {
  formData: DataSourceFormData
  updateFormData: (updates: Partial<DataSourceFormData>) => void
  isPrefilled?: boolean // New prop to hide fields
}

const predefinedTags = [
  "Active Customers",
  "Premium Leads",
  "Test Audience",
  "Inactive Users",
  "VIP Customers",
]

export function AssignAudienceDetails({
  formData,
  updateFormData,
  isPrefilled = false,
}: AssignAudienceDetailsProps) {
  const [customTagInput, setCustomTagInput] = useState("")
  const [showCustomTagInput, setShowCustomTagInput] = useState(false)
  
  const [objectives, setObjectives] = useState<any[]>([]);
  const [isLoadingObjectives, setIsLoadingObjectives] = useState(false);

  // Fetch objectives only if NOT prefilled (since we hide the select anyway)
  useEffect(() => {
    if (isPrefilled || !formData.category) return;

    const loadObjectives = async () => {
      setIsLoadingObjectives(true);
      try {
        const result = await fetchCampaignObjectives(formData.category);
        setObjectives(result.items || []);
        
        // Only reset if not already set (to preserve prefilled value if logic changes)
        if (!formData.campaignObjectiveId) {
             updateFormData({ campaignObjectiveId: "" });
        }
      } catch (err) {
        console.error("Failed to load objectives", err);
      } finally {
        setIsLoadingObjectives(false);
      }
    };

    loadObjectives();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData.category, isPrefilled]);

  const handleTagToggle = (tag: string) => {
    const currentTags = formData.tags || []
    if (currentTags.includes(tag)) {
      updateFormData({ tags: currentTags.filter((t) => t !== tag) })
    } else {
      updateFormData({ tags: [...currentTags, tag] })
    }
  }

  const handleAddCustomTag = () => {
    const trimmed = customTagInput.trim()
    if (trimmed && !formData.tags?.includes(trimmed)) {
      updateFormData({ tags: [...(formData.tags || []), trimmed] })
      setCustomTagInput("")
      setShowCustomTagInput(false)
    }
  }

  const removeTag = (tagToRemove: string) => {
    const currentTags = formData.tags || []
    updateFormData({ tags: currentTags.filter((t) => t !== tagToRemove) })
  }

  return (
    <div className="space-y-8 p-1">
      {/* Section Header */}
      <div className="flex flex-col gap-1">
        <h3 className="text-xl font-semibold tracking-tight text-foreground">
          Audience Configuration
        </h3>
        <p className="text-sm text-muted-foreground">
          Define the target group and organize them for better campaign tracking.
        </p>
      </div>

      <div className="grid gap-8">
        
        {/* 1. Category Selection - HIDDEN IF PREFILLED */}
        {!isPrefilled && (
          <div className="space-y-3">
            <Label className="text-sm font-medium text-foreground/80">
              Select Audience Category <span className="text-destructive">*</span>
            </Label>
            <RadioGroup
              value={formData.category}
              onValueChange={(value) => updateFormData({ category: value })}
              className="grid grid-cols-1 gap-4 md:grid-cols-2"
            >
              <Label
                htmlFor="pre-sales"
                className={cn(
                  "relative flex cursor-pointer flex-col gap-4 rounded-xl border-2 p-5 transition-all hover:bg-accent/40 hover:border-primary/50",
                  formData.category === "pre-sales"
                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                    : "border-border bg-card"
                )}
              >
                <RadioGroupItem value="pre-sales" id="pre-sales" className="sr-only" />
                <div className="flex items-start justify-between">
                  <div className="rounded-lg bg-primary/10 p-2.5 dark:bg-primary/30">
                    <Target className="h-5 w-5 text-primary" />
                  </div>
                  {formData.category === "pre-sales" && (
                    <CheckCircle2 className="h-5 w-5 text-primary animate-in fade-in zoom-in duration-300" />
                  )}
                </div>
                <div className="space-y-1">
                  <p className="font-semibold leading-none">Pre-Sales Audience</p>
                  <p className="text-xs text-muted-foreground">
                    Targeting new leads, enquiries, and test drive requests.
                  </p>
                </div>
              </Label>

              <Label
                htmlFor="post-sales"
                className={cn(
                  "relative flex cursor-pointer flex-col gap-4 rounded-xl border-2 p-5 transition-all hover:bg-accent/40 hover:border-primary/50",
                  formData.category === "post-sales"
                    ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                    : "border-border bg-card"
                )}
              >
                <RadioGroupItem value="post-sales" id="post-sales" className="sr-only" />
                <div className="flex items-start justify-between">
                  <div className="rounded-lg bg-primary/10 p-2.5 dark:bg-primary/30">
                    <Users className="h-5 w-5 text-primary" />
                  </div>
                  {formData.category === "post-sales" && (
                    <CheckCircle2 className="h-5 w-5 text-primary animate-in fade-in zoom-in duration-300" />
                  )}
                </div>
                <div className="space-y-1">
                  <p className="font-semibold leading-none">Post-Sales Audience</p>
                  <p className="text-xs text-muted-foreground">
                    Existing owners, service reminders, and retention.
                  </p>
                </div>
              </Label>
            </RadioGroup>
          </div>
        )}

        {/* 2. Objective Selection - HIDDEN IF PREFILLED */}
        {!isPrefilled && formData.category && (
          <div className="space-y-3 animate-in fade-in slide-in-from-top-4 duration-300">
            <Label className="text-sm font-medium text-foreground/80">
              Select Campaign Objective <span className="text-destructive">*</span>
            </Label>
            
            <Select
              disabled={isLoadingObjectives}
              value={formData.campaignObjectiveId}
              onValueChange={(value) => updateFormData({ campaignObjectiveId: value })}
            >
              <SelectTrigger className="h-10">
                <SelectValue placeholder={
                   isLoadingObjectives 
                    ? "Loading objectives..." 
                    : "Select an objective"
                } />
              </SelectTrigger>
              <SelectContent>
                {objectives.length === 0 && !isLoadingObjectives ? (
                  <div className="p-2 text-sm text-muted-foreground text-center">
                    No objectives found for selected category
                  </div>
                ) : (
                  objectives.map((obj) => (
                    <SelectItem key={obj.campaign_objective_id} value={obj.campaign_objective_id}>
                      {obj.campaign_objective_name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>{/* Helper Description for selected objective */}
          {formData.campaignObjectiveId && (
            <p className="text-[11px] text-muted-foreground ml-1">
              {objectives.find(o => o.campaign_objective_id === formData.campaignObjectiveId)?.campaign_objective_description}
            </p>
          )}
          </div>
        )}

        {/* 3. Audience Name */}
        <div className="space-y-3">
          <Label htmlFor="audienceName" className="text-sm font-medium text-foreground/80">
            Audience Name <span className="text-destructive">*</span>
          </Label>
          <div className="relative">
            <div className="absolute left-3 top-2.5 text-muted-foreground">
              <Type className="h-4 w-4" />
            </div>
            <Input
              id="audienceName"
              placeholder="e.g., Nexa Premium Owners – Q4 Campaign"
              value={formData.audienceName}
              onChange={(e) => updateFormData({ audienceName: e.target.value })}
              className="pl-9 h-10 border-input/80 focus-visible:ring-primary/20"
            />
          </div>
        </div>

        {/* 4. Tags (Always Visible) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-sm font-medium text-foreground/80">
              Tags & Segments
            </Label>
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Optional
            </span>
          </div>

          <div className="rounded-xl border bg-background p-4 shadow-sm space-y-4">
            <div className="min-h-[2.5rem] w-full rounded-md border border-dashed bg-muted/30 p-2">
               {(!formData.tags || formData.tags.length === 0) && (
                 <div className="flex h-full items-center justify-center text-xs text-muted-foreground py-2">
                   <Tag className="mr-2 h-3 w-3" />
                   No tags selected.
                 </div>
               )}
               <div className="flex flex-wrap gap-2">
                 {formData.tags?.map((tag) => (
                   <Badge
                     key={tag}
                     variant="secondary"
                     className="group pl-2.5 pr-1.5 py-1 text-sm font-medium border-primary/10 bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                   >
                     {tag}
                     <button
                       onClick={() => removeTag(tag)}
                       className="ml-1.5 rounded-full p-0.5 hover:bg-primary/20 text-primary/60 group-hover:text-primary transition-colors focus:outline-none"
                     >
                       <X className="h-3 w-3" />
                       <span className="sr-only">Remove {tag}</span>
                     </button>
                   </Badge>
                 ))}
               </div>
            </div>

            <div className="space-y-3 pt-2">
              <p className="text-xs font-medium text-muted-foreground">
                Suggested Tags
              </p>
              <div className="flex flex-wrap gap-2">
                {predefinedTags.map((tag) => {
                  if (formData.tags?.includes(tag)) return null
                  return (
                    <Badge
                      key={tag}
                      variant="outline"
                      className="cursor-pointer px-3 py-1.5 text-xs font-normal hover:border-primary/50 hover:bg-accent hover:text-accent-foreground transition-all active:scale-95"
                      onClick={() => handleTagToggle(tag)}
                    >
                      <Plus className="mr-1.5 h-3 w-3 opacity-50" />
                      {tag}
                    </Badge>
                  )
                })}
                
                {!showCustomTagInput ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-7 px-3 text-xs border border-dashed text-muted-foreground hover:text-foreground"
                    onClick={() => setShowCustomTagInput(true)}
                  >
                    + Create New
                  </Button>
                ) : (
                  <div className="flex items-center gap-2 animate-in slide-in-from-left-2 duration-200">
                    <Input
                      placeholder="Tag name..."
                      value={customTagInput}
                      onChange={(e) => setCustomTagInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault()
                          handleAddCustomTag()
                        }
                        if (e.key === "Escape") setShowCustomTagInput(false)
                      }}
                      className="h-7 w-40 text-xs"
                      autoFocus
                    />
                    <Button type="button" size="sm" className="h-7 px-2 text-xs" onClick={handleAddCustomTag}>
                      Add
                    </Button>
                    <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setShowCustomTagInput(false)}>
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}