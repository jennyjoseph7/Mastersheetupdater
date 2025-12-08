// Audience metadata for header
const audienceMetadata: Record<string, { name: string; description: string }> =
  {
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
