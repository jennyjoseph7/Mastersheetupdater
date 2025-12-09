"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Separator } from "@/components/ui/separator"
import { Bold, Italic, Underline, LinkIcon, ImageIcon } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"

interface SmtpConfigDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: any) => void
}

export function SmtpConfigDialog({ open, onOpenChange, onSubmit }: SmtpConfigDialogProps) {
  const [formData, setFormData] = useState({
    fromName: "",
    fromEmail: "",
    username: "",
    password: "",
    smtpHost: "",
    smtpPort: "587",
    smtpSecurity: "TLS",
    useDifferentImap: false,
    imapHost: "",
    imapPort: "993",
    imapSecurity: "TLS",
    signature: "",
    bccEmail: "",
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData)
  }

  const updateField = (field: string, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] p-0">
        <DialogHeader className="px-6 pt-6">
          <DialogTitle>SMTP Configuration</DialogTitle>
          <DialogDescription>
            Configure your email settings for sending and receiving campaign emails.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col">
          <ScrollArea className="flex-1 px-6" style={{ maxHeight: "calc(90vh - 180px)" }}>
            <div className="space-y-6 pb-6">
              {/* SMTP Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">SMTP Settings (sending emails)</h3>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="fromName">From Name</Label>
                    <Input
                      id="fromName"
                      placeholder="Your Company Name"
                      value={formData.fromName}
                      onChange={(e) => updateField("fromName", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="fromEmail">From Email</Label>
                    <Input
                      id="fromEmail"
                      type="email"
                      placeholder="noreply@yourcompany.com"
                      value={formData.fromEmail}
                      onChange={(e) => updateField("fromEmail", e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="username">User Name</Label>
                    <Input
                      id="username"
                      placeholder="smtp.username"
                      value={formData.username}
                      onChange={(e) => updateField("username", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={formData.password}
                      onChange={(e) => updateField("password", e.target.value)}
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="smtpHost">SMTP Host</Label>
                    <Input
                      id="smtpHost"
                      placeholder="smtp.gmail.com"
                      value={formData.smtpHost}
                      onChange={(e) => updateField("smtpHost", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtpPort">SMTP Port</Label>
                    <Input
                      id="smtpPort"
                      placeholder="587"
                      value={formData.smtpPort}
                      onChange={(e) => updateField("smtpPort", e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <RadioGroup
                    value={formData.smtpSecurity}
                    onValueChange={(value) => updateField("smtpSecurity", value)}
                    className="flex gap-6"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="SSL" id="smtp-ssl" />
                      <Label htmlFor="smtp-ssl" className="font-normal">
                        SSL
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="TLS" id="smtp-tls" />
                      <Label htmlFor="smtp-tls" className="font-normal">
                        TLS
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="None" id="smtp-none" />
                      <Label htmlFor="smtp-none" className="font-normal">
                        None
                      </Label>
                    </div>
                  </RadioGroup>
                </div>
              </div>

              <Separator />

              {/* IMAP Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">IMAP Settings (receives emails)</h3>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="useDifferentImap"
                    checked={formData.useDifferentImap}
                    onCheckedChange={(checked) => updateField("useDifferentImap", checked)}
                  />
                  <Label htmlFor="useDifferentImap" className="font-normal">
                    Use different email accounts for receiving emails
                  </Label>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="imapHost">IMAP Host</Label>
                    <Input
                      id="imapHost"
                      placeholder="imap.gmail.com"
                      value={formData.imapHost}
                      onChange={(e) => updateField("imapHost", e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="imapPort">IMAP Port</Label>
                    <Input
                      id="imapPort"
                      placeholder="993"
                      value={formData.imapPort}
                      onChange={(e) => updateField("imapPort", e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <RadioGroup
                    value={formData.imapSecurity}
                    onValueChange={(value) => updateField("imapSecurity", value)}
                    className="flex gap-6"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="SSL" id="imap-ssl" />
                      <Label htmlFor="imap-ssl" className="font-normal">
                        SSL
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="TLS" id="imap-tls" />
                      <Label htmlFor="imap-tls" className="font-normal">
                        TLS
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="None" id="imap-none" />
                      <Label htmlFor="imap-none" className="font-normal">
                        None
                      </Label>
                    </div>
                  </RadioGroup>
                </div>
              </div>

              <Separator />

              {/* Signature */}
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold">Signature</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Enter your email signature below (manually or by copy-pasting it from your email client).
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex gap-1 rounded-md border p-2">
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8">
                      <Bold className="h-4 w-4" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8">
                      <Italic className="h-4 w-4" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8">
                      <Underline className="h-4 w-4" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8">
                      <LinkIcon className="h-4 w-4" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon" className="h-8 w-8">
                      <ImageIcon className="h-4 w-4" />
                    </Button>
                  </div>
                  <Textarea
                    placeholder="Enter your email signature here..."
                    className="min-h-[120px]"
                    value={formData.signature}
                    onChange={(e) => updateField("signature", e.target.value)}
                  />
                </div>
              </div>

              <Separator />

              {/* BCC to CRM Settings */}
              <div className="space-y-4">
                <h3 className="font-semibold">BCC to CRM Settings</h3>

                <div className="space-y-2">
                  <Label htmlFor="bccEmail">BCC Email Address</Label>
                  <Input
                    id="bccEmail"
                    type="email"
                    placeholder="crm@yourcompany.com"
                    value={formData.bccEmail}
                    onChange={(e) => updateField("bccEmail", e.target.value)}
                  />
                  <p className="text-sm text-muted-foreground">
                    Automatically BCC this email address on all outbound emails for CRM tracking
                  </p>
                </div>
              </div>
            </div>
          </ScrollArea>

          {/* Footer with buttons */}
          <div className="flex justify-end gap-3 border-t px-6 py-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" className="hover:bg-purple-700 bg-primary">
              Save
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
