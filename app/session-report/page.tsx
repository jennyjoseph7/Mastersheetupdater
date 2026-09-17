'use client';
import { useState, useRef, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import BatchProgressBar from '@/components/BatchProgressBar';
import { useBatchProgress } from '@/hooks/useBatchProgress';
import * as XLSX from 'xlsx';
import { validateFileSync, clean, canonicalHeader, excelSafe } from '@/lib/data-pipeline';
import { buildDispoValidationPrompt, parseLlmResponse, hashStr } from '@/app/post-sales-sync/prompt-builder';
import { runLlmBatches } from '@/lib/ai/llm-batch-runner';
import styles from './session-report.module.css';

import {
  REPORT_HEADERS,
  cellToString,
  get,
  normalizePhone,
  extractPhone,
  extractAllPhoneCandidates,
  detectFileRoles,
  extractVehicleNumber,
  extractVehicleModel,
  extractShowroom,
  extractServicePlan,
  extractServiceDueDate,
  determineLeadCategory,
} from './report-utils';

const log = (...args: unknown[]) => console.log('[SessionReport]', ...args);

export default function SessionReportPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [rawFile1, setRawFile1] = useState<File | null>(null);
  const [rawFile2, setRawFile2] = useState<File | null>(null);
  const [file1Status, setFile1Status] = useState('Drag & drop or click to browse');
  const [file2Status, setFile2Status] = useState('Drag & drop or click to browse');
  const [hasFile1, setHasFile1] = useState(false);
  const [hasFile2, setHasFile2] = useState(false);
  const [dragOver1, setDragOver1] = useState(false);
  const [dragOver2, setDragOver2] = useState(false);
  const [pillStep, setPillStep] = useState(0); // 0=initial, 1=file1, 2=file2, 3=ready, 4=results

  const [dealerKey, setDealerKey] = useState('keerthi_triumph');
  const [processing, setProcessing] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'ok' | 'err' | 'warn' | ''>('');
  
  const [outputRows, setOutputRows] = useState<Record<string, string>[]>([]);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc' | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const file1Ref = useRef<HTMLInputElement>(null);
  const file2Ref = useRef<HTMLInputElement>(null);

  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
  const [debugInfo, setDebugInfo] = useState<any>(null);

  const aiProgress = useBatchProgress();
  const aiValidationRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);

  if (!isAuthenticated && !loading) return null;

  async function parseSheet(file: File): Promise<Record<string, string>[]> {
    const ab = await file.arrayBuffer();
    const wb = XLSX.read(ab, { type: 'array', raw: true, cellDates: true });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];
    
    if (rows.length < 2) return [];
    
    let headerIdx = 0;
    let maxNonEmpty = 0;
    let bestHeaderIdx = 0;
    
    // Find the row with the most non-empty cells (up to the first 20 rows)
    for (let i = 0; i < Math.min(20, rows.length); i++) {
      const rowArr = rows[i] as unknown[];
      const nonEmptyCells = rowArr.filter(c => clean(c)).length;
      if (nonEmptyCells > maxNonEmpty) {
        maxNonEmpty = nonEmptyCells;
        bestHeaderIdx = i;
      }
    }
    headerIdx = bestHeaderIdx;

    if (headerIdx >= rows.length || maxNonEmpty < 2) return [];
    
    const headers = rows[headerIdx].map(h => canonicalHeader(h));
    const result: Record<string, string>[] = [];
    
    for (let i = headerIdx + 1; i < rows.length; i++) {
      const raw = rows[i] as unknown[];
      if (!raw.some(c => clean(c))) continue;
      const obj: Record<string, string> = {};
      headers.forEach((h, j) => {
        if (h) obj[h] = cellToString(raw[j]);
      });
      result.push(obj);
    }
    return result;
  }

  function cancelAiValidation() {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    aiProgress.abort('AI validation cancelled.');
    aiValidationRef.current = false;
    abortRef.current = null;
  }

  function validateDispositionsWithLLM(force = false) {
    if (!outputRows.length) return;
    if (aiValidationRef.current) return;
    log('AI validation started, total rows:', outputRows.length);

    const getAuth = (k: string) => (typeof window !== 'undefined' ? (sessionStorage.getItem(k) || localStorage.getItem(k)) : '') || '';
    if (!getAuth('gryd_token') || !getAuth('gryd_session_id')) {
      setStatusMsg('Not signed in or session expired. Please log in again.');
      setStatusType('warn');
      return;
    }

    // Filter rows with completed session_status and summary
    const candidates: { index: number; summary: string; history: string; currentDisp: string; callDate: string; outcome: string; vehicleModel: string; campaignId: string; dealerName: string; supportedLanguages: string }[] = [];
    for (let i = 0; i < outputRows.length; i++) {
      const r = outputRows[i];
      const summ = (r['Call Summary'] || '').trim();
      const hist = (r['_session_history'] || '').trim();
      const disp = (r['Disposition Detail'] || r['Disposition'] || '').trim();
      // Check if session status is completed or similar
      const status = (r['_session_status'] || '').trim().toLowerCase();
      
      if (status === 'completed' || status === 'contacted' || summ) {
        candidates.push({
          index: i,
          summary: summ,
          history: hist,
          currentDisp: disp,
          callDate: r['Call Date'] || '',
          outcome: r['_outcome'] || '',
          vehicleModel: r['Vehicle Model'] || '',
          campaignId: r['Campaign'] || '',
          dealerName: 'Keerthi Triumph',
          supportedLanguages: 'Kannada, English, Hindi',
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

    const cacheInput = candidates.map(c => `${c.summary}||${c.history}||${c.currentDisp}||${c.callDate}||${c.outcome}||${c.vehicleModel}||${c.campaignId}||${c.dealerName}||${c.supportedLanguages}`).join('|');
    const cacheKey = 'ps-disp-validate-session-report-v2-' + hashStr(cacheInput);
    const cached = force ? null : (typeof window !== 'undefined' ? localStorage.getItem(cacheKey) : null);
    let cachedParsed: any[] | null = null;
    if (cached) {
      try { cachedParsed = JSON.parse(cached); } catch { /* ignore */ }
    }

    if (cachedParsed) {
      const correctedResults: Record<number, { disp: string, reason: string }> = {};
      for (const item of cachedParsed) {
        if (item.isCorrect === false && item.correctedDisposition) {
          correctedResults[item.rowIndex] = { disp: item.correctedDisposition, reason: item.reason || '' };
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

    const correctedResults: Record<number, { disp: string, reason: string }> = {};

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
          'X-GRYD-TOKEN': getAuth('gryd_token'),
          'X-GRYD-SESSION-ID': getAuth('gryd_session_id'),
          'X-GRYD-ENTERPRISE-ID': getAuth('gryd_enterprise_id') || 'autocrm',
          'X-GRYD-SIGNUP-TOKEN': cfg.grydSignupToken || '',
          'X-GRYD-APPLICATION-ID': 'autocrm',
        };
      },
      parseResponse: (text, batch, batchIndex) => {
        return parseLlmResponse(text, batchIndex, BATCH_SIZE, batch);
      },
      onProgress: (done, total, message, pct) => {
        aiProgress.setDone(done, message);
      },
      signal: abortController.signal,
    }).then((result) => {
      if (result.aborted || !aiValidationRef.current) {
        aiProgress.abort('AI validation cancelled.');
        aiValidationRef.current = false;
        abortRef.current = null;
        return;
      }

      // Collect corrections from runner results
      for (let ri = 0; ri < candidates.length; ri++) {
        const dec = result.results.get(ri);
        if (dec && (dec as any).isCorrect === false && (dec as any).correctedDisposition) {
          correctedResults[candidates[ri].index] = { disp: (dec as any).correctedDisposition, reason: (dec as any).reason || '' };
        }
      }

      // Save to cache
      const cacheArray = candidates.map((c, idx) => {
        const dec = result.results.get(idx);
        if (dec && (dec as any).isCorrect === false && (dec as any).correctedDisposition) {
          return { rowIndex: c.index, isCorrect: false, correctedDisposition: (dec as any).correctedDisposition, reason: (dec as any).reason || '' };
        }
        return { rowIndex: c.index, isCorrect: true, correctedDisposition: null };
      });
      try { if (typeof window !== 'undefined') localStorage.setItem(cacheKey, JSON.stringify(cacheArray)); } catch { /* ignore */ }

      applyCorrections(candidates, correctedResults);
      const correctedCount = Object.keys(correctedResults).length;
      if (correctedCount > 0) aiProgress.markCorrected(correctedCount);
      aiProgress.complete(correctedCount > 0
        ? `AI validation complete — ${correctedCount} disposition(s) corrected. Check the Updated Disposition column.`
        : 'AI validation complete — all dispositions appear correct.');
      aiValidationRef.current = false;
      abortRef.current = null;
    }).catch((err) => {
      if (abortController.signal.aborted) return;
      console.error('LLM Batch Error:', err);
      aiProgress.abort('AI validation failed.');
      aiValidationRef.current = false;
      abortRef.current = null;
    });
  }

  function applyCorrections(candidates: { index: number }[], correctedResults: Record<number, { disp: string, reason: string }>) {
    setOutputRows(prev => prev.map((r, idx) => {
      if (correctedResults[idx]) {
        return { 
          ...r, 
          'Updated Disposition': correctedResults[idx].disp, 
          'AI Reason': correctedResults[idx].reason 
        };
      }
      return r;
    }));
  }

  // File 1 handler
  async function handleFile1Change(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) {
      setFile1Status(v.error!);
      return;
    }
    setRawFile1(f);
    setFile1Status(`Loaded: ${f.name}`);
    setHasFile1(true);
    setPillStep(prev => (prev >= 2 ? 3 : 1));
    setShowResults(false);
    setOutputRows([]);
    setStatusMsg('');
    setStatusType('');
    log('File 1 loaded:', f.name);
  }

  // File 2 handler
  async function handleFile2Change(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const v = validateFileSync(f);
    if (!v.valid) {
      setFile2Status(v.error!);
      return;
    }
    setRawFile2(f);
    setFile2Status(`Loaded: ${f.name}`);
    setHasFile2(true);
    setPillStep(prev => (prev >= 1 ? 3 : 2));
    setShowResults(false);
    setOutputRows([]);
    setStatusMsg('');
    setStatusType('');
    log('File 2 loaded:', f.name);
  }

  function handleDrop1(e: React.DragEvent) {
    e.preventDefault();
    setDragOver1(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const dt = new DataTransfer();
    dt.items.add(f);
    if (file1Ref.current) {
      file1Ref.current.files = dt.files;
      file1Ref.current.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  function handleDrop2(e: React.DragEvent) {
    e.preventDefault();
    setDragOver2(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const dt = new DataTransfer();
    dt.items.add(f);
    if (file2Ref.current) {
      file2Ref.current.files = dt.files;
      file2Ref.current.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  // Process Both Files
  async function processFiles() {
    if (!rawFile1 || !rawFile2) return;
    setProcessing(true);
    setStatusMsg('Parsing and joining records...');
    setStatusType('');

    try {
      const [rows1, rows2] = await Promise.all([parseSheet(rawFile1), parseSheet(rawFile2)]);

      // 1. Detect if user uploaded files in swapped order
      const { leadRows, sessionRows, swapped } = detectFileRoles(rows1, rows2);

      // 2. Build multi-index lookup map from lead rows
      const leadMap = new Map<string, any>();
      leadRows.forEach(lead => {
        // Phone numbers (all extracted variants)
        const phones = extractAllPhoneCandidates(lead);
        for (const p of phones) {
          leadMap.set(p, lead);
          leadMap.set('91' + p, lead);
          if (p.length === 10) leadMap.set(p, lead);
          if (p.startsWith('91') && p.length === 12) leadMap.set(p.slice(2), lead);
        }

        // AutoEngage user_id match
        const aeUserId = get(lead, ['user_id', 'lead_id', 'id']);
        if (aeUserId) {
          leadMap.set('AE_USER_' + String(aeUserId).trim(), lead);
        }

        // Vehicle Registration
        const reg = extractVehicleNumber(lead, {});
        if (reg) {
          leadMap.set('REG_' + reg.toUpperCase().replace(/[\s-]+/g, ''), lead);
        }

        // Vehicle ID
        const vid = get(lead, ['vehicle_id']);
        if (vid) {
          leadMap.set('VID_' + vid.toLowerCase().trim(), lead);
        }

        // VIN
        const vin = get(lead, ['vin_number', 'vin', 'chassis_number']);
        if (vin) {
          leadMap.set('VIN_' + vin.toLowerCase().trim(), lead);
        }

        // Session ID (last_session_id in leads)
        const sessId = get(lead, ['last_session_id', 'session_id', 'first_session_id']);
        if (sessId) {
          leadMap.set('SESS_' + sessId.trim(), lead);
        }

        // Lead ID
        const leadId = get(lead, ['post_sales_lead_id', 'lead_id', 'user_id']);
        if (leadId) {
          leadMap.set('LEADID_' + leadId.trim(), lead);
        }

        // Name
        const name = get(lead, ['person_name', 'name', 'customer_name', 'customer']);
        if (name && name.length > 3) {
          leadMap.set('NAME_' + name.toLowerCase().trim().replace(/\s+/g, ''), lead);
        }
      });

      // 3. Process session rows, joining with lead data
      const processed: Record<string, string>[] = sessionRows.map(session => {
        let lead: any = null;

        // Try phone matching
        const sPhones = extractAllPhoneCandidates(session);
        for (const sp of sPhones) {
          if (leadMap.has(sp)) { lead = leadMap.get(sp); break; }
          if (sp.length === 10 && leadMap.has('91' + sp)) { lead = leadMap.get('91' + sp); break; }
          if (sp.startsWith('91') && sp.length === 12 && leadMap.has(sp.slice(2))) { lead = leadMap.get(sp.slice(2)); break; }
        }

        // Try AutoEngage User ID match
        if (!lead) {
          const aeLeadId = get(session, ['lead_id', 'user_id']);
          if (aeLeadId && leadMap.has('AE_USER_' + String(aeLeadId).trim())) {
            lead = leadMap.get('AE_USER_' + String(aeLeadId).trim());
          }
        }

        // Try Session ID match (e.g. session.session_id == lead.last_session_id)
        if (!lead) {
          const sessId = get(session, ['session_id', 'last_session_id', 'first_session_id', 'id']);
          if (sessId && leadMap.has('SESS_' + sessId.trim())) {
            lead = leadMap.get('SESS_' + sessId.trim());
          }
        }

        // Try Vehicle Registration match
        if (!lead) {
          const sReg = extractVehicleNumber({}, session);
          if (sReg && leadMap.has('REG_' + sReg.toUpperCase().replace(/[\s-]+/g, ''))) {
            lead = leadMap.get('REG_' + sReg.toUpperCase().replace(/[\s-]+/g, ''));
          }
        }

        // Try Vehicle ID match
        if (!lead) {
          const sVid = get(session, ['vehicle_id']);
          if (sVid && leadMap.has('VID_' + sVid.toLowerCase().trim())) {
            lead = leadMap.get('VID_' + sVid.toLowerCase().trim());
          }
        }

        // Try VIN match
        if (!lead) {
          const sVin = get(session, ['vin_number', 'vin', 'chassis_number']);
          if (sVin && leadMap.has('VIN_' + sVin.toLowerCase().trim())) {
            lead = leadMap.get('VIN_' + sVin.toLowerCase().trim());
          }
        }

        // Try Lead ID match
        if (!lead) {
          const sLeadId = get(session, ['post_sales_lead_id', 'lead_id', 'user_id']);
          if (sLeadId && leadMap.has('LEADID_' + sLeadId.trim())) {
            lead = leadMap.get('LEADID_' + sLeadId.trim());
          }
        }

        // Try Name match
        if (!lead) {
          const sName = get(session, ['person_name', 'name', 'customer_name', 'customer']);
          if (sName && sName.length > 3 && leadMap.has('NAME_' + sName.toLowerCase().trim().replace(/\s+/g, ''))) {
            lead = leadMap.get('NAME_' + sName.toLowerCase().trim().replace(/\s+/g, ''));
          }
        }

        let isMatched = false;
        if (lead) {
          isMatched = true;
        } else {
          lead = {}; // Empty fallback so get() doesn't throw
        }

        // Extract vehicle info
        const vehicleNumber = extractVehicleNumber(lead, session);
        // Requirement 2: Fetch vehicle model from leads file vehicle_model
        const vehicleModel = get(lead, ['vehicle_model', 'existing_vehicle_model', 'model', 'vehiclemodel', 'car_model', 'bike_model', 'vehicle_name']) || extractVehicleModel(lead, session);
        
        // Workshop / Showroom
        const showroom = extractShowroom(lead, session);
        
        // Service Plan
        const servicePlan = extractServicePlan(lead, session);

        // Requirement 4: Fetch Service Due Date (Records) from leads file
        const serviceDueDate = extractServiceDueDate(lead, session);

        // Lead Category
        const leadCategory = determineLeadCategory(session, lead);

        // Disposition based flags
        const disp = get(session, ['disposition', 'Disposition']).toLowerCase();
        const dispDetail = get(session, ['disposition_detail', 'Disposition Detail', 'disposition_details', 'updated_disposition']).toLowerCase();
        const isConverted = disp.includes('converted') || dispDetail.includes('converted');

        let serviceBooked = get(session, ['service_booked', 'Service Booked?']);
        if (!serviceBooked) {
          serviceBooked = isConverted ? 'Yes' : (disp ? 'No' : '');
        }

        // Dates
        let statedDate = get(session, ['confirmed_date', 'Confirmed/Stated Date (Call)', 'stated_date', 'scheduled_date']);
        const summary = get(session, ['summary', 'call_summary', 'conversation_summary', 'notes', 'remarks']);
        if (!statedDate && summary) {
          const dateMatch = summary.match(/(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}/i) ||
                            summary.match(/\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}/i);
          if (dateMatch) {
            statedDate = dateMatch[0];
          }
        }
        
        const callDateTime = get(session, ['start_time', 'start_date', 'call_start_time', 'created', 'created_at', 'Call Date/Time']);

        // Phone number to display
        const displayPhone = get(session, ['phone_number', 'phone', 'mobile', 'contact_number']) || 
                             get(lead, ['phone_number', 'phone', 'mobile', 'contact_number']) || 
                             (sPhones[0] || '');

        // Customer Name
        let name = get(lead, ['person_name', 'person_name1', 'customer_name', 'name', 'full_name', 'Name']) || 
                   get(session, ['person_name', 'Name']);
        if (!name) {
          const st = get(lead, ['search_term']) || get(session, ['search_term']);
          if (st && st.includes('-')) {
            const parts = st.split('-');
            if (parts.length >= 4) {
              name = parts[2].trim().split(' ').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
            }
          }
        }
        
        return {
          '_leadMatched': isMatched ? 'true' : 'false',
          // 'Debug Match': isMatched ? 'MATCHED' : 'NO MATCH',
          'Name': name,
          'Phone Number': displayPhone,
          'Campaign': get(session, ['campaign_name', 'campaign_model', 'campaign_id', 'Campaign']) || get(lead, ['campaign_name', 'campaign_id']),
          'Lead Category': leadCategory,
          'Service Booked?': serviceBooked,
          'Vehicle Number': vehicleNumber,
          'Vehicle Model': vehicleModel,
          'Showroom': showroom,
          'Service Plan': servicePlan,
          'Service Due Date (Records)': serviceDueDate,
          'Confirmed/Stated Date (Call)': statedDate,
          'Disposition': get(session, ['disposition', 'Disposition']),
          'Disposition Detail': get(session, ['disposition_detail', 'Disposition Detail', 'disposition_details', 'updated_disposition']),
          'Call Date': callDateTime ? new Date(callDateTime).toLocaleDateString() : '',
          'Call Summary': summary,
          'Updated Disposition': '',
          'AI Reason': '',
          '_session_history': get(session, ['session_history', 'history', 'transcript', 'conversation_history', 'Conversation History', 'conversation history', 'Transcript']) || '',
          '_session_status': get(session, ['session_status', 'status', 'call_status', 'Session Status']) || '',
          '_outcome': get(session, ['outcome', 'call_outcome', 'Call Outcome']) || '',
        };
      });

      /*
      setDebugInfo({
        leadKeys: leadRows[0] ? Object.keys(leadRows[0]) : [],
        sessionKeys: sessionRows[0] ? Object.keys(sessionRows[0]) : [],
        leadMapSize: leadMap.size,
        totalProcessed: processed.length,
        matchedCount: processed.filter(r => r['_leadMatched'] === 'true').length
      });
      */

      setOutputRows(processed);
      setShowResults(true);
      setPillStep(4);
      const swapNote = swapped ? ' (Lead and Session files were auto-detected and aligned)' : '';
      setStatusMsg(`Successfully merged and processed ${processed.length} rows${swapNote}.`);
      setStatusType('ok');
    } catch (err: any) {
      setStatusMsg(err.message || 'Failed to process files.');
      setStatusType('err');
    } finally {
      setProcessing(false);
    }
  }

  function exportToExcel() {
    if (!outputRows.length) return;
    const sanitizedRows = outputRows.map(r => {
      const row: Record<string, string> = {};
      REPORT_HEADERS.forEach(h => {
        row[h] = excelSafe(r[h]);
      });
      return row;
    });

    const ws = XLSX.utils.json_to_sheet(sanitizedRows, { header: REPORT_HEADERS });
    const range = XLSX.utils.decode_range(ws['!ref'] || 'A1:P1');
    for (let R = range.s.r + 1; R <= range.e.r; ++R) {
      const cellRef = XLSX.utils.encode_cell({ r: R, c: 1 });
      if (ws[cellRef]) {
        ws[cellRef].t = 's';
      }
    }

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Session Report');
    const filename = `Keerthi_Report_${new Date().toISOString().slice(0, 10)}.xlsx`;
    XLSX.writeFile(wb, filename);

    setStatusMsg(`Downloaded ${filename} successfully.`);
    setStatusType('ok');
  }

  async function copyData() {
    if (!outputRows.length) return;
    const tsv = [
      REPORT_HEADERS.join('\t'),
      ...outputRows.map(r => REPORT_HEADERS.map(k => String(r[k] ?? '').replace(/\t/g, ' ').replace(/\r?\n/g, ' ')).join('\t'))
    ].join('\n');

    try {
      await navigator.clipboard.writeText(tsv);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = tsv;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setStatusMsg(`Copied ${outputRows.length} rows to clipboard.`);
    setStatusType('ok');
  }

  function resetAll() {
    setRawFile1(null);
    setRawFile2(null);
    setFile1Status('Drag & drop or click to browse');
    setFile2Status('Drag & drop or click to browse');
    setHasFile1(false);
    setHasFile2(false);
    setOutputRows([]);
    setShowResults(false);
    setPillStep(0);
    setStatusMsg('');
    setStatusType('');
    setSearchQuery('');
    setSortKey(null);
    setSortDir(null);
    setCurrentPage(1);
    if (file1Ref.current) file1Ref.current.value = '';
    if (file2Ref.current) file2Ref.current.value = '';
  }

  function toggleSort(key: string) {
    if (sortKey === key) {
      if (sortDir === 'asc') setSortDir('desc');
      else if (sortDir === 'desc') {
        setSortKey(null);
        setSortDir(null);
      }
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  // Filter and Sort Data
  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) return outputRows;
    const q = searchQuery.toLowerCase().trim();
    return outputRows.filter(r => {
      return (
        String(r['Name'] || '').toLowerCase().includes(q) ||
        String(r['Phone Number'] || '').includes(q) ||
        String(r['Vehicle Number'] || '').toLowerCase().includes(q) ||
        String(r['Vehicle Model'] || '').toLowerCase().includes(q) ||
        String(r['Disposition'] || '').toLowerCase().includes(q) ||
        String(r['Disposition Detail'] || '').toLowerCase().includes(q) ||
        String(r['Lead Category'] || '').toLowerCase().includes(q) ||
        String(r['Showroom'] || '').toLowerCase().includes(q)
      );
    });
  }, [outputRows, searchQuery]);

  const sortedData = useMemo(() => {
    if (!sortKey || !sortDir) return filteredData;
    const dir = sortDir === 'asc' ? 1 : -1;
    return [...filteredData].sort((a, b) => {
      const va = String(a[sortKey!] || '');
      const vb = String(b[sortKey!] || '');
      return va < vb ? -dir : (va > vb ? dir : 0);
    });
  }, [filteredData, sortKey, sortDir]);

  const previewData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  // Statistics
  const totalLeads = outputRows.length;
  const bookedCount = outputRows.filter(r => (r['Service Booked?'] || '').toLowerCase() === 'yes').length;
  const hotCount = outputRows.filter(r => (r['Lead Category'] || '').toLowerCase().includes('hot')).length;
  const warmCount = outputRows.filter(r => (r['Lead Category'] || '').toLowerCase().includes('warm')).length;
  const vehicleCount = outputRows.filter(r => r['Vehicle Number'] && String(r['Vehicle Number']).trim() !== '').length;
  const summaryCount = outputRows.filter(r => r['Call Summary'] && String(r['Call Summary']).trim() !== '').length;

  return (
    <div className="sub-page">
      <ProcessingOverlay show={processing} message="Processing batch..." />
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Keerthi Report Generator</h1>
              <div className="header-sub">AutoEngage → Standardized 15-Column Report</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        {/* Step 1 Workflow Panel */}
        <section className={styles['workflow-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 1</div>
              <div className={styles['section-title']}>Prepare the report batch</div>
            </div>
            <div className={styles['section-note']}>
              Drop the Lead File and Session File, verify column mapping, then process.
            </div>
          </div>

          {/* Upload Grid */}
          <div className={styles['upload-grid']}>
            {/* File 1: Audience & Leads */}
            <div
              className={`${styles['drop-zone']} ${dragOver1 ? styles['drag-over'] : ''} ${hasFile1 ? styles['has-file'] : ''}`}
              onClick={() => file1Ref.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver1(true); }}
              onDragLeave={() => setDragOver1(false)}
              onDrop={handleDrop1}
            >
              <div className={`${styles['dz-icon']} ${styles.file1}`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className={styles['dz-label']}>File 1 — Audience & Leads</div>
              <div className={styles['dz-sublabel']}>AutoEngage → Audience & Leads export (.xlsx, .csv)</div>
              <div className={styles['dz-cols']}>
                person_name · phone_number · vehicle_id · vehicle_model<br />
                search_term · reg_number · next_service_due · workshop_name
              </div>
              <div className={`${styles['dz-status']} ${hasFile1 ? styles.ok : ''}`}>{file1Status}</div>
              <input ref={file1Ref} type="file" accept=".csv,.xlsx,.xls" onChange={handleFile1Change} style={{ display: 'none' }} />
            </div>

            {/* File 2: Sessions */}
            <div
              className={`${styles['drop-zone']} ${dragOver2 ? styles['drag-over'] : ''} ${hasFile2 ? styles['has-file'] : ''}`}
              onClick={() => file2Ref.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver2(true); }}
              onDragLeave={() => setDragOver2(false)}
              onDrop={handleDrop2}
            >
              <div className={`${styles['dz-icon']} ${styles.file2}`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <path d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
              </div>
              <div className={styles['dz-label']}>File 2 — Sessions</div>
              <div className={styles['dz-sublabel']}>AutoEngage → Call Sessions export (.xlsx, .csv)</div>
              <div className={styles['dz-cols']}>
                phone_number · created · start_time · summary<br />
                disposition · disposition_detail
              </div>
              <div className={`${styles['dz-status']} ${hasFile2 ? styles.ok : ''}`}>{file2Status}</div>
              <input ref={file2Ref} type="file" accept=".csv,.xlsx,.xls" onChange={handleFile2Change} style={{ display: 'none' }} />
            </div>
          </div>

          {/* Pill Strip */}
          <div className={styles['pill-strip']}>
            <div className={`${styles['step-pill']} ${pillStep >= 1 ? styles.active : ''}`}>
              <span className={styles.num}>1</span> Leads uploaded
            </div>
            <div className={`${styles['step-pill']} ${pillStep >= 2 ? styles.active : ''}`}>
              <span className={styles.num}>2</span> Sessions uploaded
            </div>
            <div className={`${styles['step-pill']} ${pillStep >= 3 ? styles.active : ''}`}>
              <span className={styles.num}>3</span> Ready to process
            </div>
            <div className={`${styles['step-pill']} ${pillStep >= 4 ? styles.active : ''}`}>
              <span className={styles.num}>4</span> Results ready
            </div>
          </div>

          {/* Action Bar */}
          <div className={styles['action-bar']}>
            <button
              className={`${styles.btn} ${styles['btn-primary']}`}
              onClick={processFiles}
              disabled={!rawFile1 || !rawFile2 || processing}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
              </svg>
              Process Both Files
            </button>

            <div className={styles['control-group']}>
              <span className={styles['control-label']}>Dealership</span>
              <div className={styles['select-wrapper']}>
                <select
                  value={dealerKey}
                  onChange={e => setDealerKey(e.target.value)}
                  style={{
                    padding: '0.5rem 1.8rem 0.5rem 0.75rem',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'var(--bg)',
                    color: 'var(--text)',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    appearance: 'none',
                    fontFamily: 'var(--body)'
                  }}
                >
                  <option value="keerthi_triumph">Keerthi Triumph (15-Column Report)</option>
                </select>
              </div>
            </div>

            {showResults && (
              <>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => validateDispositionsWithLLM()} disabled={aiProgress.state.show && !aiProgress.state.completed && !aiProgress.state.aborted}>
                  Validate with AI
                </button>
                <button className={`${styles.btn} ${styles['btn-success']}`} onClick={exportToExcel}>
                  Export Excel
                </button>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={copyData}>
                  Copy All Data
                </button>
                <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={resetAll}>
                  Reset
                </button>
              </>
            )}

            <span className={`${styles['status-msg']} ${statusType ? styles[statusType] : ''}`}>
              {statusMsg}
            </span>
          </div>
        </section>

        {/* Step 2 Results Panel */}
        <section className={styles['results-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Step 2</div>
              <div className={styles['section-title']}>Review and hand off</div>
            </div>
            <div className={styles['section-note']}>
              After processing, use the stats and preview tables for spot checks before copying or exporting.
            </div>
          </div>

          {showResults ? (
            <>
              {/* 
              {debugInfo && (
                <div style={{ background: 'var(--card-bg)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '1rem', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                  <b>Debug Info:</b><br/>
                  Matched Leads: {debugInfo.matchedCount} / {debugInfo.totalProcessed}<br/>
                  Lead Map Size: {debugInfo.leadMapSize}<br/>
                  Lead Keys: {JSON.stringify(debugInfo.leadKeys)}<br/>
                  Session Keys: {JSON.stringify(debugInfo.sessionKeys)}
                </div>
              )} 
              */}

              {/* AI Progress Bar */}
              {aiProgress.state.show && (
                <div style={{ marginBottom: '1.5rem' }}>
                  <BatchProgressBar
                    state={aiProgress.state}
                    onDismiss={() => aiProgress.reset()}
                    onRetry={() => validateDispositionsWithLLM(true)}
                    onCancel={cancelAiValidation}
                    retryLabel="↻ Re-run AI"
                  />
                </div>
              )}

              {/* Stats Bar */}
              <div className={styles['stats-bar']} style={{ display: 'flex' }}>
                <div className={styles['stat-card']}>
                  <div className={styles['stat-label']}>Total Leads</div>
                  <div className={`${styles['stat-val']} ${styles.blue}`}>{totalLeads}</div>
                </div>
                <div className={styles['stat-card']}>
                  <div className={styles['stat-label']}>Service Booked</div>
                  <div className={`${styles['stat-val']} ${styles.green}`}>{bookedCount}</div>
                </div>
                <div className={styles['stat-card']}>
                  <div className={styles['stat-label']}>Hot Leads</div>
                  <div className={`${styles['stat-val']} ${styles.red}`}>{hotCount}</div>
                </div>
                <div className={styles['stat-card']}>
                  <div className={styles['stat-label']}>Warm Leads</div>
                  <div className={`${styles['stat-val']} ${styles.amber}`}>{warmCount}</div>
                </div>
                <div className={styles['stat-card']}>
                  <div className={styles['stat-label']}>Vehicles Identified</div>
                  <div className={`${styles['stat-val']} ${styles.purple}`}>{vehicleCount}</div>
                </div>
                <div className={styles['stat-card']}>
                  <div className={styles['stat-label']}>With Summary</div>
                  <div className={`${styles['stat-val']} ${styles.gray}`}>{summaryCount}</div>
                </div>
              </div>

              {/* Table Wrapper */}
              <div className={styles['table-wrapper']} style={{ display: 'block' }}>
                <div className={styles['table-header']} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <div className={styles['table-title']}>Output Preview</div>
                    <div className={styles['table-caption']}>
                      Showing {sortedData.length > 0 ? (currentPage - 1) * pageSize + 1 : 0} - {Math.min(sortedData.length, currentPage * pageSize)} of {sortedData.length} rows
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <select 
                      className={styles.input} 
                      value={pageSize} 
                      onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
                      style={{ padding: '0.4rem', width: 'auto' }}
                    >
                      <option value={50}>50 rows</option>
                      <option value={100}>100 rows</option>
                      <option value={200}>200 rows</option>
                      <option value={500}>500 rows</option>
                      <option value={1000}>1000 rows</option>
                    </select>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button 
                        className={`${styles.btn} ${styles['btn-secondary']}`}
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        style={{ padding: '0.4rem 0.75rem' }}
                      >
                        Prev
                      </button>
                      <button 
                        className={`${styles.btn} ${styles['btn-secondary']}`}
                        onClick={() => setCurrentPage(p => Math.min(Math.ceil(sortedData.length / pageSize), p + 1))}
                        disabled={currentPage >= Math.ceil(sortedData.length / pageSize) || sortedData.length === 0}
                        style={{ padding: '0.4rem 0.75rem' }}
                      >
                        Next
                      </button>
                    </div>
                    <input
                      type="text"
                      className={styles.input}
                      placeholder="Search in preview..."
                      value={searchQuery}
                      onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }}
                    />
                  </div>
                </div>

                <div className={styles['table-scroll']}>
                  <table>
                    <thead>
                      <tr>
                        {REPORT_HEADERS.map(h => {
                          const isCurrentSort = sortKey === h;
                          const sortArrow = isCurrentSort ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';
                          return (
                            <th
                              key={h}
                              className={styles['th-sortable']}
                              onClick={() => toggleSort(h)}
                              title={`Click to sort by ${h}`}
                            >
                              {h}{sortArrow}
                            </th>
                          );
                        })}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.map((r, i) => (
                        <tr key={i}>
                          {REPORT_HEADERS.map(h => {
                            const val = r[h] ?? '';
                            if (h === 'Phone Number') {
                              return (
                                <td key={h} className={styles['cell-phone']}>
                                  {val || '—'}
                                </td>
                              );
                            }
                            if (h === 'Vehicle Number') {
                              return (
                                <td key={h}>
                                  {val ? <span className={styles['badge-reg']}>{val}</span> : '—'}
                                </td>
                              );
                            }
                            if (h === 'Lead Category') {
                              const lower = val.toLowerCase();
                              let badgeClass = styles['badge-cold'];
                              if (lower.includes('converted')) badgeClass = styles['badge-converted'];
                              else if (lower.includes('hot')) badgeClass = styles['badge-hot'];
                              else if (lower.includes('warm')) badgeClass = styles['badge-warm'];
                              return (
                                <td key={h}>
                                  {val ? <span className={`${styles['badge-pill']} ${badgeClass}`}>{val}</span> : '—'}
                                </td>
                              );
                            }
                            if (h === 'Service Booked?') {
                              const isYes = val.toLowerCase() === 'yes';
                              const isNo = val.toLowerCase() === 'no';
                              return (
                                <td
                                  key={h}
                                  className={isYes ? styles['cell-connected'] : isNo ? styles['cell-not-connected'] : ''}
                                >
                                  {val || '—'}
                                </td>
                              );
                            }
                            return (
                              <td key={h} title={val}>
                                {val || '—'}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontStyle: 'italic' }}>
              No processed batch yet. Upload both exports in Step 1 and click &ldquo;Process Both Files&rdquo;.
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
