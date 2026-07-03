export const CAMPAIGN_TYPES = ['pre-sales', 'post-sales', 'dealership'] as const;

export const CAMPAIGN_SUB_TYPES = [
  'brand awareness', 'service overdue', 'product awareness', 'event',
  'lead generation', 'lead qualification', 'lead nurturing', 'lead conversion',
  'workshop awareness', 'offers', 'new accessories', 'new procedures',
  'customer retention', 'service reminder', 'upsell/cross-sell', 'review',
  'feedback', 'reminder', 'product recall', 'software update', 'other',
] as const;

export const CTA_OPTIONS = [
  'know-more', 'register-to-event', 'book-test-drive', 'book-showroom-visit',
  'download-brochure', 'book-home-test-drive', 'get-onroad-price', 'request-callback',
  'confirm-booking', 'book-service', 'order-accessory', 'renew-insurance',
  'order-spare-part', 'order-extended-warranty', 'order-care-package',
] as const;

export const WORKFLOW_OPTIONS = [
  'Product Discovery/launch', 'Showroom launch-l', 'Test drive booking-l',
  'Test drive feedback', 'Test drive remainder', 'Post sales feedback-l',
  'Lost Customer Reactivation-l', 'Service remainder-l', 'Insurance renewal-l',
  'Post Service Feedback-l', 'ownership verification-l', 'Wishes-birthday/Festival',
  'other',
] as const;

export const CAMPAIGN_TYPE_LABELS: Record<string, string> = {
  'pre-sales': 'Pre-Sales',
  'post-sales': 'Post-Sales',
  'dealership': 'Dealership',
};

export interface CampaignFamily {
  id: string;
  label: string;
  icon: string;
  description: string;
  campaignType: string;
  subTypes: { id: string; label: string }[];
  extraFields: { key: string; label: string; hint: string }[];
  fieldOverrides?: Record<string, { label: string; hint: string }>;
  ctaOptions: string[];
  workflowOptions: string[];
  requiredAttributes: string[];
  targetAudienceTags: string[];
}

export function getFamiliesByType(type: string): CampaignFamily[] {
  return Object.values(CAMPAIGN_FAMILIES).filter(f => f.campaignType === type);
}

export const CAMPAIGN_FAMILIES: Record<string, CampaignFamily> = {
  presales_voice: {
    id: 'presales_voice',
    label: 'Test Drive Booking',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 17h14M5 17a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2M5 17l-2 4M19 17l2 4M9 11h6M12 8v6"/></svg>',
    description: 'Voice campaigns for booking test drives',
    campaignType: 'pre-sales',
    subTypes: [
      { id: 'tdb_outbound', label: 'TDB Outbound' },
      { id: 'tdb_followup', label: 'Follow-up Calls' },
      { id: 'tdb_reengage', label: 'Re-engagement Campaigns' },
    ],
    extraFields: [
      { key: 'vehicle_model', label: 'Vehicle Model', hint: 'e.g., Hyryder, Grand Vitara' },
      { key: 'dealer_city', label: 'Dealer City', hint: 'City where dealership is located' },
      { key: 'preferred_date', label: 'Preferred Date', hint: 'Preferred test drive date' },
      { key: 'preferred_time', label: 'Preferred Time', hint: 'Preferred time slot' },
    ],
    ctaOptions: ['book-test-drive', 'request-callback', 'download-brochure', 'book-showroom-visit', 'book-home-test-drive', 'get-onroad-price', 'know-more'],
    workflowOptions: ['Test drive booking', 'Test drive feedback', 'Lost Customer Reactivation', 'Test drive remainder'],
    requiredAttributes: ['phone', 'name', 'city', 'vehicle-model'],
    targetAudienceTags: ['existing-customers', 'new-leads', 'website-visitors', 'showroom-visitors'],
  },
  service_voice: {
    id: 'service_voice',
    label: 'Service Reminder',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M16 12h-4V8M8 12h.01"/></svg>',
    description: 'Voice campaigns for service reminders',
    campaignType: 'post-sales',
    subTypes: [
      { id: 'service_due', label: 'Service Due Reminder' },
      { id: 'service_overdue', label: 'Overdue Service Alert' },
      { id: 'service_feedback', label: 'Post-service Feedback' },
    ],
    extraFields: [
      { key: 'vehicle_model', label: 'Vehicle Model', hint: 'e.g., Hyryder, Grand Vitara' },
      { key: 'service_type', label: 'Service Type', hint: 'Periodic, Major, Minor' },
      { key: 'last_service_date', label: 'Last Service Date', hint: 'Date of last service' },
      { key: 'odometer_reading', label: 'Odometer Reading', hint: 'Current km reading' },
    ],
    ctaOptions: ['book-service', 'request-callback', 'order-spare-part', 'order-extended-warranty', 'order-care-package', 'renew-insurance'],
    workflowOptions: ['Service remainder', 'Post Service Feedback', 'Insurance renewal', 'ownership verification'],
    requiredAttributes: ['phone', 'name', 'vehicle-model', 'last-service-date'],
    targetAudienceTags: ['existing-customers', 'service-due', 'overdue-service', 'premium-customers'],
  },
  whatsapp: {
    id: 'whatsapp',
    label: 'WhatsApp Template',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/><path d="M8 10h.01M12 10h.01M16 10h.01"/></svg>',
    description: 'WhatsApp template campaigns',
    campaignType: 'dealership',
    subTypes: [
      { id: 'wa_promo', label: 'Promotional Templates' },
      { id: 'wa_service', label: 'Service Reminder WhatsApp' },
      { id: 'wa_feedback', label: 'Feedback Collection Templates' },
    ],
    extraFields: [
      { key: 'template_name', label: 'Template Name', hint: 'WhatsApp template name' },
      { key: 'cta_text', label: 'CTA Button Text', hint: 'Call to action button label' },
      { key: 'media_type', label: 'Media Type', hint: 'Image, Video, Document' },
      { key: 'media_url', label: 'Media URL', hint: 'URL for media attachment' },
    ],
    ctaOptions: ['know-more', 'register-to-event', 'download-brochure', 'request-callback', 'book-test-drive', 'book-service'],
    workflowOptions: ['Product Discovery/launch', 'Showroom launch', 'Post sales feedback', 'Wishes-birthday/Festival'],
    requiredAttributes: ['phone', 'name'],
    targetAudienceTags: ['opt-in-customers', 'whatsapp-active', 'all-customers'],
  },
};
