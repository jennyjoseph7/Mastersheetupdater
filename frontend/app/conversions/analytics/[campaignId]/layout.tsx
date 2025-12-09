// Sample campaigns data - in production, fetch from API
const sampleCampaigns = [
  {
    id: "CPG001",
    name: "Summer Insurance Promo 2024",
    createdOn: "2024-01-15",
    channelsUsed: ["WhatsApp", "Email", "SMS"],
    status: "Live",
    totalLeads: 320,
    conversions: 87,
    budget: 50000,
  },
  {
    id: "CPG002",
    name: "Health Coverage Campaign",
    createdOn: "2024-01-10",
    channelsUsed: ["Email", "Voice"],
    status: "Completed",
    totalLeads: 245,
    conversions: 68,
    budget: 35000,
  },
  {
    id: "CPG003",
    name: "Life Insurance Awareness",
    createdOn: "2024-01-20",
    channelsUsed: ["Email", "WhatsApp", "Voice"],
    status: "Live",
    totalLeads: 180,
    conversions: 52,
    budget: 42000,
  },
];

export async function generateStaticParams() {
  return sampleCampaigns.map((campaign) => ({
    campaignId: campaign.id,
  }));
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
