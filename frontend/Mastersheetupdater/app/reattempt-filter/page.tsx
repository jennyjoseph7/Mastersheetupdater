'use client';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import { readFileAsArrayBuffer, excelSafe, validateFileSync } from '@/lib/data-pipeline';
import * as XLSX from 'xlsx';
import styles from './reattempt-filter.module.css';

const AE_LEADS_PER_BATCH = 100;
const AE_BATCH_STORAGE_KEY = 'jejo-ae-batch-export-v1';

const TERMINAL_DISPOSITIONS = new Set(['not interested', 'dnd', 'wrong number', 'test drive booked', 'converted']);
const CONNECTED_OUTCOMES = new Set(['connected']);
const REATTEMPT_CONNECTED_SUMMARY_PHRASES = ['LANGUAGE BARRIER', 'No Response', 'Received call at wrong time', 'REQUESTED CALLBACK', 'VOICEMAIL', 'JUST EXPLORING'];
const DISPOSITION_FILTER_VALUES = ['__blanks__', 'audio issue', 'call disconnected', 'follow up required', 'general enquiry', 'just exploring', 'language barrier', 'no response', 'others', 'purchase postponed', 'requested callback', 'voicemail'];

interface DealershipConfig {
  name: string;
  type: 'pre-sales' | 'post-sales';
  showroom_code: string;
  region_name: string;
  dealership_id: string;
  brand: string;
  subdivision_name: string;
  workshop_code?: string;
}

const DEALERSHIPS: Record<string, DealershipConfig> = {
  anant_cars: { name: 'Anant Cars', type: 'pre-sales', showroom_code: '', region_name: 'India', dealership_id: 'anant-cars-india', brand: 'Mahindra', subdivision_name: '' },
  singhal: { name: 'Singhal', type: 'pre-sales', showroom_code: '', region_name: 'India', dealership_id: 'singhal-india', brand: 'Volkswagen', subdivision_name: '' },
  fortune_hyryder: { name: 'Fortune Hyryder', type: 'pre-sales', showroom_code: '', region_name: 'India', dealership_id: 'fortune-hyryder-india', brand: 'Toyota Kirloskar Motor', subdivision_name: '' },
  perfect_riders: { name: 'Perfect Riders', type: 'post-sales', showroom_code: '', region_name: 'India', dealership_id: 'perfect-riders-india', brand: '', subdivision_name: '', workshop_code: '' },
  ambal_service: { name: 'Ambal', type: 'post-sales', showroom_code: '', region_name: 'India', dealership_id: 'ambal-india', brand: '', subdivision_name: '', workshop_code: '' },
  bullmen_service: { name: 'Bullmen', type: 'post-sales', showroom_code: '', region_name: 'India', dealership_id: 'bullmen-india', brand: '', subdivision_name: '', workshop_code: '' },
  fortune_service: { name: 'Fortune Toyota', type: 'post-sales', showroom_code: '', region_name: 'India', dealership_id: 'fortune-toyota-india', brand: '', subdivision_name: '', workshop_code: '' },
  suryabala_service: { name: 'Suryabala Honda', type: 'post-sales', showroom_code: '', region_name: 'India', dealership_id: 'suryabala-honda-india', brand: '', subdivision_name: '', workshop_code: '' },
  icare_feedback: { name: 'Icare', type: 'post-sales', showroom_code: '', region_name: 'India', dealership_id: 'icare-india', brand: '', subdivision_name: '', workshop_code: '' },
};

interface ExcludedLead {
  phone: string;
  full_name: string;
  bestOutcome: string;
  bestDisposition: string;
  daysSeen: number;
  reason: string;
}

interface IncludedLead {
  phone: string;
  full_name: string;
  disposition_raw: string;
  updated_disposition_raw: string;
  model: string;
  seating: string;
  city: string;
  pincode: string;
  daysSeen: number;
  showroom_code: string;
  region_name: string;
  dealership_id: string;
  brand: string;
  subdivision_name: string;
  source_date: string;
  reattempt_reason: string;
  _row: Record<string, string>;
}

interface OutputSchema {
  headers: string[];
  mapRow: (r: IncludedLead) => string[];
}

export default function ReattemptFilterPage() {
  const log = (...args) => console.log('[Reattempt]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [rawFile, setRawFile] = useState<File | null>(null);
  const [includedLeads, setIncludedLeads] = useState<IncludedLead[]>([]);
  const [allIncludedLeads, setAllIncludedLeads] = useState<IncludedLead[]>([]);
  const [excludedLeads, setExcludedLeads] = useState<ExcludedLead[]>([]);
  const [dealershipKey, setDealershipKey] = useState('anant_cars');
  const [dateParseOrder, setDateParseOrder] = useState<'DMY' | 'MDY'>('DMY');
  const [excludeTerminal, setExcludeTerminal] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState('');
  const [fileStatus, setFileStatus] = useState('Drag & drop or click to browse');
  const [fileDragOver, setFileDragOver] = useState(false);
  const [hasFile, setHasFile] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [activeDispoFilter, setActiveDispoFilter] = useState<Set<string>>(new Set());
  const [dispoFilterVisible, setDispoFilterVisible] = useState(false);
  const [startLead, setStartLead] = useState(1);
  const [numBatches, setNumBatches] = useState(1);
  const [batchHint, setBatchHint] = useState('');
  const [connectedCount, setConnectedCount] = useState(0);
  const [terminalCount, setTerminalCount] = useState(0);
  const [skippedNoPhone, setSkippedNoPhone] = useState(0);
  const [groupsWithDate, setGroupsWithDate] = useState(0);
  const [groupsWithoutDate, setGroupsWithoutDate] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const batchFingerprintRef = useRef('');
  const batchInputRowCountRef = useRef(0);
  const batchTemplateIdRef = useRef('');
  const dispoDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  const dealership = DEALERSHIPS[dealershipKey];

  function cellToString(val: unknown): string {
    if (val == null) return '';
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

  function normalizePhone(raw: unknown): string | null {
    if (!raw) return null;
    let s = String(raw).trim();
    if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) s = String(Math.round(parseFloat(s)));
    const digits = s.replace(/\D/g, '');
    if (!digits) return null;
    if (digits.startsWith('91') && digits.length === 12) return digits.slice(2);
    if (digits.startsWith('0') && digits.length === 11) return digits.slice(1);
    if (digits.length === 10) return digits;
    if (digits.startsWith('91') && digits.length >= 12) return digits.slice(digits.length - 10);
    return null;
  }

  function findCol(row: Record<string, string>, candidates: string[]): string {
    for (const c of candidates) {
      if (row[c] !== undefined && row[c] !== '') return row[c];
    }
    return '';
  }

  function detectPhone(row: Record<string, string>) { return findCol(row, ['phone', 'phone_number', 'mobile', 'contact']); }
  function detectOutcome(row: Record<string, string>) { return findCol(row, ['outcome', 'call_outcome', 'status']); }
  function detectDisposition(row: Record<string, string>) { return findCol(row, ['updated_disposition', 'manual_disposition_detail', 'disposition_detail', 'disposition_details', 'disposition', 'call_disposition']); }
  function detectUpdatedDisposition(row: Record<string, string>) { return findCol(row, ['updated_disposition']); }
  function detectSummary(row: Record<string, string>) { return findCol(row, ['summary', 'call_summary', 'conversation_summary', 'notes']); }
  function detectFullName(row: Record<string, string>) { return findCol(row, ['full_name', 'person_name', 'name', 'customer_name']); }
  function detectModel(row: Record<string, string>) { return findCol(row, ['model', 'model_preference', 'interested_vehicle_name', 'vehicle', 'vehicle_model']); }
  function detectSeating(row: Record<string, string>) { return findCol(row, ['seating', 'seating_capacity_preference', 'seating_preference']); }
  function detectCity(row: Record<string, string>) { return findCol(row, ['city', 'location']); }
  function detectPincode(row: Record<string, string>) { return findCol(row, ['pincode', 'pin_code', 'zip', 'postal_code']); }
  function detectCallDate(row: Record<string, string>) { return findCol(row, ['call_date', 'date', 'call_triggered']); }
  function detectAttempts(row: Record<string, string>): number {
    const val = findCol(row, ['number_of_attempts', 'no._of_attempts', 'attempts', 'num_attempts']);
    if (val && !val.startsWith('=')) return parseInt(val) || 1;
    return 1;
  }

  function parseExcelSerialDate(value: unknown): Date | null {
    const num = Number(value);
    if (!isFinite(num) || num < 20000 || num > 80000) return null;
    const epoch = Date.UTC(1899, 11, 30);
    return new Date(epoch + num * 86400000);
  }

  function buildValidatedDate(year: number, month: number, day: number): Date | null {
    const date = new Date(year, month - 1, day);
    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null;
    return date;
  }

  function parseCallDate(value: unknown): Date | null {
    if (value == null || value === '') return null;
    const serial = parseExcelSerialDate(value);
    if (serial) return serial;
    const raw = String(value).trim();
    if (!raw) return null;
    const iso = raw.match(/(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
    if (iso) return buildValidatedDate(parseInt(iso[1], 10), parseInt(iso[2], 10), parseInt(iso[3], 10));
    const slash = raw.match(/(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})/);
    if (slash) {
      const first = parseInt(slash[1], 10), second = parseInt(slash[2], 10);
      let year = parseInt(slash[3], 10);
      if (year < 100) year += 2000;
      if (dateParseOrder === 'MDY') {
        const mdy = buildValidatedDate(year, first, second);
        if (mdy) return mdy;
        if (first > 12 && second <= 12) return null;
        return buildValidatedDate(year, second, first);
      }
      const dmy = buildValidatedDate(year, second, first);
      if (dmy) return dmy;
      if (first > 12 && second <= 12) return null;
      return buildValidatedDate(year, first, second);
    }
    return null;
  }

  function getRowRank(row: Record<string, string>) {
    const date = parseCallDate(detectCallDate(row));
    return { time: date ? date.getTime() : 0, hasDate: Boolean(date), attempts: detectAttempts(row), rowIndex: Number(row.__rowIndex || 0) };
  }

  function getLatestRow(rows: Record<string, string>[]) {
    if (!rows.length) return null;
    return rows.slice().sort((a, b) => {
      const ar = getRowRank(a), br = getRowRank(b);
      if (ar.time !== br.time) return ar.time - br.time;
      if (ar.attempts !== br.attempts) return ar.attempts - br.attempts;
      return ar.rowIndex - br.rowIndex;
    })[rows.length - 1];
  }

  function formatRankDate(row: Record<string, string>): string {
    const date = parseCallDate(detectCallDate(row));
    if (!date) return 'date unavailable';
    return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
  }

  function isConnectedOutcome(outcome: string): boolean {
    const o = outcome.toLowerCase().trim();
    if (!o) return false;
    if (CONNECTED_OUTCOMES.has(o)) return true;
    return o.includes('connected') && !o.includes('not connected');
  }

  function isReattemptConnectedSummary(summary: string): boolean {
    const s = summary.toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
    if (!s) return false;
    return REATTEMPT_CONNECTED_SUMMARY_PHRASES.some(phrase => s.includes(phrase.toLowerCase()));
  }

  function formatSerialDate(val: unknown): string {
    const num = Number(val);
    if (!isFinite(num) || num < 20000 || num > 80000) return String(val ?? '');
    const d = new Date(Date.UTC(1899, 11, 30) + num * 86400000);
    return `${String(d.getUTCDate()).padStart(2, '0')}/${String(d.getUTCMonth() + 1).padStart(2, '0')}/${d.getUTCFullYear()}`;
  }

  function getOutputSchema(key: string): OutputSchema {
    const d = DEALERSHIPS[key];
    if (key === 'singhal') return { headers: ['person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name', 'seating_capacity_preference', 'city'], mapRow: r => [r.full_name, r.phone, r.model, r.brand, r.seating, r.city] };
    if (key === 'fortune_hyryder') return { headers: ['showroom_code', 'person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name'], mapRow: r => [r.showroom_code, r.full_name, r.phone, r.model || 'Urban Cruiser Hyryder', r.brand || 'Toyota Kirloskar Motor'] };
    if (key === 'anant_cars') return { headers: ['showroom_code', 'region_name', 'dealership_id', 'person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name', 'seating_capacity_preference', 'city', 'pincode', 'subdivision_name', 'alt_phone_number_2', 'lead_source'], mapRow: r => [r.showroom_code, r.region_name, r.dealership_id, r.full_name, r.phone, r.model, r.brand, r.seating, r.city, r.pincode, r.subdivision_name, '', ''] };
    if (key === 'bullmen_service') return { headers: ['workshop_code', 'purchase_date', 'vin_number', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'phone_number', 'alt_phone_number_2', 'last_service_date'], mapRow: r => { const row = r._row || {}; return [findCol(row, ['workshop_code', 'dealer_code']), formatSerialDate(findCol(row, ['purchase_date', 'sale_date'])), findCol(row, ['vin_number', 'vin', 'chassis_number']), formatSerialDate(findCol(row, ['next_service_date', 'next_service_due'])), r.full_name, r.model, findCol(row, ['reg_number', 'registration_number']), r.phone, '', formatSerialDate(findCol(row, ['last_service_date', 'last_service']))]; } };
    if (key === 'ambal_service') return { headers: ['workshop_code', 'vin_number', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'phone_number', 'alt_phone_number_2', 'odometer_reading', 'last_service_date', 'customer_score', 'purpose_of_visit'], mapRow: r => { const row = r._row || {}; return [findCol(row, ['workshop_code', 'dealer_code']), findCol(row, ['vin_number', 'vin', 'chassis_number']), formatSerialDate(findCol(row, ['next_service_date', 'next_service_due'])), r.full_name, r.model, findCol(row, ['reg_number', 'registration_number']), r.phone, '', findCol(row, ['odometer_reading', 'odometer', 'kms']), formatSerialDate(findCol(row, ['last_service_date', 'last_service'])), findCol(row, ['customer_score', 'score']), 'yearly service']; } };
    if (key === 'fortune_service') return { headers: ['next_service_due', 'workshop_code', 'service_plan_type', 'person_name', 'phone_number', 'reg_number', 'vin_number', 'vehicle_model', 'purchase_date'], mapRow: r => { const row = r._row || {}; return [formatSerialDate(findCol(row, ['next_service_date', 'next_service_due'])), findCol(row, ['workshop_code', 'dealer_code']), findCol(row, ['service_plan_type', 'service_type', 'predicted_service_type']), r.full_name, r.phone, findCol(row, ['reg_number', 'registration_number']), findCol(row, ['vin_number', 'vin', 'chassis_number']), r.model, formatSerialDate(findCol(row, ['purchase_date', 'sale_date']))]; } };
    if (key === 'suryabala_service') return { headers: ['person_name', 'phone_number', 'vehicle_model', 'reg_number', 'service_type', 'next_service_due', 'vin_number'], mapRow: r => { const row = r._row || {}; return [r.full_name, r.phone, r.model, findCol(row, ['reg_number', 'registration_number']), findCol(row, ['service_type', 'next_service_type']), formatSerialDate(findCol(row, ['next_service_date', 'next_service_due'])), findCol(row, ['vin_number', 'vin', 'chassis_number'])]; } };
    if (key === 'icare_feedback') return { headers: ['showroom_code', 'person_name', 'phone_number', 'lead_tags'], mapRow: r => { const row = r._row || {}; return [r.showroom_code, r.full_name, r.phone, findCol(row, ['lead_tags', 'lead_tag', 'id', 'bill_no'])]; } };
    if (key === 'perfect_riders') return {
      headers: ['workshop_code', 'region_name', 'dealership_id', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'vin_number', 'phone_number', 'alt_phone_number_2', 'odometer_reading', 'last_service_date', 'customer_score', 'purpose_of_visit'],
      mapRow: r => {
        const row = r._row || {};
        return [
          findCol(row, ['workshop_code', 'dealer_code', 'network_code']),
          '',
          '',
          formatSerialDate(findCol(row, ['next_service_date', 'next_service_due', 'service_due_date'])),
          r.full_name,
          r.model,
          findCol(row, ['reg_number', 'registration_number']),
          findCol(row, ['vin_number', 'vin', 'chassis_number', 'chassis_no']),
          r.phone,
          findCol(row, ['alt_phone_number_2', 'retail_mobile_no']),
          findCol(row, ['odometer_reading', 'odometer', 'previous_meter_reading']),
          formatSerialDate(findCol(row, ['last_service_date', 'last_service', 'previous_jobcard_date'])),
          '',
          'yearly service',
        ];
      },
    };
    if (d.type === 'post-sales') return { headers: ['region_name', 'dealership_id', 'workshop_code', 'next_service_due', 'person_name', 'vehicle_model', 'reg_number', 'phone_number', 'alt_phone_number_2', 'odometer_reading', 'last_service_date', 'purchase_date', 'last_service_type'], mapRow: r => { const row = r._row || {}; return [r.region_name, r.dealership_id, findCol(row, ['workshop_code', 'dealer_code']), formatSerialDate(findCol(row, ['next_service_date', 'next_service_due'])), r.full_name, r.model, findCol(row, ['reg_number', 'registration_number']), r.phone, '', '', formatSerialDate(findCol(row, ['last_service_date', 'last_service'])), '', '']; } };
    return { headers: ['showroom_code', 'region_name', 'dealership_id', 'person_name', 'phone_number', 'interested_vehicle_name', 'interested_vehicle_brand_name', 'seating_capacity_preference', 'city', 'pincode', 'subdivision_name', 'alt_phone_number_2'], mapRow: r => [r.showroom_code, r.region_name, r.dealership_id, r.full_name, r.phone, r.model, r.brand, r.seating, r.city, r.pincode, r.subdivision_name, ''] };
  }

  function detectDateFormat(dateStrings: string[]): 'DMY' | 'MDY' {
    const limit = Math.min(dateStrings.length, 250);
    for (let i = 0; i < limit; i++) {
      const s = String(dateStrings[i] || '').trim();
      const m = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);
      if (!m) continue;
      const a = parseInt(m[1], 10), b = parseInt(m[2], 10);
      if (a > 12 && b <= 12) return 'DMY';
      if (b > 12 && a <= 12) return 'MDY';
    }
    return 'DMY';
  }

  function readAeBatchStore(): Record<string, unknown> {
    try { return JSON.parse(localStorage.getItem(AE_BATCH_STORAGE_KEY) || '{}'); } catch { return {}; }
  }
  function writeAeBatchStore(store: Record<string, unknown>) { try { localStorage.setItem(AE_BATCH_STORAGE_KEY, JSON.stringify(store)); } catch {} }
  function getSavedBatchProgress(fp: string, tId: string, rc: number) {
    const store = readAeBatchStore();
    const rec = store[fp] as Record<string, unknown> | undefined;
    if (!rec || rec.templateId !== tId || Number(rec.inputRowCount) !== Number(rc)) return null;
    return { nextLeadIndex: Number(rec.nextLeadIndex) || 1 };
  }
  function saveBatchProgress(fp: string, tId: string, rc: number, nli: number) {
    const store = readAeBatchStore();
    store[fp] = { templateId: tId, inputRowCount: rc, nextLeadIndex: nli };
    writeAeBatchStore(store);
  }
  function clearBatchProgressForFingerprint(fp: string) {
    const store = readAeBatchStore();
    delete store[fp];
    writeAeBatchStore(store);
  }
  function fileBatchFingerprint(file: File, rc: number) { return [file.name, String(file.size), String(file.lastModified), String(rc)].join('|'); }

  async function processFileAction() {
    if (!rawFile) return;
    setProcessing(true);
    setStatusMsg('Parsing file...');
    setStatusType('');

    try {
      const ab = await readFileAsArrayBuffer(rawFile);
      const wb = XLSX.read(ab, { type: 'array', raw: true, cellText: false, cellDates: false });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];
      if (rows.length < 2) { setStatusMsg('No data rows found.'); setStatusType('err'); setProcessing(false); return; }

      const headers = rows[0].map(h => String(h).trim().toLowerCase().replace(/\s+/g, '_'));
      const parsedRows: Record<string, string>[] = [];
      for (let i = 1; i < rows.length; i++) {
        const raw = rows[i] as unknown[];
        const obj: Record<string, string> = { __rowIndex: String(i) };
        headers.forEach((h, j) => { if (h) obj[h] = cellToString(raw[j]); });
        parsedRows.push(obj);
      }

      const dates = parsedRows.map(r => detectCallDate(r));
      const autoOrder = detectDateFormat(dates);
      setDateParseOrder(autoOrder);

      const phoneGroups = new Map<string, { rows: Record<string, string>[]; outcomes: string[]; dispositions: string[] }>();
      let skippedNoPhone = 0;
      for (const row of parsedRows) {
        const rawPhone = detectPhone(row);
        const phone = normalizePhone(rawPhone);
        if (!phone) { skippedNoPhone++; continue; }
        if (!phoneGroups.has(phone)) phoneGroups.set(phone, { rows: [], outcomes: [], dispositions: [] });
        const g = phoneGroups.get(phone)!;
        g.rows.push(row);
        g.outcomes.push(detectOutcome(row).toLowerCase().trim());
        g.dispositions.push(detectDisposition(row).toLowerCase().trim());
      }

      const included: IncludedLead[] = [];
      const excluded: ExcludedLead[] = [];
      let connectedCount = 0, terminalCount = 0, groupsWithDate = 0, groupsWithoutDate = 0;

      for (const [phone, group] of phoneGroups) {
        const connectedRows = group.rows.filter(row => isConnectedOutcome(detectOutcome(row)));
        const reattemptableConnectedRows = connectedRows.filter(row => isReattemptConnectedSummary(detectSummary(row)));
        const blockingConnectedRows = connectedRows.filter(row => !isReattemptConnectedSummary(detectSummary(row)));
        const hasConnected = blockingConnectedRows.length > 0;
        const hasReattemptableConnected = reattemptableConnectedRows.length > 0;
        const hasTerminal = excludeTerminal && group.dispositions.some(d => TERMINAL_DISPOSITIONS.has(d));
        const bestRow = getLatestRow(group.rows)!;
        const terminalRows = group.rows.filter(row => TERMINAL_DISPOSITIONS.has(String(detectDisposition(row)).toLowerCase().trim()));
        const blockingConnectedRow = getLatestRow(blockingConnectedRows);
        const reattemptableConnectedRow = getLatestRow(reattemptableConnectedRows);
        const terminalRow = getLatestRow(terminalRows);
        if (group.rows.some(row => getRowRank(row).hasDate)) groupsWithDate++;
        else groupsWithoutDate++;

        if (hasConnected) {
          connectedCount++;
          excluded.push({ phone, full_name: detectFullName(bestRow), bestOutcome: 'Connected', bestDisposition: detectDisposition(blockingConnectedRow || bestRow) || group.dispositions[group.dispositions.length - 1], daysSeen: group.rows.length, reason: `Connected on ${formatRankDate(blockingConnectedRow!)}; latest row ${formatRankDate(bestRow)}` });
        } else if (hasTerminal) {
          terminalCount++;
          excluded.push({ phone, full_name: detectFullName(bestRow), bestOutcome: detectOutcome(terminalRow || bestRow), bestDisposition: detectDisposition(terminalRow!) || group.dispositions.find(d => TERMINAL_DISPOSITIONS.has(d)) || group.dispositions[group.dispositions.length - 1], daysSeen: group.rows.length, reason: `Terminal on ${formatRankDate(terminalRow!)}: ${detectDisposition(terminalRow!)}` });
        } else {
          included.push({ phone, full_name: detectFullName(bestRow), disposition_raw: detectDisposition(bestRow).toLowerCase().trim(), updated_disposition_raw: detectUpdatedDisposition(bestRow).toLowerCase().trim(), model: detectModel(bestRow), seating: detectSeating(bestRow), city: detectCity(bestRow), pincode: detectPincode(bestRow), daysSeen: group.rows.length, showroom_code: dealership.showroom_code, region_name: dealership.region_name, dealership_id: dealership.dealership_id, brand: dealership.brand, subdivision_name: dealership.subdivision_name, source_date: formatRankDate(bestRow), reattempt_reason: hasReattemptableConnected ? detectSummary(reattemptableConnectedRow!) : '', _row: bestRow });
        }
      }

      setAllIncludedLeads(included.slice());
      setIncludedLeads(included.slice());
      setExcludedLeads(excluded);
      setConnectedCount(connectedCount);
      setTerminalCount(terminalCount);
      setSkippedNoPhone(skippedNoPhone);
      setGroupsWithDate(groupsWithDate);
      setGroupsWithoutDate(groupsWithoutDate);
      setShowResults(true);

      batchFingerprintRef.current = fileBatchFingerprint(rawFile, parsedRows.length);
      batchInputRowCountRef.current = parsedRows.length;
      batchTemplateIdRef.current = dealershipKey;
      setStartLead(1);
      setNumBatches(1);

      setStatusMsg(`✓ ${included.length} leads ready for re-attempt. ${connectedCount + terminalCount} excluded.`);
      setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg('Error processing request.');
      setStatusType('err');
    }
    setProcessing(false);
  }

  function applyDispoFilter(filter: Set<string>) {
    if (filter.size === 0) {
      setIncludedLeads(allIncludedLeads.slice());
    } else {
      setIncludedLeads(allIncludedLeads.filter(lead => {
        const disp = lead.disposition_raw || '';
        const updDisp = lead.updated_disposition_raw || '';
        let matched = false;
        filter.forEach(val => {
          if (val === '__blanks__') { if (!disp || !updDisp || disp === '' || updDisp === '') matched = true; }
          else { if (disp === val || updDisp === val) matched = true; }
        });
        return matched;
      }));
    }
  }

  function downloadOutput() {
    if (!includedLeads.length) return;
    const schema = getOutputSchema(dealershipKey);
    const total = includedLeads.length;
    let start = startLead;
    if (start < 1) start = 1;
    if (start > total) { setStatusMsg(`Start lead must be between 1 and ${total}.`); setStatusType('err'); return; }
    const remaining = total - start + 1;
    const maxBatches = Math.ceil(remaining / AE_LEADS_PER_BATCH);
    let num = numBatches;
    if (num < 1) num = 1;
    if (num > maxBatches) num = maxBatches;

    const dateStr = new Date().toISOString().slice(0, 10);
    const safeName = dealership.name.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '');
    let exported = 0, filesWritten = 0;

    for (let b = 0; b < num; b++) {
      const sliceStartIdx = start - 1 + b * AE_LEADS_PER_BATCH;
      if (sliceStartIdx >= total) break;
      const sliceLen = Math.min(AE_LEADS_PER_BATCH, total - sliceStartIdx);
      const slice = includedLeads.slice(sliceStartIdx, sliceStartIdx + sliceLen);
      const aoa: string[][] = [schema.headers];
      for (const r of slice) aoa.push(schema.mapRow(r));
      const part = num > 1 ? '_batch' + (b + 1) : '';
      const fileName = safeName + '_ReAttempt_' + dateStr + part + '.csv';
      const csvRows = aoa.map(row => row.map(c => { const s = excelSafe(c); return /[\",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }).join(','));
      const bom = '\uFEFF';
      const blob = new Blob([bom + csvRows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      try {
        const a = document.createElement('a');
        a.href = url; a.download = fileName;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
      } finally {
        URL.revokeObjectURL(url);
      }
      exported += sliceLen; filesWritten++;
    }

    const nextLeadIndex = start + exported;
    if (batchFingerprintRef.current && batchTemplateIdRef.current) saveBatchProgress(batchFingerprintRef.current, batchTemplateIdRef.current, batchInputRowCountRef.current, nextLeadIndex);
    if (nextLeadIndex <= total) { setStartLead(nextLeadIndex); const rem = total - nextLeadIndex + 1; setNumBatches(Math.max(1, Math.ceil(rem / AE_LEADS_PER_BATCH))); }
    else { setStartLead(1); setNumBatches(1); }
    setStatusMsg(`Downloaded ${filesWritten} file(s), ${exported} lead(s).`);
    setStatusType('ok');
  }

  async function copyOutputData() {
    if (!includedLeads.length) return;
    const schema = getOutputSchema(dealershipKey);
    const lines = [schema.headers.join('\t')];
    for (const r of includedLeads) lines.push(schema.mapRow(r).map(v => String(v ?? '').replace(/\t/g, ' ').replace(/\n/g, ' ')).join('\t'));
    const tsv = lines.join('\n');
    try { await navigator.clipboard.writeText(tsv); setStatusMsg('✓ Copied'); setStatusType('ok'); }
    catch { setStatusMsg('⚠ Copy failed'); setStatusType('warn'); }
  }

  function resetAll() {
    setRawFile(null); setIncludedLeads([]); setAllIncludedLeads([]); setExcludedLeads([]); setShowResults(false);
    setFileStatus('Drag & drop or click to browse'); setHasFile(false);
    setStatusMsg(''); setStatusType('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const v = validateFileSync(file);
    if (!v.valid) { setFileStatus(v.error!); return; }
    setRawFile(file);
    setFileStatus(`Loaded: ${file.name}`);
    setHasFile(true);
    setShowResults(false);
    setIncludedLeads([]);
    setAllIncludedLeads([]);
    setExcludedLeads([]);
    setStatusMsg('');
    setStatusType('');
    setActiveDispoFilter(new Set());
    setStartLead(1);
    setNumBatches(1);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setFileDragOver(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const dt = new DataTransfer(); dt.items.add(f);
    if (fileInputRef.current) { fileInputRef.current.files = dt.files; fileInputRef.current.dispatchEvent(new Event('change', { bubbles: true })); }
  }

  function esc(v: unknown) { return String(v ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }

  const schema = getOutputSchema(dealershipKey);
  const previewLimit = 200;
  const includedPreview = includedLeads.slice(0, previewLimit);
  const excludedPreview = excludedLeads.slice(0, previewLimit);
  const totalRows = batchInputRowCountRef.current || 0;
  const phoneGroupCount = allIncludedLeads.length + excludedLeads.length;
  const dedupRemoved = totalRows - phoneGroupCount;

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Re-Attempt Filter</h1>
              <div className="header-sub">Smart Re-Attempt Filter → AutoEngage Upload</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        <section className={styles.panel}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 1</div>
              <div className={styles['section-title']}>Upload & Configure</div>
            </div>
            <div className={styles['section-note']}>Upload your Zoho Master Sheet export with multi-day data.</div>
          </div>

          <div
            className={`${styles['drop-zone']} ${fileDragOver ? styles['drag-over'] : ''} ${hasFile ? styles['has-file'] : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setFileDragOver(true); }}
            onDragLeave={() => setFileDragOver(false)}
            onDrop={handleDrop}
          >
            <div className={styles['dz-icon']}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg></div>
            <div className={styles['dz-label']}>Zoho Master Sheet Export</div>
            <div className={styles['dz-sublabel']}>Upload filtered multi-day data as CSV or Excel</div>
            <div className={styles['dz-cols']}>Lead_Id · Full_Name · Phone · City · Pincode · Language · Lead_Source<br />Cohort · Campaign_ID · Call Triggered · Outcome · Disposition<br />SUMMARY · Conversion · Call_Date · Number of attempts · Model · Seating</div>
            <div className={`${styles['dz-status']} ${hasFile ? styles['ok'] : ''}`}>{fileStatus}</div>
            <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} style={{ display: 'none' }} />
          </div>

          <div className={styles['action-bar']}>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>Dealership</span>
              <div className={styles['select-wrapper']}>
                <select className={styles['custom-select']} value={dealershipKey} onChange={e => setDealershipKey(e.target.value)}>
                  <optgroup label="Pre-Sales">
                    <option value="anant_cars">Anant Cars (Sales)</option>
                    <option value="singhal">Singhal (Sales)</option>
                    <option value="fortune_hyryder">Fortune Hyryder (Sales)</option>
                  </optgroup>
                  <optgroup label="Post-Sales">
                    <option value="perfect_riders">Perfect Riders (Service)</option>
                    <option value="ambal_service">Ambal (Service)</option>
                    <option value="bullmen_service">Bullmen (Service)</option>
                    <option value="fortune_service">Fortune Toyota (Service)</option>
                    <option value="suryabala_service">Suryabala Honda (Service)</option>
                    <option value="icare_feedback">Icare (Feedback)</option>
                  </optgroup>
                </select>
              </div>
            </div>

            <div className={styles['toggle-group']}>
              <input type="checkbox" id="chkExcludeTerminal" checked={excludeTerminal} onChange={e => setExcludeTerminal(e.target.checked)} />
              <label htmlFor="chkExcludeTerminal">Exclude terminal dispositions</label>
            </div>

            <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={processFileAction} disabled={!rawFile || processing}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M4 4v5h.582m15.356 2A8 8 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8 8 0 01-15.357-2m15.357 2H15"/></svg>
              Filter Re-Attempt Leads
            </button>

            <span className={styles['date-parser-note']}>Format: {dateParseOrder === 'MDY' ? 'MM/DD/YYYY' : 'DD/MM/YYYY'}</span>

            {showResults && (
              <>
                {allIncludedLeads.length > 0 && (
                  <div className={styles['dispo-filter-wrapper']} style={{ display: 'inline-flex' }}>
                    <button className={`${styles['btn-dispo-filter']} ${activeDispoFilter.size > 0 ? styles['active'] : ''}`} onClick={() => setDispoFilterVisible(!dispoFilterVisible)}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
                      Disposition
                      {activeDispoFilter.size > 0 && <span className={styles['dispo-filter-badge']}>{activeDispoFilter.size}</span>}
                    </button>
                    {dispoFilterVisible && (
                      <div ref={dispoDropdownRef} className={styles['dispo-filter-dropdown']} style={{ display: 'block' }}>
                        <div className={styles['dispo-filter-header']}>Filter by disposition</div>
                        <div className={`${styles['dispo-filter-count']} ${activeDispoFilter.size === 0 ? styles['muted'] : ''}`}>
                          {activeDispoFilter.size > 0 ? `${includedLeads.length} of ${allIncludedLeads.length} leads match` : `All ${allIncludedLeads.length} leads (no filter)`}
                        </div>
                        {DISPOSITION_FILTER_VALUES.map(val => (
                          <label key={val} className={styles['dispo-filter-option']}>
                            <input type="checkbox" checked={activeDispoFilter.has(val)} onChange={() => {
                              const next = new Set(activeDispoFilter);
                              if (next.has(val)) next.delete(val); else next.add(val);
                              setActiveDispoFilter(next);
                              applyDispoFilter(next);
                            }} />
                            {val === '__blanks__' ? 'Blanks' : val.charAt(0).toUpperCase() + val.slice(1)}
                          </label>
                        ))}
                        <div className={styles['dispo-filter-actions']}>
                          <button className={`${styles.btn} ${styles['btn-sm']}`} onClick={() => { const empty = new Set<string>(); setActiveDispoFilter(empty); applyDispoFilter(empty); }}>Clear</button>
                          <button className={`${styles.btn} ${styles['btn-sm']} ${styles['btn-primary']}`} onClick={() => setDispoFilterVisible(false)}>Done</button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                <button className={`${styles.btn} ${styles['btn-success']}`} onClick={downloadOutput} disabled={!includedLeads.length}>Export Batches</button>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={copyOutputData} disabled={!includedLeads.length}>Copy TSV</button>
                <button className={`${styles.btn} ${styles['btn-danger-outline']}`} onClick={resetAll}>Reset</button>
              </>
            )}
            <span className={`${styles['status-msg']} ${statusType ? styles[statusType] : ''}`}>{statusMsg}</span>
          </div>
        </section>

        {/* Batch Panel */}
        {showResults && includedLeads.length > 0 && (
          <div className={styles['batch-panel']} style={{ display: 'block' }}>
            <div className={styles['batch-panel-title']}>Batch download</div>
            <div className={styles['batch-panel-note']}>Each file: header + up to 100 leads (101 rows max per batch).</div>
            <div className={styles['batch-row']}>
              <div className={styles['batch-field']}>
                <label>Start at lead #</label>
                <input type="number" min={1} value={startLead} onChange={e => setStartLead(parseInt(e.target.value) || 1)} />
              </div>
              <div className={styles['batch-field']}>
                <label>Batches to download</label>
                <input type="number" min={1} value={numBatches} onChange={e => setNumBatches(parseInt(e.target.value) || 1)} />
              </div>
            </div>
            <div className={`${styles['batch-hint']} ${styles.mono}`}>
              {includedLeads.length} lead(s). From lead #{Math.min(startLead, includedLeads.length)}, {Math.max(0, includedLeads.length - startLead + 1)} left.
            </div>
            <button className={styles['batch-forget']} onClick={() => {
              if (batchFingerprintRef.current) clearBatchProgressForFingerprint(batchFingerprintRef.current);
              setStatusMsg('Forgot saved batch progress.'); setStatusType('ok');
            }}>Forget saved progress</button>
          </div>
        )}

        <section className={styles.panel}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 2</div>
              <div className={styles['section-title']}>Results</div>
            </div>
          </div>

          {!showResults && (
            <div className={styles['empty-state']}>
              <div><strong>Waiting for data</strong><p>Upload a Zoho Master Sheet export and click Filter.</p></div>
              <div className={styles['empty-steps']}><span>Upload</span><span>Filter</span><span>Review</span><span>Download</span></div>
            </div>
          )}

          {showResults && (
            <>
              <div className={styles['stats-bar']} style={{ display: 'flex' }}>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Total Rows</div><div className={`${styles['stat-val']} ${styles.blue}`}>{totalRows}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Unique Phones</div><div className={`${styles['stat-val']} ${styles.purple}`}>{phoneGroupCount}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Other Connected (Excluded)</div><div className={`${styles['stat-val']} ${styles.green}`}>{excludedLeads.length}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Terminal (Excluded)</div><div className={`${styles['stat-val']} ${styles.amber}`}>{terminalCount}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Re-Attempt List</div><div className={`${styles['stat-val']} ${styles.red}`}>{includedLeads.length}</div></div>
              </div>

              <div className={styles['dedup-summary']} style={{ display: 'block' }}>
                <div className={styles['dedup-title']}>Deduplication Breakdown</div>
                <div className={styles['dedup-grid']}>
                  {[
                    { label: 'Total input rows', value: totalRows, tone: 'blue' },
                    { label: 'Unique phones', value: phoneGroupCount, tone: 'purple' },
                    { label: 'Duplicate rows removed', value: Math.max(0, totalRows - phoneGroupCount - skippedNoPhone), tone: 'amber' },
                    { label: 'Other connected (excluded)', value: connectedCount, tone: 'green' },
                    { label: 'Terminal disp. (excluded)', value: terminalCount, tone: 'amber' },
                    { label: 'Invalid phones skipped', value: skippedNoPhone, tone: 'red' },
                    { label: 'Re-attempt output', value: includedLeads.length, tone: 'blue' },
                    { label: 'Exclusion rate', value: phoneGroupCount ? Math.round(((connectedCount + terminalCount) / phoneGroupCount) * 100) + '%' : '0%', tone: 'purple' },
                    { label: 'Date-ranked phones', value: groupsWithDate, tone: 'green' },
                    { label: 'File-order fallback', value: groupsWithoutDate, tone: groupsWithoutDate ? 'amber' : 'green' },
                  ].map((item, i) => (
                    <div key={i} className={`${styles['dedup-item']} ${styles[item.tone]}`}>
                      <div className={styles.label}>{item.label}</div>
                      <div className={styles.value}>{item.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Included Table */}
              <div className={styles['table-wrapper']} style={{ display: includedLeads.length ? 'block' : 'none' }}>
                <div className={styles['table-header']}>
                  <div className={styles['table-title'] + ' ' + styles.included}>Re-Attempt List</div>
                  <div className={styles['table-caption']}>
                    {includedLeads.length > previewLimit ? `Showing first ${previewLimit} of ${includedLeads.length} leads` : `${includedLeads.length} leads`}
                  </div>
                </div>
                <div className={styles['table-scroll']}>
                  <table>
                    <thead><tr>{schema.headers.map(h => <th key={h}>{esc(h)}</th>)}</tr></thead>
                    <tbody>
                      {includedPreview.map((r, i) => (
                        <tr key={i}>{schema.mapRow(r).map((v, j) => <td key={j} className={j === schema.headers.indexOf('phone_number') ? styles['cell-phone'] : ''}>{esc(v)}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Excluded Table */}
              <div className={styles['table-wrapper']} style={{ display: excludedLeads.length ? 'block' : 'none' }}>
                <div className={styles['table-header']}>
                  <div className={styles['table-title'] + ' ' + styles.excluded}>Excluded Leads</div>
                  <div className={styles['table-caption']}>
                    {excludedLeads.length > previewLimit ? `Showing first ${previewLimit} of ${excludedLeads.length} leads` : `${excludedLeads.length} leads`}
                  </div>
                </div>
                <div className={styles['table-scroll']}>
                  <table>
                    <thead><tr><th>Phone</th><th>Full Name</th><th>Best Outcome</th><th>Best Disposition</th><th>Days Seen</th><th>Reason</th></tr></thead>
                    <tbody>
                      {excludedPreview.map((r, i) => (
                        <tr key={i}>
                          <td className={styles['cell-phone']}>{esc(r.phone)}</td>
                          <td>{esc(r.full_name)}</td>
                          <td className={styles['cell-connected']}>{esc(r.bestOutcome)}</td>
                          <td className={styles['cell-terminal']}>{esc(r.bestDisposition)}</td>
                          <td>{r.daysSeen}</td>
                          <td className={styles['cell-reason']}>{esc(r.reason)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </section>
      </main>
      <footer>AutoNage — Re-Attempt Filter — Zoho → Re-Attempt → AutoEngage</footer>
      <ProcessingOverlay show={processing} message="Processing file…" />
    </div>
  );
}
