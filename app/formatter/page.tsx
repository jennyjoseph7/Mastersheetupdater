'use client';
import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import { readFileAsArrayBuffer, esc, excelSafe, validateFileSync } from '@/lib/data-pipeline';
import * as XLSX from 'xlsx';
import { TEMPLATES, FormatterTemplate, buildTargetSources, normalizeHeader, normalizeToyotaVehicleModel, normalizeMahindraVehicleName, canonicalHeader } from './templates';
import styles from './formatter.module.css';

const AE_BATCH_STORAGE_KEY = 'jejo-ae-batch-export-v1';
const AE_BATCH_SIZE_KEY = 'jejo-ae-batch-size';

interface ParsedResult {
  data: Record<string, string>[];
  rawHeaders: string[];
}

interface AuditSection {
  title: string;
  level: string;
  rows: string[];
}

interface MappingAudit {
  hasWarnings: boolean;
  sections: AuditSection[];
}

export default function FormatterPage() {
  const log = (...args) => console.log('[Formatter]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [rawFile, setRawFile] = useState<File | null>(null);
  const [templateId, setTemplateId] = useState<string>('bullmenn_service');
  const [outputRows, setOutputRows] = useState<Record<string, string>[]>([]);
  const [inputRowCount, setInputRowCount] = useState(0);
  const [mappedCells, setMappedCells] = useState(0);
  const [defaultCells, setDefaultCells] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState('');
  const [fileStatus, setFileStatus] = useState('No file selected');
  const [processing, setProcessing] = useState(false);
  const [startLead, setStartLead] = useState(1);
  const [numBatches, setNumBatches] = useState(1);
  const [batchSize, setBatchSize] = useState(() => {
    try { return parseInt(localStorage.getItem(AE_BATCH_SIZE_KEY) || '100', 10) || 100; } catch { return 100; }
  });
  const [audit, setAudit] = useState<MappingAudit | null>(null);
  const [fileDragOver, setFileDragOver] = useState(false);
  const [hasFile, setHasFile] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const batchFingerprintRef = useRef('');
  const batchInputRowCountRef = useRef(0);
  const batchTemplateIdRef = useRef('');

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);
  if (!isAuthenticated && !loading) return null;

  const template = TEMPLATES[templateId];

  function readAeBatchStore(): Record<string, unknown> {
    try { return JSON.parse(localStorage.getItem(AE_BATCH_STORAGE_KEY) || '{}'); }
    catch { return {}; }
  }

  function writeAeBatchStore(store: Record<string, unknown>) {
    try { localStorage.setItem(AE_BATCH_STORAGE_KEY, JSON.stringify(store)); }
    catch { /* quota */ }
  }

  function getSavedBatchProgress(fp: string, tId: string, rowCount: number) {
    const store = readAeBatchStore();
    const rec = store[fp] as Record<string, unknown> | undefined;
    if (!rec || rec.templateId !== tId || Number(rec.inputRowCount) !== Number(rowCount)) return null;
    return { nextLeadIndex: Number(rec.nextLeadIndex) || 1 };
  }

  function saveBatchProgress(fp: string, tId: string, rowCount: number, nextLeadIndex: number) {
    const store = readAeBatchStore();
    store[fp] = { templateId: tId, inputRowCount: rowCount, nextLeadIndex };
    writeAeBatchStore(store);
  }

  function clearBatchProgressForFingerprint(fp: string) {
    const store = readAeBatchStore();
    delete store[fp];
    writeAeBatchStore(store);
  }

  function fileBatchFingerprint(file: File, rowCount: number): string {
    return [file.name, String(file.size), String(file.lastModified), String(rowCount)].join('|');
  }

  function cellToString(val: unknown): string {
    if (val == null) return '';
    if (typeof val === 'number') {
      if (Number.isInteger(val) && val > 40000 && val < 200000) {
        const d = new Date((val - 25569) * 86400 * 1000);
        if (!isNaN(d.getTime())) {
          const dd = String(d.getDate()).padStart(2, '0');
          const mm = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()];
          const yy = String(d.getFullYear()).slice(-2);
          return `${dd}-${mm}-${yy}`;
        }
      }
      if (Number.isInteger(val)) return String(val);
      if (val > 999999 && Math.abs(val - Math.round(val)) < 0.01) return String(Math.round(val));
    }
    return String(val).trim();
  }

  function limitedRows(rows: string[], emptyText: string): string[] {
    if (!rows.length) return [emptyText];
    const limit = 8;
    const shown = rows.slice(0, limit);
    if (rows.length > limit) shown.push('+' + (rows.length - limit) + ' more');
    return shown;
  }

  function buildMappingHint() {
    const t = TEMPLATES[templateId];
    const lines: string[] = [];
    for (const [src, trg] of Object.entries(t.sourceToTarget || {})) lines.push(src + ' -> ' + trg);
    if (t.multiSource) {
      for (const [tgt, arr] of Object.entries(t.multiSource)) {
        lines.push('[' + tgt + ' alt] ' + arr.join(' | '));
      }
    }
    for (const [key, val] of Object.entries(t.defaults || {})) lines.push('[default] ' + key + ' = ' + val);
    return lines.join(' | ');
  }

  function parseSheet(ab: ArrayBuffer, tmpl: FormatterTemplate): ParsedResult {
    const wb = XLSX.read(ab, { type: 'array', raw: true, cellText: false, cellDates: false });
    const targetSources = buildTargetSources(tmpl);
    const allTargetKeys = new Set<string>();
    for (const keys of Object.values(targetSources)) keys.forEach(k => allTargetKeys.add(k));

    let bestRows: unknown[][] = [];
    let bestHeaderIndex = 0;
    let maxMatches = -1;

    for (const sheetName of wb.SheetNames) {
      const ws = wb.Sheets[sheetName];
      const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];
      if (rows.length < 1) continue;
      for (let i = 0; i < Math.min(rows.length, 25); i++) {
        const candidateHeaders = rows[i].map(cellToString).map(normalizeHeader);
        const matches = candidateHeaders.filter(h => h && allTargetKeys.has(h)).length;
        if (matches > maxMatches) {
          maxMatches = matches;
          bestRows = rows;
          bestHeaderIndex = i;
        }
      }
      if (maxMatches >= 3) break;
    }

    if (!bestRows.length || maxMatches === 0) {
      const ws = wb.Sheets[wb.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];
      if (rows.length < 2) return { data: [], rawHeaders: [] };
      const rawHeaders = rows[0].map(cellToString);
      const headers = rawHeaders.map(normalizeHeader);
      const data: Record<string, string>[] = [];
      for (let i = 1; i < rows.length; i++) {
        const raw = rows[i] as unknown[];
        if (!raw || raw.every(c => cellToString(c) === '')) continue;
        const obj: Record<string, string> = {};
        for (let j = 0; j < headers.length; j++) obj[headers[j]] = cellToString(raw[j]);
        data.push(obj);
      }
      return { data, rawHeaders };
    }

    const rawHeaders = bestRows[bestHeaderIndex].map(cellToString);
    const headers = rawHeaders.map(normalizeHeader);
    const data: Record<string, string>[] = [];
    for (let i = bestHeaderIndex + 1; i < bestRows.length; i++) {
      const raw = bestRows[i] as unknown[];
      if (!raw || raw.every(c => cellToString(c) === '')) continue;
      const obj: Record<string, string> = {};
      for (let j = 0; j < headers.length; j++) {
        if (headers[j]) obj[headers[j]] = cellToString(raw[j]);
      }
      data.push(obj);
    }
    return { data, rawHeaders };
  }

  function firstMappedCell(inputRow: Record<string, string>, canonicalKeys: string[]): string {
    if (!canonicalKeys?.length) return '';
    for (const ck of canonicalKeys) {
      const v = inputRow[ck];
      if (v !== undefined && v !== null && v !== '') return v;
    }
    return '';
  }

  function buildMappingAudit(tmpl: FormatterTemplate, parsed: ParsedResult, rows: Record<string, string>[]): MappingAudit {
    const headerSet = new Set(parsed.rawHeaders.map(normalizeHeader).filter(Boolean));
    const targetSources = buildTargetSources(tmpl);
    const mappingEntries = Object.entries(targetSources).map(([target, keys]) => ({
      target, keys, matchedKeys: keys.filter(k => headerSet.has(k)),
    }));
    const matched = mappingEntries.filter(e => e.matchedKeys.length);
    const missing = mappingEntries.filter(e => !e.matchedKeys.length);
    const usedSourceKeys = new Set<string>();
    matched.forEach(e => e.matchedKeys.forEach(k => usedSourceKeys.add(k)));
    const defaults = Object.entries(tmpl.defaults || {});
    const blankColumns = tmpl.outputOrder.filter(key => rows.every(row => String(row[key] || '').trim() === ''));
    const ignoredHeaders = parsed.rawHeaders.filter(header => {
      const key = normalizeHeader(header);
      return key && !usedSourceKeys.has(key);
    });

    return {
      hasWarnings: Boolean(missing.length || blankColumns.length),
      sections: [
        { title: 'Matched mappings', level: matched.length ? 'ok' : 'warn', rows: limitedRows(matched.map(e => e.target + ' <- ' + e.matchedKeys.join(', ')), 'No template mappings matched.') },
        { title: 'Missing source columns', level: missing.length ? 'warn' : 'ok', rows: limitedRows(missing.map(e => e.target + ' (need: ' + e.keys.join(', ') + ')'), 'None') },
        { title: 'Defaults applied', level: defaults.length ? 'info' : 'ok', rows: limitedRows(defaults.map(p => p[0] + ' = ' + p[1]), 'None') },
        { title: 'Blank output columns', level: blankColumns.length ? 'warn' : 'ok', rows: limitedRows(blankColumns, 'None') },
        { title: 'Ignored upload columns', level: ignoredHeaders.length ? 'info' : 'ok', rows: limitedRows(ignoredHeaders, 'None') },
      ],
    };
  }

  async function processFile() {
    if (!rawFile) return;
    setProcessing(true);
    setStatusMsg('Parsing file...');
    setStatusType('');

    try {
      const ab = await readFileAsArrayBuffer(rawFile);
      const parsed = parseSheet(ab, template);
      if (!parsed.data.length) {
        setStatusMsg('No data rows found in file.');
        setStatusType('err');
        setOutputRows([]);
        setInputRowCount(0);
        setProcessing(false);
        return;
      }

      const targetSources = buildTargetSources(template);
      const rows: Record<string, string>[] = [];
      let mappedCount = 0;
      let defaultCount = 0;

      for (const inputRow of parsed.data) {
        const out: Record<string, string> = {};
        for (const key of template.outputOrder) {
          const keys = targetSources[key];
          const rawVal = keys?.length ? firstMappedCell(inputRow, keys) : '';
          if (rawVal !== '') {
            out[key] = rawVal;
            mappedCount++;
          } else if (template.defaults[key] !== undefined) {
            out[key] = template.defaults[key];
            defaultCount++;
          } else {
            out[key] = '';
          }
        }
        if (template.normalizeToyotaModels && out.vehicle_model) {
          out.vehicle_model = normalizeToyotaVehicleModel(out.vehicle_model);
        }
        if (template.normalizeMahindraModels && out.interested_vehicle_name) {
          out.interested_vehicle_name = normalizeMahindraVehicleName(out.interested_vehicle_name);
        }
        rows.push(out);
      }

      setOutputRows(rows);
      setInputRowCount(parsed.data.length);
      setMappedCells(mappedCount);
      setDefaultCells(defaultCount);

      const mappingAudit = buildMappingAudit(template, parsed, rows);
      setAudit(mappingAudit);

      batchFingerprintRef.current = fileBatchFingerprint(rawFile, parsed.data.length);
      batchInputRowCountRef.current = parsed.data.length;
      batchTemplateIdRef.current = templateId;
      setStartLead(1);
      setNumBatches(1);

      setStatusMsg(mappingAudit.hasWarnings
        ? `Formatted ${rows.length} row(s). Review mapping audit before download.`
        : `Formatted ${rows.length} row(s). Ready to download.`,
      );
      setStatusType(mappingAudit.hasWarnings ? 'warn' : 'ok');
    } catch (err: unknown) {
      setStatusMsg('Error processing request.');
      setStatusType('err');
    }
    setProcessing(false);
  }

  function downloadOutput() {
    if (!outputRows.length) return;

    const total = outputRows.length;
    let start = startLead;
    if (start < 1) start = 1;
    if (start > total) { setStatusMsg(`Start lead must be between 1 and ${total}.`); setStatusType('err'); return; }
    const remaining = total - start + 1;
    if (remaining < 1) { setStatusMsg('Nothing left to export.'); setStatusType('err'); return; }
    const maxBatches = Math.ceil(remaining / batchSize);
    let num = numBatches;
    if (num < 1) num = 1;
    if (num > maxBatches) num = maxBatches;

    const headers = template.outputOrder;
    const dateStr = new Date().toISOString().slice(0, 10);
    const safeName = template.label.replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '');

    let exported = 0;
    let filesWritten = 0;

    for (let b = 0; b < num; b++) {
      const sliceStartIdx = start - 1 + b * batchSize;
      if (sliceStartIdx >= total) break;
      const sliceLen = Math.min(batchSize, total - sliceStartIdx);
      const slice = outputRows.slice(sliceStartIdx, sliceStartIdx + sliceLen);
      const aoa: string[][] = [headers];
      for (const row of slice) aoa.push(headers.map(h => row[h] || ''));
      const part = num > 1 ? '_batch' + (b + 1) : '';
      const fileName = safeName + '_AutoEngage_' + dateStr + part + '.csv';
      const csvRows = aoa.map(row => row.map(c => {
        const s = excelSafe(c);
        return /[\",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
      }).join(','));
      const bom = '\uFEFF';
      const blob = new Blob([bom + csvRows.join('\r\n')], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      try {
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } finally {
        URL.revokeObjectURL(url);
      }
      exported += sliceLen;
      filesWritten++;
    }

    const nextLeadIndex = start + exported;
    if (batchFingerprintRef.current && batchTemplateIdRef.current) {
      saveBatchProgress(batchFingerprintRef.current, batchTemplateIdRef.current, batchInputRowCountRef.current, nextLeadIndex);
    }
    if (nextLeadIndex <= total) {
      setStartLead(nextLeadIndex);
      const rem = total - nextLeadIndex + 1;
      setNumBatches(Math.max(1, Math.ceil(rem / batchSize)));
    } else {
      setStartLead(1);
      setNumBatches(1);
    }
    setStatusMsg(`Downloaded ${filesWritten} file(s), ${exported} lead(s).`);
    setStatusType('ok');
  }

  function clearOutput() {
    setOutputRows([]);
    setInputRowCount(0);
    setMappedCells(0);
    setDefaultCells(0);
    setAudit(null);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const v = validateFileSync(file);
    if (!v.valid) { setFileStatus(v.error!); return; }
    setRawFile(file);
    clearOutput();
    setFileStatus('Loaded: ' + file.name);
    setHasFile(true);
    setStatusMsg('File loaded. Click Format File.');
    setStatusType('');
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setFileDragOver(false);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const dt = new DataTransfer();
    dt.items.add(f);
    if (fileInputRef.current) {
      fileInputRef.current.files = dt.files;
      fileInputRef.current.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  function handleTemplateChange(val: string) {
    setTemplateId(val);
    clearOutput();
    if (rawFile) { setStatusMsg('Template changed. Click Format File again.'); setStatusType('warn'); }
  }

  const mappingHint = buildMappingHint();
  const sortedRows = outputRows.slice(0, 250);

  let resumeData: { nextLeadIndex: number } | null = null;
  if (outputRows.length > 0 && batchFingerprintRef.current && batchTemplateIdRef.current) {
    resumeData = getSavedBatchProgress(batchFingerprintRef.current, batchTemplateIdRef.current, batchInputRowCountRef.current);
  }

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>AutoEngage Formatter</h1>
              <div className="header-sub">Client file → AutoEngage upload schema</div>
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
          <div className={styles['section-title']}>Step 1 — Template and file</div>
          <div className={styles['step-note']}>1) Choose template 2) Upload Sheet 3) Click Format File</div>
          <div className={styles.controls}>
            <select className={styles.select} value={templateId} onChange={e => handleTemplateChange(e.target.value)}>
              {Object.entries(TEMPLATES).map(([key, tpl]) => (
                <option key={key} value={key}>{tpl.label}</option>
              ))}
            </select>
            <button className={`${styles.btn} ${styles['btn-upload']}`} onClick={() => fileInputRef.current?.click()}>Upload Sheet</button>
            <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={processFile} disabled={!rawFile || processing}>Format File</button>
            <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={downloadOutput} disabled={!outputRows.length}>Export Batches</button>
          </div>

          <div
            className={`${styles['drop-zone']} ${fileDragOver ? styles['drag-over'] : ''} ${hasFile ? styles['has-file'] : ''}`}
            onDragOver={e => { e.preventDefault(); setFileDragOver(true); }}
            onDragLeave={() => setFileDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <div className={styles['upload-row']}>
              <div>
                <div className={styles['dz-label']}>Upload client CSV/XLSX</div>
                <div className={styles['dz-sub']}>Use Upload Sheet button above, or drag and drop file.</div>
              </div>
            </div>
            <div className={`${styles.status} ${hasFile ? styles['ok'] : ''}`}>{fileStatus}</div>
            <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} style={{ display: 'none' }} />
          </div>

          <div className={`${styles.hint} ${styles.mono}`}>{mappingHint}</div>
          <div className={`${styles.status} ${statusType ? styles[statusType] : ''}`}>{statusMsg}</div>

          <div className={styles['batch-panel']} style={{ display: outputRows.length ? 'block' : 'none' }}>
            <div className={styles['batch-panel-title']}>Batch download</div>
            <div className={styles['batch-panel-note']}>
              Each file uses a <strong>header row</strong> plus up to <strong>{batchSize} leads</strong> per batch.
            </div>
            {resumeData && resumeData.nextLeadIndex > 1 && (
              <>
                <div className={`${styles['resume-banner']} ${styles['show']}`}>
                  {resumeData.nextLeadIndex <= outputRows.length
                    ? `Previously exported up to lead ${resumeData.nextLeadIndex - 1} of ${outputRows.length}. Next lead: ${resumeData.nextLeadIndex}.`
                    : `Saved progress (lead ${resumeData.nextLeadIndex}) is past the end (${outputRows.length} leads).`
                  }
                </div>
                <div className={styles['resume-actions']}>
                  {resumeData.nextLeadIndex <= outputRows.length && (
                    <button className={`${styles.btn} ${styles['btn-primary']}`} onClick={() => {
                      setStartLead(resumeData.nextLeadIndex);
                      const rem = outputRows.length - resumeData.nextLeadIndex + 1;
                      setNumBatches(Math.max(1, Math.ceil(rem / batchSize)));
                    }}>
                      Continue from lead {resumeData.nextLeadIndex}
                    </button>
                  )}
                  <button className={`${styles.btn} ${styles['btn-secondary']}`} onClick={() => {
                    setStartLead(1);
                    setNumBatches(1);
                    if (batchFingerprintRef.current) clearBatchProgressForFingerprint(batchFingerprintRef.current);
                  }}>
                    {resumeData.nextLeadIndex <= outputRows.length ? 'Start from lead 1' : 'Start from lead 1 (clear saved position)'}
                  </button>
                </div>
              </>
            )}
            <div className={styles['batch-row']}>
              <div className={styles['batch-field']}>
                <label>Start at lead #</label>
                <input type="number" min={1} value={startLead} onChange={e => setStartLead(parseInt(e.target.value) || 1)} />
              </div>
              <div className={styles['batch-field']}>
                <label>Batches to download</label>
                <input type="number" min={1} value={numBatches} onChange={e => setNumBatches(parseInt(e.target.value) || 1)} />
              </div>
              <div className={styles['batch-field']}>
                <label>Batch size</label>
                <input type="number" min={1} max={500} value={batchSize} onChange={e => { const v = parseInt(e.target.value) || 100; setBatchSize(v); try { localStorage.setItem(AE_BATCH_SIZE_KEY, String(v)); } catch {} }} />
              </div>
            </div>
            <div className={`${styles['batch-hint']} ${styles.mono}`}>
              {outputRows.length > 0 && `${outputRows.length} lead(s) formatted.`}
            </div>
            <button className={styles['batch-forget']} onClick={() => {
              if (batchFingerprintRef.current) clearBatchProgressForFingerprint(batchFingerprintRef.current);
              setStatusMsg('Forgot saved batch progress.');
              setStatusType('ok');
            }}>Forget saved progress</button>
          </div>
        </section>

        <section className={styles.panel}>
          <div className={styles['section-title']}>Step 2 — Output preview</div>
          <div className={styles.stats}>
            <div className={styles.stat}><div className={styles['stat-label']}>Input Rows</div><div className={styles['stat-value']}>{inputRowCount}</div></div>
            <div className={styles.stat}><div className={styles['stat-label']}>Output Rows</div><div className={styles['stat-value']}>{outputRows.length}</div></div>
            <div className={styles.stat}><div className={styles['stat-label']}>Mapped Cells</div><div className={styles['stat-value']}>{mappedCells}</div></div>
            <div className={styles.stat}><div className={styles['stat-label']}>Default Cells</div><div className={styles['stat-value']}>{defaultCells}</div></div>
          </div>

          {audit && (
            <div className={styles['audit-card']} style={{ display: 'block' }}>
              <div className={styles['audit-title']}>{audit.hasWarnings ? 'Mapping audit — review before download' : 'Mapping audit — ready'}</div>
              <div className={styles['audit-grid']}>
                {audit.sections.map((s, i) => (
                  <div key={i} className={`${styles['audit-item']} ${styles[s.level]}`}>
                    <strong>{s.title}</strong>
                    {s.rows.map((r, j) => <div key={j}>{r}</div>)}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className={styles['table-wrap']} style={{ display: sortedRows.length ? 'block' : 'none' }}>
            <div className={styles['table-scroll']}>
              <table>
                <thead><tr>{template.outputOrder.map(h => <th key={h}>{esc(h)}</th>)}</tr></thead>
                <tbody>
                  {sortedRows.map((row, i) => (
                    <tr key={i}>{template.outputOrder.map(h => <td key={h}>{esc(row[h])}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </main>
      <footer>AutoNage — AutoEngage Formatter</footer>
      <ProcessingOverlay show={processing} message="Formatting file…" />
    </div>
  );
}
