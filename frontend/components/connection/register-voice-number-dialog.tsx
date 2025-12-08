"use client"

import type React from "react"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Checkbox } from "@/components/ui/checkbox"
import { Upload } from "lucide-react"

interface RegisterVoiceNumberDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: any) => void
}

export function RegisterVoiceNumberDialog({ open, onOpenChange, onSubmit }: RegisterVoiceNumberDialogProps) {
  const [formData, setFormData] = useState({
    countryCode: "+91",
    phoneNumber: "",
    provider: "",
    callerName: "",
    proofOfOwnership: null as File | null,
    verificationMethod: "otp",
    confirmed: false,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
    setFormData({
      countryCode: "+91",
      phoneNumber: "",
      provider: "",
      callerName: "",
      proofOfOwnership: null,
      verificationMethod: "otp",
      confirmed: false,
    })
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, proofOfOwnership: e.target.files[0] })
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Register New Number</DialogTitle>
          <DialogDescription>Register your phone number for voice call campaigns</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phone-number">
                Phone Number <span className="text-red-500">*</span>
              </Label>
              <div className="flex gap-2">
                <Select
                  value={formData.countryCode}
                  onValueChange={(value) => setFormData({ ...formData, countryCode: value })}
                >
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="+91">+91</SelectItem>
                    <SelectItem value="+1">+1</SelectItem>
                    <SelectItem value="+44">+44</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  id="phone-number"
                  placeholder="XXXXXXXXXX"
                  value={formData.phoneNumber}
                  onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
                  className="flex-1"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider">
                Provider / Carrier <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.provider}
                onValueChange={(value) => setFormData({ ...formData, provider: value })}
              >
                <SelectTrigger id="provider">
                  <SelectValue placeholder="Choose Provider" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Twilio">Twilio</SelectItem>
                  <SelectItem value="Airtel IQ">Airtel IQ</SelectItem>
                  <SelectItem value="Exotel">Exotel</SelectItem>
                  <SelectItem value="Knowlarity">Knowlarity</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="caller-name">
                Caller ID / Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="caller-name"
                placeholder="e.g., ABC Motors"
                value={formData.callerName}
                onChange={(e) => setFormData({ ...formData, callerName: e.target.value })}
                required
              />
              <p className="text-sm text-muted-foreground">This name will be displayed to recipients receiving calls</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="proof">
                Proof of Ownership <span className="text-red-500">*</span>
              </Label>
              <div className="border-2 border-dashed rounded-lg p-8 text-center hover:border-purple-300 transition-colors">
                <input
                  type="file"
                  id="proof"
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={handleFileChange}
                />
                <label htmlFor="proof" className="cursor-pointer">
                  <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {formData.proofOfOwnership
                      ? formData.proofOfOwnership.name
                      : "Upload telecom bill, invoice, or contract (PDF, JPG, PNG, DOC)"}
                  </p>
                </label>
              </div>
            </div>

            <div className="space-y-2">
              <Label>
                Verification Method <span className="text-red-500">*</span>
              </Label>
              <RadioGroup
                value={formData.verificationMethod}
                onValueChange={(value) => setFormData({ ...formData, verificationMethod: value })}
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="otp" id="otp" />
                  <Label htmlFor="otp" className="font-normal cursor-pointer">
                    OTP / PIN via SMS
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="callback" id="callback" />
                  <Label htmlFor="callback" className="font-normal cursor-pointer">
                    Call-back verification
                  </Label>
                </div>
              </RadioGroup>
            </div>

            <div className="flex items-start space-x-2">
              <Checkbox
                id="confirm"
                checked={formData.confirmed}
                onCheckedChange={(checked) => setFormData({ ...formData, confirmed: checked as boolean })}
              />
              <Label htmlFor="confirm" className="text-sm font-normal leading-relaxed cursor-pointer">
                I confirm that this number is owned by my business and will be used in compliance with applicable
                regulations
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              className="bg-purple-600 hover:bg-purple-700"
              disabled={
                !formData.phoneNumber ||
                !formData.provider ||
                !formData.callerName ||
                !formData.proofOfOwnership ||
                !formData.confirmed
              }
            >
              Register Number
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
