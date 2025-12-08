"use client"

import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { User, Building } from "lucide-react"
import type { DealershipData } from "@/types/dealership"

interface ContactInfoStepProps {
  data: DealershipData
  updateData: (data: Partial<DealershipData>) => void
}

export function ContactInfoStep({ data, updateData }: ContactInfoStepProps) {
  return (
    <div className="space-y-8">
      {/* Primary Contact */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-indigo-100 rounded-lg">
            <User className="h-5 w-5 text-indigo-600" />
          </div>
          <h3 className="text-lg font-semibold">Primary Contact</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="primary_contact_name">
              Full Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="primary_contact_name"
              placeholder="John Doe"
              value={data.primary_contact_name}
              onChange={(e) => updateData({ primary_contact_name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="primary_contact_role">Role</Label>
            <Input
              id="primary_contact_role"
              placeholder="General Manager"
              value={data.primary_contact_role}
              onChange={(e) => updateData({ primary_contact_role: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="primary_contact_email">
              Email <span className="text-red-500">*</span>
            </Label>
            <Input
              id="primary_contact_email"
              type="email"
              placeholder="john@dealership.com"
              value={data.primary_contact_email}
              onChange={(e) => updateData({ primary_contact_email: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="primary_contact_phone">
              Phone <span className="text-red-500">*</span>
            </Label>
            <Input
              id="primary_contact_phone"
              type="tel"
              placeholder="+91 98765 43210"
              value={data.primary_contact_phone}
              onChange={(e) => updateData({ primary_contact_phone: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* Secondary Contact */}
      <div className="space-y-4 pt-6 border-t">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-purple-100 rounded-lg">
            <User className="h-5 w-5 text-purple-600" />
          </div>
          <h3 className="text-lg font-semibold">Secondary Contact (Optional)</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="secondary_contact_name">Full Name</Label>
            <Input
              id="secondary_contact_name"
              placeholder="Jane Smith"
              value={data.secondary_contact_name}
              onChange={(e) => updateData({ secondary_contact_name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="secondary_contact_role">Role</Label>
            <Input
              id="secondary_contact_role"
              placeholder="Sales Manager"
              value={data.secondary_contact_role}
              onChange={(e) => updateData({ secondary_contact_role: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="secondary_contact_email">Email</Label>
            <Input
              id="secondary_contact_email"
              type="email"
              placeholder="jane@dealership.com"
              value={data.secondary_contact_email}
              onChange={(e) => updateData({ secondary_contact_email: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="secondary_contact_phone">Phone</Label>
            <Input
              id="secondary_contact_phone"
              type="tel"
              placeholder="+91 98765 43211"
              value={data.secondary_contact_phone}
              onChange={(e) => updateData({ secondary_contact_phone: e.target.value })}
            />
          </div>
        </div>
      </div>

      {/* Billing Contact */}
      <div className="space-y-4 pt-6 border-t">
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 bg-green-100 rounded-lg">
            <Building className="h-5 w-5 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold">Billing Information</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="billing_address">
              Billing Address <span className="text-red-500">*</span>
            </Label>
            <Textarea
              id="billing_address"
              placeholder="Enter complete billing address"
              value={data.billing_address}
              onChange={(e) => updateData({ billing_address: e.target.value })}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="billing_contact_name">Contact Name</Label>
            <Input
              id="billing_contact_name"
              placeholder="Accounts Manager"
              value={data.billing_contact_name}
              onChange={(e) => updateData({ billing_contact_name: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="billing_contact_email">Email</Label>
            <Input
              id="billing_contact_email"
              type="email"
              placeholder="billing@dealership.com"
              value={data.billing_contact_email}
              onChange={(e) => updateData({ billing_contact_email: e.target.value })}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="billing_contact_phone">Phone</Label>
            <Input
              id="billing_contact_phone"
              type="tel"
              placeholder="+91 98765 43212"
              value={data.billing_contact_phone}
              onChange={(e) => updateData({ billing_contact_phone: e.target.value })}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
