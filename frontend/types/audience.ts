export interface AudienceMember {
  id: string;
  name?: string;
  phoneNumber?: string;
  email?: string;
  city?: string;
  vehicleType?: string;
  status?: "Lead" | "Qualified" | "Converted" | "Losing" | "Lost";
  lastInteraction?: string;
  totalInteractions?: number;
  lifetimeValue?: number;
  // New fields from CSV data
  person_name?: string;
  phone_number?: string;
  vehicle_model?: string;
  vin_number?: string;
  dealership_id?: string;
  city?: string;
}

export interface AudienceGroup {
  id: string;
  name: string;
  description: string;
  memberCount: number;
  icon: string;
  color: string;
  gradient: string;
}
