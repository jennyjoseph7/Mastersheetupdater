'use client';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import { readFileAsArrayBuffer, clean, excelSafe, validateFileSync } from '@/lib/data-pipeline';
import * as XLSX from 'xlsx';
import JSZip from 'jszip';
import { $log, $mask } from '@/lib/logger';
import styles from './recording-renamer.module.css';

const OUTPUT_HEADERS = [
  'Lead_ID', 'Full_Name', 'Phone', 'City', 'Pincode', 'Language', 'Lead_Source', 'Cohort',
  'Campaign_ID', 'Call Triggered', 'Outcome', 'Disposition', 'SUMMARY', 'Updated SUMMARY',
  'Conversion', 'Call_Date', 'Number of attempts', 'SENTIMENT', 'Recordings', 'Model',
  'Seating', 'Exclusion_Flag',
];

const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const RECORDING_FETCH_TIMEOUT_MS = 45000;
const RECORDING_FETCH_RETRIES = 2;

interface ParsedRow {
  rowNumber: number;
  values: Record<string, string>;
  raw: string[];
}

interface ResultRow {
  status: string;
  tone: string;
  rowNumber: number;
  phone: string;
  callDate: string;
  sourceFile: string;
  outputFile: string;
  attempts: string | number;
  recordingRef: string;
  reason: string;
  callDateObj?: Date;
  url?: string;
}

export default function RecordingRenamerPage() {
  const log = (...args) => console.log('[RecordingRenamer]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [dataFile, setDataFile] = useState<File | null>(null);
  const [parsedRows, setParsedRows] = useState<ParsedRow[]>([]);
  const [resultRows, setResultRows] = useState<ResultRow[]>([]);
  const [matchedRows, setMatchedRows] = useState<ResultRow[]>([]);
  const [reportCsv, setReportCsv] = useState('');
  const [useCorsProxy, setUseCorsProxy] = useState(false);
  const [dateParseOrder, setDateParseOrder] = useState<'DMY' | 'MDY'>('DMY');
  const [dateFormatSelect, setDateFormatSelect] = useState('auto');
  const [isBusy, setIsBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState('');
  const [dataStatus, setDataStatus] = useState('Click to browse or drop file');
  const [hasFile, setHasFile] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [statsRows, setStatsRows] = useState(0);
  const [statsAudio, setStatsAudio] = useState(0);
  const [statsMatched, setStatsMatched] = useState(0);
  const [statsMissing, setStatsMissing] = useState(0);
  const [statsSkipped, setStatsSkipped] = useState(0);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  function getCorsProxyUrl(): string {
    return ''; // Would come from clientConfig if available
  }

  function normalizeHeader(value: string): string {
    return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
  }

  function normalizePhone(raw: unknown): string {
    if (raw === undefined || raw === null || raw === '') return '';
    let s = String(raw).trim();
    if (/^\d[\d.]*e[+\-]?\d+$/i.test(s)) {
      s = String(Math.round(parseFloat(s)));
    }
    const digits = s.replace(/\D/g, '');
    if (!digits) return '';
    if (digits.length === 10) return digits;
    if (digits.startsWith('91') && digits.length === 12) return digits.slice(2);
    if (digits.startsWith('0') && digits.length === 11) return digits.slice(1);
    if (digits.startsWith('91') && digits.length > 12) return digits.slice(-10);
    return '';
  }

  function cellToString(value: unknown): string {
    if (value === undefined || value === null || value === '') return '';
    if (value instanceof Date) return value.toISOString();
    if (typeof value === 'number') {
      if (Number.isInteger(value)) return String(value);
      if (value > 999999 && Math.abs(value - Math.round(value)) < 0.01) return String(Math.round(value));
    }
    return String(value).trim();
  }

  function parseExcelSerial(value: unknown): Date | null {
    const num = Number(value);
    if (!Number.isFinite(num) || num < 20000 || num > 70000) return null;
    const epoch = Date.UTC(1899, 11, 30);
    return new Date(epoch + num * 86400000);
  }

  function buildValidatedDate(year: number, month: number, day: number, hour = 0, minute = 0, second = 0): Date | null {
    const date = new Date(year, month - 1, day, hour, minute, second);
    if (date.getFullYear() !== year || date.getMonth() + 1 !== month || date.getDate() !== day) return null;
    return date;
  }

  function parseDate(value: unknown): Date | null {
    if (value instanceof Date && !isNaN(value.getTime())) return value;
    if (value === undefined || value === null || value === '') return null;
    if (typeof value === 'number') return parseExcelSerial(value);
    const raw = String(value).trim();
    if (!raw) return null;
    const serial = parseExcelSerial(raw);
    if (serial) return serial;
    const dmy = raw.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})(?:[,\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?)?/i);
    if (dmy) {
      const first = parseInt(dmy[1], 10), secondPart = parseInt(dmy[2], 10);
      let year = parseInt(dmy[3], 10), hour = parseInt(dmy[4] || '0', 10);
      const minute = parseInt(dmy[5] || '0', 10), second = parseInt(dmy[6] || '0', 10);
      const ampm = String(dmy[7] || '').toLowerCase();
      if (year < 100) year += 2000;
      if (ampm === 'pm' && hour !== 12) hour += 12;
      if (ampm === 'am' && hour === 12) hour = 0;
      if (dateParseOrder === 'MDY') {
        const mdy = buildValidatedDate(year, first, secondPart, hour, minute, second);
        if (mdy) return mdy;
        if (secondPart > 12) return null;
        return buildValidatedDate(year, secondPart, first, hour, minute, second);
      }
      const ddmmyyyy = buildValidatedDate(year, secondPart, first, hour, minute, second);
      if (ddmmyyyy) return ddmmyyyy;
      if (first > 12) return null;
      return buildValidatedDate(year, first, secondPart, hour, minute, second);
    }
    const iso = raw.match(/^(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{2})(?::(\d{2}))?)?/);
    if (iso) {
      const year = parseInt(iso[1], 10), month = parseInt(iso[2], 10), day = parseInt(iso[3], 10);
      const hour = parseInt(iso[4] || '0', 10), minute = parseInt(iso[5] || '0', 10), second = parseInt(iso[6] || '0', 10);
      return buildValidatedDate(year, month, day, hour, minute, second);
    }
    return null;
  }

  function formatDateToken(date: Date): string {
    if (!date) return '';
    return `${date.getDate()}${MONTH_SHORT[date.getMonth()]}`;
  }

  function formatDateDisplay(date: Date): string {
    if (!date) return '';
    return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
  }

  function getExtension(name: string): string {
    const clean = String(name || '').split(/[?#]/)[0];
    const match = clean.match(/\.([a-z0-9]{2,5})$/i);
    return match ? match[1].toLowerCase() : '';
  }

  function getRowValue(row: ParsedRow, names: string[]): string {
    for (const name of names) {
      const key = normalizeHeader(name);
      if (row.values[key] !== undefined && row.values[key] !== '') return row.values[key];
    }
    return '';
  }

  async function parseDataFile(file: File): Promise<ParsedRow[]> {
    const ab = await readFileAsArrayBuffer(file);
    const wb = XLSX.read(ab, { type: 'array', raw: true, cellText: false, cellDates: false });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];
    if (!rows.length) return [];
    const first = rows[0].map(cellToString);
    const firstNormalized = new Set(first.map(normalizeHeader));
    const hasHeader = firstNormalized.has('phone') && (firstNormalized.has('calldate') || firstNormalized.has('recordings') || firstNormalized.has('leadid'));
    const headers = hasHeader ? first : OUTPUT_HEADERS;
    const startIndex = hasHeader ? 1 : 0;
    const parsed: ParsedRow[] = [];
    for (let i = startIndex; i < rows.length; i++) {
      const raw = rows[i];
      if (!raw || (raw as unknown[]).every(cell => String(cellToString(cell)).trim() === '')) continue;
      const values: Record<string, string> = {};
      for (let j = 0; j < headers.length; j++) {
        const key = normalizeHeader(headers[j] || OUTPUT_HEADERS[j] || `column_${j + 1}`);
        const cellRef = XLSX.utils.encode_cell({ r: i, c: j });
        const cell = ws[cellRef];
        values[key] = cell && cell.l && cell.l.Target ? cell.l.Target : cellToString(raw[j]);
      }
      parsed.push({ rowNumber: i + 1, values, raw: raw.map(cellToString) });
    }
    return parsed;
  }

  function uniqueOutputName(baseName: string, extension: string, usedOutputNames: Set<string>): string {
    const ext = extension ? `.${extension}` : '';
    let name = `${baseName}${ext}`;
    let counter = 2;
    while (usedOutputNames.has(name.toLowerCase())) {
      name = `${baseName}_${counter}${ext}`;
      counter += 1;
    }
    usedOutputNames.add(name.toLowerCase());
    return name;
  }

  function buildResults(rows: ParsedRow[]): { results: ResultRow[]; matches: ResultRow[]; urlCount: number } {
    const usedOutputNames = new Set<string>();
    const results: ResultRow[] = [];
    const matches: ResultRow[] = [];
    for (const row of rows) {
      const phone = normalizePhone(getRowValue(row, ['Phone', 'phone_number', 'Mobile', 'Contact Number']));
      const dateRaw = getRowValue(row, ['Call_Date', 'Call Date', 'Date', 'Updated']);
      const date = parseDate(dateRaw);
      const recordingRef = String(getRowValue(row, ['Recordings', 'Recording', 'Recording URL', 'Call Recording', 'call_recording', 'call_url', 'audio_url']) || '').trim();
      if (!phone) {
        results.push({ status: 'Skipped', tone: 'err', rowNumber: row.rowNumber, phone: '', callDate: '', sourceFile: '', outputFile: '', attempts: '', recordingRef, reason: 'Missing or invalid phone' });
        continue;
      }
      if (!date) {
        results.push({ status: 'Skipped', tone: 'err', rowNumber: row.rowNumber, phone, callDate: String(dateRaw || ''), sourceFile: '', outputFile: '', attempts: '', recordingRef, reason: 'Missing or invalid Call_Date' });
        continue;
      }
      if (!recordingRef) {
        results.push({ status: 'Missing', tone: 'warn', rowNumber: row.rowNumber, phone, callDate: formatDateDisplay(date), sourceFile: '', outputFile: '', attempts: '', recordingRef, reason: 'Missing Recordings URL' });
        continue;
      }
      if (!/^https?:\/\//i.test(recordingRef)) {
        results.push({ status: 'Skipped', tone: 'err', rowNumber: row.rowNumber, phone, callDate: formatDateDisplay(date), sourceFile: recordingRef, outputFile: '', attempts: '', recordingRef, reason: 'Recording value is not an HTTP URL' });
        continue;
      }
      const ext = getExtension(recordingRef) || 'mp3';
      const outputFile = uniqueOutputName(`${phone}_${formatDateToken(date)}`, ext, usedOutputNames);
      const result: ResultRow = { status: 'Ready', tone: 'ok', rowNumber: row.rowNumber, phone, callDate: formatDateDisplay(date), sourceFile: recordingRef, outputFile, attempts: '', recordingRef, reason: 'Ready to download', callDateObj: date };
      results.push(result);
      matches.push({ ...result, url: recordingRef, callDateObj: date });
    }
    const urlCount = results.filter(r => r.recordingRef && /^https?:\/\//i.test(r.recordingRef)).length;
    return { results, matches, urlCount };
  }

  function csvEscape(value: unknown): string {
    const s = excelSafe(value);
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  }

  function makeReportCsv(results: ResultRow[]): string {
    const header = ['Status', 'Row', 'Phone', 'Call_Date', 'Recording_URL', 'Source_URL', 'Output_File', 'Attempts', 'Reason'];
    const lines = [header.map(csvEscape).join(',')];
    for (const row of results) {
      lines.push([row.status, row.rowNumber, row.phone, row.callDate, row.recordingRef, row.sourceFile, row.outputFile, row.attempts, row.reason].map(csvEscape).join(','));
    }
    return lines.join('\r\n');
  }

  async function processBatch() {
    if (!dataFile) return;
    setStatusMsg('Reading processed file...');
    setStatusType('');
    setIsBusy(true);
    try {
      const newParsedRows = await parseDataFile(dataFile);
      setParsedRows(newParsedRows);
      applyDateFormat(newParsedRows);
      const built = buildResults(newParsedRows);
      const newResultRows = built.results;
      setResultRows(newResultRows);
      const newMatchedRows = built.matches;
      setMatchedRows(newMatchedRows);
      const newReportCsv = makeReportCsv(newResultRows);
      setReportCsv(newReportCsv);
      renderResults(resultRows, built.urlCount);
      const missing = resultRows.filter(r => r.status === 'Missing').length;
      const skipped = resultRows.filter(r => r.status === 'Skipped').length;
      setStatusMsg(`${matchedRows.length} recording URL(s) ready. ${missing} missing, ${skipped} skipped.`);
      setStatusType(missing || skipped ? 'warn' : 'ok');
    } catch (error: unknown) {
      setStatusMsg(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setStatusType('err');
    }
    setIsBusy(false);
  }

  function renderResults(rows: ResultRow[], urlCount: number) {
    const matched = rows.filter(r => r.status === 'Ready' || r.status === 'Downloaded').length;
    const missing = rows.filter(r => r.status === 'Missing').length;
    const skipped = rows.filter(r => r.status === 'Skipped' || r.status === 'Failed').length;
    setStatsRows(parsedRows.length);
    setStatsAudio(urlCount);
    setStatsMatched(matched);
    setStatsMissing(missing);
    setStatsSkipped(skipped);
    setShowResults(true);
  }

  function updateResultStatus(matchRow: ResultRow, status: string, tone: string, outputFile: string, reason: string, attempts: string | number = '') {
    const result = resultRows.find(r => r.rowNumber === matchRow.rowNumber && r.recordingRef === matchRow.recordingRef);
    if (!result) return;
    result.status = status;
    result.tone = tone;
    result.outputFile = outputFile;
    result.attempts = attempts;
    result.reason = reason;
    setResultRows([...resultRows]);
  }

  function isAllowedRecordingUrl(url: string): boolean {
    if (!url || typeof url !== 'string') return false;
    try {
      const parsed = new URL(url);
      if (parsed.protocol !== 'https:') return false;
      const host = parsed.hostname;
      if (host === 'localhost' || host === '127.0.0.1' || host === '::1' ||
          host === '0.0.0.0' || host.startsWith('10.') || host.startsWith('192.168.') ||
          host.startsWith('172.') || host.endsWith('.local') || host.endsWith('.internal')) return false;
      return true;
    } catch { return false; }
  }

  function buildFetchUrl(originalUrl: string): string | null {
    if (useCorsProxy) {
      const proxyUrl = getCorsProxyUrl();
      if (proxyUrl) {
        if (!isAllowedRecordingUrl(originalUrl)) {
          console.warn('Blocked recording URL:', originalUrl);
          return null;
        }
        return proxyUrl + '?url=' + encodeURIComponent(originalUrl);
      }
    }
    return originalUrl;
  }

  async function fetchRecordingWithRetry(row: ResultRow, onAttempt?: (a: number, m: number) => void): Promise<{ blob: Blob; attempts: number; contentType: string | null }> {
    const maxAttempts = RECORDING_FETCH_RETRIES + 1;
    const fetchUrl = buildFetchUrl(row.url || '');
    if (!fetchUrl) throw new Error('URL blocked by security policy');
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      if (onAttempt) onAttempt(attempt, maxAttempts);
      const controller = new AbortController();
      let timedOut = false;
      const timeoutId = setTimeout(() => { timedOut = true; controller.abort(); }, RECORDING_FETCH_TIMEOUT_MS);
      try {
        const response = await fetch(fetchUrl, { signal: controller.signal });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        return { blob, attempts: attempt, contentType: response.headers.get('content-type') };
      } catch (error) {
        if (attempt < maxAttempts) await new Promise(r => setTimeout(r, 500 * attempt));
        if (attempt === maxAttempts) {
          const timedOutMsg = (timedOut || (error as Error)?.name === 'AbortError') ? `Timed out after ${RECORDING_FETCH_TIMEOUT_MS / 1000}s` : `Failed: ${(error as Error)?.message || 'Unknown'}`;
          throw new Error(timedOutMsg);
        }
      } finally { clearTimeout(timeoutId); }
    }
    throw new Error('Download failed after all attempts');
  }

  function extensionFromContentType(contentType: string | null): string {
    const type = String(contentType || '').toLowerCase();
    if (type.includes('audio/mpeg') || type.includes('audio/mp3')) return 'mp3';
    if (type.includes('audio/wav') || type.includes('audio/x-wav')) return 'wav';
    if (type.includes('audio/mp4') || type.includes('audio/aac')) return 'm4a';
    if (type.includes('audio/ogg')) return 'ogg';
    if (type.includes('audio/webm')) return 'webm';
    if (type.includes('audio/flac')) return 'flac';
    if (type.includes('video/mp4')) return 'mp4';
    return '';
  }

  function replaceExtension(filename: string, extension: string): string {
    return String(filename || '').replace(/\.[a-z0-9]{2,5}$/i, `.${extension}`);
  }

  function getZipDateToken(): string {
    const matchedDates = matchedRows.map(r => r.callDateObj || parseDate(r.callDate)).filter(Boolean) as Date[];
    const unique = new Set(matchedDates.map(formatDateToken));
    if (unique.size === 1) return Array.from(unique)[0];
    const now = new Date();
    return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
  }

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function downloadZip() {
    if (!matchedRows.length) return;
    setStatusMsg('Downloading recordings...');
    setStatusType('');
    setIsBusy(true);
    try {
      const zip = new JSZip();
      const folder = zip.folder('renamed_recordings');
      let downloaded = 0, failed = 0;
      for (let i = 0; i < matchedRows.length; i++) {
        const row = matchedRows[i];
        try {
          const fetched = await fetchRecordingWithRetry(row, (attempt, max) => {
            setStatusMsg(`Downloading ${i + 1}/${matchedRows.length} attempt ${attempt}/${max}: ${row.outputFile}`);
            setStatusType('');
          });
          const detectedExt = extensionFromContentType(fetched.contentType);
          const outputFile = detectedExt && getExtension(row.outputFile) === 'mp3' ? replaceExtension(row.outputFile, detectedExt) : row.outputFile;
          folder?.file(outputFile, fetched.blob);
          downloaded++;
          updateResultStatus(row, 'Downloaded', 'ok', outputFile, `Downloaded${fetched.attempts > 1 ? ` after ${fetched.attempts} attempts` : ''}`, fetched.attempts);
        } catch (error: unknown) {
          failed++;
          updateResultStatus(row, 'Failed', 'err', row.outputFile, (error as Error)?.message || 'Download failed', '');
        }
      }
      const updatedReportCsv = makeReportCsv(resultRows);
      setReportCsv(updatedReportCsv);
      if (!downloaded) {
        renderResults(resultRows, resultRows.filter(r => r.recordingRef && /^https?:\/\//i.test(r.recordingRef)).length);
        setStatusMsg('No recordings could be downloaded.');
        setStatusType('err');
        setIsBusy(false);
        return;
      }
      zip.file('recording_rename_report.csv', reportCsv);
      const blob = await zip.generateAsync({ type: 'blob' });
      const dateToken = getZipDateToken();
      triggerDownload(blob, `AutoNage_Recordings_${dateToken}.zip`);
      renderResults(resultRows, resultRows.filter(r => r.recordingRef && /^https?:\/\//i.test(r.recordingRef)).length);
      setStatusMsg(`ZIP downloaded with ${downloaded} recording(s). ${failed} failed.`);
      setStatusType(failed ? 'warn' : 'ok');
    } catch (error: unknown) {
      setStatusMsg(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setStatusType('err');
    }
    setIsBusy(false);
  }

  function downloadReport() {
    if (!resultRows.length) return;
    const blob = new Blob([reportCsv || makeReportCsv(resultRows)], { type: 'text/csv;charset=utf-8' });
    triggerDownload(blob, `AutoNage_Recording_Rename_Report_${getZipDateToken()}.csv`);
  }

  function resetAll() {
    setDataFile(null);
    setParsedRows([]);
    setResultRows([]);
    setMatchedRows([]);
    setReportCsv('');
    setShowResults(false);
    setHasFile(false);
    setStatsRows(0); setStatsAudio(0); setStatsMatched(0); setStatsMissing(0); setStatsSkipped(0);
    setDataStatus('Click to browse or drop file');
    setStatusMsg(''); setStatusType('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function toggleProxyMode() {
    setUseCorsProxy(prev => !prev);
  }

  function applyDateFormat(rows?: ParsedRow[]) {
    const target = rows ?? parsedRows;
    if (dateFormatSelect === 'auto') {
      const dates = target.map(r => getRowValue(r, ['Call_Date', 'Call Date', 'Date', 'Updated']));
      setDateParseOrder(detectDateFormat(dates));
    } else {
      setDateParseOrder(dateFormatSelect as 'DMY' | 'MDY');
    }
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

  function handleDateFormatChange() {
    applyDateFormat(parsedRows);
    if (parsedRows.length) processBatch();
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) { setDataStatus(v.error!); return; }
    setDataFile(f);
    setHasFile(true);
    setDataStatus(`Loaded: ${f.name}`);
    setStatusMsg('Ready — upload a processed file to begin');
    setStatusType('');
    setShowResults(false);
    setParsedRows([]);
    setResultRows([]);
    setMatchedRows([]);
    setReportCsv('');
    setStatsRows(0);
    setStatsAudio(0);
    setStatsMatched(0);
    setStatsMissing(0);
    setStatsSkipped(0);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) {
      setDataFile(f);
      setHasFile(true);
      setDataStatus(`Loaded: ${f.name}`);
      setStatusMsg('Ready — upload a processed file to begin');
      setStatusType('');
      setShowResults(false);
      setParsedRows([]);
      setResultRows([]);
      setMatchedRows([]);
      setReportCsv('');
      setStatsRows(0);
      setStatsAudio(0);
      setStatsMatched(0);
      setStatsMissing(0);
      setStatsSkipped(0);
    }
  }

  function esc(val: unknown): string {
    return String(val ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  const displayRows = resultRows.slice(0, 300);

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Recording Renamer</h1>
              <div className="header-sub">Processed Pre-Sales Sync export · Download &amp; rename recordings</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        <section className={styles['workflow-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Inputs</div>
              <div className={styles['section-title']}>Load processed data</div>
            </div>
            <div className={styles['section-note']}>The processed file must contain Phone, Call_Date, and Recordings.</div>
          </div>

          <div className={styles['upload-grid']}>
            <div
              className={`${styles['drop-zone']} ${dragOver ? styles['drag-over'] : ''} ${hasFile ? styles['has-file'] : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => {
                e.preventDefault(); setDragOver(false);
                const f = e.dataTransfer.files[0];
                if (f) {
                  setDataFile(f); setHasFile(true);
                  setDataStatus(`Loaded: ${f.name}`);
                  setStatusMsg('Ready — upload a processed file to begin');
                  setStatusType('');
                }
              }}
            >
              <div className={styles['dz-icon']}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              </div>
              <div className={styles['dz-label']}>Processed CSV/XLSX</div>
              <div className={styles['dz-sublabel']}>Upload the output file from Pre-Sales Sync.</div>
              <div className={styles['dz-cols']}>Phone | Call_Date | Recordings</div>
              <div className={`${styles['dz-status']} ${hasFile ? styles['ok'] : ''}`}>{dataStatus}</div>
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls,.tsv" onChange={handleFileChange} style={{ display: 'none' }} />
            </div>
          </div>

          <div className={styles['upload-controls']}>
            <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={processBatch} disabled={!dataFile || isBusy}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg> Process
            </button>
            <button className={`${styles.btn} ${styles['btn-success']}`} onClick={downloadZip} disabled={!matchedRows.length || isBusy}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4"/></svg> Download ZIP
            </button>
            <div className={styles['control-group']}>
              <span className={styles['mode-label']}>Proxy</span>
              <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={toggleProxyMode} style={{ padding: '0.2rem 0.4rem', fontSize: '0.72rem', fontWeight: 600, border: useCorsProxy ? '1px solid var(--success)' : 'none', color: useCorsProxy ? 'var(--success)' : undefined }}>
                {useCorsProxy ? 'On' : 'Off'}
              </button>
            </div>
            <div className={styles['control-group']}>
              <span className={styles['mode-label']}>Date</span>
              <select className={styles['mode-select']} value={dateFormatSelect} onChange={e => { setDateFormatSelect(e.target.value); handleDateFormatChange(); }} style={{ padding: '0.35rem 0.55rem', fontSize: '0.72rem' }}>
                <option value="auto">Auto Detect</option>
                <option value="DMY">DD/MM/YYYY</option>
                <option value="MDY">MM/DD/YYYY</option>
              </select>
              <span className={styles['date-parser-note']}>Format: {dateParseOrder === 'MDY' ? 'MM/DD/YYYY' : 'DD/MM/YYYY'} ({dateFormatSelect === 'auto' ? 'Auto' : 'Manual'})</span>
            </div>
            <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={downloadReport} disabled={!resultRows.length}>Download Report</button>
            <button className={`${styles.btn} ${styles['btn-danger']}`} onClick={resetAll}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4v5h.582m15.356 2A8 8 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8 8 0 01-15.357-2m15.357 2H15"/></svg> Reset
            </button>
          </div>

          <div className={`${styles['status-bar']} ${statusType ? styles[statusType] : ''}`}>
            <span className={styles['status-dot']}></span>
            <span className={styles['status-msg']}>{statusMsg || 'Ready to process'}</span>
          </div>
        </section>

        <section className={styles['results-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Output</div>
              <div className={styles['section-title']}>Review downloads</div>
            </div>
            <div className={styles['section-note']}>Renamed files use the format <span className={styles.mono}>9035937158_2May.mp3</span>.</div>
          </div>

          {!showResults && <div className={styles['empty-state']}>Waiting for inputs.</div>}

          <div className={styles['stats-grid']} style={{ display: showResults ? 'grid' : 'none' }}>
            <div className={styles['stat-card']}><div className={styles['stat-label']}>Rows Read</div><div className={`${styles['stat-val']} ${styles.blue}`}>{statsRows}</div></div>
            <div className={styles['stat-card']}><div className={styles['stat-label']}>Recording URLs</div><div className={`${styles['stat-val']} ${styles.blue}`}>{statsAudio}</div></div>
            <div className={styles['stat-card']}><div className={styles['stat-label']}>Ready</div><div className={`${styles['stat-val']} ${styles.green}`}>{statsMatched}</div></div>
            <div className={styles['stat-card']}><div className={styles['stat-label']}>Missing</div><div className={`${styles['stat-val']} ${styles.amber}`}>{statsMissing}</div></div>
            <div className={styles['stat-card']}><div className={styles['stat-label']}>Skipped</div><div className={`${styles['stat-val']} ${styles.red}`}>{statsSkipped}</div></div>
          </div>

          {showResults && (
            <div className={styles['table-wrapper']}>
              <div className={styles['table-header']}>
                <div className={styles['table-title']}>Match Preview</div>
                <div className={styles['table-caption']}>{resultRows.length} rows</div>
              </div>
              <div className={styles['table-scroll']}>
                <table>
                  <thead><tr><th>Status</th><th>Row</th><th>Phone</th><th>Call Date</th><th>Source URL</th><th>Output File</th><th>Attempts</th><th>Reason</th></tr></thead>
                  <tbody>
                    {displayRows.map((r, i) => (
                      <tr key={i}>
                        <td><span className={`${styles.badge} ${styles[r.tone] || ''}`}>{esc(r.status)}</span></td>
                        <td className={styles.mono}>{esc(r.rowNumber)}</td>
                        <td className={styles.mono}>{esc(r.phone)}</td>
                        <td>{esc(r.callDate)}</td>
                        <td className={styles.truncate} title={esc(r.sourceFile)}>{esc(r.sourceFile)}</td>
                        <td className={`${styles.mono} ${styles.truncate}`} title={esc(r.outputFile)}>{esc(r.outputFile)}</td>
                        <td className={styles.mono}>{esc(r.attempts)}</td>
                        <td>{esc(r.reason)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>
      </main>

      <footer>AutoNage — Recording Renamer</footer>
      <ProcessingOverlay show={isBusy} message={statusMsg || 'Processing…'} />
    </div>
  );
}
