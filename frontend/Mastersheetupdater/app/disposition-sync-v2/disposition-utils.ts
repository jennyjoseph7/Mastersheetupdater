export interface DealerColumn {
  header: string;
  key: string;
}

export interface DealerConfig {
  name: string;
  summarySource: string;
  columns: DealerColumn[];
}

export interface BusinessConfig {
  dispositionPriority: Record<string, number>;
  terminalThreshold: number;
  connectedDispositions: string[];
  notConnectedDispositions: string[];
  seatingRules: { matches: string[]; value: string }[];
  validation: {
    file1RequiredGroups: { label: string; candidates: string[] }[];
    file1RecommendedGroups: { label: string; candidates: string[] }[];
    file2RequiredGroups: { label: string; candidates: string[] }[];
    file2RecommendedGroups: { label: string; candidates: string[] }[];
  };
}

export interface SessionEntry {
  selectionReason: string;
  recording: string;
  summary: string;
  sentiment: string;
  dateStr: string;
  startTime: string;
  channel: string;
  duration: string;
  session_id: string;
  session_disposition: string;
  history_text: string;
}

export interface QualityWarning {
  level: string;
  title: string;
  detail: string;
}

export interface QualityReport {
  status: string;
  subtitle: string;
  metrics: { label: string; value: number; tone: string }[];
  warnings: QualityWarning[];
  samples: { title: string; rows: string[] }[];
  counts: Record<string, number>;
}

export const BUSINESS_CONFIG: BusinessConfig = {
  dispositionPriority: {
    'test drive booked': 10,
    'converted': 10,
    'not interested': 9,
    'dnd': 9,
    'wrong number': 9,
    'interested': 8,
    'callback requested': 6,
    'call back': 6,
    'busy': 4,
    'not connected': 3,
    'no revert': 3,
    'user did not speak': 2,
  },
  terminalThreshold: 9,
  connectedDispositions: ['contacted', 'reached', 'engaged', 'converted'],
  notConnectedDispositions: ['attempted', 'busy'],
  seatingRules: [
    { matches: ['basalt'], value: '5 Seater' },
    { matches: ['aircross', 'c3'], value: '5 Seater & 7 Seater' },
    { matches: ['meridian', 'jeep'], value: '5 Seater & 7 Seater' },
  ],
  validation: {
    file1RequiredGroups: [
      { label: 'Phone', candidates: ['phone_number', 'phone', 'mobile'] },
      { label: 'Disposition', candidates: ['disposition'] },
      { label: 'Updated date', candidates: ['updated', 'call_date'] },
    ],
    file1RecommendedGroups: [
      { label: 'Full name', candidates: ['person_name', 'full_name', 'name'] },
      { label: 'City', candidates: ['city'] },
      { label: 'Campaign ID', candidates: ['campaign_id'] },
      { label: 'Lead source', candidates: ['lead_source'] },
      { label: 'Summary detail', candidates: ['disposition_detail'] },
      { label: 'Lead summary', candidates: ['lead_summary'] },
      { label: 'Model', candidates: ['interested_vehicle_name', 'model_preference', 'name'] },
      { label: 'Cohort', candidates: ['campaign_objective_name'] },
      { label: 'Session ID', candidates: ['last_session_id', 'session_id'] },
    ],
    file2RecommendedGroups: [
      { label: 'Phone', candidates: ['phone_number', 'phone', 'mobile', 'contact', 'contact_number'] },
      { label: 'Date/time', candidates: ['created', 'start_time', 'date', 'timestamp', 'call_date'] },
      { label: 'Summary', candidates: ['summary', 'call_summary', 'conversation_summary', 'notes'] },
      { label: 'Recording', candidates: ['call_recording', 'recording', 'recording_url', 'call_url', 'audio_url'] },
      { label: 'Sentiment', candidates: ['sentiment_score', 'sentiment', 'score'] },
      { label: 'Channel', candidates: ['channel', 'call_channel', 'communication_channel'] },
      { label: 'History', candidates: ['history', 'session_history', 'transcript', 'conversation_history', 'chat_history', 'messages'] },
      { label: 'Duration', candidates: ['duration', 'call_duration', 'recording_duration', 'talk_time'] },
    ],
    file2RequiredGroups: [
      { label: 'Phone', candidates: ['phone_number', 'phone', 'mobile', 'contact', 'contact_number'] },
      { label: 'Date/time', candidates: ['created', 'start_time', 'date', 'timestamp', 'call_date'] },
    ],
  },
};

export const COMMON_COLUMNS: DealerColumn[] = [
  { header: 'Lead_Id', key: 'lead_id' },
  { header: 'Full_Name', key: 'full_name' },
  { header: 'Phone', key: 'phone' },
  { header: 'City', key: 'city' },
  { header: 'PIncode', key: 'pincode' },
  { header: 'Language', key: 'language' },
  { header: 'Lead_Source', key: 'lead_source' },
  { header: 'Cohort', key: 'cohort' },
  { header: 'Campaign_ID', key: 'campaign_id' },
  { header: 'Last_session_id', key: 'last_session_id' },
  { header: 'Origin', key: 'origin' },
  { header: 'Lead_Timeline', key: 'lead_timeline' },
  { header: 'Call_Triggered', key: 'call_triggered' },
  { header: 'Outcome', key: 'outcome' },
  { header: 'Disposition', key: 'disposition' },
  { header: 'Summary', key: 'summary' },
  { header: 'Disposition_detail', key: 'disposition_detail' },
  { header: 'Manual_Disposition_detail', key: 'manual_disposition_detail' },
  { header: 'Call_Date', key: 'call_date' },
  { header: 'Number_of_attempts', key: 'num_attempts' },
  { header: 'Sentiment', key: 'sentiment' },
  { header: 'Recordings', key: 'recordings' },
  { header: 'Call_Duration', key: 'call_duration' },
  { header: 'Model', key: 'model' },
  { header: 'Seating', key: 'seating' },
];

export const STELLANTIS_COLUMNS: DealerColumn[] = [
  { header: 'Lead_ID+A1', key: 'lead_id' },
  { header: 'Full_Name', key: 'full_name' },
  { header: 'Phone', key: 'phone' },
  { header: 'City', key: 'city' },
  { header: 'PIncode', key: 'pincode' },
  { header: 'Language', key: 'language' },
  { header: 'Disposition_Detail_AI', key: 'manual_disposition_detail' },
  { header: 'Source', key: 'lead_source' },
  { header: 'Cohort', key: 'cohort' },
  { header: 'Campaign_ID', key: 'campaign_id' },
  { header: 'Call Triggered', key: 'call_triggered' },
  { header: 'Origin', key: 'origin' },
  { header: 'Lead_Timeline', key: 'lead_timeline' },
  { header: 'Outcome', key: 'outcome' },
  { header: 'Disposition', key: 'disposition' },
  { header: 'Disposition_Detail', key: 'disposition_detail' },
  { header: 'Conversions', key: 'conversion' },
  { header: 'SUMMARY', key: 'summary' },
  { header: 'Call_Date', key: 'call_date' },
  { header: 'Number of atempts', key: 'num_attempts' },
  { header: 'SENTIMENT', key: 'sentiment' },
  { header: 'Session_id', key: 'last_session_id' },
  { header: 'Channel', key: 'channel' },
  { header: 'Model', key: 'model' },
  { header: 'Seating', key: 'seating' },
];

export const SAISAMARTH_COLUMNS: DealerColumn[] = [
  { header: 'Lead_ID', key: 'lead_id' },
  { header: 'Full_Name', key: 'full_name' },
  { header: 'Phone', key: 'phone' },
  { header: 'City', key: 'city' },
  { header: 'Pincode', key: 'pincode' },
  { header: 'Language', key: 'language' },
  { header: 'Lead_Source', key: 'lead_source' },
  { header: 'Cohort', key: 'cohort' },
  { header: 'Campaign_ID', key: 'campaign_id' },
  { header: 'Session ID', key: 'last_session_id' },
  { header: 'Call Triggered', key: 'call_triggered' },
  { header: 'Origin', key: 'origin' },
  { header: 'Lead_Timeline', key: 'lead_timeline' },
  { header: 'Outcome', key: 'outcome' },
  { header: 'Disposition', key: 'disposition' },
  { header: 'Disposition_detail', key: 'disposition_detail' },
  { header: 'Summary', key: 'summary' },
  { header: 'Manual_Disposition_detail', key: 'manual_disposition_detail' },
  { header: 'Conversion', key: 'conversion' },
  { header: 'Call_Date', key: 'call_date' },
  { header: 'No. of Attempts', key: 'num_attempts' },
  { header: 'SENTIMENT', key: 'sentiment' },
  { header: 'Recordings', key: 'recordings' },
  { header: 'Recording Duration', key: 'call_duration' },
  { header: 'Channel', key: 'channel' },
  { header: 'Model', key: 'model' },
  { header: 'Seating', key: 'seating' },
];

export const BIMAL_COLUMNS: DealerColumn[] = [
  { header: 'Lead_Id', key: 'lead_id' },
  { header: 'Full_Name', key: 'full_name' },
  { header: 'Phone', key: 'phone' },
  { header: 'City', key: 'city' },
  { header: 'PIncode', key: 'pincode' },
  { header: 'Language', key: 'language' },
  { header: 'Lead_Source', key: 'lead_source' },
  { header: 'Cohort', key: 'cohort' },
  { header: 'Showroom_Code', key: 'showroom_code' },
  { header: 'Campaign_ID', key: 'campaign_id' },
  { header: 'Last_session_id', key: 'last_session_id' },
  { header: 'Origin', key: 'origin' },
  { header: 'Lead_Timeline', key: 'lead_timeline' },
  { header: 'Call_Triggered', key: 'call_triggered' },
  { header: 'Outcome', key: 'outcome' },
  { header: 'Disposition', key: 'disposition' },
  { header: 'Summary', key: 'summary' },
  { header: 'Disposition_detail', key: 'disposition_detail' },
  { header: 'Manual_Disposition_detail', key: 'manual_disposition_detail' },
  { header: 'Conversion', key: 'conversion' },
  { header: 'Call_Date', key: 'call_date' },
  { header: 'Number_of_attempts', key: 'num_attempts' },
  { header: 'Sentiment', key: 'sentiment' },
  { header: 'Recordings', key: 'recordings' },
  { header: 'Call_Duration', key: 'call_duration' },
  { header: 'Model', key: 'model' },
  { header: 'Seating', key: 'seating' },
];

export const DEALER_CONFIGS: Record<string, DealerConfig> = {
  anant_cars: { name: 'Anant Cars', summarySource: 'lead_summary', columns: COMMON_COLUMNS },
  bimal: { name: 'Bimal', summarySource: 'lead_summary', columns: BIMAL_COLUMNS },
  anant_wa: {
    name: 'Anant WA', summarySource: 'lead_summary',
    columns: [
      { header: 'Lead_ID', key: 'lead_id' },
      { header: 'Full_Name', key: 'full_name' },
      { header: 'Phone', key: 'phone' },
      { header: 'City', key: 'city' },
      { header: 'Pincode', key: 'pincode' },
      { header: 'Language', key: 'language' },
      { header: 'Lead_Source', key: 'lead_source' },
      { header: 'Cohort', key: 'cohort' },
      { header: 'Campaign_ID', key: 'campaign_id' },
      { header: 'Call_Triggered', key: 'call_triggered' },
      { header: 'Lead_Timeline', key: 'lead_timeline' },
      { header: 'Outcome', key: 'outcome' },
      { header: 'VEHICLE_MODEL', key: 'vehicle_model' },
      { header: 'REG_NUMBER', key: 'reg_number' },
      { header: 'VIN_NUMBER', key: 'vin_number' },
      { header: 'Disposition', key: 'disposition' },
      { header: 'SUMMARY', key: 'summary' },
      { header: 'Conversion', key: 'conversion' },
      { header: 'History', key: 'session_history' },
      { header: 'Call_Date', key: 'call_date' },
      { header: 'No. of Attempts', key: 'num_attempts' },
      { header: 'SENTIMENT', key: 'sentiment' },
      { header: 'Session ID', key: 'last_session_id' },
      { header: 'Channel', key: 'channel' },
      { header: 'Model', key: 'model' },
      { header: 'Seating', key: 'seating' },
    ],
  },
  perfect_rider_wa: {
    name: 'Perfect Rider WA', summarySource: 'lead_summary',
    columns: [
      { header: 'Lead_ID', key: 'lead_id' },
      { header: 'Full_Name', key: 'full_name' },
      { header: 'Phone', key: 'phone' },
      { header: 'City', key: 'city' },
      { header: 'Pincode', key: 'pincode' },
      { header: 'Language', key: 'language' },
      { header: 'Lead_Source', key: 'lead_source' },
      { header: 'Cohort', key: 'cohort' },
      { header: 'Campaign_ID', key: 'campaign_id' },
      { header: 'Call_Triggered', key: 'call_triggered' },
      { header: 'Lead_Timeline', key: 'lead_timeline' },
      { header: 'Outcome', key: 'outcome' },
      { header: 'VEHICLE_MODEL', key: 'vehicle_model' },
      { header: 'REG_NUMBER', key: 'reg_number' },
      { header: 'VIN_NUMBER', key: 'vin_number' },
      { header: 'Disposition', key: 'disposition' },
      { header: 'SUMMARY', key: 'summary' },
      { header: 'Conversion', key: 'conversion' },
      { header: 'History', key: 'session_history' },
      { header: 'Call_Date', key: 'call_date' },
      { header: 'No. of Attempts', key: 'num_attempts' },
      { header: 'SENTIMENT', key: 'sentiment' },
      { header: 'Session ID', key: 'last_session_id' },
      { header: 'Channel', key: 'channel' },
      { header: 'Model', key: 'model' },
      { header: 'Seating', key: 'seating' },
    ],
  },
  chennai_ev: { name: 'ChennaiEV', summarySource: 'summary', columns: COMMON_COLUMNS },
  singhal: { name: 'Singhal', summarySource: 'lead_summary', columns: COMMON_COLUMNS },
  fortune_hyryder: { name: 'Fortune Hyryder', summarySource: 'lead_summary', columns: COMMON_COLUMNS },
  fortune_honda: { name: 'Fortune Honda', summarySource: 'lead_summary', columns: COMMON_COLUMNS },
  stellantis_wa: { name: 'Stellantis WA', summarySource: 'lead_summary', columns: STELLANTIS_COLUMNS },
  saisamarth: { name: 'Saisamarth', summarySource: 'lead_summary', columns: SAISAMARTH_COLUMNS },
  default: { name: 'Default', summarySource: 'disposition_detail', columns: COMMON_COLUMNS },
};

export const DISPOSITION_PRIORITY = BUSINESS_CONFIG.dispositionPriority;
export const TERMINAL_THRESHOLD = BUSINESS_CONFIG.terminalThreshold;
export const CONNECTED_SET = new Set(BUSINESS_CONFIG.connectedDispositions);
export const NOT_CONNECTED_SET = new Set(BUSINESS_CONFIG.notConnectedDispositions);
export const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

// Phone normalization
export function normalizePhone(raw: unknown): string | null {
  if (!raw) return null;
  let s = String(raw).trim();
  if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) {
    s = String(Math.round(parseFloat(s)));
  }
  const digits = s.replace(/\D/g, '');
  if (!digits) return null;
  if (digits.startsWith('91') && digits.length === 12) return digits.slice(2);
  if (digits.startsWith('0') && digits.length === 11) return digits.slice(1);
  if (digits.length === 10) return digits;
  if (digits.startsWith('91') && digits.length >= 12) return digits.slice(digits.length - 10);
  return null;
}

export function isPhoneLike(val: unknown): boolean {
  return /^\+?[\d\s\-()]{10,15}$/.test(String(val).trim());
}

export function isLikelyIndianMobile(phone: string): boolean {
  return /^[6-9]\d{9}$/.test(String(phone || ''));
}

// Date parsing
export function parseAutoEngageDate(str: string): Date | null {
  if (!str) return null;
  const s = String(str).trim();
  const m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4}),?\s+(\d{1,2}):(\d{2}):(\d{2})\s*(am|pm)?/i);
  if (m) {
    let [, dd, mm, yyyy, hh, min, sec, ampm] = m;
    let day = parseInt(dd, 10), month = parseInt(mm, 10), year = parseInt(yyyy, 10);
    let hour = parseInt(hh, 10), minute = parseInt(min, 10), second = parseInt(sec, 10);
    if (ampm) {
      const a = ampm.toLowerCase();
      if (a === 'pm' && hour !== 12) hour += 12;
      if (a === 'am' && hour === 12) hour = 0;
    }
    return new Date(year, month - 1, day, hour, minute, second);
  }
  const dmy = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (dmy) {
    const day = parseInt(dmy[1], 10), month = parseInt(dmy[2], 10), year = parseInt(dmy[3], 10);
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) return new Date(year, month - 1, day);
  }
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (iso) {
    const year = parseInt(iso[1], 10), month = parseInt(iso[2], 10), day = parseInt(iso[3], 10);
    const hour = parseInt(iso[4] || '0', 10), min = parseInt(iso[5] || '0', 10), sec = parseInt(iso[6] || '0', 10);
    if (month >= 1 && month <= 12 && day >= 1 && day <= 31) return new Date(year, month - 1, day, hour, min, sec);
  }
  return null;
}

export function formatCallDate(dateObj: Date | null): string {
  if (!dateObj) return '';
  const dd = String(dateObj.getDate()).padStart(2, '0');
  const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
  const yyyy = dateObj.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

export function isDateStr(val: unknown): boolean {
  return /\d{1,2}\/\d{1,2}\/\d{4}/.test(String(val));
}

export function ordinalSuffix(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export function formatTime12(dateObj: Date): string {
  let h = dateObj.getHours();
  const m = dateObj.getMinutes();
  const ampm = h >= 12 ? 'pm' : 'am';
  h = h % 12 || 12;
  return `${h}:${String(m).padStart(2, '0')}${ampm}`;
}

// Session detection helpers
export function detectPhonesFromObj(obj: Record<string, string>): string[] {
  const phones = new Set<string>();
  const exactNames = ['phone_number', 'phone', 'mobile', 'contact', 'contact_number'];
  for (const c of exactNames) {
    const n = normalizePhone(obj[c]);
    if (n) phones.add(n);
  }
  if (phones.size > 0) return Array.from(phones);
  // fallback: check raw values
  for (const val of Object.values(obj)) {
    if (!val) continue;
    const s = String(val).trim();
    if (isPhoneLike(s)) {
      const n = normalizePhone(s);
      if (n) phones.add(n);
    }
    if (s.length > 10) {
      const matches = s.match(/\+?(?:91|0)?[\s\-]?\d{10,12}\b/g);
      if (matches) {
        for (const m of matches) {
          const n = normalizePhone(m);
          if (n && isLikelyIndianMobile(n)) phones.add(n);
        }
      }
    }
  }
  return Array.from(phones);
}

export function detectRecording(obj: Record<string, string>): string {
  function cleanLink(str: string): string | null {
    if (!str) return null;
    let s = str.trim();
    const low = s.toLowerCase();
    if (low === 'null' || low === 'n/a' || low === 'none' || low === '-' || s === '') return null;
    return s;
  }
  function extractUrl(str: string): string | null {
    if (!str) return null;
    const m = str.match(/(?:https?|s3):\/\/[^\s"'<>\\[\]]+/i);
    return m ? m[0] : null;
  }

  const exactNames = ['call_recording', 'recording', 'recording_url', 'call_url', 'audio_url', 'audio', 'media_url', 'record_url', 'call_record'];
  for (const c of exactNames) {
    if (obj[c]) {
      const val = cleanLink(obj[c]);
      if (val) {
        const url = extractUrl(val);
        return url || val;
      }
    }
  }
  for (const [k, v] of Object.entries(obj)) {
    if (!v || k === '__raw') continue;
    if (/record|audio|media/i.test(k)) {
      const clean = cleanLink(v);
      if (!clean) continue;
      const url = extractUrl(clean);
      if (url) return url;
      if (clean.length > 5 && !clean.includes('{')) return clean;
    }
  }
  return '';
}

export function detectDate(obj: Record<string, string>): string {
  const candidates = ['created', 'date', 'start_time', 'timestamp', 'call_date'];
  for (const c of candidates) {
    if (obj[c] && isDateStr(obj[c])) return obj[c];
  }
  for (const val of Object.values(obj)) {
    if (typeof val === 'string' && isDateStr(val)) return val;
  }
  return '';
}

export function detectSummary(obj: Record<string, string>): string {
  const candidates = ['summary', 'call_summary', 'conversation_summary', 'notes'];
  for (const c of candidates) {
    if (obj[c] && obj[c].length > 3) return obj[c];
  }
  return '';
}

export function detectSentiment(obj: Record<string, string>): string {
  const candidates = ['sentiment_score', 'sentiment', 'score'];
  for (const c of candidates) {
    if (obj[c] !== undefined && obj[c] !== '') return obj[c];
  }
  return '';
}

export function detectChannel(obj: Record<string, string>): string {
  const candidates = ['channel', 'call_channel', 'communication_channel'];
  for (const c of candidates) {
    if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();
  }
  return '';
}

export function detectDuration(obj: Record<string, string>): string {
  const candidates = ['duration', 'call_duration', 'recording_duration', 'talk_time'];
  for (const c of candidates) {
    if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();
  }
  return '';
}

export function detectSessionId(obj: Record<string, string>): string {
  const candidates = ['session_id', 'id', 'last_session_id'];
  for (const c of candidates) {
    if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();
  }
  return '';
}

export function detectSessionDisposition(obj: Record<string, string>): string {
  const candidates = ['disposition_detail', 'disposition', 'call_disposition'];
  for (const c of candidates) {
    if (obj[c] !== undefined && obj[c] !== '') return String(obj[c]).trim();
  }
  return '';
}

export function deriveSeating(seating: string, model: string): string {
  if (seating && seating.trim() !== '') return seating.trim();
  if (!model) return '';
  const m = model.toLowerCase();
  for (const rule of BUSINESS_CONFIG.seatingRules) {
    if (rule.matches.some(term => m.includes(term))) return rule.value;
  }
  return '';
}

export function cellToString(val: unknown): string {
  if (val === undefined || val === null || val === '') return '';
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return String(val);
    if (val > 999999 && Math.abs(val - Math.round(val)) < 0.01) return String(Math.round(val));
    return String(val);
  }
  let s = String(val).trim();
  if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) {
    const n = parseFloat(s);
    if (isFinite(n) && n > 999999) return String(Math.round(n));
  }
  return s;
}

export function getDispositionPriority(d: string): number {
  if (!d) return 1;
  return DISPOSITION_PRIORITY[d.trim().toLowerCase()] ?? 1;
}

// Column detection
export function getColumnNames(rows: Record<string, string>[]): Set<string> {
  const cols = new Set<string>();
  for (const row of rows) {
    Object.keys(row || {}).forEach(k => {
      if (k !== '__raw') cols.add(k);
    });
    if (cols.size) break;
  }
  return cols;
}

export function getMissingColumnGroups(rows: Record<string, string>[], groups: { label: string; candidates: string[] }[]): string[] {
  const cols = getColumnNames(rows);
  return groups
    .filter(group => !group.candidates.some(candidate => cols.has(candidate)))
    .map(group => group.label);
}

export function addQualityWarning(warnings: QualityWarning[], level: string, title: string, detail: string) {
  warnings.push({ level, title, detail });
}

export function buildQualityReport(
  rows1: Record<string, string>[],
  rows2: Record<string, string>[],
  allLeads: { row: Record<string, string>; phone: string }[],
  sessionGroups: Record<string, Record<string, string>[]>,
  sessionMap: Record<string, SessionEntry>,
  output: Record<string, string>[],
  callTriggered: string,
): QualityReport {
  const validation = BUSINESS_CONFIG.validation;
  const leadPhoneCounts = new Map<string, number>();
  const invalidLeadRows: { rowNumber: number; name: string; rawPhone: string }[] = [];

  rows1.forEach((row, index) => {
    const rawPhone = row['phone_number'] || row['phone'] || row['mobile'] || '';
    const phone = normalizePhone(rawPhone);
    if (!phone) {
      invalidLeadRows.push({ rowNumber: index + 2, name: row['person_name'] || '', rawPhone: rawPhone || '(blank)' });
      return;
    }
    leadPhoneCounts.set(phone, (leadPhoneCounts.get(phone) || 0) + 1);
  });

  const duplicatePhones = Array.from(leadPhoneCounts.entries())
    .filter(([, count]) => count > 1)
    .map(([phone, count]) => ({ phone, count }));

  let sessionRowsWithPhone = 0;
  const sessionRowsWithoutPhone: { rowNumber: number }[] = [];
  rows2.forEach((row, index) => {
    const phones = detectPhonesFromObj(row).filter(isLikelyIndianMobile);
    if (phones.length) sessionRowsWithPhone += 1;
    else sessionRowsWithoutPhone.push({ rowNumber: index + 2 });
  });

  const sessionPhones = Object.keys(sessionGroups).filter(isLikelyIndianMobile);
  const sessionOnlyPhones = sessionPhones.filter(phone => !leadPhoneCounts.has(phone));
  const unmatchedLeads = output.filter(r => !sessionMap[r.phone]);
  const matchedLeadCount = output.length - unmatchedLeads.length;
  const unknownDispositionRows = output.filter(r => r.outcome === 'Unknown');
  const sessionSelectionCounts = { recording: 0, summary: 0, fallback: 0 };
  Object.values(sessionMap).forEach(session => {
    const reason = session.selectionReason || 'fallback';
    (sessionSelectionCounts as Record<string, number>)[reason] = ((sessionSelectionCounts as Record<string, number>)[reason] || 0) + 1;
  });

  const missingFile1Required = getMissingColumnGroups(rows1, validation.file1RequiredGroups);
  const missingFile1Recommended = getMissingColumnGroups(rows1, validation.file1RecommendedGroups);
  const missingFile2Recommended = getMissingColumnGroups(rows2, validation.file2RecommendedGroups);
  const warnings: QualityWarning[] = [];

  if (!rows1.length) addQualityWarning(warnings, 'danger', 'File 1 has no data rows', 'Audience & Leads parsed successfully, but no lead rows were found.');
  if (!rows2.length) addQualityWarning(warnings, 'danger', 'File 2 has no data rows', 'Sessions parsed successfully, but no session rows were found.');
  if (missingFile1Required.length) addQualityWarning(warnings, 'danger', 'File 1 required columns missing', `Missing: ${missingFile1Required.join(', ')}.`);
  if (invalidLeadRows.length) addQualityWarning(warnings, 'warn', 'Rows skipped because phone is invalid', `${invalidLeadRows.length} File 1 row(s) were skipped by the existing phone normalization rule.`);
  if (duplicatePhones.length) addQualityWarning(warnings, 'warn', 'Duplicate File 1 phone numbers found', `${duplicatePhones.length} phone number(s) appear more than once in Audience & Leads.`);
  if (unmatchedLeads.length) addQualityWarning(warnings, 'warn', 'Processed leads without a session match', `${unmatchedLeads.length} processed lead(s) did not match any Sessions row.`);
  if (sessionOnlyPhones.length) addQualityWarning(warnings, 'warn', 'Sessions not present in File 1', `${sessionOnlyPhones.length} session phone number(s) were not present in Audience & Leads.`);
  if (unknownDispositionRows.length) {
    const names = Array.from(new Set(unknownDispositionRows.map(r => r.disposition || '(blank)'))).slice(0, 6);
    addQualityWarning(warnings, 'warn', 'Unknown dispositions need review', `${unknownDispositionRows.length} lead(s) mapped to Unknown. Examples: ${names.join(', ')}.`);
  }
  if (sessionRowsWithoutPhone.length) addQualityWarning(warnings, 'warn', 'Session rows without detectable phone', `${sessionRowsWithoutPhone.length} File 2 row(s) had no detectable 10 digit phone.`);
  if (!callTriggered) addQualityWarning(warnings, 'warn', 'Call triggered text is empty', 'No valid session date range was detected from File 2.');
  if (missingFile1Recommended.length) addQualityWarning(warnings, 'info', 'File 1 optional columns missing', `Missing: ${missingFile1Recommended.join(', ')}.`);
  if (missingFile2Recommended.length) addQualityWarning(warnings, 'info', 'File 2 optional columns missing', `Missing: ${missingFile2Recommended.join(', ')}.`);
  if (!warnings.length) addQualityWarning(warnings, 'info', 'No review issues found', 'The batch passed validation and reconciliation checks.');

  const metrics = [
    { label: 'Valid leads', value: output.length, tone: 'blue' },
    { label: 'Matched leads', value: matchedLeadCount, tone: 'green' },
    { label: 'Unmatched leads', value: unmatchedLeads.length, tone: unmatchedLeads.length ? 'amber' : 'green' },
    { label: 'Skipped rows', value: invalidLeadRows.length, tone: invalidLeadRows.length ? 'red' : 'green' },
    { label: 'Duplicate phones', value: duplicatePhones.length, tone: duplicatePhones.length ? 'amber' : 'green' },
    { label: 'Unknown dispositions', value: unknownDispositionRows.length, tone: unknownDispositionRows.length ? 'amber' : 'green' },
    { label: 'Selected by recording', value: sessionSelectionCounts.recording, tone: 'green' },
    { label: 'Selected by summary', value: sessionSelectionCounts.summary, tone: 'blue' },
    { label: 'Selection fallback', value: sessionSelectionCounts.fallback, tone: sessionSelectionCounts.fallback ? 'amber' : 'green' },
  ];

  const samples: { title: string; rows: string[] }[] = [];
  if (invalidLeadRows.length) samples.push({ title: 'Invalid File 1 phones', rows: invalidLeadRows.slice(0, 5).map(r => `Row ${r.rowNumber}: ${r.rawPhone}${r.name ? ' - ' + r.name : ''}`) });
  if (duplicatePhones.length) samples.push({ title: 'Duplicate File 1 phones', rows: duplicatePhones.slice(0, 5).map(r => `${r.phone} appears ${r.count} times`) });
  if (unmatchedLeads.length) samples.push({ title: 'Leads without session match', rows: unmatchedLeads.slice(0, 5).map(r => `${r.phone}${r.full_name ? ' - ' + r.full_name : ''}`) });
  if (sessionOnlyPhones.length) samples.push({ title: 'Session-only phones', rows: sessionOnlyPhones.slice(0, 5) });
  if (unknownDispositionRows.length) samples.push({ title: 'Unknown dispositions', rows: unknownDispositionRows.slice(0, 5).map(r => `${r.phone}: ${r.disposition || '(blank)'}`) });
  samples.push({
    title: 'Session selection method',
    rows: [
      `Recording priority: ${sessionSelectionCounts.recording}`,
      `Summary priority: ${sessionSelectionCounts.summary}`,
      `Fallback latest row: ${sessionSelectionCounts.fallback}`,
    ],
  });

  const reviewCount = warnings.filter(w => w.level !== 'info').length;
  return {
    status: reviewCount ? `${reviewCount} review item${reviewCount === 1 ? '' : 's'}` : 'Clean batch',
    subtitle: 'This report explains batch health only. It does not change Zoho formulas, copy output, or Excel export columns.',
    metrics,
    warnings,
    samples,
    counts: {
      file1Rows: rows1.length,
      file2Rows: rows2.length,
      sessionRowsWithPhone,
      sessionRowsWithoutPhone: sessionRowsWithoutPhone.length,
      sessionOnlyPhones: sessionOnlyPhones.length,
      allLeads: allLeads.length,
    },
  };
}

// Anant WA helpers
export function isAnantWAConfig(dealerKey: string): boolean {
  return dealerKey === 'anant_wa';
}

export function formatAnantWAFields(record: Record<string, string>): Record<string, string> {
  return {
    ...record,
    conversion: '',
    session_history: record.session_history || '',
    last_session_id: record.last_session_id || '',
    pincode: record.pincode?.toLowerCase() || '',
    channel: record.channel || '',
    num_attempts: record.num_attempts ? 'No. of Attempts' : '0',
    sentiment: record.sentiment?.toUpperCase() || '',
  };
}
