export interface Campaign {
  id: string
  name: string
  createdOn: string
  channelsUsed: string[]
  status: "Live" | "Completed" | "Paused" | "Draft"
  totalLeads?: number
  conversions?: number
  budget?: number
}
