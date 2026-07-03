/**
 * Seed Objectives — pre-created, verified campaign objectives.
 *
 * ─── HOW TO ADD CONTENT ─────────────────────────────────────────────
 * You have 6-7 best-performing campaigns with real data.
 * To add your content:
 *   1. Copy a seed objective entry below
 *   2. Fill in every field with your real campaign data
 *   3. Set `verified: true` once you've QA'd it
 *   4. Set `isPlaceholder: false`
 *
 * Structure:
 *   - id: Unique slug (e.g., "hyryder-tdb-outbound")
 *   - familyId: Which campaign family (presales_voice, service_voice, whatsapp)
 *   - subType: Campaign sub-type
 *   - fields: All form field values
 *   - verified: Has this been QA'd?
 *   - isPlaceholder: True = needs real content
 */

export interface SeedObjective {
  id: string;
  name: string;
  description: string;
  familyId: string;
  subType: string;
  tags: string[];
  verified: boolean;
  isPlaceholder: boolean;
  fields: Record<string, string>;
}



export const SEED_OBJECTIVES: SeedObjective[] = [
  /* ─────────────────────────────────────────────────────────────────
     4W PRE-SALES
     ───────────────────────────────────────────────────────────────── */

  // 1. Hyryder TDB Outbound
  {
    id: 'hyryder-tdb-outbound',
    name: 'Hyryder TDB Outbound',
    description: 'Outbound test drive booking campaign for Urban Cruiser Hyryder',
    familyId: 'presales_voice',
    subType: 'tdb_outbound',
    tags: ['4w', 'pre-sales', 'toyota', 'suv', 'hyryder'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Hyryder TDB Outbound - English',
      campaign_objective_description: 'Outbound voice campaign targeting prospects who have shown interest in the Urban Cruiser Hyryder to book a test drive',
      purpose: 'Book a test drive for the Urban Cruiser Hyryder by connecting with warm leads, highlighting key features, and scheduling a convenient slot at the nearest dealership',
      purpose_steps: '1. Greet and introduce\n2. Confirm customer identity and interest\n3. Highlight 2-3 key features (fuel efficiency, hybrid tech, spacious interior)\n4. Check preferred date and time\n5. Confirm dealership location\n6. End with confirmation and thank you',
      conversation_tone: 'Friendly, professional, and enthusiastic',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} calling from {dealer_name}. I hope you\'re having a great day! I\'m calling about the Urban Cruiser Hyryder — I believe you\'d requested some information about it?',
      why_user_should_avail_this: 'The Urban Cruiser Hyryder offers best-in-class fuel efficiency with Toyota\'s strong hybrid technology, a spacious and premium interior, and advanced safety features. Booking a test drive lets you experience the smooth drive and hybrid performance firsthand.',
      reasons_users_may_not_be_interested: 'Not looking to buy right now, Already booked a test drive elsewhere, Prefer a different vehicle segment, Budget constraints, Waiting for a different variant',
      reasons_for_non_applicability: 'Already purchased the vehicle, Not in service area, Commercial vehicle use, Requested not to be contacted',
      guardrails_guidelines: 'Do not make false claims about mileage or pricing. Do not pressure the customer. If customer is not interested, politely end the call. Do not share competitor pricing comparisons.',
      other_important_information: 'Campaign runs Mon-Sat 10 AM to 7 PM. Follow-up if no answer: max 3 attempts. Transfer to sales team if customer asks for detailed pricing.',
      required_attributes: 'phone, name, city, vehicle-model',
      target_audience_tags: 'existing-customers, new-leads, website-visitors, showroom-visitors',
      ctas: 'book-test-drive, request-callback, know-more',
      workflows: 'Test drive booking, Test drive feedback, Lost Customer Reactivation',
      vehicle_model: 'Urban Cruiser Hyryder',
      dealer_city: '',
      preferred_date: '',
      preferred_time: '',
    },
  },

  // 2. Grand Vitara Follow-up
  {
    id: 'grand-vitara-followup',
    name: 'Grand Vitara Follow-up',
    description: 'Follow-up calls for Grand Vitara prospects who visited the showroom',
    familyId: 'presales_voice',
    subType: 'tdb_followup',
    tags: ['4w', 'pre-sales', 'maruti', 'suv', 'grand-vitara'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Grand Vitara Showroom Follow-up - English',
      campaign_objective_description: 'Follow-up voice campaign for customers who visited the showroom for Grand Vitara but did not book a test drive',
      purpose: 'Re-engage showroom visitors who showed interest in Grand Vitara, address any concerns, and book a test drive',
      purpose_steps: '1. Greet and reference showroom visit\n2. Ask about their experience\n3. Address any concerns or questions\n4. Offer a test drive booking\n5. Confirm date/time\n6. Thank and confirm',
      conversation_tone: 'Warm, helpful, and consultative',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I noticed you visited our showroom recently to see the Grand Vitara — I hope you had a good experience! I was calling to see if you had any questions I could help with.',
      why_user_should_avail_this: 'The Grand Vitara combines powerful SUV styling with exceptional comfort and advanced safety features. A test drive is the best way to feel the difference — and we can schedule it at your convenience.',
      reasons_users_may_not_be_interested: 'Still deciding, Already booked elsewhere, Found a different vehicle they prefer, Need to discuss with family, Budget concerns',
      reasons_for_non_applicability: 'Already purchased vehicle, Requested no contact, Not the right contact person, Out of market area',
      guardrails_guidelines: 'Do not be pushy. Respect customer timelines. Do not offer discounts unless authorized. Notes should capture specific concerns for the sales team.',
      other_important_information: 'Follow-up within 48 hours of showroom visit. Transfer to sales if customer wants pricing or exchange evaluation.',
      required_attributes: 'phone, name, vehicle-model',
      target_audience_tags: 'showroom-visitors, existing-customers, new-leads',
      ctas: 'book-test-drive, request-callback, book-showroom-visit',
      workflows: 'Test drive booking, Test drive feedback',
      vehicle_model: 'Grand Vitara',
      dealer_city: '',
      preferred_date: '',
      preferred_time: '',
    },
  },

  // 3. Scorpio-N Re-engage
  {
    id: 'scorpio-n-reengage',
    name: 'Scorpio-N Re-engagement',
    description: 'Re-engagement campaign for Scorpio-N leads that went cold',
    familyId: 'presales_voice',
    subType: 'tdb_reengage',
    tags: ['4w', 'pre-sales', 'mahindra', 'suv', 'scorpio'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Scorpio-N Re-engagement - English',
      campaign_objective_description: 'Voice campaign to re-engage prospects who showed interest in Scorpio-N but have not converted',
      purpose: 'Re-engage Scorpio-N prospects with new offers, updates, or limited-time benefits to revive interest and book test drives',
      purpose_steps: '1. Greet and reference previous interest\n2. Share any new updates or offers\n3. Ask if they are still in the market\n4. Address any previous concerns\n5. Offer to book a test drive\n6. Close with confirmation',
      conversation_tone: 'Friendly, low-pressure, and informative',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I hope you\'re doing well! We spoke a while back about the Scorpio-N, and I wanted to check in and share some exciting new updates about the vehicle.',
      why_user_should_avail_this: 'The Scorpio-N offers uncompromising SUV performance with new features and possibly limited-period benefits. We currently have some attractive offers that make this the perfect time to take a test drive.',
      reasons_users_may_not_be_interested: 'Already purchased a different vehicle, No longer in the market, Budget constraints, Waiting for facelift/update, Found a better alternative',
      reasons_for_non_applicability: 'Already purchased Scorpio-N from another dealer, Requested no contact, Wrong number, Sold vehicle',
      guardrails_guidelines: 'Do not create false urgency. Do not offer discounts unless authorized. Limit to 2 re-engagement attempts. Respect opt-out requests immediately.',
      other_important_information: 'Best to call during evening hours (6-8 PM) as these were earlier leads. Reference the previous interaction date if available.',
      required_attributes: 'phone, name, vehicle-model',
      target_audience_tags: 'lost-leads, cold-leads, re-engagement',
      ctas: 'book-test-drive, request-callback, know-more',
      workflows: 'Lost Customer Reactivation, Test drive booking',
      vehicle_model: 'Scorpio-N',
      dealer_city: '',
      preferred_date: '',
      preferred_time: '',
    },
  },

  // 4. Thar Off-Road Experience
  {
    id: 'thar-offroad',
    name: 'Thar Off-Road Experience',
    description: 'Test drive campaign for Thar highlighting off-road experience',
    familyId: 'presales_voice',
    subType: 'tdb_outbound',
    tags: ['4w', 'pre-sales', 'mahindra', 'suv', 'thar', 'offroad'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Thar Off-Road Experience - English',
      campaign_objective_description: 'Voice campaign targeting adventure enthusiasts for Thar test drive bookings with off-road experience',
      purpose: 'Book a Thar test drive focusing on the off-road experience and lifestyle appeal',
      purpose_steps: '1. Greet and establish rapport\n2. Ask about their adventure/SUV interests\n3. Highlight Thar\'s off-road capabilities\n4. Offer a curated test drive experience\n5. Schedule date and time\n6. Confirm and close',
      conversation_tone: 'Energetic, passionate, and adventurous',
      custom_conversation_start_pattern: 'Hey {customer_name}! This is {agent_name} from {dealer_name}. I\'m calling because I know you\'re someone who loves adventure — and we have something truly exciting to talk about!',
      why_user_should_avail_this: 'The Thar is India\'s most iconic off-road SUV with unmatched 4x4 capability, a convertible top option, and bold design. We\'re offering a special off-road experience test drive — not just on road, but on a dedicated off-road track!',
      reasons_users_may_not_be_interested: 'Not an SUV person, Fuel efficiency concerns, Need a family vehicle, Comfort concerns for daily use, Budget constraints',
      reasons_for_non_applicability: 'Commercial use, Fleet purchase, Government employee restrictions, Already owns a Thar',
      guardrails_guidelines: 'Do not exaggerate off-road capabilities for safety. Do not compare directly with competitor SUVs in a negative way. Ensure test drive safety brief is provided.',
      other_important_information: 'Ideal for weekend test drives. Off-road track experience requires prior booking. Customer must have valid driving license.',
      required_attributes: 'phone, name, city',
      target_audience_tags: 'enthusiasts, adventure-seekers, website-visitors, social-media-leads',
      ctas: 'book-test-drive, request-callback, know-more, get-onroad-price',
      workflows: 'Test drive booking, Test drive feedback',
      vehicle_model: 'Thar',
      dealer_city: '',
      preferred_date: '',
      preferred_time: '',
    },
  },

  // 5. XUV700 Test Drive
  {
    id: 'xuv700-tdb',
    name: 'XUV700 Test Drive',
    description: 'Test drive booking campaign for Mahindra XUV700',
    familyId: 'presales_voice',
    subType: 'tdb_outbound',
    tags: ['4w', 'pre-sales', 'mahindra', 'suv', 'xuv700'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'XUV700 TDB Outbound - English',
      campaign_objective_description: 'Outbound voice campaign for Mahindra XUV700 test drive bookings targeting luxury SUV buyers',
      purpose: 'Book test drives for XUV700 by highlighting its premium features, ADAS technology, and commanding presence',
      purpose_steps: '1. Greet and introduce\n2. Confirm interest in XUV700\n3. Highlight key premium features\n4. Offer test drive at dealership\n5. Schedule date/time\n6. Close with confirmation',
      conversation_tone: 'Premium, sophisticated, and informative',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I understand you\'ve been exploring the XUV700 — it\'s truly a remarkable vehicle, and I\'d love to help you experience it firsthand.',
      why_user_should_avail_this: 'The XUV700 is India\'s first SUV with Level 2 ADAS, a panoramic sunroof, and a luxurious cabin that redefines its segment. A test drive will show you why it\'s setting new benchmarks for safety and comfort.',
      reasons_users_may_not_be_interested: 'Waiting period too long, Considering a different SUV, Budget overrun, Prefer a different brand, Already booked elsewhere',
      reasons_for_non_applicability: 'Already purchased XUV700, Fleet/commercial use, Wrong contact, Requested no contact',
      guardrails_guidelines: 'Mention waiting period honestly if asked. Do not misrepresent ADAS capabilities. Do not guarantee delivery timelines.',
      other_important_information: 'Emphasize ADAS demo during test drive. Digital showroom tour available if preferred.',
      required_attributes: 'phone, name, city',
      target_audience_tags: 'premium-buyers, suv-enthusiasts, website-visitors, showroom-visitors',
      ctas: 'book-test-drive, request-callback, download-brochure, get-onroad-price',
      workflows: 'Test drive booking, Test drive feedback',
      vehicle_model: 'XUV700',
      dealer_city: '',
      preferred_date: '',
      preferred_time: '',
    },
  },

  /* ─────────────────────────────────────────────────────────────────
     4W POST-SALES
     ───────────────────────────────────────────────────────────────── */

  // 6. Service Due Reminder
  {
    id: '4w-service-due',
    name: '4W Service Due Reminder',
    description: 'Service due reminder for 4-wheeler customers',
    familyId: 'service_voice',
    subType: 'service_due',
    tags: ['4w', 'post-sales', 'service', 'reminder'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Service Due Reminder - English',
      campaign_objective_description: 'Outbound voice campaign reminding customers that their vehicle service is due',
      purpose: 'Remind customers about upcoming or due service, highlight the importance of timely maintenance, and book a service appointment',
      purpose_steps: '1. Greet and identify customer\n2. Inform about service due status\n3. Explain importance of timely service\n4. Offer convenient appointment slots\n5. Book service appointment\n6. Confirm details and thank',
      conversation_tone: 'Caring, professional, and helpful',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I\'m calling about your {vehicle_model} — it\'s coming up for its regular service, and I wanted to help you schedule a convenient appointment.',
      why_user_should_avail_this: 'Regular service keeps your vehicle performing at its best, maintains warranty validity, ensures safety, and prevents costly repairs down the road. We currently have service slots available at your convenience.',
      reasons_users_may_not_be_interested: 'Already serviced elsewhere, Vehicle not being used, Too busy to bring it in, Will book later, Budget concerns',
      reasons_for_non_applicability: 'Vehicle already sold, Not the owner, Warranty expired/void, Service already booked elsewhere',
      guardrails_guidelines: 'Do not scare the customer about consequences. Do not promise discounts unless authorized. Respect if customer says they will book later.',
      other_important_information: 'Offer pick-and-drop service if available at dealership. Mention current service offers or packages.',
      required_attributes: 'phone, name, vehicle-model, last-service-date',
      target_audience_tags: 'existing-customers, service-due, premium-customers',
      ctas: 'book-service, request-callback',
      workflows: 'Service remainder',
      vehicle_model: '',
      service_type: 'Periodic',
      last_service_date: '',
      odometer_reading: '',
    },
  },

  // 7. Overdue Service Alert
  {
    id: '4w-service-overdue',
    name: '4W Overdue Service Alert',
    description: 'Alert for customers with overdue service (30+ days past due)',
    familyId: 'service_voice',
    subType: 'service_overdue',
    tags: ['4w', 'post-sales', 'service', 'overdue', 'urgent'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Overdue Service Alert - English',
      campaign_objective_description: 'Voice campaign for customers whose vehicle service is overdue by more than 30 days',
      purpose: 'Alert customers about overdue service, explain risks of delayed service, and urgently book a service appointment',
      purpose_steps: '1. Greet and identify\n2. Inform about overdue service\n3. Explain risks of delayed service\n4. Offer priority scheduling\n5. Book appointment\n6. Confirm and thank',
      conversation_tone: 'Professional, concerned but not alarming',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I\'m reaching out regarding your {vehicle_model} — I noticed the service is overdue, and I wanted to help get it scheduled right away at no extra charge for the delay.',
      why_user_should_avail_this: 'Delayed service can lead to reduced fuel efficiency, potential engine wear, voided warranty claims, and safety concerns. We\'re offering priority scheduling to get your vehicle back in top shape quickly.',
      reasons_users_may_not_be_interested: 'Already serviced elsewhere, Vehicle not in use, Planning to sell, Not the primary user, Financial constraints',
      reasons_for_non_applicability: 'Vehicle sold, Not the current owner, Already booked elsewhere, Warranty expired',
      guardrails_guidelines: 'Do not use fear tactics. Do not charge penalty for overdue service. Be respectful if customer is defensive. Note the reason for delay.',
      other_important_information: 'Priority scheduling available for overdue customers. Mention any loyalty discounts.',
      required_attributes: 'phone, name, vehicle-model, last-service-date',
      target_audience_tags: 'overdue-service, existing-customers, premium-customers',
      ctas: 'book-service, request-callback',
      workflows: 'Service remainder',
      vehicle_model: '',
      service_type: 'Overdue',
      last_service_date: '',
      odometer_reading: '',
    },
  },

  // 8. Post-Service Feedback
  {
    id: '4w-post-service-feedback',
    name: '4W Post-Service Feedback',
    description: 'Feedback collection after service completion',
    familyId: 'service_voice',
    subType: 'service_feedback',
    tags: ['4w', 'post-sales', 'service', 'feedback'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Post-Service Feedback - English',
      campaign_objective_description: 'Voice campaign to collect feedback from customers after their vehicle service',
      purpose: 'Collect post-service feedback, measure customer satisfaction, and address any concerns while building loyalty',
      purpose_steps: '1. Greet and thank for choosing dealership\n2. Ask about overall service experience\n3. Inquire about specific aspects (timeliness, quality, communication)\n4. Address any concerns\n5. Thank and offer future service booking',
      conversation_tone: 'Appreciative, attentive, and solution-oriented',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I\'m calling to follow up on your recent service visit for your {vehicle_model}. We truly value your feedback and would love to hear about your experience.',
      why_user_should_avail_this: 'Your feedback helps us serve you better. By sharing your experience, you help us improve our service quality and ensure every visit is excellent.',
      reasons_users_may_not_be_interested: 'Too busy, Not satisfied and doesn\'t want to discuss, Already gave feedback elsewhere, Not the person who brought the vehicle',
      reasons_for_non_applicability: 'Service not completed, Wrong contact, Not the vehicle owner',
      guardrails_guidelines: 'Do not be defensive if feedback is negative. Listen fully before responding. Escalate serious complaints to service manager. Never argue with the customer.',
      other_important_information: 'Call within 3 days of service completion. Negative feedback should be flagged for manager follow-up.',
      required_attributes: 'phone, name, vehicle-model',
      target_audience_tags: 'existing-customers, service-completed, premium-customers',
      ctas: 'request-callback, book-service',
      workflows: 'Post Service Feedback',
      vehicle_model: '',
      service_type: '',
      last_service_date: '',
      odometer_reading: '',
    },
  },

  // 9. Insurance Renewal Reminder
  {
    id: '4w-insurance-renewal',
    name: '4W Insurance Renewal',
    description: 'Insurance renewal reminder for 4-wheeler customers',
    familyId: 'service_voice',
    subType: 'service_due',
    tags: ['4w', 'post-sales', 'insurance', 'renewal'],
    verified: false,
    isPlaceholder: true,
    fields: {
      campaign_objective_name: 'Insurance Renewal Reminder - English',
      campaign_objective_description: 'Voice campaign reminding customers about upcoming insurance renewal',
      purpose: 'Remind customers about insurance renewal date, explain the benefits of renewing through the dealership, and facilitate hassle-free renewal',
      purpose_steps: '1. Greet and identify customer\n2. Inform about insurance expiry\n3. Explain dealership renewal benefits\n4. Share renewal premium estimate\n5. Process renewal or schedule callback\n6. Confirm and thank',
      conversation_tone: 'Helpful, informative, and reassuring',
      custom_conversation_start_pattern: 'Hello {customer_name}, this is {agent_name} from {dealer_name}. I\'m calling about your {vehicle_model}\'s insurance, which is due for renewal soon. We can help you renew it hassle-free with some great benefits.',
      why_user_should_avail_this: 'Renewing through the dealership ensures genuine claims processing, zero paperwork hassles, competitive premium rates, and add-on cover recommendations tailored to your vehicle.',
      reasons_users_may_not_be_interested: 'Already renewed elsewhere, Comparing other providers, Want to reduce coverage, Not the decision maker, Budget constraints',
      reasons_for_non_applicability: 'Vehicle sold, Already renewed, Not the owner, Commercial vehicle policy',
      guardrails_guidelines: 'Do not misrepresent coverage. Do not pressure into add-ons. Provide transparent premium breakdown. Do not guarantee claim approval.',
      other_important_information: 'Offer to share a quote via WhatsApp if customer prefers. Mention no-claim bonus protection if applicable.',
      required_attributes: 'phone, name, vehicle-model',
      target_audience_tags: 'insurance-due, existing-customers, premium-customers',
      ctas: 'renew-insurance, request-callback, order-care-package',
      workflows: 'Insurance renewal',
      vehicle_model: '',
      service_type: 'Insurance',
      last_service_date: '',
      odometer_reading: '',
    },
  },
];

/**
 * Helpers for working with seed objectives
 */

export function getSeedObjectivesByFamily(familyId: string): SeedObjective[] {
  return SEED_OBJECTIVES.filter(s => s.familyId === familyId);
}


export function getSeedObjectiveById(id: string): SeedObjective | undefined {
  return SEED_OBJECTIVES.find(s => s.id === id);
}

export function getSeedsByTag(tag: string): SeedObjective[] {
  return SEED_OBJECTIVES.filter(s => s.tags.includes(tag));
}

export function searchSeeds(query: string): SeedObjective[] {
  const q = query.toLowerCase().trim();
  if (!q) return SEED_OBJECTIVES;
  return SEED_OBJECTIVES.filter(s =>
    s.name.toLowerCase().includes(q) ||
    s.description.toLowerCase().includes(q) ||
    s.tags.some(t => t.toLowerCase().includes(q)) ||
    s.fields.campaign_objective_name?.toLowerCase().includes(q)
  );
}
