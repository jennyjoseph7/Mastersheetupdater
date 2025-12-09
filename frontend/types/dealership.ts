export interface DealershipData {
  dealer_name: string
  dealership_type: "Single Brand" | "Multi Brand"
  supported_brands: string[]
  languages: string[]
  channels: string[]
  dealership_url: string
  pan_card_link: string
  gstin: string
  gst_certificate: File | null
  dealership_legal_name: string
  certificate_of_incorporation: string
  website: string
  linkedin_url: string
  year_established: number
  showroom_center_count: number
  workshop_center_count: number
  buyback_center_count: number
  billing_address: string
  billing_contact_name: string
  billing_contact_email: string
  billing_contact_phone: string
  primary_contact_name: string
  primary_contact_role: string
  primary_contact_email: string
  primary_contact_phone: string
  secondary_contact_name: string
  secondary_contact_role: string
  secondary_contact_email: string
  secondary_contact_phone: string
  dealership_guidelines: string
  dealership_guardrails: string
  dealership_description: string
  region_id: string
  dealer_group_id?: string
}
