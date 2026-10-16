export interface ClassificationResult {
  outcome: 'Connected' | 'Not Connected' | 'Unknown';
  priority: number;
  terminal: boolean;
}

export const DISPOSITION_RULES: { terms: string[]; outcome: 'Connected' | 'Not Connected'; priority: number; terminal: boolean }[] = [
  // ponytail: canonical post-sales rules recognizing both master tags and legacy sheet labels
  { terms: ['service booked', 'service appointment booked', 'appointment booked', 'booking confirmed', 'slot booked', 'service already booked', 'vehicle booked for service', 'converted'], outcome: 'Connected', priority: 10, terminal: true },
  { terms: ['vehicle serviced', 'service completed', 'serviced', 'already serviced', 'has serviced car in another dealership', 'existing dealer contact'], outcome: 'Connected', priority: 10, terminal: true },
  { terms: ['feedback given', 'feedback received', 'feedback completed', 'feedback captured', 'happy customer', 'feedback provided'], outcome: 'Connected', priority: 10, terminal: true },
  { terms: ['complaint', 'escalation', 'negative feedback', 'unhappy', 'dissatisfied'], outcome: 'Connected', priority: 9, terminal: true },
  { terms: ['not interested', 'refused service', 'service not required', 'vehicle sold', 'has sold', 'moved to another location', 'has moved', 'postponed', 'service postponed', 'lost to competition', 'contact fatigue', 'vehicle is commercial', 'vehicle is not being run'], outcome: 'Connected', priority: 9, terminal: true },
  { terms: ['wrong number', 'invalid number', 'invalid lead', 'wrong contact number'], outcome: 'Not Connected', priority: 9, terminal: true },
  { terms: ['dnd', 'do not disturb', 'unsubscribed'], outcome: 'Not Connected', priority: 9, terminal: true },
  { terms: ['callback requested', 'requested a callback', 'call back', 'callback', 'asked to call later', 'requested_callback', 'follow up required', 'follow_up_required'], outcome: 'Connected', priority: 7, terminal: false },
  { terms: ['connected', 'contacted', 'spoken', 'customer answered', 'answered', 'vehicle in center', 'will call showroom/workshop themselves', 'will call workshop themselves', 'talk to human', 'enquired for dealership details', 'enquired for others', 'looking for a discount', 'price inquiry', 'showroom visit planned'], outcome: 'Connected', priority: 6, terminal: false },
  { terms: ['not reachable', 'not connected', 'no answer', 'ringing', 'switched off', 'busy', 'customer busy', 'user did not speak', 'voicemail', 'no response', 'user disconnected call', 'agent disconnected call', 'call disconnected', 'audio issue', 'call quality issue', 'connection issue', 'language barrier'], outcome: 'Not Connected', priority: 3, terminal: false },
];

export function normalizedText(value: string): string {
  return String(value ?? '').trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ');
}

export function classifyDisposition(disposition: string, status: string, summary: string): ClassificationResult {
  const text = normalizedText([disposition, status, summary].filter(Boolean).join(' '));
  if (!text) return { outcome: 'Unknown', priority: 1, terminal: false };
  for (const rule of DISPOSITION_RULES) {
    if (rule.terms.some(term => text.includes(term))) {
      return { outcome: rule.outcome, priority: rule.priority, terminal: rule.terminal };
    }
  }
  if (text.includes('completed') || text.includes('success')) {
    return { outcome: 'Connected', priority: 5, terminal: false };
  }
  if (text.includes('failed') || text.includes('missed')) {
    return { outcome: 'Not Connected', priority: 3, terminal: false };
  }
  return { outcome: 'Unknown', priority: 1, terminal: false };
}

export function isServiceBooked(row: Record<string, string>): boolean {
  const ud = String(row.updated_disposition || '').trim().toLowerCase();
  if (ud === 'converted' || ud === 'vehicle booked for service' || ud === 'service already booked') return true;
  const text = normalizedText(row.disposition_detail || row.disposition || '');
  return ['service booked', 'service appointment booked', 'appointment booked', 'slot booked', 'booking confirmed', 'converted', 'follow up required', 'follow-up required', 'booked', 'interested', 'service already booked', 'vehicle booked for service'].some(term => text.includes(term));
}

export function isServiceCompleted(row: Record<string, string>): boolean {
  const ud = String(row.updated_disposition || '').trim().toLowerCase();
  if (ud === 'has serviced car in another dealership' || ud === 'existing dealer contact' || ud === 'already serviced') return true;
  const text = normalizedText(row.disposition_detail || row.disposition || '');
  return ['vehicle serviced', 'service completed', 'has serviced car in another dealership', 'already serviced', 'serviced', 'existing dealer contact'].some(term => text.includes(term));
}

export function isNotInterested(row: Record<string, string>): boolean {
  const ud = String(row.updated_disposition || '').trim().toLowerCase();
  if (['not interested', 'invalid lead', 'rejected', 'vehicle sold', 'has sold/given away the car', 'moved to another location', 'has moved to another location', 'postponed', 'service postponed', 'unsubscribed'].includes(ud)) return true;
  const text = normalizedText(row.disposition_detail || row.disposition || '');
  return ['not interested', 'refused service', 'service not required', 'vehicle sold', 'has sold', 'moved to another location', 'has moved', 'service postponed', 'postponed', 'unsubscribed'].some(term => text.includes(term));
}

export function isFeedbackOrEscalation(row: { disposition_detail?: string; summary?: string; session_status?: string }): boolean {
  const text = normalizedText([row.disposition_detail, row.summary, row.session_status].join(' '));
  return ['feedback', 'complaint', 'escalation', 'unhappy', 'dissatisfied', 'negative'].some(term => text.includes(term));
}

export function extractPerfectRidersLocation(summary: string): string {
  const text = normalizedText(summary);
  if (!text) return '';
  if (text.includes('jayanagar')) return 'JAYANAGAR';
  if (text.includes('lalbagh')) return 'LALBAGH';
  return '';
}

export function extractPerfectRidersCRE(summary: string): string {
  const text = normalizedText(summary);
  if (!text) return '';
  const remarkMatch = text.match(/remarks?\s*[:-]\s*(.+)/i);
  if (remarkMatch) return remarkMatch[1].trim();
  const creMatch = text.match(/cre\s*[:-]\s*(.+)/i);
  if (creMatch) return creMatch[1].trim();
  const truncated = summary.trim().substring(0, 120);
  return truncated.length < summary.trim().length ? truncated + '…' : truncated;
}
