import { type NextRequest, NextResponse } from "next/server"

export async function generateStaticParams() {
  return [
    { id: "car-buyers" },
    { id: "service-customers" },
    { id: "test-drive" },
  ]
}

// Mock data for audience members
const mockAudienceData: Record<string, any[]> = {
  "car-buyers": [
    {
      id: "1",
      name: "John Smith",
      phoneNumber: "+1-555-0123",
      email: "john.smith@email.com",
      city: "Mumbai",
      vehicleType: "Sedan",
      status: "Converted",
      lastInteraction: "2024-01-15",
      totalInteractions: 8,
      lifetimeValue: 45000,
    },
    {
      id: "2",
      name: "Sarah Johnson",
      phoneNumber: "+1-555-0456",
      email: "sarah.johnson@email.com",
      city: "Delhi",
      vehicleType: "SUV",
      status: "Qualified",
      lastInteraction: "2024-01-14",
      totalInteractions: 5,
      lifetimeValue: 62000,
    },
    {
      id: "3",
      name: "Mike Davis",
      phoneNumber: "+1-555-0789",
      email: "mike.davis@email.com",
      city: "Bangalore",
      vehicleType: "Hatchback",
      status: "Lead",
      lastInteraction: "2024-01-13",
      totalInteractions: 3,
      lifetimeValue: 28000,
    },
    {
      id: "4",
      name: "Emily Wilson",
      phoneNumber: "+1-555-0321",
      email: "emily.wilson@email.com",
      city: "Chennai",
      vehicleType: "Sedan",
      status: "Lost",
      lastInteraction: "2024-01-10",
      totalInteractions: 2,
      lifetimeValue: 0,
    },
    {
      id: "5",
      name: "Robert Brown",
      phoneNumber: "+1-555-0654",
      email: "robert.brown@email.com",
      city: "Pune",
      vehicleType: "SUV",
      status: "Converted",
      lastInteraction: "2024-01-16",
      totalInteractions: 12,
      lifetimeValue: 78000,
    },
    {
      id: "6",
      name: "Lisa Anderson",
      phoneNumber: "+1-555-0987",
      email: "lisa.anderson@email.com",
      city: "Mumbai",
      vehicleType: "Luxury",
      status: "Qualified",
      lastInteraction: "2024-01-15",
      totalInteractions: 6,
      lifetimeValue: 95000,
    },
    {
      id: "7",
      name: "David Martinez",
      phoneNumber: "+1-555-0147",
      email: "david.martinez@email.com",
      city: "Hyderabad",
      vehicleType: "Sedan",
      status: "Lead",
      lastInteraction: "2024-01-12",
      totalInteractions: 4,
      lifetimeValue: 0,
    },
    {
      id: "8",
      name: "Jennifer Taylor",
      phoneNumber: "+1-555-0258",
      email: "jennifer.taylor@email.com",
      city: "Kolkata",
      vehicleType: "Hatchback",
      status: "Losing",
      lastInteraction: "2024-01-11",
      totalInteractions: 7,
      lifetimeValue: 32000,
    },
  ],
  "service-customers": [
    {
      id: "9",
      name: "Michael Chen",
      phoneNumber: "+1-555-0369",
      email: "michael.chen@email.com",
      city: "Mumbai",
      vehicleType: "Sedan",
      status: "Converted",
      lastInteraction: "2024-01-16",
      totalInteractions: 15,
      lifetimeValue: 12000,
    },
    {
      id: "10",
      name: "Amanda Rodriguez",
      phoneNumber: "+1-555-0741",
      email: "amanda.rodriguez@email.com",
      city: "Delhi",
      vehicleType: "SUV",
      status: "Qualified",
      lastInteraction: "2024-01-14",
      totalInteractions: 9,
      lifetimeValue: 8500,
    },
  ],
  "test-drive": [
    {
      id: "11",
      name: "Kevin Lee",
      phoneNumber: "+1-555-0852",
      email: "kevin.lee@email.com",
      city: "Bangalore",
      vehicleType: "SUV",
      status: "Lead",
      lastInteraction: "2024-01-15",
      totalInteractions: 2,
      lifetimeValue: 0,
    },
    {
      id: "12",
      name: "Rachel Green",
      phoneNumber: "+1-555-0963",
      email: "rachel.green@email.com",
      city: "Chennai",
      vehicleType: "Luxury",
      status: "Qualified",
      lastInteraction: "2024-01-16",
      totalInteractions: 4,
      lifetimeValue: 0,
    },
  ],
}

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  const { id } = params

  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 800))

  const audienceData = mockAudienceData[id] || []

  return NextResponse.json({
    success: true,
    data: audienceData,
  })
}
