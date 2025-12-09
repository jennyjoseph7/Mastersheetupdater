"use client"

import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import type { DealershipData } from "@/types/dealership"

interface GuidelinesStepProps {
  data: DealershipData
  updateData: (data: Partial<DealershipData>) => void
}

export function GuidelinesStep({ data, updateData }: GuidelinesStepProps) {
  return (
    <div className="space-y-6">
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p className="text-sm text-amber-800">
          These guidelines will help AI understand your business better and generate more relevant campaigns.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="dealership_description" className="text-base font-semibold">
          Dealership Description
        </Label>
        <Textarea
          id="dealership_description"
          placeholder="Describe your dealership, its history, values, and unique selling points..."
          value={data.dealership_description}
          onChange={(e) => updateData({ dealership_description: e.target.value })}
          rows={5}
          className="resize-none"
        />
        <p className="text-sm text-muted-foreground">Provide a comprehensive overview of your business</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="dealership_guidelines" className="text-base font-semibold">
          Business Guidelines
        </Label>
        <Textarea
          id="dealership_guidelines"
          placeholder="Enter your business guidelines, brand voice, communication style, and best practices..."
          value={data.dealership_guidelines}
          onChange={(e) => updateData({ dealership_guidelines: e.target.value })}
          rows={5}
          className="resize-none"
        />
        <p className="text-sm text-muted-foreground">How should AI communicate on behalf of your dealership?</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="dealership_guardrails" className="text-base font-semibold">
          Content Guardrails
        </Label>
        <Textarea
          id="dealership_guardrails"
          placeholder="Specify any restrictions, prohibited topics, or compliance requirements..."
          value={data.dealership_guardrails}
          onChange={(e) => updateData({ dealership_guardrails: e.target.value })}
          rows={5}
          className="resize-none"
        />
        <p className="text-sm text-muted-foreground">What should AI avoid when generating content?</p>
      </div>
    </div>
  )
}
