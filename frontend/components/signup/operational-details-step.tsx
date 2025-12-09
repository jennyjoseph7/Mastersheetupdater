"use client"

import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { X } from "lucide-react"
import type { DealershipData } from "@/types/dealership"

interface OperationalDetailsStepProps {
  data: DealershipData
  updateData: (data: Partial<DealershipData>) => void
}

const AVAILABLE_CHANNELS = [
  { id: "rcs", label: "RCS" },
  { id: "email", label: "Email" },
  { id: "web_chat", label: "Web Chat" },
  { id: "whatsapp_chat", label: "WhatsApp Chat" },
  { id: "whatsapp_voice_call", label: "WhatsApp Voice" },
  { id: "voice_phone", label: "Voice Phone" },
  { id: "fb_chat", label: "Facebook" },
  { id: "insta_chat", label: "Instagram" },
]

const AVAILABLE_LANGUAGES = [
  "english",
  "hindi",
  "kannada",
  "telugu",
  "tamil",
  "malayalam",
  "odia",
  "bengali",
  "marathi",
  "gujarati",
  "assamese",
  "punjabi",
]

export function OperationalDetailsStep({ data, updateData }: OperationalDetailsStepProps) {
  const handleChannelToggle = (channelId: string) => {
    const currentChannels = data.channels
    const newChannels = currentChannels.includes(channelId)
      ? currentChannels.filter((c) => c !== channelId)
      : [...currentChannels, channelId]
    updateData({ channels: newChannels })
  }

  const handleLanguageToggle = (language: string) => {
    const currentLanguages = data.languages
    const newLanguages = currentLanguages.includes(language)
      ? currentLanguages.filter((l) => l !== language)
      : [...currentLanguages, language]
    updateData({ languages: newLanguages })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <Label className="text-base font-semibold">Communication Channels</Label>
        <p className="text-sm text-muted-foreground">Select the channels you want to use for campaigns</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {AVAILABLE_CHANNELS.map((channel) => (
            <div
              key={channel.id}
              className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Checkbox
                id={channel.id}
                checked={data.channels.includes(channel.id)}
                onCheckedChange={() => handleChannelToggle(channel.id)}
              />
              <Label htmlFor={channel.id} className="cursor-pointer flex-1">
                {channel.label}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-4 pt-6 border-t">
        <Label className="text-base font-semibold">Supported Languages</Label>
        <p className="text-sm text-muted-foreground">Select languages for customer communication</p>
        <div className="flex flex-wrap gap-2">
          {AVAILABLE_LANGUAGES.map((language) => (
            <Badge
              key={language}
              variant={data.languages.includes(language) ? "default" : "outline"}
              className="cursor-pointer px-3 py-2 text-sm capitalize"
              onClick={() => handleLanguageToggle(language)}
            >
              {language}
              {data.languages.includes(language) && <X className="h-3 w-3 ml-2" />}
            </Badge>
          ))}
        </div>
      </div>

      <div className="space-y-4 pt-6 border-t">
        <Label className="text-base font-semibold">Center Counts</Label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="showroom_center_count">Showroom Centers</Label>
            <Input
              id="showroom_center_count"
              type="number"
              min="0"
              value={data.showroom_center_count}
              onChange={(e) => updateData({ showroom_center_count: Number.parseInt(e.target.value) || 0 })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="workshop_center_count">Workshop Centers</Label>
            <Input
              id="workshop_center_count"
              type="number"
              min="0"
              value={data.workshop_center_count}
              onChange={(e) => updateData({ workshop_center_count: Number.parseInt(e.target.value) || 0 })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="buyback_center_count">Buyback Centers</Label>
            <Input
              id="buyback_center_count"
              type="number"
              min="0"
              value={data.buyback_center_count}
              onChange={(e) => updateData({ buyback_center_count: Number.parseInt(e.target.value) || 0 })}
            />
          </div>
        </div>
      </div>

      <div className="space-y-4 pt-6 border-t">
        <Label className="text-base font-semibold">Additional Information</Label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="website">Website</Label>
            <Input
              id="website"
              type="url"
              placeholder="https://www.yourdealership.com"
              value={data.website}
              onChange={(e) => updateData({ website: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="linkedin_url">LinkedIn URL</Label>
            <Input
              id="linkedin_url"
              type="url"
              placeholder="https://linkedin.com/company/..."
              value={data.linkedin_url}
              onChange={(e) => updateData({ linkedin_url: e.target.value })}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
