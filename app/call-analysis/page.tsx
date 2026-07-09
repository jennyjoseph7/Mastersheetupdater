'use client';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import { readFileAsArrayBuffer, clean, esc, validateFileSync } from '@/lib/data-pipeline';
import * as XLSX from 'xlsx';
import styles from './call-analysis.module.css';

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

const DEALER_NAMES: Record<string, string> = {
  perfect_riders_service: 'Perfect Riders',
  fortune_service: 'Fortune',
  ambal_service: 'Ambal',
  bullmen_service: 'Bullmen',
  pressana_service_feedback: 'Pressana',
  pressana_post_service_feedback: 'Pressana Post',
  suryabala_service: 'Suryabala',
  icare_feedback: 'Icare',
};

const PRE_SALES_DISPOSITIONS: Record<string, string> = {
  "Voicemail": "Customer reached voicemail", "Rejected": "Customer rejected the offer",
  "Language barrier": "Language differences", "Is not decision maker": "Not the right person",
  "Will decide later, will purchase within 15 days": "Will purchase within 15 days",
  "Will decide later, will purchase within 1 to 3 months": "Will purchase within 1-3 months",
  "Will decide later, exploring options": "Exploring options", "No buying intent": "No purchase intent",
  "Just Exploring": "Just browsing", "Will call showroom themselves": "Will contact dealer directly",
  "Requested Callback": "Asked for callback", "Purchased elsewhere": "Already bought elsewhere",
  "Enquired for Pricing": "Asked about price", "Enquired for Specifications": "Asked about specs",
  "Enquired for Test Drive": "Asked for test drive", "Enquired for Showroom Visit": "Asked for showroom visit",
  "Enquired for Brochure": "Asked for brochure", "Enquired for Dealership Details": "Asked for dealer info",
  "Enquired for Others": "Asked other questions", "Comparing with another brand": "Comparing brands",
  "Call Disconnected": "Call disconnected", "Others": "Other responses",
  "General Inquiry": "General questions", "Not Interested": "Not interested",
  "Follow Up Required": "Needs follow-up", "No Response": "No response",
  "Lost to Competition": "Lost to competitor", "Test Drive Completed": "Test drive done",
  "Invalid Lead": "Invalid lead", "Purchase Postponed": "Purchase postponed",
  "Audio Issue": "Audio problems", "Showroom Visit Planned": "Visit planned",
  "Converted": "Converted", "Talk to Human": "Requested human agent",
  "Interested in another car same dealership": "Interested in different model",
};

const POST_SALES_DISPOSITIONS: Record<string, string> = {
  "Voicemail": "Voicemail", "Rejected": "Rejected", "Language barrier": "Language barrier",
  "Vehicle is commercial or part of a fleet": "Commercial vehicle", "Vehicle is not being run": "Unused vehicle",
  "Requires special spare parts": "Special parts needed", "Others": "Others",
  "Wrong contact number": "Wrong number", "Has sold/given away the car": "Sold vehicle",
  "Has moved to another location": "Moved", "Cannot make decision on servicing": "Not decision maker",
  "Will call workshop themselves": "Will call workshop", "Requested Callback": "Requested callback",
  "Looking for a discount": "Wants discount", "Has serviced car in another dealership": "Serviced elsewhere",
  "Will decide tomorrow": "Decide tomorrow", "Will decide within 1 to 3 days": "Decide 1-3 days",
  "Will decide within 4 to 7 days": "Decide 4-7 days", "Will decide within 8 to 14 days": "Decide 8-14 days",
  "Will decide within 15 to 30 days": "Decide 15-30 days", "Will decide within 31 to 60 days": "Decide 31-60 days",
  "Will decide within 61 to 90 days": "Decide 61-90 days", "Will decide after 90 days": "Decide after 90 days",
  "Unsubscribed": "Unsubscribed", "Call Disconnected": "Call disconnected", "Audio Issue": "Audio issue",
  "Call Quality Issue": "Call quality issue", "Connection Issue": "Connection issue",
  "Customer Busy": "Customer busy", "No Response": "No response", "Price Inquiry": "Price inquiry",
  "Lost to Competition": "Lost to competition", "Invalid Lead": "Invalid lead",
  "Not Interested": "Not interested", "Service Postponed": "Service postponed",
  "Showroom Visit Planned": "Visit planned", "Existing Dealer Contact": "Existing dealer contact",
  "Contact Fatigue": "Contact fatigue", "Converted": "Converted", "Talk to Human": "Talk to human",
  "Interested in another car same dealership": "Interested in different model",
};

const POST_SALES_KPI_GROUPS: Record<string, string[]> = {
  "Service Booked": ["Converted"],
  "Service Completed": ["Has serviced car in another dealership", "Existing Dealer Contact"],
  "Invalid Lead": ["Invalid Lead", "Not Interested", "Rejected"],
  "Requested Callback": ["Requested Callback"],
  "Follow Up Required": [
    "Showroom Visit Planned", "Will call workshop themselves",
    "Service Postponed", "Will decide tomorrow",
    "Will decide within 1 to 3 days", "Will decide within 4 to 7 days",
    "Will decide within 8 to 14 days", "Will decide within 15 to 30 days",
    "Will decide within 31 to 60 days", "Will decide within 61 to 90 days",
    "Will decide after 90 days", "Talk to Human",
  ],
  "Voicemail": ["Voicemail"],
};

interface CallDataRow {
  full_name: string; phone: string; city: string; model: string;
  outcome: string; status: string; disposition: string;
  updated_disposition: string; summary: string; updated_summary: string;
  disposition_detail: string; manual_disposition_detail: string;
  conversion: string; session_summary: string;
  call_date_raw: string; call_date: string; attempts: string;
  next_service_due: string;
}

interface KpiItem { label: string; val: number; cls: string; sub: string; }

export default function CallAnalysisPage() {
  const log = (...args) => console.log('[CallAnalysis]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [importedRows, setImportedRows] = useState<CallDataRow[]>([]);
  const [summaryItems, setSummaryItems] = useState<KpiItem[]>([]);
  const [summaryTitle, setSummaryTitle] = useState('');
  const [campaignMode, setCampaignMode] = useState('auto');
  const [activeMode, setActiveMode] = useState<'pre' | 'post'>('pre');
  const [dealerKey, setDealerKey] = useState('perfect_riders_service');
  const [dateParseOrder, setDateParseOrder] = useState<'DMY' | 'MDY'>('DMY');
  const [dateFormatSelect, setDateFormatSelect] = useState('auto');
  const [callsPerDay, setCallsPerDay] = useState<{ date: string; dayName: string; count: number; pct: number }[]>([]);
  const [bookingPreviewData, setBookingPreviewData] = useState<CallDataRow[]>([]);
  const [completedPreviewData, setCompletedPreviewData] = useState<CallDataRow[]>([]);
  const [fileMeta, setFileMeta] = useState('');
  const [fileStatus, setFileStatus] = useState('No file selected');
  const [rowCount, setRowCount] = useState(0);
  const [copyBtnDisabled, setCopyBtnDisabled] = useState(true);
  const [hasFile, setHasFile] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [showResults, setShowResults] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  function normalizeKey(value: string): string {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function lower(value: string): string {
    return clean(value).toLowerCase();
  }

  function phoneKey(value: string): string {
    const digits = clean(value).replace(/\D/g, '');
    if (!digits) return '';
    return digits.length > 10 ? digits.slice(-10) : digits;
  }

  function makeGetter(row: Record<string, unknown>) {
    const normalized: Record<string, unknown> = {};
    Object.keys(row).forEach(key => { normalized[normalizeKey(key)] = row[key]; });
    return (candidates: string[]) => {
      for (const c of candidates) {
        const val = normalized[normalizeKey(c)];
        if (val !== undefined && val !== null) return val;
      }
      return '';
    };
  }

  function rowHasData(row: Record<string, unknown>): boolean {
    return Object.values(row).some(v => clean(v) !== '');
  }

  function cellToString(val: unknown): string {
    if (val == null) return '';
    if (typeof val === 'number') {
      if (Number.isInteger(val)) return String(val);
      if (val > 999999 && Math.abs(val - Math.round(val)) < 0.01) return String(Math.round(val));
      return String(val);
    }
    return String(val).trim();
  }

  function normalizeRows(rows: Record<string, unknown>[]): CallDataRow[] {
    return rows.filter(rowHasData).map(row => {
      const get = makeGetter(row);
      return {
        full_name: clean(get(['Full_Name', 'Full Name', 'person_name', 'name'])),
        phone: clean(get(['Phone', 'phone_number', 'mobile', 'contact_number'])),
        city: clean(get(['City', 'city'])),
        model: clean(get(['Model', 'Vehicle_Model', 'Vehicle Model', 'model_preference', 'interested_vehicle_name', 'existing_vehicle_model'])),
        outcome: clean(get(['Outcome', 'OUTCOME'])),
        status: clean(get(['STATUS', 'Status', 'session_status', 'Session_Status'])),
        disposition: clean(get(['Disposition', 'DISPOSITION_DETAILS', 'Disposition_Details', 'disposition_detail', 'Disposition Details'])),
        updated_disposition: clean(get(['UPDATED_DISPOSITION', 'Updated Disposition', 'updated_disposition'])),
        summary: clean(get(['SUMMARY', 'Summary', 'call_summary', 'conversation_summary', 'notes'])),
        updated_summary: clean(get(['Updated SUMMARY', 'Updated Summary', 'updated_summary'])),
        disposition_detail: clean(get(['Disposition_detail', 'disposition_detail', 'DISPOSITION_DETAILS', 'Disposition_Details', 'Disposition Details'])),
        manual_disposition_detail: clean(get(['Manual_Disposition_detail', 'manual_disposition_detail', 'MANUAL_DISPOSITION_DETAIL'])),
        conversion: clean(get(['Conversion', 'conversion'])),
        session_summary: clean(get(['Session_Summary', 'Session Summary', 'session_summary'])),
        call_date_raw: clean(get(['Call_Date', 'Call Date', 'created', 'start_time', 'date'])),
        call_date: '',
        attempts: clean(get(['NUMBER OF ATTEMPTS', 'NUMBER_OF_ATTEMPTS', 'number_of_attempts', 'attempts', 'Attempt'])),
        next_service_due: clean(get(['NEXT_SERVICE_DUE', 'next_service_due', 'NEXT_SERVICE_DATE', 'next_service_date'])),
      };
    });
  }

  function detectDateFormat(dateStrings: string[]): 'DMY' | 'MDY' {
    const limit = Math.min(dateStrings.length, 250);
    for (let i = 0; i < limit; i++) {
      const s = String(dateStrings[i] || '').trim();
      const m = s.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})$/);
      if (!m) continue;
      const a = parseInt(m[1], 10), b = parseInt(m[2], 10);
      if (a > 12 && b <= 12) return 'DMY';
      if (b > 12 && a <= 12) return 'MDY';
    }
    return 'DMY';
  }

  function normalizeDateString(raw: string): string {
    if (!raw) return '';
    const s = String(raw).trim();
    const match = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$/);
    if (!match) return s;
    const first = parseInt(match[1], 10), second = parseInt(match[2], 10);
    let year = parseInt(match[3], 10);
    if (year < 100) year += 2000;
    if (dateParseOrder === 'MDY') {
      if (first >= 1 && first <= 12 && second >= 1 && second <= 31) {
        return `${String(second).padStart(2, '0')}/${String(first).padStart(2, '0')}/${year}`;
      }
      if (second >= 1 && second <= 12 && first >= 1 && first <= 31) {
        return `${String(first).padStart(2, '0')}/${String(second).padStart(2, '0')}/${year}`;
      }
      return s;
    }
    if (second >= 1 && second <= 12 && first >= 1 && first <= 31) {
      return `${String(first).padStart(2, '0')}/${String(second).padStart(2, '0')}/${year}`;
    }
    if (first >= 1 && first <= 12 && second >= 1 && second <= 31) {
      return `${String(second).padStart(2, '0')}/${String(first).padStart(2, '0')}/${year}`;
    }
    return s;
  }

  function readSheetRows(workbook: XLSX.WorkBook, sheetName: string): Record<string, unknown>[] {
    const ws = workbook.Sheets[sheetName];
    if (!ws) return [];
    return XLSX.utils.sheet_to_json(ws, { defval: '', raw: false });
  }

  function getSummarySheetName(workbook: XLSX.WorkBook): string | undefined {
    return workbook.SheetNames.find(name => normalizeKey(name) === 'summarysource') || workbook.SheetNames[0];
  }

  function mergeWorkbookRows(primaryRows: CallDataRow[], supplementRows: CallDataRow[]): CallDataRow[] {
    if (!primaryRows.length) return supplementRows;
    if (!supplementRows.length) return primaryRows;
    const supplementsByPhone = new Map<string, CallDataRow>();
    supplementRows.forEach(row => {
      const key = phoneKey(row.phone);
      if (key && !supplementsByPhone.has(key)) supplementsByPhone.set(key, row);
    });
    const seenPhones = new Set<string>();
    const merged = primaryRows.map(row => {
      const key = phoneKey(row.phone);
      if (key) seenPhones.add(key);
      const supplement = key ? supplementsByPhone.get(key) : null;
      if (!supplement) return row;
      const combined = { ...supplement, ...row } as CallDataRow;
      (Object.keys(supplement) as (keyof CallDataRow)[]).forEach(field => {
        if (!clean(combined[field]) && clean(supplement[field])) (combined[field] as string) = supplement[field];
      });
      return combined;
    });
    supplementRows.forEach(row => {
      const key = phoneKey(row.phone);
      if (!key || !seenPhones.has(key)) merged.push(row);
    });
    return merged;
  }

  function getWorkbookRows(workbook: XLSX.WorkBook): CallDataRow[] {
    const primarySheetName = getSummarySheetName(workbook);
    if (!primarySheetName) return [];
    const primaryRows = normalizeRows(readSheetRows(workbook, primarySheetName));
    const processedSheetName = workbook.SheetNames.find(name => normalizeKey(name) === 'processedleads');
    const supplementSheetName = processedSheetName && processedSheetName !== primarySheetName
      ? processedSheetName
      : workbook.SheetNames.find(name => name !== primarySheetName);
    if (!supplementSheetName) return primaryRows;
    return mergeWorkbookRows(primaryRows, normalizeRows(readSheetRows(workbook, supplementSheetName)));
  }

  function getEffectiveSummary(row: CallDataRow): string {
    const md = clean(row.manual_disposition_detail);
    if (md) return md;
    const dd = clean(row.disposition_detail);
    if (dd) return dd;
    const us = clean(row.updated_summary);
    if (us) return us;
    return clean(row.summary);
  }

  function isConnected(row: CallDataRow): boolean { return lower(row.outcome) === 'connected'; }
  function isNotConnected(row: CallDataRow): boolean { return lower(row.outcome) === 'not connected'; }

  function isTestDriveBooking(row: CallDataRow): boolean {
    if (lower(row.conversion) === 'yes') return true;
    if (!isConnected(row)) return false;
    const s = lower(getEffectiveSummary(row));
    if (s.includes('follow up required') || s.includes('converted')) return true;
    if (s.includes('not interested')) return false;
    return s.includes('interested');
  }

  function isTestDriveCompleted(row: CallDataRow): boolean {
    const s = lower(getEffectiveSummary(row));
    return isConnected(row) && s.includes('already booked');
  }

  function hasAny(text: string, terms: string[]): boolean {
    return terms.some(t => text.includes(t));
  }

  function detectCampaignModeFromRows(rows: CallDataRow[]): 'pre' | 'post' {
    if (!rows.length) return 'pre';
    let postScore = 0, preScore = 0;
    rows.slice(0, 300).forEach(row => {
      if (clean(row.next_service_due)) postScore += 4;
      const st = lower(row.status || '');
      const oc = lower(row.outcome || '');
      if (st.includes('attempted') || st.includes('completed') || st.includes('busy')) postScore += 3;
      if (oc === 'connected' || oc === 'not connected') preScore += 3;
      const text = lower(clean(row.summary) + ' ' + clean(row.disposition) + ' ' + clean(row.updated_disposition) + ' ' + clean(row.status));
      if (hasAny(text, ['service booked', 'service appointment', 'feedback', 'serviced', 'next service', 'complaint'])) postScore++;
      if (hasAny(text, ['test drive', 'brochure', 'vehicle inquiry'])) preScore++;
    });
    return postScore > preScore ? 'post' : 'pre';
  }

  function resolveCampaignMode(selectValue: string, rows: CallDataRow[]): 'pre' | 'post' {
    if (selectValue === 'pre' || selectValue === 'post') return selectValue;
    return detectCampaignModeFromRows(rows);
  }

  function getPostDispositionKey(row: CallDataRow): string | null {
    const ud = clean(row.updated_disposition);
    if (ud && POST_SALES_DISPOSITIONS[ud]) return ud;
    const d = clean(row.disposition_detail || row.disposition);
    if (d && POST_SALES_DISPOSITIONS[d]) return d;
    return null;
  }

  function isDispositionMatch(row: CallDataRow, keys: string[]): boolean {
    const k = getPostDispositionKey(row);
    return k !== null && keys.indexOf(k) !== -1;
  }

  function isPostConnected(row: CallDataRow): boolean {
    const st = lower(row.status || '');
    return st.includes('attempted') || st.includes('completed');
  }

  function isPostNotConnected(row: CallDataRow): boolean {
    return lower(row.status || '').includes('busy');
  }

  function hasPostVoicemail(row: CallDataRow): boolean { return isDispositionMatch(row, POST_SALES_KPI_GROUPS["Voicemail"]); }
  function isPostServiceBooked(row: CallDataRow): boolean { return isDispositionMatch(row, POST_SALES_KPI_GROUPS["Service Booked"]); }
  function isPostServiceCompleted(row: CallDataRow): boolean { return isDispositionMatch(row, POST_SALES_KPI_GROUPS["Service Completed"]); }
  function isPostInvalidLead(row: CallDataRow): boolean { return isDispositionMatch(row, POST_SALES_KPI_GROUPS["Invalid Lead"]); }
  function isPostFollowUpRequired(row: CallDataRow): boolean { return isDispositionMatch(row, POST_SALES_KPI_GROUPS["Follow Up Required"]); }
  function isPostRequestedCallback(row: CallDataRow): boolean { return isDispositionMatch(row, POST_SALES_KPI_GROUPS["Requested Callback"]); }

  function countPostUniqueCalls(data: CallDataRow[]): number {
    const hasAttemptCol = data.some(r => clean(r.attempts) !== '');
    if (hasAttemptCol) {
      return data.filter(r => {
        const a = lower(r.attempts || '');
        return a === '1' || a === '1.0' || a === 'one';
      }).length;
    }
    const seen = new Set<string>();
    data.forEach(r => { const k = phoneKey(r.phone); if (k) seen.add(k); });
    return seen.size;
  }

  function detectPostLocation(row: CallDataRow): string {
    const text = lower(row.summary || '');
    if (text.includes('jayanagar')) return 'JAYANAGAR';
    if (text.includes('lalbagh')) return 'LALBAGH';
    return '';
  }

  function detectBookingLocation(row: CallDataRow): string {
    const text = lower(row.session_summary);
    if (text.includes('bannerghatta road') || text.includes('bannerghatta')) return 'Bannerghatta Road';
    if (text.includes('mysore rd') || text.includes('mysore road')) return 'Mysore Rd';
    if (text.includes('ramanagara')) return 'Ramanagara';
    if (text.includes('marathahalli')) return 'Marathahalli';
    if (text.includes('kr puram') || text.includes('k r puram')) return 'KR Puram';
    return '';
  }

  function getBookingDisposition(row: CallDataRow): string {
    const disp = clean(row.disposition);
    if (lower(disp).includes('converted') || (!disp && lower(row.conversion) === 'yes')) return 'Test Drive Booked';
    return disp;
  }

  function getBookingColumns(row: CallDataRow): string[] {
    return [row.phone, row.model, getBookingDisposition(row), detectBookingLocation(row), row.call_date];
  }

  function getCompletedColumns(row: CallDataRow): string[] {
    return [row.phone, row.model, row.call_date, getEffectiveSummary(row)];
  }

  function getBookingColumnsPost(row: CallDataRow): string[] {
    let disp = clean(row.updated_disposition) || clean(row.disposition);
    if (disp === 'Converted') disp = 'Service Booked';
    return [row.phone, row.model, disp, detectPostLocation(row), row.call_date];
  }

  function getCompletedColumnsPost(row: CallDataRow): string[] {
    return [row.phone, row.model, row.call_date, clean(row.updated_disposition) || clean(row.disposition)];
  }

  function renderRuleAudit(rules: { label: string; count: number; detail: string }[]) {
    // Rendered in JSX
  }

  function renderBookingTable(data: CallDataRow[]) {
    const isPost = activeMode === 'post';
    const previewData = data.filter(isPost ? isPostServiceBooked : isTestDriveBooking);
    setBookingPreviewData(previewData);
  }

  function renderCompletedTable(data: CallDataRow[]) {
    const isPost = activeMode === 'post';
    const previewData = data.filter(isPost ? isPostServiceCompleted : isTestDriveCompleted);
    setCompletedPreviewData(previewData);
  }

  function renderPreviewTables(data: CallDataRow[]) {
    renderBookingTable(data);
    renderCompletedTable(data);
  }

  function computeCallsPerDay(data: CallDataRow[]): { date: string; dayName: string; count: number; pct: number }[] {
    const groups = new Map<string, number>();
    data.forEach(row => {
      const d = (row.call_date || '').trim();
      if (!d) return;
      groups.set(d, (groups.get(d) || 0) + 1);
    });
    const total = data.length || 1;
    const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return Array.from(groups.entries())
      .map(([date, count]) => {
        // Parse the normalized date to get day of week
        let dayName = '';
        const parts = date.split(/[\/\-.]/);
        if (parts.length === 3) {
          let d: number, m: number, y: number;
          if (dateParseOrder === 'MDY') {
            m = parseInt(parts[0], 10) - 1;
            d = parseInt(parts[1], 10);
            y = parseInt(parts[2], 10);
          } else {
            d = parseInt(parts[0], 10);
            m = parseInt(parts[1], 10) - 1;
            y = parseInt(parts[2], 10);
          }
          const dt = new Date(y, m, d);
          dayName = DAY_NAMES[dt.getDay()] || '';
        }
        return { date, dayName, count, pct: total > 0 ? Math.round((count / total) * 100) : 0 };
      })
      .sort((a, b) => {
        // Sort chronologically
        const parseDate = (s: string) => {
          const parts = s.split(/[\/\-.]/);
          if (parts.length !== 3) return new Date(0);
          if (dateParseOrder === 'MDY') return new Date(parseInt(parts[2], 10), parseInt(parts[0], 10) - 1, parseInt(parts[1], 10));
          return new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
        };
        return parseDate(a.date).getTime() - parseDate(b.date).getTime();
      });
  }

  function renderSummary(data: CallDataRow[]) {
    const now = new Date();
    const dateLabel = now.getDate() + ' ' + MONTH_NAMES[now.getMonth()] + ' ' + now.getFullYear();
    const resolvedMode = resolveCampaignMode(campaignMode, data);
    setActiveMode(resolvedMode);
    const modeLabel = resolvedMode === 'post' ? 'Post-Sales' : 'Pre-Sales';
    const titleText = dateLabel + ' — Call Analysis Summary (' + modeLabel + ')';
    const total = data.length;

    if (resolvedMode === 'post') {
      const dealerName = DEALER_NAMES[dealerKey] || '';
      const connected = data.filter(isPostConnected).length;
      const notConnectedCalls = data.filter(isPostNotConnected).length;
      const voicemail = data.filter(hasPostVoicemail).length;
      const uniqueCalls = countPostUniqueCalls(data);
      const serviceBooked = data.filter(isPostServiceBooked).length;
      const serviceCompleted = data.filter(isPostServiceCompleted).length;
      const invalidLead = data.filter(isPostInvalidLead).length;
      const requestedCallbacks = data.filter(isPostRequestedCallback).length;
      const followUpRequired = data.filter(isPostFollowUpRequired).length;

      setSummaryTitle(dateLabel + (dealerName ? ' ' + dealerName : '') + ' Call Analysis Summary');
      setSummaryItems([
        { label: 'Total Calls Triggered', val: total, cls: 'purple', sub: 'Imported records' },
        { label: 'Connected Calls', val: connected, cls: 'green', sub: 'STATUS: attempted / completed' },
        { label: 'Not Connected Calls', val: notConnectedCalls, cls: 'red', sub: 'STATUS: busy' },
        { label: 'Voicemail', val: voicemail, cls: 'amber', sub: 'Exact disposition match: Voicemail' },
        { label: 'Unique Calls', val: uniqueCalls, cls: 'amber', sub: 'Attempt = 1 if column exists, else unique phones' },
        { label: 'Service Booked', val: serviceBooked, cls: 'green', sub: 'Exact disposition match: Converted' },
        { label: 'Service Completed', val: serviceCompleted, cls: 'teal', sub: 'Exact disposition match: Has serviced car / Existing Dealer Contact' },
        { label: 'Invalid Lead', val: invalidLead, cls: 'red', sub: 'Exact disposition match: Invalid Lead / Not Interested / Rejected' },
        { label: 'Requested Call Back', val: requestedCallbacks, cls: 'teal', sub: 'Exact disposition match: Requested Callback' },
        { label: 'Follow Up Required', val: followUpRequired, cls: 'amber', sub: 'Exact disposition match: Showroom Visit Planned / Will call workshop / Will decide / Talk to Human' },
      ]);
    } else {
      const connected = data.filter(isConnected).length;
      const bookings = data.filter(isTestDriveBooking).length;
      const followUps = data.filter(row => {
        const s = lower(getEffectiveSummary(row));
        if (s.includes('interested') && !s.includes('not interested')) return true;
        if (s.includes('follow up')) return true;
        return s.includes('converted');
      }).length;
      const requestedCallbacks = data.filter(row => {
        const d = lower(row.disposition);
        const s = lower(getEffectiveSummary(row));
        const ss = lower(row.session_summary);
        return d.includes('call back') || d.includes('callback') || d.includes('call later') ||
          s.includes('requested call back') || s.includes('callback requested') || s.includes('requested callback') ||
          ss.includes('requested call back') || ss.includes('callback requested') || ss.includes('requested callback');
      }).length;
      const interested = data.filter(row => {
        if (!isConnected(row)) return false;
        const s = lower(getEffectiveSummary(row));
        return s.includes('interested') && !s.includes('not interested');
      }).length;
      const testDriveCompleted = data.filter(isTestDriveCompleted).length;
      const notConnectedCalls = data.filter(isNotConnected).length;

      setSummaryTitle(dateLabel + ' Call Analysis Summary');
      setSummaryItems([
        { label: 'Total Calls Triggered', val: total, cls: 'purple', sub: 'Imported records' },
        { label: 'Connected Calls', val: connected, cls: 'green', sub: 'Outcome based' },
        { label: 'Test Drive Bookings', val: bookings, cls: 'green', sub: 'Summary based' },
        { label: 'Follow Up Required', val: followUps, cls: 'amber', sub: 'Summary based' },
        { label: 'Interested', val: interested, cls: 'amber', sub: 'Summary based' },
        { label: 'Requested Call Back', val: requestedCallbacks, cls: 'teal', sub: 'Disposition + summary' },
        { label: 'Test Drive Completed', val: testDriveCompleted, cls: 'blue', sub: 'Summary based' },
        { label: 'Not Connected Calls', val: notConnectedCalls, cls: 'red', sub: 'Outcome based' },
      ]);
    }

    setCallsPerDay(computeCallsPerDay(data));
    renderPreviewTables(data);
    setRowCount(total);
    setShowResults(true);
    setCopyBtnDisabled(false);
  }

  async function handleFile(file: File) {
    const v = validateFileSync(file);
    if (!v.valid) { setFileStatus(v.error!); return; }
    try {
      setFileStatus('Reading file...');
      setFileMeta(file.name);
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array', cellDates: true });
      const sheetName = getSummarySheetName(workbook);
      if (!sheetName) { throw new Error('No worksheet found in the uploaded file.'); }
      const rows = getWorkbookRows(workbook);
      if (!rows.length) { throw new Error('No usable rows found.'); }
      // Auto-detect date format
      const dates = rows.map(r => r.call_date_raw);
      const detected = detectDateFormat(dates);
      setDateParseOrder(detected);
      // Normalize dates
      const rowsWithDates = rows.map(r => ({ ...r, call_date: normalizeDateString(r.call_date_raw || '') }));
      setImportedRows(rowsWithDates);
      renderSummary(rowsWithDates);
      setFileStatus(file.name + ' imported.');
      setHasFile(true);
    } catch (error: unknown) {
      setImportedRows([]);
      setSummaryItems([]);
      setCallsPerDay([]);
      setShowResults(false);
      setCopyBtnDisabled(true);
      setHasFile(false);
      setFileStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  async function copySummaryText() {
    if (!summaryItems.length) return;
    const lines = [summaryTitle, '', ...summaryItems.map(item => `${item.label} — ${item.val}`)];
    const text = lines.join('\n');
    try {
      await navigator.clipboard.writeText(text);
      setFileStatus('Copied!');
    } catch {
      setFileStatus('Copy failed.');
    }
  }

  async function copyBookingData() {
    if (!bookingPreviewData.length) return;
    const colsFn = activeMode === 'post' ? getBookingColumnsPost : getBookingColumns;
    const rows = bookingPreviewData.map(r => colsFn(r).map(v => String(v ?? '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ')).join('\t'));
    try { await navigator.clipboard.writeText(rows.join('\n')); setFileStatus('Copied!'); }
    catch { setFileStatus('Copy failed.'); }
  }

  async function copyCompletedData() {
    if (!completedPreviewData.length) return;
    const colsFn = activeMode === 'post' ? getCompletedColumnsPost : getCompletedColumns;
    const rows = completedPreviewData.map(r => colsFn(r).map(v => String(v ?? '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ')).join('\t'));
    try { await navigator.clipboard.writeText(rows.join('\n')); setFileStatus('Copied!'); }
    catch { setFileStatus('Copy failed.'); }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  const bookingLabel = activeMode === 'post' ? 'Service Booked' : 'Test Drive Booked';
  const completedLabel = activeMode === 'post' ? 'Service Completed' : 'Test Drive Completed';

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Call Analysis Summary</h1>
              <div className="header-sub">Generate call analysis summary</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        <section className={styles['upload-section']}>
          <div className={styles['section-title']}>Upload Processed Sync Export</div>
          <div className={styles['upload-controls']}>
            <span className={styles['mode-label']}>Campaign mode</span>
            <select className={styles['mode-select']} value={campaignMode} onChange={e => { setCampaignMode(e.target.value); if (importedRows.length) renderSummary(importedRows); }}>
              <option value="auto">Auto Detect</option>
              <option value="pre">Pre-Sales</option>
              <option value="post">Post-Sales</option>
            </select>
            <span className={styles['mode-label']} style={{ marginLeft: '0.5rem' }}>Dealership</span>
            <select className={styles['mode-select']} value={dealerKey} onChange={e => { setDealerKey(e.target.value); if (importedRows.length) renderSummary(importedRows); }}>
              {Object.entries(DEALER_NAMES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <span className={styles['mode-label']} style={{ marginLeft: '0.5rem' }}>Date format</span>
            <select className={styles['mode-select']} value={dateFormatSelect} onChange={e => {
              const val = e.target.value;
              setDateFormatSelect(val);
              if (val === 'auto') {
                if (importedRows.length) {
                  const dates = importedRows.map(r => r.call_date_raw);
                  setDateParseOrder(detectDateFormat(dates));
                }
              } else {
                setDateParseOrder(val as 'DMY' | 'MDY');
              }
              if (importedRows.length) {
                const updated = importedRows.map(r => ({ ...r, call_date: normalizeDateString(r.call_date_raw || '') }));
                setImportedRows(updated);
                renderSummary(updated);
              }
            }}>
              <option value="auto">Auto Detect</option>
              <option value="DMY">DD/MM/YYYY</option>
              <option value="MDY">MM/DD/YYYY</option>
            </select>
            <span className={styles['date-parser-note']}>Format: {dateFormatSelect === 'auto' ? 'Auto' : 'Manual'} — {dateParseOrder === 'MDY' ? 'MM/DD/YYYY' : 'DD/MM/YYYY'}</span>
          </div>

          <div className={styles['upload-row']}>
            <div
              className={`${styles['drop-zone']} ${dragOver ? styles['drag-over'] : ''} ${hasFile ? styles['has-file'] : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <div className={styles['dz-icon']}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              </div>
              <div className={styles['dz-text']}>
                <strong>AutoNage_Disposition_Sync (.xlsx / .csv)</strong>
                <small id="fileMeta">{fileMeta || 'Drop file here or click to browse.'}</small>
              </div>
              <span className={`${styles['dz-status']} ${hasFile ? styles['ok'] : ''}`}>{fileStatus}</span>
              <input ref={fileInputRef} type="file" accept=".xlsx,.csv,.tsv" onChange={handleFileChange} style={{ display: 'none' }} />
            </div>

            <button className={styles['btn-generate']} onClick={copySummaryText} disabled={copyBtnDisabled}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
              Copy Summary
            </button>
          </div>
        </section>

        {showResults && (
          <>
            <div className={styles['summary-bar']}>
              <div className={styles['campaign-info']}>
                <div className={styles['campaign-name']}>{summaryTitle}</div>
                <div className={styles['campaign-subtitle']}>{fileMeta || 'Import sync export data'}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                <div className={styles['date-range-label']}>IMPORTED ROWS</div>
                <div className={styles['date-range-badge']}>{rowCount}</div>
              </div>
            </div>

            <div className={styles['summary-panel']}>
              <div className={styles['summary-grid']}>
                {summaryItems.map((item, i) => (
                  <div key={i} className={`${styles['kpi-card']} ${styles[item.cls] || ''} ${styles['slide-up']} ${styles[`stagger-${Math.min(i + 1, 7)}`]}`}>
                    <div><span className={styles['kpi-dot']}></span></div>
                    <div className={styles['kpi-value']}>{item.val}</div>
                    <div className={styles['kpi-label']}>{item.label}</div>
                    <div className={styles['kpi-sub']}>{item.sub}</div>
                  </div>
                ))}
              </div>

              {/* Calls Per Day */}
              <div className={styles['calls-per-day']}>
                <div className={styles['preview-table-header']}>
                  <div className={styles['preview-title']}>
                    <span>Calls Per Day</span>
                    <span className={styles['preview-count']}>{callsPerDay.length} days &middot; {rowCount} total calls</span>
                  </div>
                </div>
                <div className={styles['cpd-chart']}>
                  {callsPerDay.map((day, i) => (
                    <div key={i} className={styles['cpd-bar-row']}>
                      <div className={styles['cpd-date-col']}>
                        <span className={styles['cpd-date']}>{day.date}</span>
                        {day.dayName && <span className={styles['cpd-day']}>{day.dayName}</span>}
                      </div>
                      <div className={styles['cpd-bar-col']}>
                        <div className={styles['cpd-bar-track']}>
                          <div
                            className={styles['cpd-bar-fill']}
                            style={{ width: Math.max(day.pct, day.count > 0 ? 3 : 0) + '%' }}
                          ></div>
                        </div>
                      </div>
                      <div className={styles['cpd-count-col']}>
                        <span className={styles['cpd-count']}>{day.count}</span>
                        <span className={styles['cpd-pct']}>{day.pct}%</span>
                      </div>
                    </div>
                  ))}
                  {callsPerDay.length === 0 && (
                    <div className={styles['cpd-empty']}>No date data available</div>
                  )}
                </div>
              </div>

              {/* Rule Audit */}
              <div className={styles['rule-audit']}>
                <div className={styles['preview-table-header']}>
                  <div className={styles['preview-title']}>Metric Rules <span className={styles['preview-count']}>How each count was classified</span></div>
                </div>
                <div className={styles['rule-grid']}>
                  {summaryItems.map((item, i) => (
                    <div key={i} className={styles['rule-item']}>
                      <div className={styles['rule-item-title']}><span>{item.label}</span><span className={styles['rule-item-count']}>{item.val}</span></div>
                      <div className={styles['rule-item-detail']}>{item.sub}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Booking Table */}
              {bookingPreviewData.length > 0 && (
                <div className={styles['preview-table-wrapper']}>
                  <div className={styles['preview-table-header']}>
                    <div className={styles['preview-title']}>
                      <span>{bookingLabel} Preview</span>
                      <span className={styles['preview-count']}>{bookingPreviewData.length} rows</span>
                    </div>
                    <button className={styles.btn} onClick={copyBookingData}>Copy {bookingLabel}</button>
                  </div>
                  <div className={styles['preview-table-scroll']}>
                    <table>
                      <thead><tr><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>DISPOSITION_DETAILS</th><th>LOCATION</th><th>CALL_DATE</th></tr></thead>
                      <tbody>
                        {bookingPreviewData.map((r, i) => {
                          const cols = activeMode === 'post' ? getBookingColumnsPost(r) : getBookingColumns(r);
                          return <tr key={i}><td className={styles['cell-phone']}>{esc(cols[0])}</td><td>{esc(cols[1])}</td><td>{esc(cols[2])}</td><td>{esc(cols[3])}</td><td>{esc(cols[4])}</td></tr>;
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Completed Table */}
              {completedPreviewData.length > 0 && (
                <div className={styles['preview-table-wrapper']}>
                  <div className={styles['preview-table-header']}>
                    <div className={styles['preview-title']}>
                      <span>{completedLabel} Preview</span>
                      <span className={styles['preview-count']}>{completedPreviewData.length} rows</span>
                    </div>
                    <button className={styles.btn} onClick={copyCompletedData}>Copy {completedLabel}</button>
                  </div>
                  <div className={styles['preview-table-scroll']}>
                    <table>
                      <thead><tr><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>CALL_DATE</th><th>DISPOSITION_DETAILS</th></tr></thead>
                      <tbody>
                        {completedPreviewData.map((r, i) => {
                          const cols = activeMode === 'post' ? getCompletedColumnsPost(r) : getCompletedColumns(r);
                          return <tr key={i}><td className={styles['cell-phone']}>{esc(cols[0])}</td><td>{esc(cols[1])}</td><td>{esc(cols[2])}</td><td>{esc(cols[3])}</td></tr>;
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </>
        )}

        {!showResults && (
          <div className={styles['empty-state']}>
            <div className={styles['empty-icon']}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 17v-6m4 6V7m4 10v-4M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
            </div>
            <h2>Upload a Processed File to See the Summary</h2>
            <p>Use the Excel export from Pre-Sales Sync or Post-Sales Disposition Sync. Choose campaign mode or Auto Detect.</p>
          </div>
        )}
      </main>

      <footer>AutoNage — Call Analysis Summary</footer>
    </div>
  );
}
