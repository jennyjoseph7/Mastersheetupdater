import { classifyDisposition, isServiceBooked, isServiceCompleted, isNotInterested, isFeedbackOrEscalation, extractPerfectRidersLocation, extractPerfectRidersCRE } from './classify-utils';
import { detectHistory, formatHistoryForPrompt } from '@/lib/ai/history-helpers';
import { parseExcelSerialDate } from '@/lib/date-utils';

/** Extracted session data for a single session row — used when outputting one row per call attempt. */
export interface SessionRowData {
  status: string;
  disposition: string;
  duration: string;
  startTime: string;
  summary: string;
  recording: string;
  sentiment: string;
  recordingDuration: string;
  lastSessionId: string;
  serviceType: string;
  history_text: string;
}

export function extractSessionData(row: Record<string, string>): SessionRowData {
  const histKey = detectHistory(row);
  const histValue = histKey ? row[histKey] : '';
  return {
    status: get(row, ['status', 'session_status', 'call_status', 'conversation_status']),
    disposition: get(row, ['updated_disposition', 'disposition_detail', 'disposition', 'disposition_details', 'call_disposition']),
    duration: get(row, ['duration', 'call_duration', 'talk_time', 'total_duration']),
    startTime: detectDate(row),
    summary: get(row, ['summary', 'call_summary', 'conversation_summary', 'notes', 'remarks']),
    recording: detectRecording(row),
    sentiment: get(row, ['sentiment_score', 'sentiment', 'sentiment_label', 'score']),
    recordingDuration: get(row, ['duration', 'call_duration', 'recording_length', 'recording_time', 'audio_duration']),
    lastSessionId: get(row, ['last_session_id', 'session_id', 'sessionid', 'id', 'call_id']),
    serviceType: get(row, ['service_type', 'service_type_session']),
    history_text: formatHistoryForPrompt(histValue),
  };
}
import { clean, canonicalHeader, normalizePhone, isPhoneLike } from '@/lib/data-pipeline';

export interface QualityIssue {
  level: string;
  text: string;
  blocking: boolean;
}

export interface QualityReport {
  title: string;
  state: 'blocked' | 'review' | 'clean';
  canExport: boolean;
  warnings: QualityIssue[];
  samples: { title: string; rows: string[] }[];
  counts: Record<string, number>;
  roleInfo: RoleInfo;
  summary: string[];
}

interface RoleInfo {
  filesSwapped: boolean;
  confidence: string;
  margin: number;
  defaultScore: number;
  swappedScore: number;
  file1: RoleScore;
  file2: RoleScore;
}

interface RoleScore {
  lead: number;
  session: number;
}

interface DealerConfig {
  name: string;
  workflow: string;
  mode: string;
  leadColumns: string[];
  sessionColumns: string[];
}

export interface OutputColumn {
  header: string;
  key: string;
}

export interface SessionData {
  row: Record<string, string> | null;
  count: number;
  status: string;
  disposition: string;
  duration: string;
  startTime: string;
  summary: string;
  recording: string;
  sentiment: string;
  recordingDuration: string;
  lastSessionId: string;
  serviceType: string;
  history_raw: string;
  history_text: string;
}

export function getOutputColumnsForDealer(dealerKey: string): OutputColumn[] {
  const schemas: Record<string, OutputColumn[]> = {
    pressana_service_feedback: [
      { header: 'PHONE_NUMBER', key: 'phone_number' }, { header: 'VEHICLE_MODEL', key: 'vehicle_model' },
      { header: 'STATUS', key: 'session_status' }, { header: 'SUMMARY', key: 'summary' },
      { header: 'DISPOSITION_DETAILS', key: 'disposition' }, { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT_SCORE', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'DURATION', key: 'duration' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'SESSION_ID', key: 'last_session_id' },
      { header: 'INTERESTED', key: 'interested' }, { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },
      { header: 'AUTONGAGE', key: 'autongage_disposition' },
    ],
    pressana_post_service_feedback: [
      { header: 'PHONE_NUMBER', key: 'phone_number' }, { header: 'LAST_SERVICE_DATE', key: 'last_service_date' },
      { header: 'STATUS', key: 'session_status' }, { header: 'SUMMARY', key: 'summary' },
      { header: 'DISPOSITION_DETAILS', key: 'disposition' }, { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'RECORDING_DURATION', key: 'duration' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'LAST_SESSION_ID', key: 'last_session_id' },
      { header: 'INTERESTED', key: 'interested' }, { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },
      { header: 'AUTONGAGE_DISPOSITION', key: 'autongage_disposition' },
    ],
    ambal_service: [
      { header: 'PERSON_NAME', key: 'person_name' }, { header: 'PHONE_NUMBER', key: 'phone_number' },
      { header: 'REG_NUMBER', key: 'reg_number' }, { header: 'VEHICLE_MODEL', key: 'vehicle_model' },
      { header: 'VIN', key: 'vin_number' }, { header: 'STATUS', key: 'session_status' },
      { header: 'DISPOSITION_DETAILS', key: 'disposition' }, { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'SUMMARY', key: 'summary' }, { header: 'CALL_DATE', key: 'call_date' },
      { header: 'SENTIMENT', key: 'sentiment_score' }, { header: 'RECORDINGS', key: 'call_recording' },
      { header: 'DURATION', key: 'duration' }, { header: 'CAMPAIGN_ID', key: 'campaign_id' },
      { header: 'SESSION_ID', key: 'last_session_id' }, { header: 'CUSTOMER_SCORE', key: 'customer_score' },
      { header: 'NEXT_SERVICE_DUE', key: 'next_service_due' }, { header: 'ODOMETER_READING', key: 'odometer_reading' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'PURPOSE_OF_VISIT', key: 'purpose_of_visit' },
    ],
    perfect_riders_service: [
      { header: 'WORKSHOP_CODE', key: 'workshop_code' }, { header: 'PERSON_NAME', key: 'person_name' },
      { header: 'PHONE_NUMBER', key: 'phone_number' }, { header: 'VEHICLE_MODEL', key: 'vehicle_model' },
      { header: 'REG_NUMBER', key: 'reg_number' }, { header: 'VIN_NUMBER', key: 'vin_number' },
      { header: 'STATUS', key: 'session_status' }, { header: 'SUMMARY', key: 'summary' },
      { header: 'DISPOSITION_DETAILS', key: 'disposition' }, { header: 'Updated Disposition', key: 'updated_disposition' },
      { header: 'LAST_SERVICE_DATE', key: 'last_service_date' }, { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT_SCORE', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'DURATION', key: 'duration' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'SESSION_ID', key: 'last_session_id' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'INTERESTED', key: 'interested' }, { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },
    ],
    fortune_service: [
      { header: 'PERSON_NAME', key: 'person_name' }, { header: 'PHONE_NUMBER', key: 'phone_number' },
      { header: 'VEHICLE_MODEL', key: 'vehicle_model' }, { header: 'REG_NUMBER', key: 'reg_number' },
      { header: 'VIN_NUMBER', key: 'vin_number' }, { header: 'SUMMARY', key: 'summary' },
      { header: 'STATUS', key: 'session_status' }, { header: 'DISPOSITION_DETAILS', key: 'disposition_detail' },
      { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'DURATION', key: 'duration' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'SESSION_ID', key: 'last_session_id' },
      { header: 'INTERESTED', key: 'interested' }, { header: 'SERVICE_TYPE', key: 'service_type' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' }, { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },
    ],
    saisamarth: [
      { header: 'PERSON_NAME', key: 'person_name' }, { header: 'PHONE_NUMBER', key: 'phone_number' },
      { header: 'VEHICLE_MODEL', key: 'vehicle_model' }, { header: 'REG_NUMBER', key: 'reg_number' },
      { header: 'VIN_NUMBER', key: 'vin_number' }, { header: 'SUMMARY', key: 'summary' },
      { header: 'STATUS', key: 'session_status' }, { header: 'DISPOSITION_DETAILS', key: 'disposition_detail' },
      { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'DURATION', key: 'duration' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'SESSION_ID', key: 'last_session_id' },
      { header: 'INTERESTED', key: 'interested' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' }, { header: 'NUMBER OF ATTEMPTS', key: 'number_of_attempts' },
    ],
    icare_feedback: [
      { header: 'PERSON_NAME', key: 'person_name' }, { header: 'PHONE_NUMBER', key: 'phone_number' },
      { header: 'ID', key: 'id_salt' }, { header: 'SHOWROOM_CODE', key: 'lead_code_for_dealership' },
      { header: 'SUMMARY', key: 'summary' }, { header: 'STATUS', key: 'session_status' },
      { header: 'DISPOSITION_DETAILS', key: 'disposition' }, { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'RECORDING_DURATION', key: 'duration' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'LAST_SESSION_ID', key: 'last_session_id' },
      { header: 'SATISFIED', key: 'satisfied' }, { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'AUTONGAGE_DISPOSITION', key: 'autongage_disposition' },
    ],
    bullmen_service: [
      { header: 'PERSON_NAME', key: 'person_name' }, { header: 'PHONE_NUMBER', key: 'phone_number' },
      { header: 'VEHICLE_MODEL', key: 'vehicle_model' }, { header: 'REG_NUMBER', key: 'reg_number' },
      { header: 'VIN', key: 'vin_number' }, { header: 'DEALER_CODE', key: 'dealer_code' },
      { header: 'SUMMARY', key: 'summary' }, { header: 'STATUS', key: 'session_status' },
      { header: 'DISPOSITION_DETAILS', key: 'disposition' }, { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' },
      { header: 'CALL_DATE', key: 'call_date' }, { header: 'SENTIMENT', key: 'sentiment_score' },
      { header: 'RECORDINGS', key: 'call_recording' }, { header: 'DURATION', key: 'duration' },
      { header: 'CAMPAIGN_ID', key: 'campaign_id' }, { header: 'LAST_SESSION_ID', key: 'last_session_id' },
      { header: 'LAST_SERVICE_DATE', key: 'last_service_date' }, { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },
      { header: 'INTERESTED', key: 'interested' }, { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'AUTONGAGE_DISPOSITION', key: 'autongage_disposition' },
    ],
    suryabala_service: [
      { header: 'PERSON_NAME', key: 'person_name' }, { header: 'PHONE_NUMBER', key: 'phone_number' },
      { header: 'VEHICLE_MODEL', key: 'vehicle_model' }, { header: 'REG_NUMBER', key: 'reg_number' },
      { header: 'VIN_NUMBER', key: 'vin_number' }, { header: 'SUMMARY', key: 'summary' },
      { header: 'STATUS', key: 'session_status' }, { header: 'DISPOSITION_DETAILS', key: 'disposition' },
      { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' }, { header: 'CALL_DATE', key: 'call_date' },
      { header: 'SENTIMENT', key: 'sentiment_score' }, { header: 'RECORDINGS', key: 'call_recording' },
      { header: 'DURATION', key: 'duration' }, { header: 'CAMPAIGN_ID', key: 'campaign_id' },
      { header: 'SESSION_ID', key: 'last_session_id' }, { header: 'INTERESTED', key: 'interested' },
      { header: 'SERVICE_TYPE', key: 'last_service_type' }, { header: 'NEXT_SERVICE_DATE', key: 'next_service_due' },
      { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
      { header: 'NUMBER_OF_ATTEMPTS', key: 'number_of_attempts' },
    ],
    fortune_toyota_wa: [
      { header: 'Lead_ID', key: 'lead_id' },
      { header: 'Full_Name', key: 'full_name' },
      { header: 'Phone', key: 'phone_number' },
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
      { header: 'Seating', key: 'seating' },
    ],
    perfect_rider_wa: [
      { header: 'Lead_ID', key: 'lead_id' },
      { header: 'Full_Name', key: 'full_name' },
      { header: 'Phone', key: 'phone_number' },
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
      { header: 'No. of Attempts', key: 'number_of_attempts' },
      { header: 'SENTIMENT', key: 'sentiment_score' },
      { header: 'Session ID', key: 'last_session_id' },
      { header: 'Channel', key: 'channel' },
      { header: 'Seating', key: 'seating' },
    ],
  };
  return schemas[dealerKey] || [
    { header: 'PHONE_NUMBER', key: 'phone_number' }, { header: 'SUMMARY', key: 'summary' },
    { header: 'STATUS', key: 'session_status' }, { header: 'DISPOSITION_DETAILS', key: 'disposition' },
    { header: 'UPDATED_DISPOSITION', key: 'updated_disposition' }, { header: 'CALL_DATE', key: 'call_date' },
    { header: 'RECORDINGS', key: 'call_recording' }, { header: 'CAMPAIGN_ID', key: 'campaign_id' },
    { header: 'ORIGIN', key: 'origin' }, { header: 'LEAD_TIMELINE', key: 'lead_timeline' },
  ];
}

export function sessionScore(row: Record<string, string>): number {
  let score = 0;
  const date = row.start_time ? new Date(row.start_time) : null;
  if (date && !isNaN(date.getTime())) score += date.getTime() / 100000000;
  if (row.disposition_detail || row.disposition) score += 10000;
  if (row.call_recording) score += 1000;
  if (row.summary) score += 500;
  if (row.status) score += 200;
  return score;
}

export function buildSessionMap(rows: Record<string, string>[]): { map: Record<string, SessionData>; groups: Record<string, Record<string, string>[]> } {
  const groups: Record<string, Record<string, string>[]> = {};
  for (const row of rows) {
    for (const phone of detectPhones(row)) {
      if (!groups[phone]) groups[phone] = [];
      groups[phone].push(row);
    }
  }
  const map: Record<string, SessionData> = {};
  for (const [phone, sessions] of Object.entries(groups)) {
    const best = sessions.slice().sort((a, b) => sessionScore(b) - sessionScore(a))[0];
    const histKey = detectHistory(best);
    map[phone] = {
      row: best,
      count: sessions.length,
      status: get(best, ['status', 'session_status', 'call_status', 'conversation_status']),
      disposition: get(best, ['updated_disposition', 'disposition_detail', 'disposition', 'disposition_details', 'call_disposition']),
      duration: get(best, ['duration', 'call_duration', 'talk_time', 'total_duration']),
      startTime: detectDate(best),
      summary: get(best, ['summary', 'call_summary', 'conversation_summary', 'notes', 'remarks']),
      recording: detectRecording(best),
      sentiment: get(best, ['sentiment_score', 'sentiment', 'sentiment_label', 'score']),
      recordingDuration: get(best, ['duration', 'call_duration', 'recording_length', 'recording_time', 'audio_duration']),
      lastSessionId: get(best, ['last_session_id', 'session_id', 'sessionid', 'id', 'call_id']),
      serviceType: get(best, ['service_type', 'service_type_session']),
      history_raw: histKey,
      history_text: formatHistoryForPrompt(histKey),
    };
  }
  return { map, groups };
  return { map, groups };
}

export function get(row: Record<string, string> | undefined, candidates: string[]): string {
  if (!row) return '';
  for (const c of candidates) {
    if (row[c] !== undefined && clean(row[c]) !== '') return clean(row[c]);
  }
  return '';
}

export function detectDate(row: Record<string, string>): string {
  return get(row, ['start_time', 'start_date', 'call_start_time', 'call_time', 'created', 'created_at', 'date', 'timestamp', 'call_date', 'updated', 'updated_at']);
}

export function detectRecording(row: Record<string, string>): string {
  const direct = get(row, ['call_recording', 'recording', 'recording_url', 'call_url', 'audio_url', 'media_url']);
  if (direct) return direct;
  for (const [k, v] of Object.entries(row)) {
    if (k === '__raw' || !/record|audio|media/i.test(k)) continue;
    if (clean(v)) return clean(v);
  }
  return '';
}

function detectPhones(obj: Record<string, string>): string[] {
  const phones = new Set<string>();
  const exactNames = ['phone_number', 'phone', 'mobile', 'contact', 'contact_number', 'customer_phone', 'mobile_number'];
  for (const c of exactNames) {
    const n = normalizePhone(obj[c]);
    if (n) phones.add(n);
  }
  for (const val of Object.values(obj)) {
    const s = clean(val);
    if (!s) continue;
    if (isPhoneLike(s)) { const n = normalizePhone(s); if (n) phones.add(n); }
    const matches = s.match(/\+?(?:91|0)?[\s-]?\d{10,12}\b/g);
    if (matches) for (const m of matches) { const n = normalizePhone(m); if (n) phones.add(n); }
  }
  return Array.from(phones);
}

export function scoreFileRole(rows: Record<string, string>[]): RoleScore {
  if (!rows.length) return { lead: 0, session: 0 };
  const cols = new Set(Object.keys(rows[0]).filter(k => k !== '__raw'));
  const leadHints = ['phone_number', 'person_name', 'customer_name', 'name', 'campaign_id', 'vehicle_model', 'reg_number', 'vin_number', 'next_service_due', 'last_service_date', 'lead_tags', 'lead_id'];
  const sessionHints = ['status', 'session_status', 'call_status', 'summary', 'call_summary', 'disposition_detail', 'disposition', 'duration', 'start_time', 'start_date', 'created', 'call_date', 'sentiment_score', 'sentiment', 'call_recording', 'recording_url', 'session_id', 'last_session_id'];
  let lead = 0, session = 0;
  for (const key of leadHints) if (cols.has(key)) lead++;
  for (const key of sessionHints) if (cols.has(key)) session++;
  return { lead, session };
}

const ROLE_CONFIDENCE_MARGIN = 2;

export function evaluateFileRoles(role1: RoleScore, role2: RoleScore): RoleInfo {
  const defaultScore = role1.lead + role2.session;
  const swappedScore = role2.lead + role1.session;
  const filesSwapped = swappedScore > defaultScore;
  const bestScore = Math.max(defaultScore, swappedScore);
  const margin = Math.abs(defaultScore - swappedScore);
  const confidence: string = bestScore === 0 ? 'unknown' : margin >= ROLE_CONFIDENCE_MARGIN ? 'high' : 'low';
  return { filesSwapped, confidence, margin, defaultScore, swappedScore, file1: role1, file2: role2 };
}

export function parseAutoEngageDate(str: string): Date | null {
  if (!str) return null;
  const s = String(str).trim();
  const num = Number(s);
  if (!isNaN(num)) {
    if (num > 1000000000000) return new Date(num);
    if (num > 1000000000) return new Date(Math.floor(num) * 1000);
    if (num > 30000 && num < 100000) return parseExcelSerialDate(num);
  }
  const dmyTime = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4}),?\s*(\d{1,2})?:?(\d{2})?:?(\d{2})?\s*(am|pm)?/i);
  if (dmyTime) {
    let [, dd, mm, yyyy, hh, min, sec, ampm] = dmyTime;
    const day = parseInt(dd, 10), month = parseInt(mm, 10), year = parseInt(yyyy, 10);
    let hour = parseInt(hh || '0', 10), minute = parseInt(min || '0', 10), second = parseInt(sec || '0', 10);
    if (ampm) {
      const a = ampm.toLowerCase();
      if (a === 'pm' && hour !== 12) hour += 12;
      if (a === 'am' && hour === 12) hour = 0;
    }
    return new Date(year, month - 1, day, hour, minute, second);
  }
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?/);
  if (iso) return new Date(parseInt(iso[1], 10), parseInt(iso[2], 10) - 1, parseInt(iso[3], 10), parseInt(iso[4] || '0', 10), parseInt(iso[5] || '0', 10), parseInt(iso[6] || '0', 10));
  const parsed = new Date(s);
  return isNaN(parsed.getTime()) ? null : parsed;
}

export function formatDate(str: string): string {
  const d = parseAutoEngageDate(str);
  if (!d) return clean(str);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}/${d.getFullYear()}`;
}

export function convertEpochToIST(val: unknown): string {
  if (!val) return '';
  const num = typeof val === 'number' ? val : Number(String(val).trim());
  if (!isFinite(num) || num < 1000000000) return String(val).trim();
  const ts = num < 10000000000000 ? num * 1000 : num;
  const d = new Date(ts + (5.5 * 60 * 60 * 1000));
  if (isNaN(d.getTime())) return String(val).trim();
  return `${String(d.getUTCDate()).padStart(2, '0')}/${String(d.getUTCMonth() + 1).padStart(2, '0')}/${d.getUTCFullYear()}`;
}

function missingColumns(rows: Record<string, string>[], expected: string[]): string[] {
  if (!rows.length || !expected || expected.some(col => col.startsWith('Use '))) return [];
  const cols = new Set(Object.keys(rows[0]).filter(k => k !== '__raw'));
  return expected.filter(col => !cols.has(canonicalHeader(col)));
}

function sampleSourceRow(row: Record<string, string>, label: string): string {
  let raw: string[] = [];
  try { const p = JSON.parse(row.__raw || '[]'); if (Array.isArray(p)) raw = p; } catch { /* ignore */ }
  if (!raw.length) raw = Object.values(row).filter(v => clean(v)).slice(0, 4);
  const excerpt = raw.map(s => clean(s)).filter(Boolean).slice(0, 4).join(' | ');
  return excerpt ? `${label}: ${excerpt}` : label;
}

function getOutputFieldChecks(dealerKey: string, output: Record<string, string>[]): { key: string; label: string; level: string; count: number }[] {
  const keys = new Set(getOutputColumnsForDealer(dealerKey).map(col => col.key).filter(Boolean));
  const checks: { key: string; label: string; level: string; count: number }[] = [];
  if (keys.has('phone_number')) checks.push({ key: 'phone_number', label: 'Phone number', level: 'danger', count: 0 });
  if (keys.has('campaign_id')) checks.push({ key: 'campaign_id', label: 'Campaign ID', level: 'warn', count: 0 });
  if (keys.has('session_status')) checks.push({ key: 'session_status', label: 'Status', level: 'warn', count: 0 });
  if (keys.has('call_date')) checks.push({ key: 'call_date', label: 'Call date', level: 'warn', count: 0 });
  if (keys.has('disposition')) checks.push({ key: 'disposition', label: 'Disposition details', level: 'warn', count: 0 });
  else if (keys.has('disposition_detail')) checks.push({ key: 'disposition_detail', label: 'Disposition details', level: 'warn', count: 0 });
  if (keys.has('person_name')) checks.push({ key: 'person_name', label: 'Person name', level: 'warn', count: 0 });
  if (keys.has('reg_number')) checks.push({ key: 'reg_number', label: 'Registration number', level: 'warn', count: 0 });
  if (keys.has('vin_number')) checks.push({ key: 'vin_number', label: 'VIN number', level: 'warn', count: 0 });
  if (keys.has('workshop_code')) checks.push({ key: 'workshop_code', label: 'Workshop code', level: 'warn', count: 0 });
  if (keys.has('last_service_date')) checks.push({ key: 'last_service_date', label: 'Last service date', level: 'warn', count: 0 });
  if (keys.has('next_service_due')) checks.push({ key: 'next_service_due', label: 'Next service date', level: 'warn', count: 0 });
  return checks.map(c => ({ ...c, count: output.filter(row => !clean(row[c.key])).length })).filter(c => c.count > 0);
}

export function buildQualityReport(params: {
  leadRows: Record<string, string>[];
  sessionRows: Record<string, string>[];
  filteredSessionRows: Record<string, string>[];
  leads: { row: Record<string, string>; phone: string }[];
  sessionGroups: Record<string, Record<string, string>[]>;
  output: Record<string, string>[];
  dealer: DealerConfig;
  dealerKey: string;
  roleInfo: RoleInfo;
}): QualityReport {
  const warnings: QualityIssue[] = [];
  const samples: { title: string; rows: string[] }[] = [];
  const leadPhones = new Map<string, number>();
  const invalidLeads: string[] = [];
  const { leadRows, sessionRows, filteredSessionRows, leads, sessionGroups, output, dealer, dealerKey, roleInfo } = params;

  leadRows.forEach((row, index) => {
    const phone = normalizePhone(get(row, ['phone_number', 'phone', 'mobile', 'contact_number', 'mobile_number']));
    if (!phone) invalidLeads.push(sampleSourceRow(row, `Lead row ${index + 2}`));
    else leadPhones.set(phone, (leadPhones.get(phone) || 0) + 1);
  });

  const leadPhoneSet = new Set(leads.map(item => item.phone));
  const duplicatePhones = Array.from(leadPhones.entries()).filter(([, count]) => count > 1);
  const sessionPhones = Object.keys(sessionGroups);
  const matched = output.filter(r => r._matched === 'true').length;
  const unmatched = output.filter(r => r._matched !== 'true');
  const unknownRows = output.filter(r => r.outcome === 'Unknown');
  const missingLeadCols = missingColumns(leadRows, dealer.leadColumns);
  const missingSessionCols = missingColumns(sessionRows, dealer.sessionColumns);
  const sessionsWithoutPhone = sessionRows.filter(row => !detectPhones(row).length).length;
  const sessionOnlyPhones = sessionPhones.filter(phone => !leadPhoneSet.has(phone));
  const missingOutputFields = getOutputFieldChecks(dealerKey, output);
  const outputKeys = new Set(getOutputColumnsForDealer(dealerKey).map(col => col.key).filter(Boolean));
  const missingRecordings = outputKeys.has('call_recording') ? output.filter(row => row._matched === 'true' && !clean(row.call_recording)).length : 0;

  // Drop-off tracking: session rows in → out
  const filteredNoPhoneRows = filteredSessionRows.filter(row => !detectPhones(row).length);
  const filteredNoPhone = filteredNoPhoneRows.length;
  const filteredWithPhone = filteredSessionRows.length - filteredNoPhone;
  const unmatchedSessions = Math.max(0, filteredWithPhone - output.length);

  if (roleInfo.filesSwapped) addQualityIssue(warnings, roleInfo.confidence === 'high' ? 'info' : 'warn', `Upload order auto-detected as swapped. Scores default=${roleInfo.defaultScore}, swapped=${roleInfo.swappedScore}.`);
  if (roleInfo.confidence !== 'high') addQualityIssue(warnings, 'warn', `Upload role confidence is ${roleInfo.confidence}.`);
  if (!leadRows.length) addQualityIssue(warnings, 'danger', 'Leads file has no data rows.');
  if (!sessionRows.length) addQualityIssue(warnings, 'danger', 'Sessions file has no data rows.');
  if (!output.length) addQualityIssue(warnings, 'danger', 'No master-sheet rows were produced.');
  if (output.length && sessionRows.length && matched === 0) addQualityIssue(warnings, 'danger', 'No processed leads matched a Sessions row.');
  if (invalidLeads.length) addQualityIssue(warnings, 'warn', `${invalidLeads.length} lead row(s) skipped — invalid phone.`);
  if (duplicatePhones.length) addQualityIssue(warnings, 'warn', `${duplicatePhones.length} duplicate lead phone(s) found.`);
  if (unmatched.length) addQualityIssue(warnings, 'warn', `${unmatched.length} lead(s) did not match a Sessions row.`);
  if (sessionOnlyPhones.length) addQualityIssue(warnings, 'info', `${sessionOnlyPhones.length} Sessions phone(s) not in Leads.`);
  if (sessionsWithoutPhone) addQualityIssue(warnings, 'warn', `${sessionsWithoutPhone} session row(s) had no phone in raw file.`);
  if (filteredNoPhone > 0) addQualityIssue(warnings, 'warn', `${filteredNoPhone} filtered session row(s) had no detectable phone.`);
  if (unmatchedSessions > 0) addQualityIssue(warnings, 'warn', `${unmatchedSessions} session row(s) had phones not matching any lead — no output produced.`);
  if (unknownRows.length) addQualityIssue(warnings, 'warn', `${unknownRows.length} row(s) mapped to Unknown. Review dispositions.`);
  for (const check of missingOutputFields) addQualityIssue(warnings, check.level, `${check.count} row(s) missing ${check.label}.`);
  if (missingRecordings) addQualityIssue(warnings, 'info', `${missingRecordings} matched row(s) have no recording.`);
  if (missingLeadCols.length) addQualityIssue(warnings, 'info', `Lead columns not found: ${missingLeadCols.join(', ')}.`);
  if (missingSessionCols.length) addQualityIssue(warnings, 'info', `Session columns not found: ${missingSessionCols.join(', ')}.`);

  const blocked = warnings.some(w => w.blocking);
  const review = warnings.some(w => w.level === 'warn' || w.level === 'danger');
  if (!warnings.length) addQualityIssue(warnings, 'ok', 'All checks passed.');

  if (invalidLeads.length) samples.push({ title: 'Invalid lead phones', rows: invalidLeads.slice(0, 5) });
  if (duplicatePhones.length) samples.push({ title: 'Duplicate lead phones', rows: duplicatePhones.slice(0, 5).map(([p, c]) => `${p} appears ${c} times`) });
  const unmatchedSamples = unmatched.slice(0, 5).map(r => `${r.phone_number}${r.person_name ? ' - ' + r.person_name : ''}`);
  if (unmatchedSamples.length) samples.push({ title: 'Unmatched leads', rows: unmatchedSamples });
  if (filteredNoPhoneRows.length) samples.push({ title: 'Filtered session rows with no phone', rows: filteredNoPhoneRows.slice(0, 5).map((r, i) => `Row ${i + 1}: ${Object.values(r).filter(v => clean(v)).slice(0, 3).join(' | ') || '(empty)'}`) });
  if (sessionOnlyPhones.length) samples.push({ title: 'Session phones not in leads', rows: sessionOnlyPhones.slice(0, 20) });
  if (unknownRows.length) samples.push({ title: 'Unknown outcomes', rows: unknownRows.slice(0, 5).map(r => `${r.phone_number}: ${r.disposition_detail || '(blank)'}`) });
  const missingFieldsMissing = missingOutputFields.filter(c => c.count > 0);
  if (missingFieldsMissing.length) samples.push({ title: 'Missing output fields', rows: missingFieldsMissing.map(c => `${c.label}: ${c.count} row(s)`) });
  if (!samples.length) samples.push({ title: 'No samples', rows: ['No invalid, duplicate, unmatched, or unknown rows to sample.'] });

  return {
    title: blocked ? 'Blocked - fix input files' : review ? 'Review needed' : 'Ready to copy',
    state: blocked ? 'blocked' : review ? 'review' : 'clean',
    canExport: output.length > 0 && !blocked,
    warnings, samples,
    counts: { leadRows: leadRows.length, sessionRows: sessionRows.length, filteredSessionRows: filteredSessionRows.length, leads: leads.length, matched, unmatched: unmatched.length, invalidLeads: invalidLeads.length, duplicatePhones: duplicatePhones.length, sessionPhones: sessionPhones.length, sessionOnlyPhones: sessionOnlyPhones.length, sessionsWithoutPhone, unknown: unknownRows.length, filteredNoPhone, unmatchedSessions },
    roleInfo,
    summary: [`${leads.length} valid lead(s)`, `${matched}/${output.length} output`, `${sessionRows.length} sessions → ${filteredSessionRows.length} filtered → ${output.length} output`, `${sessionPhones.length} session phone(s)`, `role confidence: ${roleInfo.confidence}`],
  };
}

function addQualityIssue(issues: QualityIssue[], level: string, text: string, blocking?: boolean) {
  issues.push({ level, text, blocking: blocking || level === 'danger' });
}
