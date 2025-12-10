// Audience metadata for header - includes data source IDs
const audienceMetadata: Record<string, { name: string; description: string }> =
  {
    "1": {
      name: "Premium Customers - CRM",
      description: "Premium customers from Salesforce CRM",
    },
    "2": {
      name: "Q4 Leads",
      description: "Leads from Q4 campaign",
    },
    "3": {
      name: "Active Subscribers",
      description: "Active subscribers from HubSpot",
    },
    "car-buyers": {
      name: "Car Buyers",
      description: "Customers who have purchased vehicles",
    },
    "service-customers": {
      name: "Service Customers",
      description: "Regular service and maintenance customers",
    },
    "test-drive": {
      name: "Test Drive Requests",
      description: "Leads who requested test drives",
    },
    financing: {
      name: "Financing Inquiries",
      description: "Customers interested in financing options",
    },
    "trade-in": {
      name: "Trade-In Leads",
      description: "Customers looking to trade in vehicles",
    },
    vip: {
      name: "VIP Customers",
      description: "High-value and premium customers",
    },
  };

export async function generateStaticParams() {
  return Object.keys(audienceMetadata).map((id) => ({
    id,
  }));
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
