"use client"

import { useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export type ChannelType = "all" | "chatbots" | "avatar-chatbots" | "whatsapp" | "voicebots"

interface ChannelFilterProps {
  onChannelChange: (channel: ChannelType) => void
  defaultValue?: ChannelType
}

export function ChannelFilter({ onChannelChange, defaultValue = "all" }: ChannelFilterProps) {
  const [selectedChannel, setSelectedChannel] = useState<ChannelType>(defaultValue)

  const handleChannelChange = (value: ChannelType) => {
    setSelectedChannel(value)
    onChannelChange(value)
  }

  return (
    <Select value={selectedChannel} onValueChange={handleChannelChange}>
      <SelectTrigger className="w-[200px]">
        <SelectValue placeholder="Select channel" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All Channels</SelectItem>
        <SelectItem value="chatbots">Chatbots (Text)</SelectItem>
        <SelectItem value="avatar-chatbots">Avatar Chatbots</SelectItem>
        <SelectItem value="whatsapp">WhatsApp</SelectItem>
        <SelectItem value="voicebots">Voicebots / Calls</SelectItem>
      </SelectContent>
    </Select>
  )
}
