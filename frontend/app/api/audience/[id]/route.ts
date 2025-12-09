import { type NextRequest, NextResponse } from "next/server"

export async function generateStaticParams() {
  return [
    { id: "car-buyers" },
    { id: "service-customers" },
    { id: "test-drive" },
  ]
}

// Mock data for audience members with new CSV field structure
const mockAudienceData: Record<string, any[]> = {
  "car-buyers": [
    {
      id: "1",
      person_name: "Rajesh Kumar",
      phone_number: "+91-98765-43210",
      vehicle_model: "Maruti Swift",
      vin_number: "MA3SW1234567890123",
      dealership_id: "DL001",
    },
    {
      id: "2",
      person_name: "Priya Sharma",
      phone_number: "+91-98765-43211",
      vehicle_model: "Hyundai Creta",
      vin_number: "HY4CR1234567890124",
      dealership_id: "MH001",
    },
    {
      id: "3",
      person_name: "Amit Patel",
      phone_number: "+91-98765-43212",
      vehicle_model: "Tata Nexon",
      vin_number: "TA5NX1234567890125",
      dealership_id: "GJ001",
    },
    {
      id: "4",
      person_name: "Sneha Reddy",
      phone_number: "+91-98765-43213",
      vehicle_model: "Honda City",
      vin_number: "HO6CT1234567890126",
      dealership_id: "KA001",
    },
    {
      id: "5",
      person_name: "Vikram Singh",
      phone_number: "+91-98765-43214",
      vehicle_model: "Mahindra XUV700",
      vin_number: "MA7XV1234567890127",
      dealership_id: "UP001",
    },
    {
      id: "6",
      person_name: "Anjali Desai",
      phone_number: "+91-98765-43215",
      vehicle_model: "Toyota Innova",
      vin_number: "TO8IN1234567890128",
      dealership_id: "TN001",
    },
    {
      id: "7",
      person_name: "Rahul Mehta",
      phone_number: "+91-98765-43216",
      vehicle_model: "Maruti Baleno",
      vin_number: "MA9BL1234567890129",
      dealership_id: "RJ001",
    },
    {
      id: "8",
      person_name: "Kavita Nair",
      phone_number: "+91-98765-43217",
      vehicle_model: "Kia Seltos",
      vin_number: "KI0SE1234567890130",
      dealership_id: "WB001",
    },
    {
      id: "9",
      person_name: "Suresh Iyer",
      phone_number: "+91-98765-43218",
      vehicle_model: "Volkswagen Polo",
      vin_number: "VO1PL1234567890131",
      dealership_id: "KL001",
    },
    {
      id: "10",
      person_name: "Meera Joshi",
      phone_number: "+91-98765-43219",
      vehicle_model: "Nissan Magnite",
      vin_number: "NI2MG1234567890132",
      dealership_id: "MP001",
    },
    {
      id: "11",
      person_name: "Arjun Malhotra",
      phone_number: "+91-98765-43220",
      vehicle_model: "MG Hector",
      vin_number: "MG3HE1234567890133",
      dealership_id: "HR001",
    },
    {
      id: "12",
      person_name: "Divya Rao",
      phone_number: "+91-98765-43221",
      vehicle_model: "Skoda Kushaq",
      vin_number: "SK4KU1234567890134",
      dealership_id: "AP001",
    },
  ],
  "service-customers": [
    {
      id: "13",
      person_name: "Ramesh Gupta",
      phone_number: "+91-98765-43222",
      vehicle_model: "Maruti Swift",
      vin_number: "MA5SW1234567890135",
      dealership_id: "DL002",
    },
    {
      id: "14",
      person_name: "Sunita Verma",
      phone_number: "+91-98765-43223",
      vehicle_model: "Hyundai i20",
      vin_number: "HY6I21234567890136",
      dealership_id: "MH002",
    },
    {
      id: "15",
      person_name: "Nikhil Agarwal",
      phone_number: "+91-98765-43224",
      vehicle_model: "Tata Harrier",
      vin_number: "TA7HR1234567890137",
      dealership_id: "GJ002",
    },
    {
      id: "16",
      person_name: "Pooja Menon",
      phone_number: "+91-98765-43225",
      vehicle_model: "Honda Amaze",
      vin_number: "HO8AM1234567890138",
      dealership_id: "KA002",
    },
    {
      id: "17",
      person_name: "Manish Tiwari",
      phone_number: "+91-98765-43226",
      vehicle_model: "Mahindra Scorpio",
      vin_number: "MA9SC1234567890139",
      dealership_id: "UP002",
    },
  ],
  "test-drive": [
    {
      id: "18",
      person_name: "Aditya Kapoor",
      phone_number: "+91-98765-43227",
      vehicle_model: "Toyota Fortuner",
      vin_number: "TO0FO1234567890140",
      dealership_id: "TN002",
    },
    {
      id: "19",
      person_name: "Shruti Bansal",
      phone_number: "+91-98765-43228",
      vehicle_model: "Maruti Grand Vitara",
      vin_number: "MA1GV1234567890141",
      dealership_id: "RJ002",
    },
    {
      id: "20",
      person_name: "Karan Chopra",
      phone_number: "+91-98765-43229",
      vehicle_model: "Kia Carens",
      vin_number: "KI2CA1234567890142",
      dealership_id: "WB002",
    },
    {
      id: "21",
      person_name: "Neha Krishnan",
      phone_number: "+91-98765-43230",
      vehicle_model: "Volkswagen Taigun",
      vin_number: "VO3TG1234567890143",
      dealership_id: "KL002",
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
