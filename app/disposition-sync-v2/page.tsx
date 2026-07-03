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
import { readFileAsArrayBuffer, clean, esc, canonicalHeader, excelSafe, validateFileSync, colLetter } from '@/lib/data-pipeline';
import { detectHistory, formatHistoryForPrompt } from '@/lib/ai/history-helpers';
import { runLlmBatches } from '@/lib/ai/llm-batch-runner';
import * as XLSX from 'xlsx';
import {
  DEALER_CONFIGS, COMMON_COLUMNS, BUSINESS_CONFIG,
  DISPOSITION_PRIORITY, TERMINAL_THRESHOLD, CONNECTED_SET, NOT_CONNECTED_SET, MONTH_NAMES,
  normalizePhone, isPhoneLike, isLikelyIndianMobile,
  parseAutoEngageDate, formatCallDate, isDateStr, ordinalSuffix, formatTime12,
  detectPhonesFromObj, detectRecording, detectDate, detectSummary,
  detectSentiment, detectChannel, detectDuration, detectSessionId, detectSessionDisposition,
  deriveSeating, cellToString, getDispositionPriority,
  buildQualityReport, isAnantWAConfig, formatAnantWAFields,
  getColumnNames, getMissingColumnGroups,
  type DealerColumn, type SessionEntry,
} from './disposition-utils';
import { ALL_DISPOSITIONS, buildPreSalesValidationPrompt, parseLlmResponse, hashStr } from './pre-sales-prompt-builder';
import styles from './disposition-sync-v2.module.css';

const log = (...args: unknown[]) => console.log('[PreSales]', ...args);

export default function DispositionSyncV2Page() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [rawFile1, setRawFile1] = useState<File | null>(null);
  const [rawFile2, setRawFile2] = useState<File | null>(null);
  const [dealerKey, setDealerKey] = useState('anant_cars');
  const [leadIdStart, setLeadIdStart] = useState('');
  const [language, setLanguage] = useState('English');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [processing, setProcessing] = useState(false);
  const [processedData, setProcessedData] = useState<Record<string, string>[]>([]);
  const [qualityReport, setQualityReport] = useState<any>(null);
  const [convertedRows, setConvertedRows] = useState<Record<string, string>[]>([]);
  const [testDriveRows, setTestDriveRows] = useState<Record<string, string>[]>([]);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState('');
  const [showResults, setShowResults] = useState(false);
  const [file1Status, setFile1Status] = useState('Drag & drop or click to browse');
  const [file2Status, setFile2Status] = useState('Drag & drop or click to browse');
  const [hasFile1, setHasFile1] = useState(false);
  const [hasFile2, setHasFile2] = useState(false);
  const [dragOver1, setDragOver1] = useState(false);
  const [dragOver2, setDragOver2] = useState(false);
  const [pillStep, setPillStep] = useState(0); // 0=initial, 1=file1, 2=file2, 3=processing, 4=results

  // Sort state
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc' | null>(null);

  const file1Ref = useRef<HTMLInputElement>(null);
  const file2Ref = useRef<HTMLInputElement>(null);

  // AI validation state
  const aiProgress = useBatchProgress();
  const aiValidationRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  const dealerCfg = DEALER_CONFIGS[dealerKey] || DEALER_CONFIGS.default;
  const previewLimit = 200;

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  const prevDealer = useRef(dealerKey);
  useEffect(() => {
    if (prevDealer.current === dealerKey) return;
    prevDealer.current = dealerKey;
    const saved = localStorage.getItem(`leadIdStart-${dealerKey}`);
    if (saved) setLeadIdStart(saved);
  }, [dealerKey]);
  if (!isAuthenticated && !loading) return null;

  function parseSheet(ab: ArrayBuffer): Record<string, string>[] {
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

  function dedupeByPhone(rows: Record<string, string>[]): Record<string, string>[] {
    const seen = new Set<string>();
    return rows.filter(r => {
      const phone = r.phone || '';
      if (!phone || seen.has(phone)) return false;
      seen.add(phone);
      return true;
    });
  }

  function rowsToTsv(rows: Record<string, string>[], keys: string[]): string {
    return rows.map(r => keys.map(k => String(r[k] ?? '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ')).join('\t')).join('\n');
  }

  async function copyText(text: string, statusTxt: string) {
    try { await navigator.clipboard.writeText(text); } catch {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
      document.body.appendChild(ta); ta.focus(); ta.select();
      document.execCommand('copy'); document.body.removeChild(ta);
    }
    setStatusMsg(statusTxt); setStatusType('ok');
  }

  async function processFiles() {
    if (!rawFile1 || !rawFile2) return;
    log('Processing started, files:', rawFile1.name, rawFile2.name);
    setProcessing(true);
    setStatusMsg('Parsing files...'); setStatusType('');
    setPillStep(3);

    try {
      const startId = parseInt(leadIdStart, 10) || 0;
      const [ab1, ab2] = await Promise.all([readFileAsArrayBuffer(rawFile1), readFileAsArrayBuffer(rawFile2)]);
      const rows1 = parseSheet(ab1);
      const rows2 = parseSheet(ab2);

      // Early validation — check required columns
      const missingFile1Required = getMissingColumnGroups(rows1, BUSINESS_CONFIG.validation.file1RequiredGroups);
      if (missingFile1Required.length > 0) {
        setProcessing(false);
        setStatusMsg(`File 1 missing required columns: ${missingFile1Required.join(', ')}. Cannot process.`);
        setStatusType('err');
        return;
      }
      const missingFile2Required = getMissingColumnGroups(rows2, BUSINESS_CONFIG.validation.file2RequiredGroups);
      if (missingFile2Required.length > 0) {
        setProcessing(false);
        setStatusMsg(`File 2 missing required columns: ${missingFile2Required.join(', ')}. Cannot process.`);
        setStatusType('err');
        return;
      }

      // Build File 1 list + lookup by phone
      const allLeads: { row: Record<string, string>; phone: string }[] = [];
      const leadsByPhone: Record<string, { row: Record<string, string>; phone: string }> = {};
      for (const r of rows1) {
        const phone = normalizePhone(r['phone_number'] || r['phone'] || r['mobile'] || '');
        if (!phone) continue;
        allLeads.push({ row: r, phone });
        leadsByPhone[phone] = { row: r, phone };
      }

      // Filter rows2 by date range before building session groups
      let filteredRows2 = rows2;
      if (fromDate) {
        const from = new Date(fromDate + 'T00:00:00');
        filteredRows2 = filteredRows2.filter(r => {
          const d = detectDate(r);
          if (!d) return false;
          const dt = parseAutoEngageDate(d);
          return dt && dt >= from;
        });
      }
      if (toDate) {
        const to = new Date(toDate + 'T23:59:59');
        filteredRows2 = filteredRows2.filter(r => {
          const d = detectDate(r);
          if (!d) return false;
          const dt = parseAutoEngageDate(d);
          return dt && dt <= to;
        });
      }

      // Build File 2 session groups from filtered rows
      const sessionGroups: Record<string, Record<string, string>[]> = {};
      for (const r of filteredRows2) {
        const phones = detectPhonesFromObj(r);
        for (const phone of phones) {
          if (!sessionGroups[phone]) sessionGroups[phone] = [];
          sessionGroups[phone].push(r);
        }
      }

      // Build session map — prioritize by recording, then summary, then latest
      const sessionMap: Record<string, SessionEntry> = {};
      for (const [phone, sessions] of Object.entries(sessionGroups)) {
        let best: Record<string, string> | null = null;
        let selectionReason = 'fallback';
        const sorted = sessions.slice().sort((a, b) => {
          const aTs = detectDate(a) || a['start_time'] || a['timestamp'] || '';
          const bTs = detectDate(b) || b['start_time'] || b['timestamp'] || '';
          return bTs.localeCompare(aTs);
        });
        for (const s of sorted) {
          const rec = detectRecording(s);
          if (rec) { best = s; selectionReason = 'recording'; break; }
        }
        if (!best) {
          for (const s of sorted) {
            const summ = detectSummary(s);
            if (summ) { best = s; selectionReason = 'summary'; break; }
          }
        }
        if (!best) best = sorted[0];
        const histRaw = detectHistory(best);
        sessionMap[phone] = {
          selectionReason,
          recording: detectRecording(best),
          summary: detectSummary(best),
          sentiment: detectSentiment(best),
          dateStr: detectDate(best),
          startTime: best['start_time'] || '',
          channel: detectChannel(best),
          duration: detectDuration(best),
          session_id: detectSessionId(best),
          session_disposition: detectSessionDisposition(best),
          history_text: histRaw && best[histRaw] ? formatHistoryForPrompt(best[histRaw]) : '',
        };
      }

      // Call Triggered text — use filtered rows2
      let minDate: Date | null = null, maxDate: Date | null = null;
      for (const r of filteredRows2) {
        const dStr = detectDate(r) || r['start_time'] || '';
        const d = parseAutoEngageDate(dStr);
        if (!d) continue;
        if (!minDate || d < minDate) minDate = d;
        if (!maxDate || d > maxDate) maxDate = d;
      }
      let callTriggered = '';
      if (minDate && maxDate) {
        const day = ordinalSuffix(minDate.getDate());
        const month = MONTH_NAMES[minDate.getMonth()];
        const tMin = formatTime12(minDate);
        const tMax = formatTime12(maxDate);
        callTriggered = `${day} ${month} Calls Triggered From ${tMin} - ${tMax}`;
      }

      // Assemble output rows
      const output: Record<string, string>[] = [];
      const selectedLanguage = language;
      const isStellantis = dealerKey === 'stellantis_wa';
      const isChennaiEV = dealerKey === 'chennai_ev';
      const phoneIdx = dealerCfg.columns.findIndex(c => c.key === 'phone');
      const phoneCol = phoneIdx >= 0 ? colLetter(phoneIdx) : 'C';

      // Session-driven join: iterate over ALL sessions, output ONE row per call attempt
      for (const [phone, sessions] of Object.entries(sessionGroups)) {
        const lead = leadsByPhone[phone];
        if (!lead) continue;
        const { row } = lead;
        const totalAttempts = sessions.length;

        for (const sessionRow of sessions) {
          const disp = (row['disposition'] || '').trim();
          const dispLower = disp.toLowerCase();
          const priority = getDispositionPriority(disp);

          let outcome: string;
          if (CONNECTED_SET.has(dispLower)) {
            outcome = 'Connected';
          } else if (NOT_CONNECTED_SET.has(dispLower)) {
            outcome = 'Not Connected';
          } else if (disp && Object.keys(ALL_DISPOSITIONS).some(k => k.toLowerCase() === dispLower)) {
            outcome = 'Connected';
          } else {
            outcome = 'Unknown';
          }

          let summary: string, dispositionDetail: string;
          if (dealerKey === 'bimal') {
            // Bimal CSV has lead_summary ↔ disposition_detail swapped
            summary = (row['disposition_detail'] || row['lead_summary'] || '').trim() || 'No Response';
            dispositionDetail = row['lead_summary'] || '';
          } else {
            const summarySrc = row[dealerCfg.summarySource] || row['disposition_detail'] || '';
            summary = summarySrc.trim() || 'No Response';
            dispositionDetail = row['disposition_detail'] || '';
          }

          const model = (row['interested_vehicle_name'] || row['model_preference'] || row['name'] || '').replace(/[\[\]"']/g, '').trim();
          const seatingRaw = row['seating_capacity_preference'] || '';
          const seating = deriveSeating(seatingRaw, model);

          // Extract session data from this specific session row
          const sd = {
            recording: detectRecording(sessionRow),
            summary: detectSummary(sessionRow),
            sentiment: detectSentiment(sessionRow),
            dateStr: detectDate(sessionRow),
            startTime: sessionRow['start_time'] || '',
            channel: detectChannel(sessionRow),
            duration: detectDuration(sessionRow),
            session_id: detectSessionId(sessionRow),
            session_disposition: detectSessionDisposition(sessionRow),
            history_text: (() => {
              const k = detectHistory(sessionRow);
              return k ? formatHistoryForPrompt(sessionRow[k]) : '';
            })(),
          };

          const leadId = startId > 0 ? `L-${startId + output.length}` : `L-${output.length + 1}`;

          const dispositionText = (row['disposition_detail'] || '').toLowerCase();

          const rec: Record<string, string> = {
            lead_id: leadId,
            full_name: row['person_name'] || '',
            phone,
            city: row['city'] || '',
            pincode: row['pincode'] || '',
            language: selectedLanguage,
            lead_source: row['lead_source'] || '',
            showroom_code: row['showroom_code'] || row['dealer_map_cd'] || row['dealer_code'] || '',
            cohort: row['campaign_objective_name'] || '',
            campaign_id: row['campaign_id'] || '',
            last_session_id: isStellantis ? (sd.session_id || '') : (sd.session_id || row['last_session_id'] || row['session_id'] || ''),
            call_triggered: callTriggered,
            outcome,
            disposition: disp,
            summary: sd.summary || summary || 'No Response',
            disposition_detail: sd.session_disposition || dispositionDetail,
            manual_disposition_detail: '',
            call_date: sd.dateStr ? formatCallDate(parseAutoEngageDate(sd.dateStr)) : '',
            num_attempts: `=COUNTIF(${phoneCol}:${phoneCol};${phone})`,
            sentiment: sd.sentiment || '',
            recordings: sd.recording || '',
            model,
            seating,
            exclusion_flag: priority >= TERMINAL_THRESHOLD ? 'YES' : '',
            origin: sessionRow['origin'] || '',
            lead_timeline: row['lead_timeline'] || '',
            session_summary: sd.summary || '',
            session_history: sd.history_text || '',
            conversion: dispositionText.includes('converted') ? 'Yes' : '',
            channel: sd.channel || '',
            call_duration: sd.duration || '',
            _ai_status: '',
            updated_disposition: '',
          };

          if (isAnantWAConfig(dealerKey)) {
            output.push(formatAnantWAFields(rec));
          } else {
            output.push(rec);
          }
        }
      }

      const qr = buildQualityReport(rows1, rows2, allLeads, sessionGroups, sessionMap, output, callTriggered);
      setProcessedData(output);
      setQualityReport(qr);

      // Converted leads (deduplicated by phone)
      const convRows = dedupeByPhone(output.filter(r => r.conversion === 'Yes' || r.disposition.toLowerCase() === 'converted'));
      setConvertedRows(convRows);

      // Test Drive completed rows (deduplicated by phone)
      const tdRows = dedupeByPhone(output.filter(r => {
        const d = r.disposition.toLowerCase();
        return d.includes('test drive') || r.disposition_detail.toLowerCase().includes('test drive');
      }));
      setTestDriveRows(tdRows);

      setShowResults(true);
      setPillStep(4);
      log(`Processing complete: ${output.length} leads, ${convRows.length} converted, ${tdRows.length} test drives`);
      if (startId > 0) localStorage.setItem(`leadIdStart-${dealerKey}`, String(startId + output.length));
setStatusMsg(`${output.length} leads processed. Ready to copy or export.`);
        setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg('Error processing request.');
      setStatusType('err');
    }
    setProcessing(false);
  }

  async function copyData() { log('Copying data to clipboard');
    if (!processedData.length) return;
    const cols = dealerCfg.columns;
    const keys = cols.map(c => c.key);
    await copyText(rowsToTsv(processedData, keys), 'Copied rows. Paste with Ctrl+V in Zoho.');
  }

  async function copyConvertedData() {
    if (!convertedRows.length) { setStatusMsg('No converted rows to copy.'); setStatusType('warn'); return; }
    const keys = ['lead_id', 'full_name', 'phone', 'model', 'language', 'disposition_detail', 'summary', 'call_date', 'city'];
    await copyText(rowsToTsv(convertedRows, keys), 'Copied converted rows.');
  }

  async function copyTestDriveData() {
    if (!testDriveRows.length) { setStatusMsg('No test drive rows to copy.'); setStatusType('warn'); return; }
    const keys = ['lead_id', 'phone', 'model', 'language', 'call_date', 'summary'];
    await copyText(rowsToTsv(testDriveRows, keys), 'Copied test drive rows.');
  }

  async function copyQualityReport() {
    if (!qualityReport) return;
    const lines = [
      'Pre-Sales Data Quality Report',
      `Status: ${qualityReport.status}`,
      qualityReport.subtitle,
      '',
      ...qualityReport.warnings.map((w: any) => `${w.level.toUpperCase()}: ${w.title} — ${w.detail}`),
      '',
      ...qualityReport.samples.flatMap((s: any) => [s.title, ...s.rows.map((r: string) => `- ${r}`), '']),
    ];
    await copyText(lines.join('\n'), 'Copied quality report.');
  }

  function exportToExcel() {
    if (!processedData.length) return;
    log('Exporting Excel, rows:', processedData.length);
    const cols = dealerCfg.columns;
    const headers = cols.map(c => c.header);
    const keys = cols.map(c => c.key);
    const sorted = getSortedData(processedData);
    const dataRows = [headers, ...sorted.map(r => keys.map(k => excelSafe(r[k] ?? '')))];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(dataRows), 'Output');

    if (convertedRows.length) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([
        ['LEAD_ID', 'PERSON_NAME', 'PHONE_NUMBER', 'VEHICLE_MODEL', 'LANGUAGE', 'DISPOSITION_DETAILS', 'SUMMARY', 'CALL_DATE', 'LOCATION'],
        ...convertedRows.map(r => [r.lead_id, r.full_name, r.phone, r.model, r.language, r.disposition_detail, r.summary, r.call_date, r.city].map(excelSafe)),
      ]), 'Converted Leads');
    }
    if (testDriveRows.length) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([
        ['LEAD_ID', 'PHONE_NUMBER', 'VEHICLE_MODEL', 'LANGUAGE', 'CALL_DATE', 'SUMMARY'],
        ...testDriveRows.map(r => [r.lead_id, r.phone, r.model, r.language, r.call_date, r.summary].map(excelSafe)),
      ]), 'Test Drive Completed');
    }

    const safeName = dealerCfg.name.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '');
    XLSX.writeFile(wb, `AutoNage_Pre_Sales_${safeName}.xlsx`);
  }

  function resetAll() {
    setRawFile1(null); setRawFile2(null);
    setFromDate('');
    setToDate('');
    setProcessedData([]); setQualityReport(null);
    setConvertedRows([]); setTestDriveRows([]);
    setShowResults(false); aiProgress.reset();
    setSortKey(null); setSortDir(null);
    setFile1Status('Drag & drop or click to browse');
    setFile2Status('Drag & drop or click to browse');
    setHasFile1(false); setHasFile2(false);
    setStatusMsg(''); setStatusType('');
    setPillStep(0);
    if (file1Ref.current) file1Ref.current.value = '';
    if (file2Ref.current) file2Ref.current.value = '';
  }

  // ── AI Validation ──────────────────────────────────────────────

  function cancelAiValidation() {
    if (abortRef.current) {
      abortRef.current.abort();
    }
  }

  function validateDispositionsWithLLM(force = false) {
    if (!processedData.length) return;
    if (aiValidationRef.current) return;
    log('AI validation started, candidates:', processedData.filter(r => r.disposition === 'engaged' && r.session_summary !== 'No Response').length);

    // Filter: rows where disposition === 'engaged' AND session_summary !== 'No Response'
    const candidates: { index: number; summary: string; history: string; currentDisp: string; model: string; outcome: string; callDuration: string; leadSource: string }[] = [];
    for (let i = 0; i < processedData.length; i++) {
      const r = processedData[i];
      const summ = (r.session_summary || '').trim();
      const hist = (r.session_history || '').trim();
      const disp = (r.disposition_detail || '').trim();
      if (r.disposition === 'engaged' && r.session_summary !== 'No Response') {
        candidates.push({
          index: i,
          summary: summ,
          history: hist,
          currentDisp: disp,
          model: r.model || '',
          outcome: r.outcome || '',
          callDuration: r.call_duration || '',
          leadSource: r.lead_source || '',
        });
      }
    }

    if (!candidates.length) {
      setStatusMsg('No rows with session summaries to validate.');
      setStatusType('warn');
      return;
    }

    aiValidationRef.current = true;
    aiProgress.begin(candidates.length);
    aiProgress.setDone(0, 'AI validating dispositions…');

    abortRef.current = new AbortController();
    const abortController = abortRef.current;
    const BATCH_SIZE = 6;

    // Cache check
    const cacheInput = candidates.map(c => `${c.summary}||${c.history}||${c.currentDisp}||${c.model}||${c.outcome}||${c.callDuration}||${c.leadSource}`).join('|');
    const cacheKey = 'disp-validate-v9-history-' + hashStr(cacheInput);
    const cached = force ? null : (typeof window !== 'undefined' ? localStorage.getItem(cacheKey) : null);
    let cachedParsed: any[] | null = null;
    if (cached) {
      try { cachedParsed = JSON.parse(cached); } catch { /* ignore */ }
    }

    if (cachedParsed) {
      const correctedResults: Record<number, string> = {};
      for (const item of cachedParsed) {
        if (item.isCorrect === false && item.correctedDisposition) {
          correctedResults[item.rowIndex] = item.correctedDisposition;
        }
      }
      applyCorrections(candidates, correctedResults, new Set(candidates.map(c => c.index)));
      const correctedCount = Object.keys(correctedResults).length;
      if (correctedCount > 0) aiProgress.markCorrected(correctedCount);
      aiProgress.complete(correctedCount > 0
        ? `AI validation complete (from cache) — ${correctedCount} disposition(s) corrected.`
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
      requestTimeoutMs: 90000,
      buildPrompt: (batch, batchIndex) => {
        return buildPreSalesValidationPrompt(batch as any[], batchIndex, BATCH_SIZE);
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
      log('AI validation done, corrected:', Object.keys(correctedResults).length);

      if (result.aborted) {
        aiProgress.abort('AI validation cancelled.');
        aiValidationRef.current = false;
        abortRef.current = null;
        return;
      }

      const evaluatedIndices = new Set<number>();
      for (let ri = 0; ri < candidates.length; ri++) {
        if (result.results.has(ri)) evaluatedIndices.add(candidates[ri].index);
      }

      for (let ri = 0; ri < candidates.length; ri++) {
        const dec = result.results.get(ri);
        if (dec && (dec as any).isCorrect === false && (dec as any).correctedDisposition) {
          correctedResults[candidates[ri].index] = (dec as any).correctedDisposition;
        }
      }

      const cacheArray = candidates.map((c, idx) => {
        const dec = result.results.get(idx);
        if (dec && (dec as any).isCorrect === false && (dec as any).correctedDisposition) {
          return { rowIndex: c.index, isCorrect: false, correctedDisposition: (dec as any).correctedDisposition };
        }
        return { rowIndex: c.index, isCorrect: true, correctedDisposition: null };
      });
      try { if (typeof window !== 'undefined') localStorage.setItem(cacheKey, JSON.stringify(cacheArray)); } catch { /* ignore */ }

      applyCorrections(candidates, correctedResults, evaluatedIndices);
      const correctedCount = Object.keys(correctedResults).length;
      if (correctedCount > 0) aiProgress.markCorrected(correctedCount);
      aiProgress.complete(correctedCount > 0
        ? `AI validation complete — ${correctedCount} disposition(s) corrected. Check the Updated Disposition column.`
        : 'AI validation complete — all dispositions appear correct.');
      aiValidationRef.current = false;
      abortRef.current = null;
    }).catch((err) => {
      aiProgress.abort('AI validation failed.');
      aiValidationRef.current = false;
      abortRef.current = null;
    });
  }

  function applyCorrections(candidates: { index: number }[], correctedResults: Record<number, string>, evaluatedIndices?: Set<number>) {
    if (Object.keys(correctedResults).length === 0 && !evaluatedIndices) {
      setProcessedData(prev => prev.map((r, idx) => {
        if (candidates.some(c => c.index === idx) && !r._ai_status) {
          return { ...r, _ai_status: 'verified' };
        }
        return r;
      }));
      return;
    }

    setProcessedData(prev => prev.map((r, idx) => {
      if (correctedResults[idx] !== undefined) {
        return { ...r, updated_disposition: correctedResults[idx], manual_disposition_detail: correctedResults[idx], _ai_status: 'corrected' };
      }
      if (evaluatedIndices) {
        if (evaluatedIndices.has(idx) && !r._ai_status) {
          return { ...r, _ai_status: 'verified' };
        }
      } else if (candidates.some(c => c.index === idx) && !r._ai_status) {
        return { ...r, _ai_status: 'verified' };
      }
      return r;
    }));
  }

  // ── File handlers ──────────────────────────────────────────────

  async function handleFile1Change(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) { setFile1Status(v.error!); return; }
    try {
      const ab = await readFileAsArrayBuffer(f);
      setRawFile1(f); setFile1Status(`Loaded: ${f.name}`); setHasFile1(true);
      setPillStep(1); log('File 1 loaded:', f.name);
      setShowResults(false);
      setProcessedData([]);
      setQualityReport(null);
      setConvertedRows([]);
      setTestDriveRows([]);
      setStatusMsg('');
      setStatusType('');
      const rows = parseSheet(ab);
      if (rows.length) {
        const idCandidates = ['last_session_id', 'session_id'];
        let idCol: string | null = null;
        for (const c of idCandidates) { if (c in rows[0]) { idCol = c; break; } }
        if (idCol) {
          let maxId = 0;
          for (const row of rows) {
            const raw = String(row[idCol] || '').trim();
            const num = parseInt(raw, 10);
            if (!isNaN(num) && num > maxId) maxId = num;
          }
          if (maxId > 0) {
            setLeadIdStart(String(maxId + 1));
            setStatusMsg(`Lead ID auto-set to ${maxId + 1} (from last_session_id max: ${maxId})`);
            setStatusType('ok');
          }
        }
      }
    } catch { /* silent */ }
  }
  function handleFile2Change(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]; if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) { setFile2Status(v.error!); return; }
    setRawFile2(f); setFile2Status(`Loaded: ${f.name}`); setHasFile2(true);
    setPillStep(2); log('File 2 loaded:', f.name);
    setShowResults(false);
    setProcessedData([]);
    setQualityReport(null);
    setConvertedRows([]);
    setTestDriveRows([]);
    setStatusMsg('');
    setStatusType('');
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

  // Stats
  const totalLeads = processedData.length;
  const connected = processedData.filter(r => r.outcome === 'Connected').length;
  const notConnected = processedData.filter(r => r.outcome === 'Not Connected').length;
  const aiReady = processedData.filter(r => r.disposition === 'engaged' && r.session_summary !== 'No Response').length;
  const skippedNoSummary = processedData.filter(r => r.session_summary === '' || r.session_summary === 'No Response').length;
  const excluded = processedData.filter(r => r.exclusion_flag === 'YES').length;
  const withRecording = processedData.filter(r => r.recordings).length;

  const outputColumns = dealerCfg.columns;
  const sortedData = getSortedData(processedData);
  const startId = parseInt(leadIdStart, 10) || 0;
  const previewData = sortedData.slice(0, previewLimit).map((r, i) => ({ ...r, lead_id: `L-${startId > 0 ? startId + i : i + 1}` })) as Record<string, string>[];

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Pre-Sales Sync</h1>
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
        <section className={`${styles['workflow-panel'] || styles.workflowPanel || ''}`}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 1</div>
              <div className={styles['section-title']}>Prepare the batch</div>
            </div>
            <div className={styles['section-note']}>Drop the two exports, choose the run settings, then process.</div>
          </div>

          {/* Upload Zones */}
          <div className={styles['upload-grid']}>
            <div
              className={`${styles['drop-zone']} ${dragOver1 ? styles['drag-over'] : ''} ${hasFile1 ? styles['has-file'] : ''}`}
              onClick={() => file1Ref.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver1(true); }}
              onDragLeave={() => setDragOver1(false)}
              onDrop={handleDrop1}
            >
              <div className={styles['dz-icon']}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>
              <div className={styles['dz-label']}>File 1 — Audience & Leads</div>
              <div className={styles['dz-sublabel']}>AutoEngage → Audience & Leads export</div>
              <div className={styles['dz-cols']}>person_name · phone_number · city · campaign_id<br />lead_source · disposition · updated · model_preference<br />seating_capacity_preference · disposition_detail</div>
              <div className={`${styles['dz-status']} ${hasFile1 ? styles['ok'] : ''}`}>{file1Status}</div>
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
              <div className={styles['dz-sublabel']}>AutoEngage → Sessions export</div>
              <div className={styles['dz-cols']}>phone_number · created · start_time<br />summary · history · call_recording · sentiment_score</div>
              <div className={`${styles['dz-status']} ${hasFile2 ? styles['ok'] : ''}`}>{file2Status}</div>
              <input ref={file2Ref} type="file" accept=".csv,.xlsx,.xls" onChange={handleFile2Change} style={{ display: 'none' }} />
            </div>
          </div>

          {/* Pill strip */}
          <div className={styles['pill-strip']}>
            <div className={`${styles['step-pill']} ${pillStep >= 1 ? styles.active : ''}`}><span className="num">1</span> Leads uploaded</div>
            <div className={`${styles['step-pill']} ${pillStep >= 2 ? styles.active : ''}`}><span className="num">2</span> Sessions uploaded</div>
            <div className={`${styles['step-pill']} ${pillStep >= 3 ? styles.active : ''}`}><span className="num">3</span> Ready to process</div>
            <div className={`${styles['step-pill']} ${pillStep >= 4 ? styles.active : ''}`}><span className="num">4</span> Results ready</div>
          </div>

          {/* Action bar */}
          <div className={styles['action-bar']}>
            <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={processFiles} disabled={!rawFile1 || !rawFile2 || processing}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg> Process Both Files
            </button>
            <div className={styles['control-group']}>
              <span className={styles['control-label']}>Dealership</span>
              <div className={styles['select-wrapper']}>
                <select className="custom-select" value={dealerKey} onChange={e => setDealerKey(e.target.value)} style={{ padding: '0.5rem 1.8rem 0.5rem 0.75rem', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', background: 'var(--bg)', color: 'var(--text)', fontSize: '0.85rem', cursor: 'pointer', appearance: 'none', fontFamily: 'var(--body)' }}>
                  <option value="anant_cars">Anant Cars</option>
                  <option value="anant_wa">Anant WA</option>
                  <option value="chennai_ev">ChennaiEV</option>
                  <option value="singhal">Singhal</option>
                  <option value="fortune_hyryder">Fortune Hyryder</option>
                  <option value="fortune_honda">Fortune Honda</option>
                  <option value="stellantis_wa">Stellantis WA</option>
                  <option value="bimal">Bimal</option>
                  <option value="saisamarth">Saisamarth</option>
                  <option value="perfect_rider_wa">Perfect Rider WA</option>
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
                  <option value="Tamil">Tamil</option>
                  <option value="Malayalam">Malayalam</option>
                  <option value="Kannada">Kannada</option>
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
                <button className={`${styles.btn} ${styles['btn-success']}`} onClick={copyData}>Copy All Data</button>
                <button className={`${styles.btn} ${styles['btn-success']}`} onClick={exportToExcel}>Export Excel</button>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => validateDispositionsWithLLM()}>
                  <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg> Validate with AI
                </button>
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

        <section className={`${styles['results-panel'] || styles.resultsPanel || ''}`}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 2</div>
              <div className={styles['section-title']}>Review and hand off</div>
            </div>
            <div className={styles['section-note']}>After processing, use the stats and preview tables for spot checks before copying or exporting.</div>
          </div>

          {showResults ? (
            <>
              {/* Stats bar */}
              <div className={styles['stats-bar']} style={{ display: 'flex' }}>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Total Leads</div><div className={`${styles['stat-val']} ${styles.blue}`}>{totalLeads}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Connected</div><div className={`${styles['stat-val']} ${styles.green}`}>{connected}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Not Connected</div><div className={`${styles['stat-val']} ${styles.amber}`}>{notConnected}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>AI-Ready</div><div className={`${styles['stat-val']} ${styles.green}`}>{aiReady}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Skipped (no summary)</div><div className={`${styles['stat-val']} ${styles.gray}`}>{skippedNoSummary}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>Excluded (Terminal)</div><div className={`${styles['stat-val']} ${styles.purple}`}>{excluded}</div></div>
                <div className={styles['stat-card']}><div className={styles['stat-label']}>With Recording</div><div className={`${styles['stat-val']} ${styles.blue}`}>{withRecording}</div></div>
              </div>

              {/* Quality card */}
              {qualityReport && (
                <div className={styles['quality-card']} style={{ display: 'block' }}>
                  <div className={styles['quality-header']}>
                    <div>
                      <div className={styles.eyebrow}>Data quality</div>
                      <div className={styles['quality-title']}>{qualityReport.status}</div>
                      <div className={styles['quality-subtitle']}>{qualityReport.subtitle}</div>
                    </div>
                    <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={copyQualityReport} style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', height: 'auto' }}>Copy Report</button>
                  </div>
                  <div className={styles['quality-grid']}>
                    {qualityReport.metrics.map((m: any, i: number) => (
                      <div key={i} className={styles['quality-metric']}>
                        <div className={styles['quality-metric-label']}>{m.label}</div>
                        <div className={styles['quality-metric-value']} style={{ color: m.tone === 'green' ? 'var(--success)' : m.tone === 'amber' ? 'var(--warn)' : m.tone === 'red' ? 'var(--danger)' : '#60a5fa' }}>{m.value}</div>
                      </div>
                    ))}
                  </div>
                  <div className={styles['quality-sections']}>
                    <div>
                      <div className={styles['quality-list-title']}>Warnings</div>
                      {qualityReport.warnings.map((w: any, i: number) => (
                        <div key={i} className={`${styles['quality-list-item']} ${styles[w.level as keyof typeof styles] || ''}`}><strong>{w.title}</strong><br />{w.detail}</div>
                      ))}
                    </div>
                    <div>
                      <div className={styles['quality-list-title']}>Reconciliation samples</div>
                      {qualityReport.samples.map((s: any, i: number) => (
                        <div key={i} className={`${styles['quality-list-item']} ${styles['info']}`}>
                          <strong>{s.title}</strong><br />{s.rows.join('<br />')}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Main output table */}
              <div className={styles['table-wrapper']} style={{ display: 'block' }}>
                <div className={styles['table-header']}>
                  <div>
                    <div className={styles['table-title']}>Output Preview</div>
                    <div className={styles['table-caption']}>{processedData.length > previewLimit ? `Showing first ${previewLimit} of ${processedData.length} rows` : `${processedData.length} rows`}</div>
                  </div>
                </div>
                <div className={styles['table-scroll']}>
                  <table>
                    <thead><tr>
                      {outputColumns.map(col => {
                        const isSortable = ['full_name', 'phone', 'disposition'].includes(col.key);
                        return <th key={col.key} className={isSortable ? styles['th-sortable'] : ''} onClick={isSortable ? () => toggleSort(col.key) : undefined}>{col.header}</th>;
                      })}
                    </tr></thead>
                    <tbody>
                      {previewData.map((r, i) => (
                        <tr key={i}>
                          {outputColumns.map(col => {
                            const val = r[col.key] ?? '';
                            if (col.key === 'phone' || col.key === 'num_attempts') return <td key={col.key} className={styles['cell-phone']}>{esc(val)}</td>;
                            if (col.key === 'recordings' && val) {
                              const lower = val.toLowerCase();
                              if (lower.startsWith('http://') || lower.startsWith('https://')) return <td key={col.key}><a className={styles['cell-url']} href={val} target="_blank" rel="noopener noreferrer">Recording</a></td>;
                            }
                            if (col.key === 'updated_disposition' || col.key === 'manual_disposition_detail') {
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

              {/* Converted Leads Preview */}
              {convertedRows.length > 0 && (
                <div className={styles['table-wrapper']} style={{ display: 'block', marginTop: '2rem' }}>
                  <div className={styles['table-header']}>
                    <div>
                      <div className={styles['table-title']}>Converted Leads Preview</div>
                      <div className={styles['table-caption']}>{convertedRows.length} rows</div>
                    </div>
                    <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={copyConvertedData} style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', height: 'auto' }}>Copy Converted</button>
                  </div>
                  <div className={styles['table-scroll']}>
                    <table>
                      <thead><tr>
                        <th>LEAD_ID</th><th>PERSON_NAME</th><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>LANGUAGE</th><th>DISPOSITION_DETAILS</th><th>SUMMARY</th><th>CALL_DATE</th><th>LOCATION</th>
                      </tr></thead>
                      <tbody>
                        {convertedRows.slice(0, previewLimit).map((r, i) => (
                          <tr key={i}>
                            <td className={styles['cell-phone']}>{esc(r.lead_id)}</td>
                            <td>{esc(r.full_name)}</td>
                            <td className={styles['cell-phone']}>{esc(r.phone)}</td>
                            <td>{esc(r.model)}</td>
                            <td>{esc(r.language)}</td>
                            <td>{esc(r.disposition_detail)}</td>
                            <td>{esc(r.summary)}</td>
                            <td>{esc(r.call_date)}</td>
                            <td>{esc(r.city)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Test Drive Completed Preview */}
              {testDriveRows.length > 0 && (
                <div className={styles['table-wrapper']} style={{ display: 'block', marginTop: '2rem' }}>
                  <div className={styles['table-header']}>
                    <div>
                      <div className={styles['table-title']}>Test Drive Completed Preview</div>
                      <div className={styles['table-caption']}>{testDriveRows.length} rows</div>
                    </div>
                    <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={copyTestDriveData} style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', height: 'auto' }}>Copy Test Drive</button>
                  </div>
                  <div className={styles['table-scroll']}>
                    <table>
                      <thead><tr>
                        <th>LEAD_ID</th><th>PHONE_NUMBER</th><th>VEHICLE_MODEL</th><th>LANGUAGE</th><th>CALL_DATE</th><th>SUMMARY</th>
                      </tr></thead>
                      <tbody>
                        {testDriveRows.slice(0, previewLimit).map((r, i) => (
                          <tr key={i}>
                            <td className={styles['cell-phone']}>{esc(r.lead_id)}</td>
                            <td className={styles['cell-phone']}>{esc(r.phone)}</td>
                            <td>{esc(r.model)}</td>
                            <td>{esc(r.language)}</td>
                            <td>{esc(r.call_date)}</td>
                            <td>{esc(r.summary)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '1rem', alignItems: 'center', padding: '1rem 1.1rem', marginBottom: '1rem', border: '1px dashed var(--border)', borderRadius: 'var(--radius-lg)', background: 'var(--accent-soft)' }}>
              <div>
                <strong style={{ display: 'block', marginBottom: '0.2rem', fontFamily: 'var(--sans)', fontSize: '1rem' }}>Waiting for a processed batch</strong>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem' }}>Upload both files and run processing. The stats, quality checks, and preview tables will appear here.</p>
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
      <footer>AutoNage - Pre-Sales Sync v2 - AutoEngage to Zoho Master Sheet</footer>
      <ProcessingOverlay show={processing} message="Processing files…" />
    </div>

  );
}
