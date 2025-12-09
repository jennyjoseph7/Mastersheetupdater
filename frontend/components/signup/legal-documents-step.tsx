"use client"

import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Upload, FileText, CheckCircle2 } from "lucide-react"
import type { DealershipData } from "@/types/dealership"

interface LegalDocumentsStepProps {
  data: DealershipData
  updateData: (data: Partial<DealershipData>) => void
}

export function LegalDocumentsStep({ data, updateData }: LegalDocumentsStepProps) {
  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          All documents should be clear, valid, and match the dealership legal name provided in the previous step.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="gstin" className="text-base font-semibold">
          GSTIN <span className="text-red-500">*</span>
        </Label>
        <Input
          id="gstin"
          placeholder="Enter 15-digit GSTIN"
          value={data.gstin}
          onChange={(e) => updateData({ gstin: e.target.value })}
          maxLength={15}
          className="text-base font-mono"
        />
        <p className="text-sm text-muted-foreground">Goods and Services Tax Identification Number</p>
      </div>

      <div className="space-y-3">
        <Label className="text-base font-semibold">
          GST Certificate <span className="text-red-500">*</span>
        </Label>
        <div className="border-2 border-dashed rounded-lg p-6 hover:border-indigo-400 transition-colors">
          <div className="flex flex-col items-center justify-center text-center">
            {data.gst_certificate ? (
              <>
                <CheckCircle2 className="h-12 w-12 text-green-500 mb-3" />
                <p className="text-sm font-medium text-gray-900">{data.gst_certificate.name}</p>
                <p className="text-xs text-muted-foreground mt-1">{(data.gst_certificate.size / 1024).toFixed(2)} KB</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3 bg-transparent"
                  onClick={() => updateData({ gst_certificate: null })}
                >
                  Remove File
                </Button>
              </>
            ) : (
              <>
                <Upload className="h-12 w-12 text-gray-400 mb-3" />
                <p className="text-sm font-medium text-gray-900 mb-1">Click to upload GST Certificate</p>
                <p className="text-xs text-muted-foreground mb-3">PDF, PNG, or JPG (max 5MB)</p>
                <Button variant="outline" size="sm">
                  <FileText className="h-4 w-4 mr-2" />
                  Choose File
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="pan_card_link" className="text-base font-semibold">
          PAN Card <span className="text-red-500">*</span>
        </Label>
        <Input
          id="pan_card_link"
          placeholder="Enter PAN number or upload document URL"
          value={data.pan_card_link}
          onChange={(e) => updateData({ pan_card_link: e.target.value })}
          className="text-base"
        />
        <p className="text-sm text-muted-foreground">Permanent Account Number or document link</p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="certificate_of_incorporation" className="text-base font-semibold">
          Certificate of Incorporation
        </Label>
        <Input
          id="certificate_of_incorporation"
          placeholder="Enter certificate URL or document ID"
          value={data.certificate_of_incorporation}
          onChange={(e) => updateData({ certificate_of_incorporation: e.target.value })}
          className="text-base"
        />
        <p className="text-sm text-muted-foreground">Business registration certificate</p>
      </div>
    </div>
  )
}
