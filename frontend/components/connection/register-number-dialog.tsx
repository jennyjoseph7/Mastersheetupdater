"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Upload } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

interface RegisterNumberDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: any) => void
}

export function RegisterNumberDialog({ open, onOpenChange, onSubmit }: RegisterNumberDialogProps) {
  const [formData, setFormData] = useState({
    provider: "",
    fbManagerId: "",
    displayName: "",
    category: "",
    website: "",
    brandLogo: null as File | null,
    businessEmail: "",
    businessDescription: "",
    businessAddress: "",
    mobileNumber: "",
    pocEmail: "",
    pocMobile: "",
    expectedTraffic: "",
    greenTickLink: "",
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
    // Reset form
    setFormData({
      provider: "",
      fbManagerId: "",
      displayName: "",
      category: "",
      website: "",
      brandLogo: null,
      businessEmail: "",
      businessDescription: "",
      businessAddress: "",
      mobileNumber: "",
      pocEmail: "",
      pocMobile: "",
      expectedTraffic: "",
      greenTickLink: "",
    })
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, brandLogo: e.target.files[0] })
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b">
          <DialogTitle className="text-xl">Register WhatsApp Business Account</DialogTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Complete the form below to register your WhatsApp Business account
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1">
          <ScrollArea className="max-h-[calc(90vh-180px)]">
            <div className="px-6 py-4 space-y-6">
              {/* WhatsApp Business Service Provider */}
              <div className="space-y-2">
                <Label htmlFor="provider">WhatsApp business service provider</Label>
                <Select
                  value={formData.provider}
                  onValueChange={(value) => setFormData({ ...formData, provider: value })}
                >
                  <SelectTrigger id="provider">
                    <SelectValue placeholder="Choose your Provider" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Meta">Meta</SelectItem>
                    <SelectItem value="Twilio">Twilio</SelectItem>
                    <SelectItem value="Airtel">Airtel</SelectItem>
                    <SelectItem value="Gupshup">Gupshup</SelectItem>
                    <SelectItem value="Kaleyra">Kaleyra</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Facebook Business Manager Information */}
              <div className="space-y-4">
                <h3 className="font-semibold">Facebook Business Manager Information</h3>
                <div className="space-y-2">
                  <Label htmlFor="fbManagerId">Facebook Business Manager ID</Label>
                  <Input
                    id="fbManagerId"
                    placeholder="Facebook Business Manager ID"
                    value={formData.fbManagerId}
                    onChange={(e) => setFormData({ ...formData, fbManagerId: e.target.value })}
                  />
                </div>
              </div>

              {/* Business Details */}
              <div className="space-y-4">
                <h3 className="font-semibold">Business Details</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="displayName">Display Name for Business Account</Label>
                    <Input
                      id="displayName"
                      placeholder="Business Name"
                      value={formData.displayName}
                      onChange={(e) => setFormData({ ...formData, displayName: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="category">Category</Label>
                    <Select
                      value={formData.category}
                      onValueChange={(value) => setFormData({ ...formData, category: value })}
                    >
                      <SelectTrigger id="category">
                        <SelectValue placeholder="Select Category" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="insurance">Insurance</SelectItem>
                        <SelectItem value="finance">Finance</SelectItem>
                        <SelectItem value="healthcare">Healthcare</SelectItem>
                        <SelectItem value="retail">Retail</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="website">Website</Label>
                    <Input
                      id="website"
                      type="url"
                      placeholder="https://yourwebsite.com"
                      value={formData.website}
                      onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="brandLogo">Brand Logo</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        id="brandLogo"
                        type="file"
                        accept="image/*"
                        onChange={handleFileChange}
                        className="hidden"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => document.getElementById("brandLogo")?.click()}
                        className="w-full"
                      >
                        <Upload className="h-4 w-4 mr-2" />
                        {formData.brandLogo ? formData.brandLogo.name : "Upload Logo"}
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="businessEmail">Business Email ID</Label>
                    <Input
                      id="businessEmail"
                      type="email"
                      placeholder="business@example.com"
                      value={formData.businessEmail}
                      onChange={(e) => setFormData({ ...formData, businessEmail: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="businessDescription">Business Description</Label>
                    <Input
                      id="businessDescription"
                      placeholder="Description"
                      value={formData.businessDescription}
                      onChange={(e) => setFormData({ ...formData, businessDescription: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="businessAddress">Business Address</Label>
                  <Textarea
                    id="businessAddress"
                    placeholder="Enter complete business address"
                    value={formData.businessAddress}
                    onChange={(e) => setFormData({ ...formData, businessAddress: e.target.value })}
                    rows={3}
                  />
                </div>
              </div>

              {/* Contact Information */}
              <div className="space-y-4">
                <h3 className="font-semibold">Contact Information</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="mobileNumber">Mobile Number</Label>
                    <Input
                      id="mobileNumber"
                      placeholder="+91-XXXXXXXXXX"
                      value={formData.mobileNumber}
                      onChange={(e) => setFormData({ ...formData, mobileNumber: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="pocEmail">POC email ID</Label>
                    <Input
                      id="pocEmail"
                      type="email"
                      placeholder="poc@example.com"
                      value={formData.pocEmail}
                      onChange={(e) => setFormData({ ...formData, pocEmail: e.target.value })}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="pocMobile">POC mobile number</Label>
                  <Input
                    id="pocMobile"
                    placeholder="+91-XXXXXXXXXX"
                    value={formData.pocMobile}
                    onChange={(e) => setFormData({ ...formData, pocMobile: e.target.value })}
                  />
                </div>
              </div>

              {/* Additional Information */}
              <div className="space-y-4">
                <h3 className="font-semibold">Additional Information</h3>
                <div className="space-y-2">
                  <Label htmlFor="expectedTraffic">
                    Expected Traffic for Business Initiated & User Initiated autoNgage:
                  </Label>
                  <Textarea
                    id="expectedTraffic"
                    placeholder="Description"
                    value={formData.expectedTraffic}
                    onChange={(e) => setFormData({ ...formData, expectedTraffic: e.target.value })}
                    rows={3}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="greenTickLink">
                    Is Article/Link you want green tick on whatsapp please share Article/Link:
                  </Label>
                  <Input
                    id="greenTickLink"
                    placeholder="Address"
                    value={formData.greenTickLink}
                    onChange={(e) => setFormData({ ...formData, greenTickLink: e.target.value })}
                  />
                </div>
              </div>
            </div>
          </ScrollArea>

          <div className="px-6 py-4 border-t flex justify-end">
            <Button type="submit" className="bg-purple-600 hover:bg-purple-700">
              Submit
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
