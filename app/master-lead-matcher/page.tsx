'use client';
import { useState, useRef, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import { readFileAsArrayBuffer, excelSafe, validateFileSync, cellToString } from '@/lib/data-pipeline';
import * as XLSX from 'xlsx';
import {
  MatchKeyType,
  MergeMode,
  MatchedRecord,
  MergeStats,
  DealershipPreset,
  DEALERSHIP_PRESETS,
  REG_CANDIDATES,
  PHONE_CANDIDATES,
  VIN_CANDIDATES,
  DEFAULT_MASTER_COLUMNS_TO_APPEND,
  detectColumnCandidate,
  executeMerge,
} from './matcher-utils';
import styles from './master-lead-matcher.module.css';

interface ParsedFile {
  file: File;
  headers: string[];
  rows: Record<string, string>[];
  detectedRegCol: string;
  detectedPhoneCol: string;
  detectedVinCol: string;
}

export default function MasterLeadMatcherPage() {
  const log = (...args: unknown[]) => console.log('[MasterLeadMatcher]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  // Dealership Preset
  const [dealershipKey, setDealershipKey] = useState<string>('kt_psf');
  const currentPreset = DEALERSHIP_PRESETS[dealershipKey] || DEALERSHIP_PRESETS.kt_psf;

  function handleDealershipChange(newKey: string) {
    setDealershipKey(newKey);
    const preset = DEALERSHIP_PRESETS[newKey];
    if (!preset) return;

    setMatchKeyType(preset.defaultMatchKey);

    if (clientFileData) {
      if (preset.expectedRegCol && clientFileData.headers.includes(preset.expectedRegCol)) {
        setClientMatchCol(preset.expectedRegCol);
      } else if (preset.defaultMatchKey === 'reg_number' && clientFileData.detectedRegCol) {
        setClientMatchCol(clientFileData.detectedRegCol);
      } else if (preset.expectedPhoneCol && clientFileData.headers.includes(preset.expectedPhoneCol)) {
        setClientMatchCol(preset.expectedPhoneCol);
      }

      if (preset.expectedPhoneCol && clientFileData.headers.includes(preset.expectedPhoneCol)) {
        setClientPhoneFallbackCol(preset.expectedPhoneCol);
      }
    }

    if (masterFileData) {
      if (preset.defaultMatchKey === 'reg_number' && masterFileData.detectedRegCol) {
        setMasterMatchCol(masterFileData.detectedRegCol);
      } else if (preset.defaultMatchKey === 'phone_number' && masterFileData.detectedPhoneCol) {
        setMasterMatchCol(masterFileData.detectedPhoneCol);
      }
    }
  }

  // File states
  const [clientFileData, setClientFileData] = useState<ParsedFile | null>(null);
  const [masterFileData, setMasterFileData] = useState<ParsedFile | null>(null);
  const [file1DragOver, setFile1DragOver] = useState(false);
  const [file2DragOver, setFile2DragOver] = useState(false);

  // Match configuration
  const [matchKeyType, setMatchKeyType] = useState<MatchKeyType>('reg_number');
  const [clientMatchCol, setClientMatchCol] = useState<string>('');
  const [masterMatchCol, setMasterMatchCol] = useState<string>('');
  const [clientPhoneFallbackCol, setClientPhoneFallbackCol] = useState<string>('');
  const [masterPhoneFallbackCol, setMasterPhoneFallbackCol] = useState<string>('');

  // Column selection to append
  const [selectedMasterCols, setSelectedMasterCols] = useState<Set<string>>(new Set());

  // Merge mode
  const [mergeMode, setMergeMode] = useState<MergeMode>('enriched_client');

  // Processing & Results
  const [processing, setProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'ok' | 'err' | 'warn' | ''>('');
  const [outputRows, setOutputRows] = useState<MatchedRecord[]>([]);
  const [outputHeaders, setOutputHeaders] = useState<string[]>([]);
  const [stats, setStats] = useState<MergeStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showResults, setShowResults] = useState(false);

  // Refs for file inputs
  const clientFileInputRef = useRef<HTMLInputElement>(null);
  const masterFileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);

  if (!isAuthenticated && !loading) return null;

  function parseWorkbook(ab: ArrayBuffer, file: File): ParsedFile {
    const wb = XLSX.read(ab, { type: 'array', raw: true, cellDates: true });
    const sheetName = wb.SheetNames[0];
    const ws = wb.Sheets[sheetName];
    const rawData = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];

    if (rawData.length < 2) {
      throw new Error(`File ${file.name} must have at least 1 header row and 1 data row.`);
    }

    // Header row is row 0 (or first row with strings)
    const headerRowIndex = 0;
    const rawHeaders = (rawData[headerRowIndex] as unknown[]).map(h => String(h || '').trim());
    
    // Ensure all header names are unique and non-empty
    const seenHeaders = new Map<string, number>();
    const headers: string[] = [];
    const colIndices: number[] = [];

    rawHeaders.forEach((rawH, colIdx) => {
      const h = rawH.trim();
      if (!h) return;
      const count = seenHeaders.get(h) || 0;
      seenHeaders.set(h, count + 1);
      const uniqueName = count === 0 ? h : `${h} (${count + 1})`;
      headers.push(uniqueName);
      colIndices.push(colIdx);
    });

    const rows: Record<string, string>[] = [];
    for (let i = headerRowIndex + 1; i < rawData.length; i++) {
      const rowArr = rawData[i] as unknown[];
      if (!rowArr || !rowArr.some(c => c != null && String(c).trim() !== '')) continue;

      const rowObj: Record<string, string> = {};
      headers.forEach((h, idx) => {
        const colIdx = colIndices[idx];
        rowObj[h] = cellToString(rowArr[colIdx]);
      });
      rows.push(rowObj);
    }

    const detectedRegCol = detectColumnCandidate(headers, REG_CANDIDATES);
    const detectedPhoneCol = detectColumnCandidate(headers, PHONE_CANDIDATES);
    const detectedVinCol = detectColumnCandidate(headers, VIN_CANDIDATES);

    return {
      file,
      headers,
      rows,
      detectedRegCol,
      detectedPhoneCol,
      detectedVinCol,
    };
  }

  async function handleClientFileUpload(file: File) {
    try {
      validateFileSync(file);
      setProcessing(true);
      const ab = await readFileAsArrayBuffer(file);
      const parsed = parseWorkbook(ab, file);
      setClientFileData(parsed);

      const preset = DEALERSHIP_PRESETS[dealershipKey] || DEALERSHIP_PRESETS.kt_psf;
      if (preset.expectedRegCol && parsed.headers.includes(preset.expectedRegCol)) {
        setClientMatchCol(preset.expectedRegCol);
      } else if (matchKeyType === 'reg_number' && parsed.detectedRegCol) {
        setClientMatchCol(parsed.detectedRegCol);
      } else if (matchKeyType === 'phone_number' && parsed.detectedPhoneCol) {
        setClientMatchCol(parsed.detectedPhoneCol);
      } else if (matchKeyType === 'vin_number' && parsed.detectedVinCol) {
        setClientMatchCol(parsed.detectedVinCol);
      } else if (parsed.headers.length > 0) {
        setClientMatchCol(parsed.detectedRegCol || parsed.detectedPhoneCol || parsed.headers[0]);
      }

      if (preset.expectedPhoneCol && parsed.headers.includes(preset.expectedPhoneCol)) {
        setClientPhoneFallbackCol(preset.expectedPhoneCol);
      } else if (parsed.detectedPhoneCol) {
        setClientPhoneFallbackCol(parsed.detectedPhoneCol);
      }

      setStatusMsg(`Loaded Client Lead File: ${parsed.rows.length} rows, ${parsed.headers.length} columns.`);
      setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg((err as Error).message || 'Failed to parse Client Lead File.');
      setStatusType('err');
    } finally {
      setProcessing(false);
    }
  }

  async function handleMasterFileUpload(file: File) {
    try {
      validateFileSync(file);
      setProcessing(true);
      const ab = await readFileAsArrayBuffer(file);
      const parsed = parseWorkbook(ab, file);
      setMasterFileData(parsed);

      // Auto-set master match column based on current matchKeyType
      if (matchKeyType === 'reg_number' && parsed.detectedRegCol) {
        setMasterMatchCol(parsed.detectedRegCol);
      } else if (matchKeyType === 'phone_number' && parsed.detectedPhoneCol) {
        setMasterMatchCol(parsed.detectedPhoneCol);
      } else if (matchKeyType === 'vin_number' && parsed.detectedVinCol) {
        setMasterMatchCol(parsed.detectedVinCol);
      } else if (parsed.headers.length > 0) {
        setMasterMatchCol(parsed.detectedRegCol || parsed.detectedPhoneCol || parsed.headers[0]);
      }

      if (parsed.detectedPhoneCol) {
        setMasterPhoneFallbackCol(parsed.detectedPhoneCol);
      }

      // Auto-select common master columns to append
      const defaultCols = new Set<string>();
      parsed.headers.forEach(h => {
        const norm = h.toLowerCase();
        const matchesDefault = DEFAULT_MASTER_COLUMNS_TO_APPEND.some(
          d => d.toLowerCase() === norm || norm.includes(d.toLowerCase())
        );
        if (matchesDefault) {
          defaultCols.add(h);
        }
      });
      setSelectedMasterCols(defaultCols);

      setStatusMsg(`Loaded Master Sheet: ${parsed.rows.length} rows, ${parsed.headers.length} columns.`);
      setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg((err as Error).message || 'Failed to parse Master Sheet.');
      setStatusType('err');
    } finally {
      setProcessing(false);
    }
  }

  // Update match columns whenever matchKeyType changes
  useEffect(() => {
    if (matchKeyType === 'reg_number') {
      if (clientFileData?.detectedRegCol) setClientMatchCol(clientFileData.detectedRegCol);
      if (masterFileData?.detectedRegCol) setMasterMatchCol(masterFileData.detectedRegCol);
    } else if (matchKeyType === 'phone_number') {
      if (clientFileData?.detectedPhoneCol) setClientMatchCol(clientFileData.detectedPhoneCol);
      if (masterFileData?.detectedPhoneCol) setMasterMatchCol(masterFileData.detectedPhoneCol);
    } else if (matchKeyType === 'vin_number') {
      if (clientFileData?.detectedVinCol) setClientMatchCol(clientFileData.detectedVinCol);
      if (masterFileData?.detectedVinCol) setMasterMatchCol(masterFileData.detectedVinCol);
    } else if (matchKeyType === 'smart_fallback') {
      if (clientFileData?.detectedRegCol) setClientMatchCol(clientFileData.detectedRegCol);
      if (masterFileData?.detectedRegCol) setMasterMatchCol(masterFileData.detectedRegCol);
      if (clientFileData?.detectedPhoneCol) setClientPhoneFallbackCol(clientFileData.detectedPhoneCol);
      if (masterFileData?.detectedPhoneCol) setMasterPhoneFallbackCol(masterFileData.detectedPhoneCol);
    }
  }, [matchKeyType, clientFileData, masterFileData]);

  function handleExecuteMerge() {
    if (!clientFileData || !masterFileData) {
      setStatusMsg('Please upload both Client Lead File and Master Sheet before merging.');
      setStatusType('err');
      return;
    }

    if (!clientMatchCol || !masterMatchCol) {
      setStatusMsg('Please select the matching key column for both files.');
      setStatusType('err');
      return;
    }

    setProcessing(true);
    try {
      const result = executeMerge({
        clientRows: clientFileData.rows,
        clientHeaders: clientFileData.headers,
        masterRows: masterFileData.rows,
        masterHeaders: masterFileData.headers,
        matchKeyType,
        clientMatchCol,
        masterMatchCol,
        clientPhoneColFallback: clientPhoneFallbackCol,
        masterPhoneColFallback: masterPhoneFallbackCol,
        selectedMasterColsToAppend: Array.from(selectedMasterCols),
        mergeMode,
      });

      setOutputRows(result.outputRows);
      setOutputHeaders(result.outputHeaders);
      setStats(result.stats);
      setShowResults(true);

      setStatusMsg(
        `Successfully merged: ${result.stats.matchedCount} / ${result.stats.totalClientRows} matched (${result.stats.matchRatePercent}%).`
      );
      setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg((err as Error).message || 'Error occurred while merging datasets.');
      setStatusType('err');
    } finally {
      setProcessing(false);
    }
  }

  function handleToggleMasterCol(col: string) {
    setSelectedMasterCols(prev => {
      const next = new Set(prev);
      if (next.has(col)) next.delete(col);
      else next.add(col);
      return next;
    });
  }

  function handleSelectAllMasterCols() {
    if (!masterFileData) return;
    setSelectedMasterCols(new Set(masterFileData.headers));
  }

  function handleSelectDefaultMasterCols() {
    if (!masterFileData) return;
    const defaultCols = new Set<string>();
    masterFileData.headers.forEach(h => {
      const norm = h.toLowerCase();
      const matchesDefault = DEFAULT_MASTER_COLUMNS_TO_APPEND.some(
        d => d.toLowerCase() === norm || norm.includes(d.toLowerCase())
      );
      if (matchesDefault) {
        defaultCols.add(h);
      }
    });
    setSelectedMasterCols(defaultCols);
  }

  function handleClearMasterCols() {
    setSelectedMasterCols(new Set());
  }

  function exportToExcel(dataRows: MatchedRecord[], filename: string) {
    if (!dataRows.length) {
      setStatusMsg('No rows available to export.');
      setStatusType('warn');
      return;
    }

    // Build sanitised rows
    const sanitizedRows = dataRows.map(r => {
      const row: Record<string, string> = {};
      outputHeaders.forEach(h => {
        row[h] = excelSafe(r[h]);
      });
      return row;
    });

    const ws = XLSX.utils.json_to_sheet(sanitizedRows, { header: outputHeaders });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Client Delivery Report');
    XLSX.writeFile(wb, filename);

    setStatusMsg(`Downloaded ${filename} successfully.`);
    setStatusType('ok');
  }

  function handleDownloadFullReport() {
    const clientName = clientFileData?.file.name.replace(/\.[^/.]+$/, '') || 'Client';
    const timestamp = new Date().toISOString().slice(0, 10);
    exportToExcel(outputRows, `${clientName}_Merged_Report_${timestamp}.xlsx`);
  }

  function handleDownloadMatchedOnly() {
    const matchedOnly = outputRows.filter(r => r._matchStatus === 'matched');
    const clientName = clientFileData?.file.name.replace(/\.[^/.]+$/, '') || 'Client';
    const timestamp = new Date().toISOString().slice(0, 10);
    exportToExcel(matchedOnly, `${clientName}_Matched_Leads_${timestamp}.xlsx`);
  }

  function handleDownloadUnmatchedClient() {
    const unmatched = outputRows.filter(r => r._matchStatus === 'unmatched_client');
    const clientName = clientFileData?.file.name.replace(/\.[^/.]+$/, '') || 'Client';
    const timestamp = new Date().toISOString().slice(0, 10);
    exportToExcel(unmatched, `${clientName}_Unmatched_Leads_${timestamp}.xlsx`);
  }

  function handleReset() {
    setClientFileData(null);
    setMasterFileData(null);
    setOutputRows([]);
    setOutputHeaders([]);
    setStats(null);
    setShowResults(false);
    setStatusMsg('');
    setStatusType('');
    if (clientFileInputRef.current) clientFileInputRef.current.value = '';
    if (masterFileInputRef.current) masterFileInputRef.current.value = '';
  }

  // Filtered rows for live preview table
  const filteredRows = useMemo(() => {
    if (!searchQuery.trim()) return outputRows;
    const q = searchQuery.toLowerCase();
    return outputRows.filter(row =>
      outputHeaders.some(h => String(row[h] || '').toLowerCase().includes(q))
    );
  }, [outputRows, outputHeaders, searchQuery]);

  const previewDisplayRows = useMemo(() => filteredRows.slice(0, 100), [filteredRows]);

  return (
    <div className="sub-page">
      <ProcessingOverlay show={processing} message="Processing datasets..." />
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Master Lead Matcher</h1>
              <div className="header-sub">Client Lead File + Zoho Master Sheet Merger</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        {/* Upload & Setup Panel */}
        <section className={styles.panel}>
          <div className={styles.sectionHead}>
            <div>
              <div className={styles.eyebrow}>Dataset Merger</div>
              <h2 className={styles.sectionTitle}>Master Lead Matcher</h2>
              <p className={styles.sectionNote}>
                Club raw Client Lead Files (with all full client columns) with processed Master Sheets (from Pre-Sales or Post-Sales Sync) using Registration Number or Phone Number.
              </p>
            </div>
            {clientFileData && masterFileData && (
              <button className={`${styles.btn} ${styles.btnOutline}`} onClick={handleReset}>
                Reset Files
              </button>
            )}
          </div>

          {/* Dealership Selector Bar */}
          <div className={styles.dealerBar}>
            <div className={styles.dealerLeft}>
              <span className={styles.dealerLabel}>Dealership:</span>
              <div className={styles.selectWrapper}>
                <select
                  className={styles.dealerSelect}
                  value={dealershipKey}
                  onChange={e => handleDealershipChange(e.target.value)}
                >
                  {Object.values(DEALERSHIP_PRESETS).map(p => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <span className={styles.workflowBadge}>{currentPreset.workflow}</span>
            </div>
            <div className={styles.dealerInfo}>
              <span>Default Key: <strong>{currentPreset.defaultMatchKey === 'reg_number' ? 'Registration No.' : 'Mobile / Phone'}</strong></span>
              {currentPreset.expectedRegCol && <span>• Expected Reg: <code style={{ fontFamily: 'var(--mono)', color: 'var(--accent-p)' }}>{currentPreset.expectedRegCol}</code></span>}
              {currentPreset.expectedPhoneCol && <span>• Expected Phone: <code style={{ fontFamily: 'var(--mono)', color: 'var(--accent-p)' }}>{currentPreset.expectedPhoneCol}</code></span>}
            </div>
          </div>

          {/* Dual Upload Grid */}
          <div className={styles.uploadGrid}>
            {/* Dropzone 1: Client Lead File */}
            <div className={styles.uploadCard}>
              <div className={styles.cardHeader}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>1. Client Lead File</span>
                <span className={styles.cardBadge}>Raw Client Data</span>
              </div>
              <input
                ref={clientFileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                style={{ display: 'none' }}
                onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) handleClientFileUpload(f);
                }}
              />
              <div
                className={`${styles.dropZone} ${file1DragOver ? styles.dragOver : ''} ${
                  clientFileData ? styles.hasFile : ''
                }`}
                onDragOver={e => {
                  e.preventDefault();
                  setFile1DragOver(true);
                }}
                onDragLeave={() => setFile1DragOver(false)}
                onDrop={e => {
                  e.preventDefault();
                  setFile1DragOver(false);
                  const f = e.dataTransfer.files?.[0];
                  if (f) handleClientFileUpload(f);
                }}
                onClick={() => clientFileInputRef.current?.click()}
              >
                <svg className={styles.dzIcon} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <div className={styles.dzLabel}>
                  {clientFileData ? clientFileData.file.name : 'Upload Client Lead File'}
                </div>
                <div className={styles.dzSublabel}>
                  {clientFileData ? `${clientFileData.rows.length} rows loaded` : 'Drag & drop Excel (.xlsx, .xls) or CSV'}
                </div>
              </div>

              {clientFileData && (
                <div className={styles.fileSummary}>
                  <div className={styles.fileSummaryRow}>
                    <span className={styles.fileSummaryName}>{clientFileData.file.name}</span>
                    <span className={styles.fileSummaryStats}>{clientFileData.rows.length} rows • {clientFileData.headers.length} cols</span>
                  </div>
                  <div className={styles.detectedPills}>
                    {clientFileData.detectedRegCol && (
                      <span className={`${styles.pill} ${styles.pillHighlight}`}>
                        Reg: {clientFileData.detectedRegCol}
                      </span>
                    )}
                    {clientFileData.detectedPhoneCol && (
                      <span className={`${styles.pill} ${styles.pillHighlight}`}>
                        Phone: {clientFileData.detectedPhoneCol}
                      </span>
                    )}
                    {clientFileData.detectedVinCol && (
                      <span className={styles.pill}>VIN: {clientFileData.detectedVinCol}</span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Dropzone 2: Master Sheet */}
            <div className={styles.uploadCard}>
              <div className={styles.cardHeader}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>2. Processed Master Sheet</span>
                <span className={styles.cardBadge}>Disposition Sync Output</span>
              </div>
              <input
                ref={masterFileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv"
                style={{ display: 'none' }}
                onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) handleMasterFileUpload(f);
                }}
              />
              <div
                className={`${styles.dropZone} ${file2DragOver ? styles.dragOver : ''} ${
                  masterFileData ? styles.hasFile : ''
                }`}
                onDragOver={e => {
                  e.preventDefault();
                  setFile2DragOver(true);
                }}
                onDragLeave={() => setFile2DragOver(false)}
                onDrop={e => {
                  e.preventDefault();
                  setFile2DragOver(false);
                  const f = e.dataTransfer.files?.[0];
                  if (f) handleMasterFileUpload(f);
                }}
                onClick={() => masterFileInputRef.current?.click()}
              >
                <svg className={styles.dzIcon} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div className={styles.dzLabel}>
                  {masterFileData ? masterFileData.file.name : 'Upload Master Sheet'}
                </div>
                <div className={styles.dzSublabel}>
                  {masterFileData ? `${masterFileData.rows.length} rows loaded` : 'Pre-Sales / Post-Sales Sync export (.xlsx)'}
                </div>
              </div>

              {masterFileData && (
                <div className={styles.fileSummary}>
                  <div className={styles.fileSummaryRow}>
                    <span className={styles.fileSummaryName}>{masterFileData.file.name}</span>
                    <span className={styles.fileSummaryStats}>{masterFileData.rows.length} rows • {masterFileData.headers.length} cols</span>
                  </div>
                  <div className={styles.detectedPills}>
                    {masterFileData.detectedRegCol && (
                      <span className={`${styles.pill} ${styles.pillHighlight}`}>
                        Reg: {masterFileData.detectedRegCol}
                      </span>
                    )}
                    {masterFileData.detectedPhoneCol && (
                      <span className={`${styles.pill} ${styles.pillHighlight}`}>
                        Phone: {masterFileData.detectedPhoneCol}
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Configuration Grid */}
          {clientFileData && masterFileData && (
            <div className={styles.configGrid}>
              {/* Match Key Selection Card */}
              <div className={styles.configCard}>
                <div className={styles.configCardTitle}>
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  Match Key & Identifier
                </div>

                <div className={styles.radioGroup}>
                  <label className={`${styles.radioOption} ${matchKeyType === 'reg_number' ? styles.selected : ''}`}>
                    <input
                      type="radio"
                      name="matchKeyType"
                      checked={matchKeyType === 'reg_number'}
                      onChange={() => setMatchKeyType('reg_number')}
                    />
                    <div className={styles.radioText}>
                      <span className={styles.radioTitle}>Vehicle Registration Number</span>
                      <span className={styles.radioDesc}>Auto-normalizes spaces, dashes, and casing (e.g. KA01AB1234)</span>
                    </div>
                  </label>

                  <label className={`${styles.radioOption} ${matchKeyType === 'phone_number' ? styles.selected : ''}`}>
                    <input
                      type="radio"
                      name="matchKeyType"
                      checked={matchKeyType === 'phone_number'}
                      onChange={() => setMatchKeyType('phone_number')}
                    />
                    <div className={styles.radioText}>
                      <span className={styles.radioTitle}>Phone / Mobile Number</span>
                      <span className={styles.radioDesc}>Strips country code +91 and extracts clean 10-digit number</span>
                    </div>
                  </label>

                  <label className={`${styles.radioOption} ${matchKeyType === 'smart_fallback' ? styles.selected : ''}`}>
                    <input
                      type="radio"
                      name="matchKeyType"
                      checked={matchKeyType === 'smart_fallback'}
                      onChange={() => setMatchKeyType('smart_fallback')}
                    />
                    <div className={styles.radioText}>
                      <span className={styles.radioTitle}>Smart Multi-Key Match</span>
                      <span className={styles.radioDesc}>Match by Registration Number first; if blank/unmatched, match by Phone</span>
                    </div>
                  </label>

                  <label className={`${styles.radioOption} ${matchKeyType === 'vin_number' ? styles.selected : ''}`}>
                    <input
                      type="radio"
                      name="matchKeyType"
                      checked={matchKeyType === 'vin_number'}
                      onChange={() => setMatchKeyType('vin_number')}
                    />
                    <div className={styles.radioText}>
                      <span className={styles.radioTitle}>Chassis / VIN Number</span>
                      <span className={styles.radioDesc}>Match by vehicle VIN / Chassis number</span>
                    </div>
                  </label>

                  <label className={`${styles.radioOption} ${matchKeyType === 'custom' ? styles.selected : ''}`}>
                    <input
                      type="radio"
                      name="matchKeyType"
                      checked={matchKeyType === 'custom'}
                      onChange={() => setMatchKeyType('custom')}
                    />
                    <div className={styles.radioText}>
                      <span className={styles.radioTitle}>Custom Columns</span>
                      <span className={styles.radioDesc}>Manually pick matching columns from both files</span>
                    </div>
                  </label>
                </div>

                {/* Column Dropdown Selectors */}
                <div className={styles.colMappingGroup}>
                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>Client Match Column</label>
                    <select
                      className={styles.select}
                      value={clientMatchCol}
                      onChange={e => setClientMatchCol(e.target.value)}
                    >
                      <option value="">-- Select Column --</option>
                      {clientFileData.headers.map((h, i) => (
                        <option key={`cm_${h}_${i}`} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>Master Match Column</label>
                    <select
                      className={styles.select}
                      value={masterMatchCol}
                      onChange={e => setMasterMatchCol(e.target.value)}
                    >
                      <option value="">-- Select Column --</option>
                      {masterFileData.headers.map((h, i) => (
                        <option key={`mm_${h}_${i}`} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {matchKeyType === 'smart_fallback' && (
                  <div className={styles.colMappingGroup} style={{ marginTop: '0.5rem', paddingTop: '0.5rem' }}>
                    <div className={styles.field}>
                      <label className={styles.fieldLabel}>Client Phone Fallback Column</label>
                      <select
                        className={styles.select}
                        value={clientPhoneFallbackCol}
                        onChange={e => setClientPhoneFallbackCol(e.target.value)}
                      >
                        <option value="">-- Select Column --</option>
                        {clientFileData.headers.map((h, i) => (
                          <option key={`cpf_${h}_${i}`} value={h}>
                            {h}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className={styles.field}>
                      <label className={styles.fieldLabel}>Master Phone Fallback Column</label>
                      <select
                        className={styles.select}
                        value={masterPhoneFallbackCol}
                        onChange={e => setMasterPhoneFallbackCol(e.target.value)}
                      >
                        <option value="">-- Select Column --</option>
                        {masterFileData.headers.map((h, i) => (
                          <option key={`mpf_${h}_${i}`} value={h}>
                            {h}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </div>

              {/* Master Columns to Append & Output Mode */}
              <div className={styles.configCard}>
                <div className={styles.colsHeader}>
                  <div className={styles.configCardTitle} style={{ marginBottom: 0 }}>
                    <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    Master Columns to Append ({selectedMasterCols.size})
                  </div>
                  <div className={styles.colsActions}>
                    <button className={styles.textBtn} onClick={handleSelectDefaultMasterCols}>
                      Defaults
                    </button>
                    <button className={styles.textBtn} onClick={handleSelectAllMasterCols}>
                      All
                    </button>
                    <button className={styles.textBtn} onClick={handleClearMasterCols}>
                      Clear
                    </button>
                  </div>
                </div>

                <div className={styles.colsGrid}>
                  {masterFileData.headers.map((col, i) => (
                    <label key={`mcol_${col}_${i}`} className={styles.colCheckbox}>
                      <input
                        type="checkbox"
                        checked={selectedMasterCols.has(col)}
                        onChange={() => handleToggleMasterCol(col)}
                      />
                      <span>{col}</span>
                    </label>
                  ))}
                </div>

                <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                  <label className={styles.fieldLabel}>Merge Mode</label>
                  <select
                    className={styles.select}
                    value={mergeMode}
                    onChange={e => setMergeMode(e.target.value as MergeMode)}
                    style={{ marginTop: '0.35rem' }}
                  >
                    <option value="enriched_client">
                      Enriched Client File (All Client Rows + Appended Master Columns)
                    </option>
                    <option value="matched_only">
                      Matched Leads Only (Only Client Leads that were called/triggered)
                    </option>
                    <option value="full_audit">
                      Full Combined Audit (Include Unmatched Master Rows as well)
                    </option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Action Bar */}
          <div className={styles.actionBar}>
            <div className={styles.actionLeft}>
              <button
                className={`${styles.btn} ${styles.btnPrimary}`}
                disabled={!clientFileData || !masterFileData || processing}
                onClick={handleExecuteMerge}
              >
                <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                Club / Merge Files
              </button>

              {statusMsg && (
                <span className={`${styles.statusMsg} ${styles[statusType]}`}>
                  {statusType === 'ok' && '✓ '}
                  {statusType === 'err' && '✕ '}
                  {statusType === 'warn' && '⚠ '}
                  {statusMsg}
                </span>
              )}
            </div>

            {showResults && outputRows.length > 0 && (
              <div className={styles.actionRight}>
                <button className={`${styles.btn} ${styles.btnSuccess}`} onClick={handleDownloadFullReport}>
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download Client Report (.xlsx)
                </button>

                <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={handleDownloadMatchedOnly}>
                  Matched Only ({stats?.matchedCount})
                </button>

                {stats && stats.unmatchedClientCount > 0 && (
                  <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={handleDownloadUnmatchedClient}>
                    Unmatched Leads ({stats.unmatchedClientCount})
                  </button>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Results & KPI Section */}
        {showResults && stats && (
          <section className={styles.panel}>
            <div className={styles.sectionHead}>
              <div>
                <div className={styles.eyebrow}>Merge Summary</div>
                <h3 className={styles.sectionTitle}>Merged Client Report Preview</h3>
              </div>
            </div>

            {/* KPI Stat Cards */}
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Client Rows</span>
                <span className={`${styles.statVal} ${styles.blue}`}>{stats.totalClientRows}</span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Master Sheet Rows</span>
                <span className={`${styles.statVal} ${styles.purple}`}>{stats.totalMasterRows}</span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Matched Leads</span>
                <span className={`${styles.statVal} ${styles.green}`}>
                  {stats.matchedCount} ({stats.matchRatePercent}%)
                </span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Unmatched in Client</span>
                <span className={`${styles.statVal} ${styles.amber}`}>{stats.unmatchedClientCount}</span>
              </div>
              <div className={styles.statCard}>
                <span className={styles.statLabel}>Unmatched in Master</span>
                <span className={styles.statVal}>{stats.unmatchedMasterCount}</span>
              </div>
            </div>

            {/* Table Search & Controls */}
            <div className={styles.tableControls}>
              <div className={styles.searchBox}>
                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Search in preview..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Showing {previewDisplayRows.length} of {filteredRows.length} rows
              </span>
            </div>

            {/* Preview Table */}
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Status</th>
                    {outputHeaders.map((h, i) => (
                      <th key={`th_${h}_${i}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {previewDisplayRows.map((row, idx) => (
                    <tr key={`row_${idx}`}>
                      <td>
                        <span className={`${styles.matchBadge} ${styles[row._matchStatus]}`}>
                          {row._matchStatus === 'matched'
                            ? 'Matched'
                            : row._matchStatus === 'unmatched_client'
                            ? 'Unmatched Client'
                            : 'Unmatched Master'}
                        </span>
                      </td>
                      {outputHeaders.map((h, i) => (
                        <td key={`td_${idx}_${h}_${i}`} title={String(row[h] || '')}>
                          {String(row[h] || '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
