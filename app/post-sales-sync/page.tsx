'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import BatchProgressBar from '@/components/BatchProgressBar';
import { useBatchProgress } from '@/hooks/useBatchProgress';
import { readFileAsArrayBuffer, clean, esc, normalizePhone, canonicalHeader, isPhoneLike, excelSafe, validateFileSync, colLetter } from '@/lib/data-pipeline';
import * as XLSX from 'xlsx';
import { $log } from '@/lib/logger';
import { classifyDisposition, isServiceBooked, isServiceCompleted, isNotInterested, isFeedbackOrEscalation, extractPerfectRidersLocation, extractPerfectRidersCRE } from './classify-utils';
import { getOutputColumnsForDealer, buildSessionMap, buildQualityReport, scoreFileRole, evaluateFileRoles, get, formatDate, convertEpochToIST, parseAutoEngageDate, extractSessionData } from './quality-utils';
import { buildDispoValidationPrompt, parseLlmResponse, hashStr } from './prompt-builder';
import { runLlmBatches } from '@/lib/ai/llm-batch-runner';
import styles from './post-sales-sync.module.css';

const DEALERSHIPS: Record<string, { name: string; workflow: string; mode: string; leadColumns: string[]; sessionColumns: string[] }> = {
  ambal_service: { name: 'Ambal', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['reg_number', 'vin_number', 'campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'customer_score', 'workshop_code', 'next_service_due', 'odometer_reading'], sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail'] },
  bullmen_service: { name: 'Bullmen', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['reg_number', 'campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'workshop_code', 'next_service_due', 'vin_number'], sessionColumns: ['status', 'summary', 'duration', 'start_time', 'call_recording', 'sentiment_score', 'disposition_detail'] },
  fortune_service: { name: 'Fortune Toyota', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'reg_number', 'vin_number', 'next_service_due'], sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail', 'service_type'] },
  saisamarth: { name: 'Saisamarth', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'reg_number', 'vin_number', 'next_service_due'], sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail'] },
  icare_feedback: { name: 'Icare', workflow: 'Post-Sales Feedback Reminder', mode: 'post', leadColumns: ['campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'reg_number', 'vin_number', 'showroom_code', 'lead_code_for_dealership'], sessionColumns: ['status', 'duration', 'start_time', 'summary', 'call_recording', 'sentiment_score', 'disposition_detail', 'id_salt'] },
  pressana_post_service_feedback: { name: 'Pressana Kia', workflow: 'Post Service Feedback', mode: 'post', leadColumns: ['campaign_id', 'phone_number', 'last_service_date'], sessionColumns: ['duration', 'status', 'start_time', 'sentiment_score', 'summary', 'call_recording', 'disposition_detail'] },
  perfect_riders_service: { name: 'Perfect Riders', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['campaign_id', 'phone_number', 'existing_vehicle_model', 'vin_number'], sessionColumns: ['duration', 'status', 'start_time', 'sentiment_score', 'summary', 'call_recording', 'disposition_detail'] },
  pressana_service_feedback: { name: 'Pressana', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['campaign_id', 'phone_number', 'existing_vehicle_model'], sessionColumns: ['duration', 'status', 'start_time', 'sentiment_score', 'summary', 'call_recording', 'disposition_detail'] },
  suryabala_service: { name: 'Suryabala Honda', workflow: 'Post-Sales Service Reminder', mode: 'post', leadColumns: ['reg_number', 'campaign_id', 'person_name', 'phone_number', 'vehicle_model', 'next_service_due', 'last_service_type', 'vin_number'], sessionColumns: ['status', 'summary', 'duration', 'start_time', 'call_recording', 'sentiment_score', 'disposition_detail'] },
  fortune_toyota_wa: { name: 'Fortune Toyota WA', workflow: 'WhatsApp Campaign', mode: 'post', leadColumns: ['lead_id', 'full_name', 'phone', 'city', 'pincode', 'language', 'cohort', 'campaign_id'], sessionColumns: ['call_triggered', 'status', 'summary', 'disposition_details', 'call_date', 'sentiment', 'duration', 'number_of_attempts'] },
  perfect_rider_wa: { name: 'Perfect Rider WA', workflow: 'WhatsApp Campaign', mode: 'post', leadColumns: ['lead_id', 'full_name', 'phone', 'city', 'pincode', 'language', 'cohort', 'campaign_id'], sessionColumns: ['call_triggered', 'status', 'summary', 'disposition_details', 'call_date', 'sentiment', 'duration', 'number_of_attempts'] },
};

export default function PostSalesSyncPage() {
  const log = (...args) => console.log('[PostSales]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [rawFile1, setRawFile1] = useState<File | null>(null);
  const [rawFile2, setRawFile2] = useState<File | null>(null);
  const [dealerKey, setDealerKey] = useState('ambal_service');
  const [leadIdStart, setLeadIdStart] = useState('');
  const [language, setLanguage] = useState('English');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [processing, setProcessing] = useState(false);
  const [processedData, setProcessedData] = useState<Record<string, string>[]>([]);
  const [qualityReport, setQualityReport] = useState<any>(null);
  const [bookedRows, setBookedRows] = useState<Record<string, string>[]>([]);
  const [completedRows, setCompletedRows] = useState<Record<string, string>[]>([]);
  const [notInterestedRows, setNotInterestedRows] = useState<Record<string, string>[]>([]);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [sessionCount, setSessionCount] = useState(0);
  const [file1Status, setFile1Status] = useState('Drag and drop or click to browse');
  const [file2Status, setFile2Status] = useState('Drag and drop or click to browse');
  const [hasFile1, setHasFile1] = useState(false);
  const [hasFile2, setHasFile2] = useState(false);
  const [dragOver1, setDragOver1] = useState(false);
  const [dragOver2, setDragOver2] = useState(false);

  // AI validation state
  const aiProgress = useBatchProgress();

  // Sort state
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc' | null>(null);

  const file1Ref = useRef<HTMLInputElement>(null);
  const file2Ref = useRef<HTMLInputElement>(null);

  const aiValidationRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  const dealer = DEALERSHIPS[dealerKey];
  const previewLimit = 200;

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  function cellToString(val: unknown): string {
    if (val == null) return '';
    if (typeof val === 'number') {
      if (Number.isInteger(val)) return String(val);
      if (val > 999999 && Math.abs(val - Math.round(val)) < 0.01) return String(Math.round(val));
      return String(val);
    }
    let s = String(val).trim();
    if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) { const n = parseFloat(s); if (isFinite(n) && n > 999999) return String(Math.round(n)); }
    return s;
  }

  function parseSheet(ab: ArrayBuffer): Record<string, string>[] {
    $log('Data', 'parseSheet — parsing workbook...');
    const wb = XLSX.read(ab, { type: 'array', raw: true, cellText: false, cellDates: false });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];
    if (rows.length < 2) return [];
    const headers = rows[0].map(h => canonicalHeader(h));
    const result: Record<string, string>[] = [];
    for (let i = 1; i < rows.length; i++) {
      const raw = rows[i] as unknown[];
      if (!raw.some(c => clean(c))) continue;
      const obj: Record<string, string> = {};
      headers.forEach((h, j) => { if (h) obj[h] = cellToString(raw[j]); });
      obj.__raw = JSON.stringify(raw.map(cellToString));
      result.push(obj);
    }
    return result;
  }

  function detectPhones(obj: Record<string, string>): string[] {
    const phones = new Set<string>();
    const exactNames = ['phone_number', 'phone', 'mobile', 'contact', 'contact_number', 'customer_phone', 'mobile_number'];
    for (const c of exactNames) { const n = normalizePhone(obj[c]); if (n) phones.add(n); }
    for (const val of Object.values(obj)) {
      const s = clean(val);
      if (!s) continue;
      if (isPhoneLike(s)) { const n = normalizePhone(s); if (n) phones.add(n); }
      const matches = s.match(/\+?(?:91|0)?[\s-]?\d{10,12}\b/g);
      if (matches) for (const m of matches) { const n = normalizePhone(m); if (n) phones.add(n); }
    }
    return Array.from(phones);
  }

  function safeRecordingHref(value: string): string | null {
    const raw = String(value ?? '').trim();
    if (!raw) return null;
    const lower = raw.toLowerCase();
    if (lower.startsWith('javascript:') || lower.startsWith('data:') || lower.startsWith('vbscript:')) return null;
    if (lower.startsWith('http://') || lower.startsWith('https://')) return raw;
    if (lower.startsWith('s3:')) return raw;
    if (/^[a-z0-9.-]+\.[a-z]{2,}(?:[/:?#].*)?$/i.test(raw)) return `https://${raw}`;
    return null;
  }

  function toggleSort(key: string) {
    if (sortKey === key) {
      if (sortDir === 'asc') setSortDir('desc');
      else if (sortDir === 'desc') { setSortKey(null); setSortDir(null); }
    } else { setSortKey(key); setSortDir('asc'); }
  }

  function getSortedData(data: Record<string, string>[]): Record<string, string>[] {
    if (!sortKey || !sortDir) return data;
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...data].sort((a, b) => {
      const va = String(a[sortKey!] || ''), vb = String(b[sortKey!] || '');
      if (va !== vb) return va < vb ? -dir : dir;
      return String(a.lead_id || '').localeCompare(String(b.lead_id || ''), undefined, { numeric: true });
    });
  }

  function renderStats(output: Record<string, string>[], booked: Record<string, string>[], completed: Record<string, string>[], notInterested: Record<string, string>[], sessionsIn: number) {
    const matched = output.filter(r => r._matched === 'true').length;
    const notConnected = output.filter(r => r.outcome === 'Not Connected').length;
    const unknown = output.filter(r => r.outcome === 'Unknown').length;
    return { leads: output.length, sessionsIn, matched, booked: booked.length, completed: completed.length, notInterested: notInterested.length, notConnected, unknown };
  }

  function dedupeByPhone(rows: Record<string, string>[]): Record<string, string>[] {
    const seen = new Set<string>();
    return rows.filter(r => {
      const phone = r.phone_number || '';
      if (!phone || seen.has(phone)) return false;
      seen.add(phone);
      return true;
    });
  }

  function rowsToTsv(rows: Record<string, string>[], keys: string[]): string {
    return rows.map(r => keys.map(k => String(r[k] ?? '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ')).join('\t')).join('\n');
  }

  async function copyText(text: string, statusText: string) {
    try { await navigator.clipboard.writeText(text); } catch {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
      document.body.appendChild(ta); ta.focus(); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta);
    }
    setStatusMsg(statusText); setStatusType('ok');
  }

  async function processFiles() {
    if (!rawFile1 || !rawFile2) return;
    log('Processing started, files:', rawFile1.name, rawFile2.name);
    setProcessing(true);
    setStatusMsg('Parsing files...'); setStatusType('');

    try {
      const startId = parseInt(leadIdStart, 10) || 0;
      const [ab1, ab2] = await Promise.all([readFileAsArrayBuffer(rawFile1), readFileAsArrayBuffer(rawFile2)]);
      const rows1 = parseSheet(ab1);
      const rows2 = parseSheet(ab2);
      const role1 = scoreFileRole(rows1);
      const role2 = scoreFileRole(rows2);
      const roleInfo = evaluateFileRoles(role1, role2);
      const filesSwapped = roleInfo.filesSwapped;
      const leadRows = filesSwapped ? rows2 : rows1;
      const sessionRows = filesSwapped ? rows1 : rows2;

      // Build leads array + lookup by phone
      const leads: { row: Record<string, string>; phone: string }[] = [];
      const leadsByPhone: Record<string, { row: Record<string, string>; phone: string }> = {};
      for (const row of leadRows) {
        const phone = normalizePhone(get(row, ['phone_number', 'phone', 'mobile', 'contact_number', 'mobile_number']));
        if (!phone) continue;
        leads.push({ row, phone });
        leadsByPhone[phone] = { row, phone };
      }

      // Filter session rows by date range
      let filteredSessionRows = sessionRows;
      if (fromDate) {
        const from = new Date(fromDate + 'T00:00:00');
        filteredSessionRows = filteredSessionRows.filter(r => {
          const d = get(r, ['start_time', 'start_date', 'call_start_time', 'call_time', 'created', 'created_at', 'date', 'timestamp', 'call_date', 'updated', 'updated_at']);
          if (!d) return false;
          const dt = parseAutoEngageDate(d);
          return dt && dt >= from;
        });
      }
      if (toDate) {
        const to = new Date(toDate + 'T23:59:59');
        filteredSessionRows = filteredSessionRows.filter(r => {
          const d = get(r, ['start_time', 'start_date', 'call_start_time', 'call_time', 'created', 'created_at', 'date', 'timestamp', 'call_date', 'updated', 'updated_at']);
          if (!d) return false;
          const dt = parseAutoEngageDate(d);
          return dt && dt <= to;
        });
      }

      const { groups: sessionGroups } = buildSessionMap(filteredSessionRows);
      const output: Record<string, string>[] = [];
      const outputCols = getOutputColumnsForDealer(dealerKey);
      const phoneIdx = outputCols.findIndex(c => c.key === 'phone_number');
      const phoneCol = phoneIdx >= 0 ? colLetter(phoneIdx) : 'C';

      // Call Triggered text — use filtered session rows date range as fallback
      let minDate: Date | null = null, maxDate: Date | null = null;
      for (const r of filteredSessionRows) {
        const d = parseAutoEngageDate(get(r, ['start_time', 'start_date', 'call_start_time', 'call_time', 'created', 'created_at', 'date', 'timestamp', 'call_date', 'updated', 'updated_at']));
        if (!d) continue;
        if (!minDate || d < minDate) minDate = d;
        if (!maxDate || d > maxDate) maxDate = d;
      }
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
      let callTriggeredText = '';
      if (minDate && maxDate) {
        const day = minDate.getDate();
        const suffix = ['th', 'st', 'nd', 'rd'][(day % 10) - 1] || 'th';
        const tMin = `${minDate.getHours()}:${String(minDate.getMinutes()).padStart(2, '0')}`;
        const tMax = `${maxDate.getHours()}:${String(maxDate.getMinutes()).padStart(2, '0')}`;
        callTriggeredText = `${day}${suffix} ${monthNames[minDate.getMonth()]} Calls Triggered From ${tMin} - ${tMax}`;
      }

      // Session-driven join: iterate over ALL sessions, output ONE row per call attempt
      for (const [phone, sessions] of Object.entries(sessionGroups)) {
        const lead = leadsByPhone[phone];
        if (!lead) continue;
        const { row } = lead;
        const totalAttempts = sessions.length;

        for (const sessionRow of sessions) {
          const sd = extractSessionData(sessionRow);
          const classification = classifyDisposition(sd.disposition, sd.status, sd.summary);
          const vehicleModel = get(row, ['vehicle_model', 'existing_vehicle_model', 'model', 'car_model']);
          const leadIdVal = startId > 0 ? `L-${startId + output.length}` : '';
          const interested = classification.outcome === 'Connected' ? 'YES' : '';
          const satisfied = (classification.outcome === 'Connected' && isFeedbackOrEscalation({ disposition_detail: sd.disposition, summary: sd.summary, session_status: sd.status })) ? 'YES' : '';

          output.push({
            lead_id: leadIdVal,
            dealership: dealer.name,
            workflow: dealer.workflow,
            campaign_id: get(row, ['campaign_id', 'campaign']),
            phone_number: phone,
            person_name: get(row, ['person_name', 'person_name1', 'customer_name', 'name', 'full_name']),
            showroom_code: get(row, ['showroom_code', 'show_room', 'dealer_code', 'store_code', 'location_code', 'lead_code_for_dealership']),
            reg_number: get(row, ['reg_number', 'registration_number', 'vehicle_registration_number']),
            vin_number: get(row, ['vin_number', 'vin', 'chassis_number', 'vin_chasis_number']),
            vehicle_model: vehicleModel,
            language,
            workshop_code: get(row, ['workshop_code', 'workshop', 'location_code', 'dealer_code', 'dealer']),
            dealer_code: get(row, ['workshop_code', 'workshop', 'location_code', 'dealer_code', 'dealer']),
            lead_tags: get(row, ['lead_tags', 'lead_tag', 'tags', 'tag', 'id', 'lead_id', 'leadid', 'customer_id']),
            full_name: get(row, ['full_name', 'person_name', 'customer_name', 'name', 'person_name1']),
            city: get(row, ['city', 'location', 'area', 'city_name']),
            pincode: get(row, ['pincode', 'pin_code', 'zip', 'zip_code', 'postal_code']),
            cohort: get(row, ['cohort', 'cohort_name', 'campaign_cohort']),
            model: get(row, ['model', 'car_model', 'model_name']),
            next_service_due: get(row, ['next_service_due', 'service_due_date', 'next_due_date']),
            last_service_date: convertEpochToIST(get(row, ['last_service_date', 'last_service_dt', 'last_service_done_date', 'last_service_done', 'last_service_on', 'last_service', 'service_date', 'service_done_date', 'service_completed_date'])),
            customer_score: get(row, ['customer_score', 'score']),
            odometer_reading: get(row, ['odometer_reading', 'odometer', 'kms']),
            last_service_type: get(row, ['last_service_type', 'service_type']),
            manual_disposition: get(row, ['manual_disposition', 'manual disposition', 'manual_disposition_detail', 'manual_disposition_details', 'manual_disposition_status', 'manual_dispo', 'manual_status']),
            origin: sessionRow['origin'] || '',
            lead_timeline: row['lead_timeline'] || '',
            session_status: sd.status || '',
            disposition: sd.disposition || '',
            disposition_detail: sd.disposition || '',
            call_triggered: get(sessionRow, ['call_triggered', 'triggered', 'trigger_type', 'call_trigger', 'is_triggered']) || callTriggeredText,
            outcome: classification.outcome,
            call_date: formatDate(sd.startTime || ''),
            duration: sd.duration || '',
            summary: sd.summary || '',
            session_summary: sd.summary || '',
            session_history: sd.history_text || '',
            sentiment_score: sd.sentiment || '',
            call_recording: sd.recording || '',
            recording_duration: sd.recordingDuration || '',
            last_session_id: sd.lastSessionId || '',
            session_id: get(sessionRow, ['session_id', 'Session_ID', 'id', 'call_id', 'last_session_id']),
            number_of_attempts: `=COUNTIF(${phoneCol}:${phoneCol};${phone})`,
            interested,
            satisfied,
            autongage_disposition: sd.disposition || '',
            service_location: dealerKey === 'perfect_riders_service' ? extractPerfectRidersLocation(sd.summary) : '',
            service_type: sd.serviceType || '',
            lead_source: dealerKey === 'perfect_rider_wa' ? get(row, ['lead_source', 'source', 'lead source']) : '',
            conversion: dealerKey === 'perfect_rider_wa' ? (row['conversion'] || '') : '',
            channel: dealerKey === 'perfect_rider_wa' ? (sessionRow['channel'] || '') : '',
            seating: dealerKey === 'perfect_rider_wa' ? get(row, ['seating', 'seat', 'seats']) : '',
            lead_row_id: get(row, ['id', 'lead_id', 'leadid', 'customer_id']),
            exclusion_flag: classification.terminal ? 'YES' : '',
            _matched: 'true',
            _priority: String(classification.priority),
            _ai_status: '',
            updated_disposition: '',
            id_salt: (dealerKey === 'icare_feedback') ? (sessionRow['id_salt'] || '') : '',
            lead_code_for_dealership: (dealerKey === 'icare_feedback') ? (row['lead_code_for_dealership'] || get(row, ['showroom_code', 'show_room', 'dealer_code', 'store_code', 'location_code', 'lead_code_for_dealership'])) : '',
          });
        }
      }

      const qr = buildQualityReport({ leadRows, sessionRows, filteredSessionRows, leads, sessionGroups, output, dealer, dealerKey, roleInfo });
      setProcessedData(output);
      setQualityReport(qr);

      // Deduplicate preview tables by phone so each lead appears once per category
      const bRows = dedupeByPhone(output.filter(isServiceBooked));
      const cRows = dedupeByPhone(output.filter(r => !isServiceBooked(r) && isServiceCompleted(r)));
      const nRows = dedupeByPhone(output.filter(r => !isServiceBooked(r) && !isServiceCompleted(r) && isNotInterested(r)));
      setBookedRows(bRows);
      setCompletedRows(cRows);
      setNotInterestedRows(nRows);
      setSessionCount(filteredSessionRows.length);
      setShowResults(true);
      log(`Processing complete: ${output.length} leads (${bRows.length} booked, ${cRows.length} completed, ${nRows.length} not interested)`);

      const roleNote = filesSwapped ? ' Upload order was auto-swapped.' : '';
      const statusTypeOut = qr.canExport ? (qr.state === 'review' ? 'warn' : 'ok') : 'err';
      const statusText = qr.canExport
        ? `${output.length} post-sales lead(s) processed for ${dealer.name}.${roleNote}`
        : `${output.length} post-sales lead(s) processed, but export blocked.${roleNote}`;
      setStatusMsg(statusText);
      setStatusType(statusTypeOut);
    } catch (err: unknown) {
      setStatusMsg('Error processing request.');
      setStatusType('err');
    }
    setProcessing(false);
  }

  async function copyData() {
    log('Copying data to clipboard');
    if (!processedData.length) return;
    if (qualityReport && !qualityReport.canExport) {
      setStatusMsg('Copy is blocked. Fix validation issues first.'); setStatusType('err');
      return;
    }
    const OUTPUT_COLUMNS = getOutputColumnsForDealer(dealerKey);
    await copyText(rowsToTsv(processedData, OUTPUT_COLUMNS.map(c => c.key)), 'Copied rows. Paste with Ctrl+V in Zoho.');
  }

  async function copyPreviewRows(type: string) {
    let rows: Record<string, string>[], keys: string[];
    if (type === 'booked') {
      rows = bookedRows;
      keys = ['phone_number', 'vehicle_model', 'vin_number', 'disposition_detail', 'service_location', 'call_date', 'cre_remarks', 'common_remarks'];
    } else if (type === 'completed') {
      rows = completedRows;
      keys = ['phone_number', 'vehicle_model', 'vin_number', 'disposition_detail', 'service_location', 'call_date', 'cre_remarks'];
    } else {
      rows = notInterestedRows;
      keys = ['phone_number', 'vehicle_model', 'vin_number', 'summary', 'call_date', 'cre_remarks'];
    }
    if (!rows?.length) { setStatusMsg('No rows to copy.'); setStatusType('warn'); return; }
    const isPR = dealerKey === 'perfect_riders_service';
    const data = rows.map(r => keys.map(k => {
      if (k === 'service_location') return isPR ? extractPerfectRidersLocation(r.summary || r.updated_disposition || r.disposition_detail) : '';
      if (k === 'cre_remarks') return isPR ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : '';
      if (k === 'common_remarks') return '';
      if (k === 'disposition_detail') return r.updated_disposition || r.disposition_detail || r.disposition || '';
      if (k === 'summary') return r.summary || '';
      return String(r[k] || '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ');
    }).join('\t')).join('\n');
    await copyText(data, `Copied ${rows.length} preview row(s).`);
  }

  async function copyQualityReport() {
    if (!qualityReport) return;
    const lines = [
      `Post-Sales Data Quality - ${qualityReport.title}`,
      `Copy/export: ${qualityReport.canExport ? 'READY' : 'BLOCKED'}`,
      ...(qualityReport.summary || []),
      '',
      ...qualityReport.warnings.map((w: any) => `${w.level.toUpperCase()}: ${w.text}`),
      '',
      ...qualityReport.samples.flatMap((s: any) => [s.title, ...s.rows.map((r: string) => `- ${r}`), '']),
    ];
    await copyText(lines.join('\n'), 'Copied quality report.');
  }

  function exportToExcel() {
    log('Exporting Excel, rows:', processedData.length);
    if (!processedData.length) return;
    if (qualityReport && !qualityReport.canExport) {
      setStatusMsg('Export is blocked.'); setStatusType('err');
      return;
    }
    const OUTPUT_COLUMNS = getOutputColumnsForDealer(dealerKey);
    const headers = OUTPUT_COLUMNS.map(c => c.header);
    const keys = OUTPUT_COLUMNS.map(c => c.key);
    const sorted = getSortedData(processedData);
    const dataRows = [headers, ...sorted.map(r => keys.map(k => excelSafe(r[k] ?? '')))];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(dataRows), 'Output');

    const isPR = dealerKey === 'perfect_riders_service';
    if (bookedRows.length) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([
        ['PHONE_NUMBER', 'VEHICLE_MODEL', 'VIN_NUMBER', 'DISPOSITION_DETAILS', 'LOCATION', 'CALL_DATE (MM/DD/YYYY)', 'Perfect Riders CRE Remarks', 'COMMON REMARKS'],
        ...bookedRows.map(r => [r.phone_number || '', r.vehicle_model || '', r.vin_number || '', r.updated_disposition || r.disposition_detail || r.disposition || '', isPR ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '', r.call_date || '', isPR ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : '', ''].map(excelSafe)),
      ]), 'Service Booked');
    }
    if (completedRows.length) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([
        ['PHONE_NUMBER', 'VEHICLE_MODEL', 'VIN_NUMBER', 'DISPOSITION_DETAILS', 'LOCATION', 'CALL_DATE (MM/DD/YYYY)', 'Perfect Riders CRE Remarks'],
        ...completedRows.map(r => [r.phone_number || '', r.vehicle_model || '', r.vin_number || '', r.updated_disposition || r.disposition_detail || r.disposition || '', isPR ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '', r.call_date || '', isPR ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : ''].map(excelSafe)),
      ]), 'Service Completed');
    }
    if (notInterestedRows.length) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([
        ['PHONE_NUMBER', 'VEHICLE_MODEL', 'VIN_NUMBER', 'SUMMARY', 'CALL_DATE (MM/DD/YYYY)', 'Perfect Riders CRE Remarks'],
        ...notInterestedRows.map(r => [r.phone_number || '', r.vehicle_model || '', r.vin_number || '', r.summary || '', r.call_date || '', isPR ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : ''].map(excelSafe)),
      ]), 'Not Interested');
    }

    const safeName = dealer.name.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '');
    XLSX.writeFile(wb, `AutoNage_Post_Sales_${safeName}.xlsx`);
  }

  function resetAll() {
    log('Reset'); setRawFile1(null); setRawFile2(null);
    setFromDate('');
    setToDate('');
    setProcessedData([]); setQualityReport(null);
    setBookedRows([]); setCompletedRows([]); setNotInterestedRows([]);
    setShowResults(false); setSessionCount(0); aiProgress.reset();
    setSortKey(null); setSortDir(null);
    setFile1Status('Drag and drop or click to browse');
    setFile2Status('Drag and drop or click to browse');
    setHasFile1(false); setHasFile2(false);
    setStatusMsg(''); setStatusType('');
    if (file1Ref.current) file1Ref.current.value = '';
    if (file2Ref.current) file2Ref.current.value = '';
  }

  function cancelAiValidation() {
    if (abortRef.current) {
      abortRef.current.abort();
    }
  }

  function validateDispositionsWithLLM(force = false) {
    if (!processedData.length) return;
    if (aiValidationRef.current) return;
    log('AI validation started, candidates:', processedData.filter(r => r.session_status === 'completed').length);

    const dealerCfg = DEALERSHIPS[dealerKey];
    const dealerName = dealerCfg ? dealerCfg.name : 'Unknown Dealership';
    const DEALER_LANGUAGES: Record<string, string[]> = {
      perfect_riders_service: ['Kannada', 'English'],
      fortune_service: ['Telugu', 'English'],
      saisamarth: ['English'],
      ambal_service: ['Tamil', 'English'],
      bullmen_service: ['Tamil', 'English'],
      pressana_service_feedback: ['Tamil', 'English'],
      pressana_post_service_feedback: ['Tamil', 'English'],
      suryabala_service: ['Tamil', 'English'],
      icare_feedback: ['Tamil', 'English'],
      fortune_toyota_wa: ['English'],
      perfect_rider_wa: ['English'],
    };
    const supportedLangs = DEALER_LANGUAGES[dealerKey] || ['English'];

    // Filter rows with completed session_status (matching original HTML logic)
    const candidates: { index: number; summary: string; history: string; currentDisp: string; callDate: string; outcome: string; vehicleModel: string; campaignId: string; dealerName: string; supportedLanguages: string }[] = [];
    for (let i = 0; i < processedData.length; i++) {
      const r = processedData[i];
      const summ = (r.session_summary || '').trim();
      const hist = (r.session_history || '').trim();
      const disp = (r.disposition_detail || r.disposition || '').trim();
      if (r.session_status === 'completed') {
        candidates.push({
          index: i,
          summary: summ,
          history: hist,
          currentDisp: disp,
          callDate: r.call_date || '',
          outcome: r.outcome || '',
          vehicleModel: r.vehicle_model || '',
          campaignId: r.campaign_id || '',
          dealerName,
          supportedLanguages: supportedLangs.join(', '),
        });
      }
    }

    if (!candidates.length) {
      setStatusMsg('No rows with session summaries to validate.'); setStatusType('warn');
      return;
    }

    aiValidationRef.current = true;
    aiProgress.begin(candidates.length);
    aiProgress.setDone(0, 'AI validating dispositions…');

    abortRef.current = new AbortController();
    const abortController = abortRef.current;
    const BATCH_SIZE = 12;

    // Cache check
    const cacheInput = candidates.map(c => `${c.summary}||${c.history}||${c.currentDisp}||${c.callDate}||${c.outcome}||${c.vehicleModel}||${c.campaignId}||${c.dealerName}||${c.supportedLanguages}`).join('|');
    const cacheKey = 'ps-disp-validate-v11-history-' + hashStr(cacheInput);
    const cached = force ? null : (typeof window !== 'undefined' ? localStorage.getItem(cacheKey) : null);
    let cachedParsed: any[] | null = null;
    if (cached) {
      try { cachedParsed = JSON.parse(cached); } catch { /* ignore */ }
    }

    if (cachedParsed) {
      // Cache hit — apply directly
      const correctedResults: Record<number, string> = {};
      for (const item of cachedParsed) {
        if (item.isCorrect === false && item.correctedDisposition) {
          correctedResults[item.rowIndex] = item.correctedDisposition;
        }
      }
      applyCorrections(candidates, correctedResults);
      if (Object.keys(correctedResults).length > 0) aiProgress.markCorrected(Object.keys(correctedResults).length);
      aiProgress.complete(Object.keys(correctedResults).length > 0
        ? `AI validation complete (from cache) — ${Object.keys(correctedResults).length} disposition(s) corrected.`
        : 'AI validation complete (from cache) — all dispositions appear correct.');
      aiValidationRef.current = false;
      return;
    }

    const correctedResults: Record<number, string> = {};

    runLlmBatches({
      items: candidates,
      batchSize: BATCH_SIZE,
      maxConcurrent: 1,
      minGapMs: 500,
      maxRetries: 1,
      requestTimeoutMs: 120000,
      buildPrompt: (batch, batchIndex) => {
        const prompt = buildDispoValidationPrompt(
          batch.map((c: any) => ({
            summary: c.summary,
            history: c.history,
            currentDisp: c.currentDisp,
            dealerName: c.dealerName,
            supportedLanguages: c.supportedLanguages,
            vehicleModel: c.vehicleModel,
            outcome: c.outcome,
            callDate: c.callDate,
            campaignId: c.campaignId,
            rowIndex: c.index,
          })),
          batchIndex,
          BATCH_SIZE
        );
        if (!prompt) return null;
        return { system: prompt.system, user: prompt.user, temperature: prompt.temperature, maxTokens: prompt.maxTokens };
      },
      buildHeaders: () => {
        const cfg = (typeof window !== 'undefined' ? (window as any).JEJO_CONFIG : null) || {};
        return {
          'X-GRYD-TOKEN': (typeof window !== 'undefined' ? sessionStorage.getItem('gryd_token') : '') || '',
          'X-GRYD-SESSION-ID': (typeof window !== 'undefined' ? sessionStorage.getItem('gryd_session_id') : '') || '',
          'X-GRYD-ENTERPRISE-ID': (typeof window !== 'undefined' ? sessionStorage.getItem('gryd_enterprise_id') : '') || 'autocrm',
          'X-GRYD-SIGNUP-TOKEN': cfg.grydSignupToken || '',
          'X-GRYD-APPLICATION-ID': 'autocrm',
        };
      },
      parseResponse: (text, batch, batchIndex) => {
        return parseLlmResponse(text, batchIndex, BATCH_SIZE);
      },
      onProgress: (done, total, message, pct) => {
        aiProgress.setDone(done, message);
      },
      signal: abortController.signal,
    }).then((result) => {
      if (result.aborted) {
        aiProgress.abort('AI validation cancelled.');
        aiValidationRef.current = false;
        abortRef.current = null;
        return;
      }

      // Collect corrections from runner results
      for (let ri = 0; ri < candidates.length; ri++) {
        const dec = result.results.get(ri);
        if (dec && (dec as any).isCorrect === false && (dec as any).correctedDisposition) {
          correctedResults[candidates[ri].index] = (dec as any).correctedDisposition;
        }
      }

      // Save to cache
      const cacheArray = candidates.map((c, idx) => {
        const dec = result.results.get(idx);
        if (dec && (dec as any).isCorrect === false && (dec as any).correctedDisposition) {
          return { rowIndex: c.index, isCorrect: false, correctedDisposition: (dec as any).correctedDisposition };
        }
        return { rowIndex: idx, isCorrect: true, correctedDisposition: null };
      });
      try { if (typeof window !== 'undefined') localStorage.setItem(cacheKey, JSON.stringify(cacheArray)); } catch { /* ignore */ }

      applyCorrections(candidates, correctedResults);
      const correctedCount = Object.keys(correctedResults).length;
      if (correctedCount > 0) aiProgress.markCorrected(correctedCount);
      aiProgress.complete(correctedCount > 0
        ? `AI validation complete — ${correctedCount} disposition(s) corrected. Check the Updated Disposition column.`
        : 'AI validation complete — all dispositions appear correct.');
      log('AI validation done, corrected:', correctedCount);
      aiValidationRef.current = false;
      abortRef.current = null;
    }).catch((err) => {
      aiProgress.abort('AI validation failed.');
      aiValidationRef.current = false;
      abortRef.current = null;
    });
  }

  function applyCorrections(candidates: { index: number }[], correctedResults: Record<number, string>) {
    if (Object.keys(correctedResults).length === 0) {
      // Still mark verified
      setProcessedData(prev => prev.map((r, idx) => {
        if (candidates.some(c => c.index === idx) && !r._ai_status) {
          return { ...r, _ai_status: 'verified' };
        }
        return r;
      }));
      return;
    }

    let updated: Record<string, string>[] = [];
    setProcessedData(prev => {
      updated = prev.map((r, idx) => {
        if (correctedResults[idx] !== undefined) {
          return { ...r, updated_disposition: correctedResults[idx], _ai_status: 'corrected' };
        }
        if (candidates.some(c => c.index === idx) && !r._ai_status) {
          return { ...r, _ai_status: 'verified' };
        }
        return r;
      });
      return updated;
    });
    // Re-classify preview rows after corrections (deduplicated by phone)
    setBookedRows(dedupeByPhone(updated.filter(isServiceBooked)));
    setCompletedRows(dedupeByPhone(updated.filter(r => !isServiceBooked(r) && isServiceCompleted(r))));
    setNotInterestedRows(dedupeByPhone(updated.filter(r => !isServiceBooked(r) && !isServiceCompleted(r) && isNotInterested(r))));
  }

  function handleFile1Change(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) { setFile1Status(v.error!); return; }
    setRawFile1(f); setFile1Status(`Loaded: ${f.name}`); setHasFile1(true);
    setShowResults(false);
    setProcessedData([]);
    setQualityReport(null);
    setBookedRows([]);
    setCompletedRows([]);
    setNotInterestedRows([]);
    setStatusMsg('');
    setStatusType('');
    log('File 1 loaded:', f.name);
  }
  function handleFile2Change(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) { setFile2Status(v.error!); return; }
    setRawFile2(f); setFile2Status(`Loaded: ${f.name}`); setHasFile2(true);
    setShowResults(false);
    setProcessedData([]);
    setQualityReport(null);
    setBookedRows([]);
    setCompletedRows([]);
    setNotInterestedRows([]);
    setStatusMsg('');
    setStatusType('');
    log('File 2 loaded:', f.name);
  }

  function handleDrop1(e: React.DragEvent) {
    e.preventDefault(); setDragOver1(false);
    const f = e.dataTransfer.files[0]; if (!f) return;
    const dt = new DataTransfer(); dt.items.add(f);
    if (file1Ref.current) { file1Ref.current.files = dt.files; file1Ref.current.dispatchEvent(new Event('change', { bubbles: true })); }
  }
  function handleDrop2(e: React.DragEvent) {
    e.preventDefault(); setDragOver2(false);
    const f = e.dataTransfer.files[0]; if (!f) return;
    const dt = new DataTransfer(); dt.items.add(f);
    if (file2Ref.current) { file2Ref.current.files = dt.files; file2Ref.current.dispatchEvent(new Event('change', { bubbles: true })); }
  }

  const OUTPUT_COLUMNS = getOutputColumnsForDealer(dealerKey);
  const sortedData = getSortedData(processedData);
  const stats = showResults ? renderStats(processedData, bookedRows, completedRows, notInterestedRows, sessionCount) : null;
  const startIdNum = parseInt(leadIdStart, 10) || 0;
  const sortedInclude = sortedData.slice(0, previewLimit).map((r, i) => ({ ...r, lead_id: startIdNum > 0 ? `L-${startIdNum + i}` : '' })) as Record<string, string>[];
  const canExport = qualityReport?.canExport ?? false;

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Post-Sales Sync</h1>
              <div className="header-sub">AutoEngage → Zoho Master Sheet</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        <section className={styles.workflowPanel || styles['workflow-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 1</div>
              <div className={styles['section-title']}>Prepare the post-sales batch</div>
            </div>
            <div className={styles['section-note']}>Select dealership, upload Leads and Sessions exports, then process.</div>
          </div>

          <div className={styles['upload-grid']}>
            <div
              className={`${styles['drop-zone']} ${dragOver1 ? styles['drag-over'] : ''} ${hasFile1 ? styles['has-file'] : ''}`}
              onClick={() => file1Ref.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver1(true); }}
              onDragLeave={() => setDragOver1(false)}
              onDrop={handleDrop1}
            >
              <div className={styles['dz-icon']}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>
              <div className={styles['dz-label']}>File 1 — Leads</div>
              <div className={styles['dz-sublabel']}>Post-sales service reminder or feedback lead export</div>
              <div className={styles['dz-cols']}>{dealer.leadColumns.join(' · ')}</div>
              <div className={`${styles['dz-status']} ${hasFile1 ? styles.ok : ''}`}>{file1Status}</div>
              <input ref={file1Ref} type="file" accept=".csv,.xlsx,.xls" onChange={handleFile1Change} style={{ display: 'none' }} />
            </div>
            <div
              className={`${styles['drop-zone']} ${dragOver2 ? styles['drag-over'] : ''} ${hasFile2 ? styles['has-file'] : ''}`}
              onClick={() => file2Ref.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver2(true); }}
              onDragLeave={() => setDragOver2(false)}
              onDrop={handleDrop2}
            >
              <div className={styles['dz-icon']}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg></div>
              <div className={styles['dz-label']}>File 2 — Sessions</div>
              <div className={styles['dz-sublabel']}>AutoEngage sessions export for the same campaign batch</div>
              <div className={styles['dz-cols']}>{dealer.sessionColumns.join(' · ')}</div>
              <div className={`${styles['dz-status']} ${hasFile2 ? styles.ok : ''}`}>{file2Status}</div>
              <input ref={file2Ref} type="file" accept=".csv,.xlsx,.xls" onChange={handleFile2Change} style={{ display: 'none' }} />
            </div>
          </div>

          <div className={styles['action-bar']}>
            <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={processFiles} disabled={!rawFile1 || !rawFile2 || processing}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg> Process Files
            </button>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>Dealership</span>
              <div className={styles['select-wrapper']}>
                <select className="custom-select" value={dealerKey} onChange={e => setDealerKey(e.target.value)} style={{ padding: '0.5rem 1.8rem 0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg)', color: 'var(--text)', fontSize: '0.85rem', cursor: 'pointer', appearance: 'none', fontFamily: 'var(--body)' }}>
                  <optgroup label="Post-sales service reminder">
                    <option value="ambal_service">Ambal — Service Reminder</option>
                    <option value="bullmen_service">Bullmen — Service Reminder</option>
                    <option value="fortune_service">Fortune — Service Reminder</option>
                    <option value="saisamarth">Saisamarth — Service Reminder</option>
                    <option value="perfect_riders_service">Perfect Riders — Service Reminder</option>
                    <option value="pressana_service_feedback">Pressana — Service Reminder</option>
                    <option value="suryabala_service">Suryabala Honda — Service Reminder</option>
                  </optgroup>
                  <optgroup label="Post-sales feedback reminder">
                    <option value="icare_feedback">Icare — Feedback Reminder</option>
                    <option value="pressana_post_service_feedback">Pressana Kia — Post Service Feedback</option>
                  </optgroup>
                  <optgroup label="WA">
                    <option value="fortune_toyota_wa">Fortune Toyota — WhatsApp Campaign</option>
                    <option value="perfect_rider_wa">Perfect Rider — WhatsApp Campaign</option>
                  </optgroup>
                </select>
              </div>
            </div>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>Lead ID</span>
              <input type="number" className={styles['lead-id-input']} value={leadIdStart} onChange={e => setLeadIdStart(e.target.value)} placeholder="e.g. 8173" min={1} />
            </div>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>Language</span>
              <div className={styles['select-wrapper']}>
                <select className="custom-select" value={language} onChange={e => setLanguage(e.target.value)} style={{ padding: '0.5rem 1.8rem 0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg)', color: 'var(--text)', fontSize: '0.85rem', cursor: 'pointer', appearance: 'none', fontFamily: 'var(--body)' }}>
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Kannada">Kannada</option>
                  <option value="Tamil">Tamil</option>
                  <option value="Malayalam">Malayalam</option>
                </select>
              </div>
            </div>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>From</span>
              <input type="date" className={styles['lead-id-input']} value={fromDate} onChange={e => setFromDate(e.target.value)} style={{ fontFamily: 'var(--body)', fontSize: '0.85rem' }} />
            </div>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>To</span>
              <input type="date" className={styles['lead-id-input']} value={toDate} onChange={e => setToDate(e.target.value)} style={{ fontFamily: 'var(--body)', fontSize: '0.85rem' }} />
            </div>
            {showResults && (
              <>
                <button className={`${styles.btn} ${styles['btn-success']}`} onClick={copyData} disabled={!canExport}>Copy Master Rows</button>
                <button className={`${styles.btn} ${styles['btn-success']}`} onClick={exportToExcel} disabled={!canExport}>Export Excel</button>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => validateDispositionsWithLLM()} style={{ display: showResults ? '' : 'none' }}>Validate with AI</button>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={resetAll}>Reset</button>
              </>
            )}
            <span className={`${styles['status-msg']} ${statusType ? styles[statusType] : ''}`}>{statusMsg}</span>
          </div>
        </section>

        {/* AI Status Bar */}
        <BatchProgressBar
          state={aiProgress.state}
          onDismiss={() => aiProgress.reset()}
          onRetry={() => validateDispositionsWithLLM(true)}
          onCancel={cancelAiValidation}
          retryLabel="↻ Re-run AI"
        />

        <section className={styles.resultsPanel || styles['results-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 2</div>
              <div className={styles['section-title']}>Review output</div>
            </div>
          </div>

          {showResults && stats && (
            <>
              <div className={styles['stats-bar']} style={{ display: 'flex' }}>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Sessions</div><div className={`${styles['stat-val']} ${styles.blue}`}>{stats.sessionsIn}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Output</div><div className={`${styles['stat-val']} ${styles.blue}`}>{stats.leads}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Matched</div><div className={`${styles['stat-val']} ${styles.green}`}>{stats.matched}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Service Booked</div><div className={`${styles['stat-val']} ${styles.green}`}>{stats.booked}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Service Completed</div><div className={`${styles['stat-val']} ${styles.green}`}>{stats.completed}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Not Interested</div><div className={`${styles['stat-val']} ${styles.amber}`}>{stats.notInterested}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Not Connected</div><div className={`${styles['stat-val']} ${styles.red}`}>{stats.notConnected}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Unknown</div><div className={`${styles['stat-val']} ${styles.amber}`}>{stats.unknown}</div></div>
              </div>

              {/* Quality Card */}
              {qualityReport && (
                <div className={`${styles['quality-card']} ${styles[qualityReport.state] || ''}`} style={{ display: 'block' }}>
                  <div className={styles['quality-header']}>
                    <div>
                      <div className={styles.eyebrow}>Data quality</div>
                      <div className={styles['quality-title']}>{qualityReport.title}</div>
                      <div className={styles['quality-meta']}>{qualityReport.summary.join(' - ')}</div>
                    </div>
                    <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={copyQualityReport}>Copy Report</button>
                  </div>
                  <div className={styles['quality-body']}>
                    <div>
                      <div className={styles['quality-list-title']}>Warnings</div>
                      {qualityReport.warnings.map((w: any, i: number) => (
                        <div key={i} className={`${styles['quality-item']} ${styles[w.level] || ''}`}>{w.text}</div>
                      ))}
                    </div>
                    <div>
                      <div className={styles['quality-list-title']}>Samples</div>
                      {qualityReport.samples.map((s: any, i: number) => (
                        <div key={i} className={`${styles['quality-item']} ${styles.info || ''}`}>
                          <strong>{s.title}</strong><br />{s.rows.join('<br />')}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Main Output Table */}
              <div className={styles['table-wrapper']} style={{ display: 'block' }}>
                <div className={styles['table-header']}>
                  <div><div className={styles['table-title']}>Zoho Master Sheet Preview</div><div className={styles['table-caption']}>{processedData.length > previewLimit ? `Showing first ${previewLimit} of ${processedData.length} rows` : `${processedData.length} rows`}</div></div>
                </div>
                <div className={styles['table-scroll']}>
                  <table>
                    <thead><tr>
                      {OUTPUT_COLUMNS.map(col => {
                        const isSortable = ['person_name', 'full_name', 'phone_number', 'disposition_detail'].includes(col.key);
                        return <th key={col.key} className={isSortable ? styles['th-sortable'] : ''} onClick={isSortable ? () => toggleSort(col.key!) : undefined}>{col.header}</th>;
                      })}
                    </tr></thead>
                    <tbody>
                      {sortedInclude.map((r, i) => (
                        <tr key={i}>
                          {OUTPUT_COLUMNS.map(col => {
                            const val = r[col.key] || '';
                            if (col.key === 'phone_number') return <td key={col.key} className={styles['cell-phone']}>{esc(val)}</td>;
                            if (col.key === 'call_recording' && val) {
                              const href = safeRecordingHref(val);
                              return href ? <td key={col.key}><a className={styles['cell-url']} href={href} target="_blank" rel="noopener noreferrer">Recording</a></td> : <td key={col.key}>{esc(val)}</td>;
                            }
                            if (col.key === 'updated_disposition') {
                              const st = r._ai_status || '';
                              let badge = '<span class="' + (styles['ai-badge'] || 'ai-badge') + ' ' + (styles.pending || 'pending') + '">—</span>';
                              if (st === 'corrected') badge = '<span class="' + (styles['ai-badge'] || 'ai-badge') + ' ' + (styles.corrected || 'corrected') + '">✎ </span>';
                              else if (st === 'verified') badge = '<span class="' + (styles['ai-badge'] || 'ai-badge') + ' ' + (styles.verified || 'verified') + '">✓ </span>';
                              return <td key={col.key} dangerouslySetInnerHTML={{ __html: badge + esc(val) }} />;
                            }
                            return <td key={col.key} title={val}>{esc(val)}</td>;
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Booked Table */}
              <div className={styles['table-wrapper']} style={{ display: bookedRows.length ? 'block' : 'none' }}>
                <div className={styles['table-header']}>
                  <div><div className={styles['table-title']}>SERVICE BOOKED</div><div className={styles['table-caption']}>{bookedRows.length} rows</div></div>
                  <button className={`${styles.btn} ${styles['btn-success']}`} onClick={() => copyPreviewRows('booked')}>Copy</button>
                </div>
                <div className={styles['table-scroll']}>
                  <table><thead><tr><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>VIN_NUMBER</th><th>DISPOSITION_DETAILS</th><th>LOCATION</th><th>CALL_DATE</th><th>CRE Remarks</th><th>COMMON REMARKS</th></tr></thead>
                    <tbody>{bookedRows.slice(0, previewLimit).map((r, i) => (
                      <tr key={i}>
                        <td className={styles['cell-phone']}>{esc(r.phone_number)}</td>
                        <td>{esc(r.vehicle_model)}</td>
                        <td>{esc(r.vin_number)}</td>
                        <td>{esc(r.updated_disposition || r.disposition_detail || r.disposition || '')}</td>
                        <td>{esc(dealerKey === 'perfect_riders_service' ? extractPerfectRidersLocation(r.summary || r.updated_disposition || r.disposition_detail) : '')}</td>
                        <td>{esc(r.call_date)}</td>
                        <td>{esc(dealerKey === 'perfect_riders_service' ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : '')}</td>
                        <td></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>

              {/* Completed Table */}
              <div className={styles['table-wrapper']} style={{ display: completedRows.length ? 'block' : 'none' }}>
                <div className={styles['table-header']}>
                  <div><div className={styles['table-title']}>Service Completed</div><div className={styles['table-caption']}>{completedRows.length} rows</div></div>
                  <button className={`${styles.btn} ${styles['btn-success']}`} onClick={() => copyPreviewRows('completed')}>Copy</button>
                </div>
                <div className={styles['table-scroll']}>
                  <table><thead><tr><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>VIN_NUMBER</th><th>DISPOSITION_DETAILS</th><th>LOCATION</th><th>CALL_DATE</th><th>CRE Remarks</th></tr></thead>
                    <tbody>{completedRows.slice(0, previewLimit).map((r, i) => (
                      <tr key={i}>
                        <td className={styles['cell-phone']}>{esc(r.phone_number)}</td>
                        <td>{esc(r.vehicle_model)}</td>
                        <td>{esc(r.vin_number)}</td>
                        <td>{esc(r.updated_disposition || r.disposition_detail || r.disposition || '')}</td>
                        <td>{esc(dealerKey === 'perfect_riders_service' ? extractPerfectRidersLocation(r.summary || r.disposition_detail) : '')}</td>
                        <td>{esc(r.call_date)}</td>
                        <td>{esc(dealerKey === 'perfect_riders_service' ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : '')}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>

              {/* Not Interested Table */}
              <div className={styles['table-wrapper']} style={{ display: notInterestedRows.length ? 'block' : 'none' }}>
                <div className={styles['table-header']}>
                  <div><div className={styles['table-title']}>Not Interested</div><div className={styles['table-caption']}>{notInterestedRows.length} rows</div></div>
                  <button className={`${styles.btn} ${styles['btn-success']}`} onClick={() => copyPreviewRows('notInterested')}>Copy</button>
                </div>
                <div className={styles['table-scroll']}>
                  <table><thead><tr><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>VIN_NUMBER</th><th>SUMMARY</th><th>CALL_DATE</th><th>CRE Remarks</th></tr></thead>
                    <tbody>{notInterestedRows.slice(0, previewLimit).map((r, i) => (
                      <tr key={i}>
                        <td className={styles['cell-phone']}>{esc(r.phone_number)}</td>
                        <td>{esc(r.vehicle_model)}</td>
                        <td>{esc(r.vin_number)}</td>
                        <td>{esc(r.summary)}</td>
                        <td>{esc(r.call_date)}</td>
                        <td>{esc(dealerKey === 'perfect_riders_service' ? extractPerfectRidersCRE(r.summary || r.updated_disposition || r.disposition_detail) : '')}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {!showResults && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', alignItems: 'center', padding: '1rem 1.1rem', marginBottom: '1rem', border: '1px dashed var(--border)', borderRadius: 'var(--radius-lg)', background: 'var(--accent-soft)' }}>
              <div>
                <strong style={{ display: 'block', marginBottom: '0.2rem', fontFamily: 'var(--sans)', fontSize: '1rem' }}>Waiting for data</strong>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>Upload leads and sessions files then click Process Files. Results will appear here.</p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }} aria-hidden="true">
                <span style={{ padding: '0.42rem 0.62rem', border: '1px solid var(--border)', borderRadius: '999px', background: 'rgba(255,255,255,0.04)', color: 'var(--text-dim)', fontSize: '0.76rem', fontWeight: 700 }}>Upload</span>
                <span style={{ padding: '0.42rem 0.62rem', border: '1px solid var(--border)', borderRadius: '999px', background: 'rgba(255,255,255,0.04)', color: 'var(--text-dim)', fontSize: '0.76rem', fontWeight: 700 }}>Process</span>
                <span style={{ padding: '0.42rem 0.62rem', border: '1px solid var(--border)', borderRadius: '999px', background: 'rgba(255,255,255,0.04)', color: 'var(--text-dim)', fontSize: '0.76rem', fontWeight: 700 }}>Review</span>
                <span style={{ padding: '0.42rem 0.62rem', border: '1px solid var(--border)', borderRadius: '999px', background: 'rgba(255,255,255,0.04)', color: 'var(--text-dim)', fontSize: '0.76rem', fontWeight: 700 }}>Export</span>
              </div>
            </div>
          )}
        </section>
      </main>
      <footer>AutoNage — Post-Sales Disposition Sync</footer>
      <ProcessingOverlay show={processing} message="Processing files…" />
    </div>

  );
}
