export interface ConversionLead {
  userId: string
  leadName: string
  email: string
  contactNumber: string
  campaignName: string
  campaignStatus: "Live" | "Completed" | "Paused"
  channelType: "WhatsApp" | "Email" | "Voice" | "SMS"
  conversionDate: string
  lifetimeValue?: number
}
