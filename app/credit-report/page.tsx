'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import XLSXStyle from 'xlsx-js-style';
const XLSX: any = XLSXStyle && (XLSXStyle as any).utils ? XLSXStyle : ((XLSXStyle as any).default || XLSXStyle);
import {
  CreditMetrics,
  ObjectiveSummary,
  processCreditData,
  generateCreditWorkbook,
  generateCreditPresentation,
  formatNum,
  formatDateDisplay,
  repairEncoding,
  runDeckQA,
} from './credit-utils';
import styles from './credit-report.module.css';

export default function CreditReportPage() {
  const { isAuthenticated, loading, logout } = useAuth();
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [clientName, setClientName] = useState('');
  const [processing, setProcessing] = useState(false);
  const [processingText, setProcessingText] = useState('Processing...');
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'ok' | 'err' | 'warn' | ''>('');
  const [metrics, setMetrics] = useState<CreditMetrics | null>(null);
  // User-tweaked objectives: keyed by objective name. Overrides the parsed values
  // for voice credits, WhatsApp credits, start date, end date.
  const [edits, setEdits] = useState<Record<string, Partial<ObjectiveSummary>>>({});
  // Currently editing row index (for inline editing UI)
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{
    rank: string;
    startDate: string;
    endDate: string;
    voiceCredits: string;
    whatsAppCredits: string;
    totalCredits: string;
    share: string;
  }>({
    rank: '',
    startDate: '',
    endDate: '',
    voiceCredits: '',
    whatsAppCredits: '',
    totalCredits: '',
    share: '',
  });
  // Selected rows for batch removal
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  // Drag and drop state for row reordering
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);

  if (!isAuthenticated && !loading) return null;

  function handleFileSelect(selectedFile: File) {
    if (!selectedFile) return;
    const lowerName = selectedFile.name.toLowerCase();
    if (!lowerName.endsWith('.csv') && !lowerName.endsWith('.xlsx') && !lowerName.endsWith('.xls')) {
      setStatusType('err');
      setStatusMsg('Please upload a valid CSV or Excel file.');
      return;
    }

    setFile(selectedFile);
    setStatusType('ok');
    setStatusMsg(`Selected: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`);

    // Auto-guess client name from filename if empty
    if (!clientName) {
      if (lowerName.includes('perfect riders') || lowerName.includes('perfect_riders') || lowerName.includes('perfectriders')) {
        setClientName('Perfect Riders');
      } else if (lowerName.includes('anant') || lowerName.includes('anantcars') || lowerName.includes('anant_cars')) {
        setClientName('Anant Cars');
      }
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  }

  async function handleProcess() {
    if (!file) {
      setStatusType('err');
      setStatusMsg('Please select a billing CSV file first.');
      return;
    }

    setProcessing(true);
    setProcessingText('Reading file...');

    try {
      const buffer = await file.arrayBuffer();
      let wb: any;

      if (file.name.toLowerCase().endsWith('.csv')) {
        let text = new TextDecoder('utf-8').decode(buffer);
        // UTF-8-sig BOM stripping
        if (text.charCodeAt(0) === 0xfeff) {
          text = text.slice(1);
        }
        text = repairEncoding(text);
        wb = XLSX.read(text, { type: 'string', cellDates: true });
      } else {
        wb = XLSX.read(buffer, { type: 'array', cellDates: true, codepage: 65001 });
      }

      const firstSheetName = wb.SheetNames[0];
      const sheet = wb.Sheets[firstSheetName];
      const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' }) as Record<string, any>[];

      if (!rows || rows.length === 0) {
        throw new Error('No debit records found in the uploaded file.');
      }

      setProcessingText(`Analyzing ${rows.length.toLocaleString()} debit rows...`);

      // Yield thread briefly for UI update
      await new Promise(res => setTimeout(res, 50));

      const processedMetrics = processCreditData(rows, clientName);
      if (!clientName && processedMetrics.clientName) {
        setClientName(processedMetrics.clientName);
      }

      setEdits({});
      setEditingIdx(null);
      setSelectedRows(new Set());
      setMetrics(processedMetrics);
      setStatusType('ok');
      setStatusMsg(
        `Successfully processed ${formatNum(processedMetrics.debitsCount)} debits totaling ${formatNum(Math.round(processedMetrics.totalCredits))} credits across ${processedMetrics.objectives.length} objectives.`
      );
    } catch (err: any) {
      console.error('Error processing credit data:', err);
      setStatusType('err');
      setStatusMsg(err?.message || 'Failed to process billing CSV.');
    } finally {
      setProcessing(false);
    }
  }

  function downloadBlob(data: Uint8Array, filename: string, mimeType: string) {
    const blob = new Blob([data as unknown as BlobPart], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function handleExportExcel() {
    const m = effectiveMetrics;
    if (!m) return;
    try {
      setProcessing(true);
      setProcessingText('Generating Excel workbook...');
      const cleanClient = (clientName || m.clientName || 'Client').replace(/[^a-zA-Z0-9_-]/g, '_');
      const workbookBytes = generateCreditWorkbook({
        ...m,
        clientName: clientName || m.clientName,
      });
      const filename = `Credit_Usage_${cleanClient}_Report.xlsx`;
      downloadBlob(
        workbookBytes,
        filename,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      );
      setStatusType('ok');
      setStatusMsg(`Downloaded ${filename}`);
    } catch (err: any) {
      console.error('Excel generation error:', err);
      setStatusType('err');
      setStatusMsg(`Excel generation failed: ${err?.message}`);
    } finally {
      setProcessing(false);
    }
  }

  async function handleExportPptx() {
    const m = effectiveMetrics;
    if (!m) return;
    try {
      setProcessing(true);
      setProcessingText('Building PowerPoint deck...');
      const cleanClient = (clientName || m.clientName || 'Client').replace(/[^a-zA-Z0-9_-]/g, '_');
      const pptxBytes = await generateCreditPresentation({
        ...m,
        clientName: clientName || m.clientName,
      });
      const filename = `Credit_Usage_${cleanClient}_Presentation.pptx`;
      downloadBlob(
        pptxBytes,
        filename,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
      );
      setStatusType('ok');
      setStatusMsg(`Downloaded ${filename}`);
    } catch (err: any) {
      console.error('PPTX generation error:', err);
      setStatusType('err');
      setStatusMsg(`PowerPoint generation failed: ${err?.message}`);
    } finally {
      setProcessing(false);
    }
  }

  function handleReset() {
    setFile(null);
    setMetrics(null);
    setEdits({});
    setEditingIdx(null);
    setSelectedRows(new Set());
    setStatusMsg('');
    setStatusType('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  // ── Effective objectives: parsed values merged with user edits ──
  const effectiveObjectives = useMemo<ObjectiveSummary[]>(() => {
    if (!metrics) return [];
    const merged = metrics.objectives.map((o) => {
      const e = edits[o.objective];
      const voice = typeof e?.voiceCredits === 'number' ? e.voiceCredits : o.voiceCredits;
      const wa = typeof e?.whatsAppCredits === 'number' ? e.whatsAppCredits : o.whatsAppCredits;
      const total = Number((voice + wa).toFixed(2));
      return {
        ...o,
        voiceCredits: voice,
        whatsAppCredits: wa,
        totalCredits: total,
        startDate: e?.startDate !== undefined ? e.startDate : o.startDate,
        endDate: e?.endDate !== undefined ? e.endDate : o.endDate,
      };
    });

    const grandTotal = merged.reduce((s, o) => s + o.totalCredits, 0);

    return merged.map((o, idx) => ({
      ...o,
      rank: idx + 1,
      shareOfTotal: grandTotal > 0 ? Number(((o.totalCredits / grandTotal) * 100).toFixed(2)) : 0,
    }));
  }, [metrics, edits]);

  // Recompute derived totals from effective objectives (keeps table, Excel & PPTX consistent)
  const effectiveMetrics = useMemo<CreditMetrics | null>(() => {
    if (!metrics) return null;
    const totalCredits = Number(effectiveObjectives.reduce((s, o) => s + o.totalCredits, 0).toFixed(2));
    const voiceCredits = Number(effectiveObjectives.reduce((s, o) => s + o.voiceCredits, 0).toFixed(2));
    const whatsAppCredits = Number(effectiveObjectives.reduce((s, o) => s + o.whatsAppCredits, 0).toFixed(2));
    const base: CreditMetrics = {
      ...metrics,
      objectives: effectiveObjectives,
      totalCredits,
      voiceCredits,
      whatsAppCredits,
      voiceShare: totalCredits > 0 ? (voiceCredits / totalCredits) * 100 : 0,
      whatsAppShare: totalCredits > 0 ? (whatsAppCredits / totalCredits) * 100 : 0,
    };
    base.qaReport = runDeckQA(base);
    return base;
  }, [metrics, effectiveObjectives]);

  function toggleSelect(idx: number) {
    setSelectedRows(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  }

  function toggleSelectAll() {
    if (!effectiveObjectives.length) return;
    if (selectedRows.size === effectiveObjectives.length) {
      setSelectedRows(new Set());
    } else {
      setSelectedRows(new Set(effectiveObjectives.map((_, i) => i)));
    }
  }

  function removeSelectedRows() {
    if (!metrics || selectedRows.size === 0) return;
    const removedNames = new Set(
      effectiveObjectives.filter((_, i) => selectedRows.has(i)).map(o => o.objective)
    );
    setMetrics(prev => {
      if (!prev) return prev;
      const next: CreditMetrics = {
        ...prev,
        objectives: prev.objectives.filter(o => !removedNames.has(o.objective)),
      };
      next.qaReport = runDeckQA(next);
      return next;
    });
    setEdits(prev => {
      const next = { ...prev };
      for (const name of removedNames) delete next[name];
      return next;
    });
    const count = selectedRows.size;
    setSelectedRows(new Set());
    setEditingIdx(null);
    setStatusType('ok');
    setStatusMsg(`Removed ${count} objective(s). Totals, Excel, and PPTX downloads updated.`);
  }

  function removeSingleRow(idx: number) {
    if (!metrics) return;
    const targetObj = effectiveObjectives[idx];
    if (!targetObj) return;
    setMetrics(prev => {
      if (!prev) return prev;
      const next: CreditMetrics = {
        ...prev,
        objectives: prev.objectives.filter(o => o.objective !== targetObj.objective),
      };
      next.qaReport = runDeckQA(next);
      return next;
    });
    setEdits(prev => {
      const next = { ...prev };
      delete next[targetObj.objective];
      return next;
    });
    setSelectedRows(new Set());
    if (editingIdx === idx) setEditingIdx(null);
    setStatusType('ok');
    setStatusMsg(`Removed "${targetObj.objective}". Totals, Excel, and PPTX downloads updated.`);
  }

  function handleDragStart(e: React.DragEvent, idx: number) {
    if (editingIdx !== null) return;
    setDraggedIdx(idx);
    e.dataTransfer.effectAllowed = 'move';
  }

  function handleDragOver(e: React.DragEvent, idx: number) {
    e.preventDefault();
    if (editingIdx !== null) return;
    e.dataTransfer.dropEffect = 'move';
    if (dragOverIdx !== idx) setDragOverIdx(idx);
  }

  function handleDragEnd() {
    setDraggedIdx(null);
    setDragOverIdx(null);
  }

  function handleDropRow(targetIdx: number) {
    if (editingIdx !== null) return;
    if (draggedIdx === null || draggedIdx === targetIdx) {
      setDraggedIdx(null);
      setDragOverIdx(null);
      return;
    }
    setMetrics(prev => {
      if (!prev) return prev;
      const list = [...prev.objectives];
      const [moved] = list.splice(draggedIdx, 1);
      list.splice(targetIdx, 0, moved);
      const next = { ...prev, objectives: list };
      next.qaReport = runDeckQA(next);
      return next;
    });
    setDraggedIdx(null);
    setDragOverIdx(null);
    setStatusType('ok');
    setStatusMsg('Reordered objectives. Excel and PPTX will export in this order.');
  }

  function startEditRow(idx: number, o: ObjectiveSummary) {
    setEditingIdx(idx);
    setEditForm({
      rank: String(o.rank),
      startDate: o.startDate || '',
      endDate: o.endDate || '',
      voiceCredits: String(o.voiceCredits),
      whatsAppCredits: String(o.whatsAppCredits),
      totalCredits: String(o.totalCredits),
      share: String(o.shareOfTotal.toFixed(1)),
    });
  }

  function handleVoiceCreditsChange(idx: number, val: string) {
    const v = parseFloat(val) || 0;
    const w = parseFloat(editForm.whatsAppCredits) || 0;
    const tot = Number((v + w).toFixed(2));
    const otherSum = effectiveObjectives.reduce((s, row, i) => i === idx ? s : s + row.totalCredits, 0);
    const newGrandTotal = otherSum + tot;
    const sh = newGrandTotal > 0 ? ((tot / newGrandTotal) * 100).toFixed(1) : '0.0';
    setEditForm(prev => ({
      ...prev,
      voiceCredits: val,
      totalCredits: String(tot),
      share: sh,
    }));
  }

  function handleWhatsAppCreditsChange(idx: number, val: string) {
    const w = parseFloat(val) || 0;
    const v = parseFloat(editForm.voiceCredits) || 0;
    const tot = Number((v + w).toFixed(2));
    const otherSum = effectiveObjectives.reduce((s, row, i) => i === idx ? s : s + row.totalCredits, 0);
    const newGrandTotal = otherSum + tot;
    const sh = newGrandTotal > 0 ? ((tot / newGrandTotal) * 100).toFixed(1) : '0.0';
    setEditForm(prev => ({
      ...prev,
      whatsAppCredits: val,
      totalCredits: String(tot),
      share: sh,
    }));
  }

  function handleTotalCreditsChange(idx: number, val: string) {
    const tot = parseFloat(val) || 0;
    let v = parseFloat(editForm.voiceCredits) || 0;
    let w = parseFloat(editForm.whatsAppCredits) || 0;
    if (tot < v) {
      v = tot;
      w = 0;
    } else {
      w = Math.max(0, Number((tot - v).toFixed(2)));
    }
    const otherSum = effectiveObjectives.reduce((s, row, i) => i === idx ? s : s + row.totalCredits, 0);
    const newGrandTotal = otherSum + tot;
    const sh = newGrandTotal > 0 ? ((tot / newGrandTotal) * 100).toFixed(1) : '0.0';
    setEditForm(prev => ({
      ...prev,
      totalCredits: val,
      voiceCredits: String(v),
      whatsAppCredits: String(w),
      share: sh,
    }));
  }

  function handleShareChange(idx: number, val: string) {
    const shVal = parseFloat(val) || 0;
    const otherSum = effectiveObjectives.reduce((s, row, i) => i === idx ? s : s + row.totalCredits, 0);
    const pct = Math.min(99.9, Math.max(0, shVal)) / 100;
    const tot = pct < 1 && (1 - pct) > 0 ? Number(((pct * otherSum) / (1 - pct)).toFixed(2)) : otherSum;
    const v = parseFloat(editForm.voiceCredits) || 0;
    let newV = v;
    let newW = 0;
    if (tot < v) {
      newV = tot;
      newW = 0;
    } else {
      newW = Math.max(0, Number((tot - v).toFixed(2)));
    }
    setEditForm(prev => ({
      ...prev,
      share: val,
      totalCredits: String(tot),
      voiceCredits: String(newV),
      whatsAppCredits: String(newW),
    }));
  }

  function cancelEditRow() {
    setEditingIdx(null);
  }

  function saveEditRow(idx: number, o: ObjectiveSummary) {
    const v = parseFloat(editForm.voiceCredits);
    const w = parseFloat(editForm.whatsAppCredits);
    if (isNaN(v) || v < 0 || isNaN(w) || w < 0) {
      setStatusType('err');
      setStatusMsg('Credits must be valid non-negative numbers.');
      return;
    }
    
    // Check if slot rank changed
    const targetRank = parseInt(editForm.rank, 10);
    const currentRank = idx + 1;
    
    // Save updated values
    setEdits(prev => ({
      ...prev,
      [o.objective]: {
        startDate: editForm.startDate.trim() || o.startDate,
        endDate: editForm.endDate.trim() || o.endDate,
        voiceCredits: Number(v.toFixed(2)),
        whatsAppCredits: Number(w.toFixed(2)),
      },
    }));

    // If rank changed, move objective in array
    if (!isNaN(targetRank) && targetRank !== currentRank && metrics) {
      const clampedTarget = Math.max(0, Math.min(metrics.objectives.length - 1, targetRank - 1));
      setMetrics(prev => {
        if (!prev) return prev;
        const list = [...prev.objectives];
        const [moved] = list.splice(idx, 1);
        list.splice(clampedTarget, 0, moved);
        const next = { ...prev, objectives: list };
        next.qaReport = runDeckQA(next);
        return next;
      });
    }

    setEditingIdx(null);
    setStatusType('ok');
    setStatusMsg(`Saved changes to "${o.objective}". Excel and PPTX downloads updated.`);
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <BrandLogo />
        <Nav />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <ThemeToggle />
          {isAuthenticated && (
            <button
              onClick={logout}
              className="btn-secondary"
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem' }}
              title="Sign out"
            >
              Sign out
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content" style={{ maxWidth: '1580px', width: '96%', margin: '0 auto', padding: '1.5rem 1rem' }}>
        {/* Upload & Setup Workflow Panel */}
        <div className={styles['workflow-panel']}>
          <div className={styles['card-header']}>
            <span className={styles['step-badge']}>STEP 1</span>
            <h3 className={styles['section-title']}>Upload Billing Debits</h3>
            <span className={styles['card-desc']}>AutoEngage platform billing debits CSV or Excel export.</span>
          </div>

          {/* Upload Drop Zone */}
          <div
            className={`${styles['drop-zone']} ${dragOver ? styles['drag-over'] : ''} ${file ? styles['has-file'] : ''}`}
            onDragOver={e => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              aria-label="Upload Credit Billing File"
              accept=".csv,.xlsx,.xls"
              style={{ display: 'none' }}
              onChange={e => {
                if (e.target.files && e.target.files[0]) {
                  handleFileSelect(e.target.files[0]);
                }
              }}
            />

            <div className={styles['drop-icon']}>
              <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>

            {file ? (
              <>
                <div className={styles['file-pill']}>
                  <span>📄 {file.name}</span>
                  <span>({(file.size / 1024).toFixed(1)} KB)</span>
                </div>
                <div className={styles['drop-sub']}>Click or drop another file to replace</div>
              </>
            ) : (
              <>
                <div className={styles['drop-title']}>Drag & drop platform billing CSV or click to browse</div>
                <div className={styles['drop-sub']}>Supports raw debit exports (.csv, .xlsx)</div>
              </>
            )}
          </div>

          {/* Control Bar */}
          <div className={styles['controls-bar']}>
            <div className={styles['client-input-wrap']}>
              <label className={styles['client-label']}>Client / Dealership Name:</label>
              <input
                type="text"
                className={styles['client-input']}
                placeholder="e.g. Perfect Riders / Anant Cars"
                value={clientName}
                onChange={e => setClientName(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
              {file && (
                <button type="button" onClick={handleReset} className={styles['btn-secondary']}>
                  Reset
                </button>
              )}
              <button
                type="button"
                onClick={handleProcess}
                disabled={!file || processing}
                className={styles['btn-primary']}
              >
                <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {metrics ? 'Re-Process Data' : 'Process Credit Report'}
              </button>
            </div>
          </div>
        </div>

        {/* Status Notification */}
        {statusMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.85rem 1.25rem',
            borderRadius: '12px',
            marginBottom: '1.25rem',
            background: statusType === 'err' ? 'rgba(239,68,68,0.12)' : statusType === 'warn' ? 'rgba(234,179,8,0.12)' : 'rgba(132,204,22,0.12)',
            border: `1px solid ${statusType === 'err' ? 'rgba(239,68,68,0.3)' : statusType === 'warn' ? 'rgba(234,179,8,0.3)' : 'rgba(132,204,22,0.3)'}`,
            color: statusType === 'err' ? '#ef4444' : statusType === 'warn' ? '#eab308' : '#84cc16',
            fontSize: '0.88rem',
            fontWeight: 600,
          }}>
            <span>{statusMsg}</span>
            <button
              type="button"
              onClick={() => setStatusMsg('')}
              style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '1.2rem', lineHeight: 1 }}
              title="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        {/* Results Panel */}
        <div className={styles['results-panel']}>
          <div className={styles['card-header']}>
            <span className={styles['step-badge']}>STEP 2</span>
            <h3 className={styles['section-title']}>Credit Consumption & Decks</h3>
            <span className={styles['card-desc']}>KPI audit, objective breakdown, and client deck exports.</span>
          </div>

          {metrics ? (
            <>
              {/* Top KPI Cards — reflect live edits */}
            <div className={styles['kpi-grid']}>
              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>Total Credits Consumed</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(effectiveMetrics!.totalCredits))}</div>
                <div className={styles['kpi-sub']}>{formatNum(metrics.debitsCount)} debits ({metrics.periodStr})</div>
              </div>

              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>Voice Spend</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(effectiveMetrics!.voiceCredits))}</div>
                <div className={styles['kpi-sub']}>
                  {effectiveMetrics!.voiceShare.toFixed(1)}% share · {formatNum(metrics.callConnectedCount)} connected calls
                </div>
              </div>

              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>WhatsApp Spend</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(effectiveMetrics!.whatsAppCredits))}</div>
                <div className={styles['kpi-sub']}>
                  {effectiveMetrics!.whatsAppShare.toFixed(1)}% share · {formatNum(metrics.messageDeliveredCount)} delivered
                </div>
              </div>

              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>Post-Sales Operations</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(metrics.postSalesCredits))}</div>
                <div className={styles['kpi-sub']}>
                  {metrics.postSalesShare.toFixed(1)}% of total · Pre-Sales: {formatNum(Math.round(metrics.preSalesCredits))}
                </div>
              </div>
            </div>

            {/* QA Verification Suite Banner (Requirement 9) */}
            {(() => {
              const qaReport = effectiveMetrics?.qaReport || metrics.qaReport;
              if (!qaReport) return null;
              return (
                <div className={styles['qa-box']}>
                  <div className={styles['qa-header']}>
                    <div className={styles['qa-title']}>
                      <span>QA Deck Verification & Audit</span>
                      <span className={qaReport.passed ? styles['qa-badge-pass'] : styles['qa-badge-fail']}>
                        {qaReport.passed ? 'All Checks Passed (5/5)' : 'Verification Failed'}
                      </span>
                    </div>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Deck: {qaReport.slideCount} slides · {qaReport.rowsShown} objectives ({qaReport.unmappedCount} unmapped)
                    </span>
                  </div>
                  <div className={styles['qa-grid']}>
                    {qaReport.checks.map((chk, i) => (
                      <div key={i} className={styles['qa-item']}>
                        <span className={chk.passed ? styles['qa-icon-pass'] : styles['qa-icon-fail']}>
                          {chk.passed ? '✓' : '✗'}
                        </span>
                        <div>
                          <strong style={{ display: 'block', color: 'var(--text)', marginBottom: '0.15rem' }}>{chk.name}</strong>
                          <span>{chk.details}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}

            {/* Export Downloads Action Bar */}
            <div className={styles['download-bar']}>
              <div className={styles['download-info']}>
                <div className={styles['download-title']}>Export Deliverables</div>
                <div className={styles['download-subtitle']}>
                  Client-ready Excel workbook & native PowerPoint presentation deck
                </div>
              </div>

              <div className={styles['download-buttons']}>
                <button
                  type="button"
                  onClick={handleExportExcel}
                  className={styles['btn-export-excel']}
                  title="Download 4-sheet reconciled Excel workbook"
                >
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Download Excel (.xlsx)
                </button>

                <button
                  type="button"
                  onClick={handleExportPptx}
                  className={styles['btn-export-pptx']}
                  title="Download 5-slide client presentation deck"
                >
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                  </svg>
                  Download Deck (.pptx)
                </button>
              </div>
            </div>

            {/* Objective Breakdown Summary Table Preview */}
            <div style={{ marginTop: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>
                    Objective Wise Credits ({effectiveObjectives.length} Objectives)
                  </h2>
                  {selectedRows.size > 0 && (
                    <button
                      type="button"
                      onClick={removeSelectedRows}
                      className={styles['btn-remove-selected']}
                      title="Remove checked objectives from report"
                    >
                      <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Remove Selected ({selectedRows.size})
                    </button>
                  )}
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Period: {effectiveMetrics?.periodStr || metrics.periodStr}
                </span>
              </div>

              <div className={styles['table-wrapper']}>
                <table className={styles['data-table']}>
                  <thead>
                    <tr>
                      <th style={{ width: '38px', textAlign: 'center' }}>
                        <input
                          type="checkbox"
                          aria-label="Select all objectives"
                          checked={effectiveObjectives.length > 0 && selectedRows.size === effectiveObjectives.length}
                          onChange={toggleSelectAll}
                          className={styles['row-checkbox']}
                        />
                      </th>
                      <th className={styles['text-center']} style={{ width: '45px' }}>#</th>
                      <th>Objective</th>
                      <th className={styles['text-center']} style={{ width: '130px' }}>Start Date</th>
                      <th className={styles['text-center']} style={{ width: '130px' }}>End Date</th>
                      <th className={styles['text-right']} style={{ width: '130px' }}>Voice Credits</th>
                      <th className={styles['text-right']} style={{ width: '140px' }}>WhatsApp Credits</th>
                      <th className={styles['text-right']} style={{ width: '120px' }}>Total Credits</th>
                      <th className={styles['text-right']} style={{ width: '75px' }}>Share</th>
                      <th className={styles['text-center']} style={{ width: '110px' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {effectiveObjectives.map((o, idx) => {
                      const isEditing = editingIdx === idx;
                      if (isEditing) {
                        return (
                          <tr key={o.objective} className={styles['row-editing']}>
                            <td className={styles['text-center']}>
                              <input
                                type="checkbox"
                                checked={selectedRows.has(idx)}
                                onChange={() => toggleSelect(idx)}
                                className={styles['row-checkbox']}
                              />
                            </td>
                            <td className={styles['text-center']}>
                              <input
                                type="number"
                                min={1}
                                max={effectiveObjectives.length}
                                className={styles['inline-input-slot']}
                                value={editForm.rank}
                                onChange={e => setEditForm(prev => ({ ...prev, rank: e.target.value }))}
                                title="Slot position (1..N)"
                              />
                            </td>
                            <td>
                              <strong>{o.objective}</strong>
                              {o.isUnmapped && <span className={styles['badge-unmapped']}>Unmapped</span>}
                            </td>
                            <td className={styles['text-center']}>
                              <input
                                type="text"
                                className={styles['inline-input']}
                                value={editForm.startDate}
                                onChange={e => setEditForm(prev => ({ ...prev, startDate: e.target.value }))}
                                placeholder="e.g. 5 Nov 2026"
                              />
                            </td>
                            <td className={styles['text-center']}>
                              <input
                                type="text"
                                className={styles['inline-input']}
                                value={editForm.endDate}
                                onChange={e => setEditForm(prev => ({ ...prev, endDate: e.target.value }))}
                                placeholder="e.g. 11 Nov 2026"
                              />
                            </td>
                            <td className={styles['text-right']}>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                className={styles['inline-input-num']}
                                value={editForm.voiceCredits}
                                onChange={e => handleVoiceCreditsChange(idx, e.target.value)}
                                title="Voice credits"
                              />
                            </td>
                            <td className={styles['text-right']}>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                className={styles['inline-input-num']}
                                value={editForm.whatsAppCredits}
                                onChange={e => handleWhatsAppCreditsChange(idx, e.target.value)}
                                title="WhatsApp credits"
                              />
                            </td>
                            <td className={styles['text-right']}>
                              <input
                                type="number"
                                step="0.01"
                                min="0"
                                className={styles['inline-input-num']}
                                value={editForm.totalCredits}
                                onChange={e => handleTotalCreditsChange(idx, e.target.value)}
                                title="Total credits"
                              />
                            </td>
                            <td className={styles['text-right']}>
                              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.15rem', justifyContent: 'flex-end' }}>
                                <input
                                  type="number"
                                  step="0.1"
                                  min="0"
                                  max="100"
                                  className={styles['inline-input-num']}
                                  style={{ width: '56px' }}
                                  value={editForm.share}
                                  onChange={e => handleShareChange(idx, e.target.value)}
                                  title="Share % of total"
                                />
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>%</span>
                              </div>
                            </td>
                            <td className={styles['text-center']}>
                              <div style={{ display: 'inline-flex', gap: '0.35rem', alignItems: 'center' }}>
                                <button
                                  type="button"
                                  onClick={() => saveEditRow(idx, o)}
                                  className={styles['btn-save-inline']}
                                  title="Save changes"
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  onClick={cancelEditRow}
                                  className={styles['btn-cancel-inline']}
                                  title="Cancel editing"
                                >
                                  Cancel
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      }

                      return (
                        <tr
                          key={o.objective}
                          draggable={editingIdx === null}
                          onDragStart={e => handleDragStart(e, idx)}
                          onDragOver={e => handleDragOver(e, idx)}
                          onDragEnd={handleDragEnd}
                          onDrop={() => handleDropRow(idx)}
                          className={`${draggedIdx === idx ? styles['row-dragging'] : ''} ${dragOverIdx === idx ? styles['row-drag-over'] : ''}`}
                        >
                          <td className={styles['text-center']}>
                            <input
                              type="checkbox"
                              checked={selectedRows.has(idx)}
                              onChange={() => toggleSelect(idx)}
                              className={styles['row-checkbox']}
                            />
                          </td>
                          <td className={styles['text-center']}>
                            <div className={styles['slot-cell']}>
                              <span className={styles['drag-handle']} title="Drag up or down to reorder">⋮⋮</span>
                              <span className={styles['slot-badge']}>{o.rank}</span>
                              <button
                                type="button"
                                onClick={() => startEditRow(idx, o)}
                                className={styles['btn-slot-edit']}
                                title={`Edit slot #${o.rank} and values`}
                              >
                                ✎
                              </button>
                            </div>
                          </td>
                          <td>
                            {o.objective}
                            {o.isUnmapped && <span className={styles['badge-unmapped']}>Unmapped</span>}
                          </td>
                          <td className={styles['text-center']}>{o.startDate}</td>
                          <td className={styles['text-center']}>{o.endDate}</td>
                          <td className={styles['text-right']}>{formatNum(o.voiceCredits, 2)}</td>
                          <td className={styles['text-right']}>{formatNum(o.whatsAppCredits, 2)}</td>
                          <td className={styles['text-right']} style={{ fontWeight: 600 }}>
                            {formatNum(o.totalCredits, 2)}
                          </td>
                          <td className={styles['text-right']}>{o.shareOfTotal.toFixed(1)}%</td>
                          <td className={styles['text-center']}>
                            <div style={{ display: 'inline-flex', gap: '0.35rem', alignItems: 'center' }}>
                              <button
                                type="button"
                                onClick={() => startEditRow(idx, o)}
                                className={styles['btn-edit-inline']}
                                title="Edit credits and dates"
                              >
                                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                </svg>
                                Edit
                              </button>
                              <button
                                type="button"
                                onClick={() => removeSingleRow(idx)}
                                className={styles['btn-delete-inline']}
                                title={`Remove "${o.objective}"`}
                              >
                                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {effectiveObjectives.length === 0 && (
                      <tr>
                        <td colSpan={10} style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
                          All objectives removed. Use Reset above or re-process to restore.
                        </td>
                      </tr>
                    )}
                    <tr className={styles['total-row']}>
                      <td className={styles['text-center']}>—</td>
                      <td className={styles['text-center']}>—</td>
                      <td>Grand Total</td>
                      <td className={styles['text-center']}>{effectiveMetrics?.objectives[0]?.startDate || '-'}</td>
                      <td className={styles['text-center']}>{effectiveMetrics?.objectives[0]?.endDate || '-'}</td>
                      <td className={styles['text-right']}>{formatNum(effectiveMetrics?.voiceCredits || 0, 2)}</td>
                      <td className={styles['text-right']}>{formatNum(effectiveMetrics?.whatsAppCredits || 0, 2)}</td>
                      <td className={styles['text-right']}>{formatNum(effectiveMetrics?.totalCredits || 0, 2)}</td>
                      <td className={styles['text-right']}>100.0%</td>
                      <td className={styles['text-center']}>—</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          <div className={styles['empty-banner']}>
            <div>
              <div className={styles['empty-banner-title']}>Waiting for billing data</div>
              <div className={styles['empty-banner-sub']}>Upload an AutoEngage billing debits export to generate KPI audit, breakdown workbook, and PowerPoint deck.</div>
            </div>
            <div className={styles['empty-banner-steps']}>
              <span className={styles['empty-banner-step']}>Upload CSV</span>
              <span className={styles['empty-banner-step']}>Process</span>
              <span className={styles['empty-banner-step']}>Audit KPIs</span>
              <span className={styles['empty-banner-step']}>Download Deck</span>
            </div>
          </div>
        )}
      </div>
      </main>

      {/* Processing Loader */}
      <ProcessingOverlay show={processing} message={processingText} />
    </div>
  );
}
