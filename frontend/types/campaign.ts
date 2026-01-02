export interface Campaign {
  id: string
  name: string
  createdOn: string
  channelsUsed: string[]
  status: "Live" | "Completed" | "Paused" | "Drafted"
  totalLeads?: number
  conversions?: number
  budget?: number
}
