'use client';

import { useState, useRef, useEffect } from 'react';
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
  processCreditData,
  generateCreditWorkbook,
  generateCreditPresentation,
  formatNum,
  repairEncoding,
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
    if (!metrics) return;
    try {
      setProcessing(true);
      setProcessingText('Generating Excel workbook...');
      const cleanClient = (clientName || metrics.clientName || 'Client').replace(/[^a-zA-Z0-9_-]/g, '_');
      const workbookBytes = generateCreditWorkbook({
        ...metrics,
        clientName: clientName || metrics.clientName,
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
    if (!metrics) return;
    try {
      setProcessing(true);
      setProcessingText('Building 5-slide PowerPoint deck...');
      const cleanClient = (clientName || metrics.clientName || 'Client').replace(/[^a-zA-Z0-9_-]/g, '_');
      const pptxBytes = await generateCreditPresentation({
        ...metrics,
        clientName: clientName || metrics.clientName,
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
    setStatusMsg('');
    setStatusType('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <BrandLogo />
        <Nav />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <ThemeToggle />
          <button
            onClick={logout}
            className="btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem' }}
            title="Sign out"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content" style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.5rem 1rem' }}>
        {/* Upload & Setup Workflow Panel */}
        <div className={styles['workflow-panel']}>
          <div className={styles['section-head']}>
            <div>
              <div className={styles.eyebrow}>Bot Billing Analytics</div>
              <h1 className={styles['section-title']}>Credit Usage Report & Deck Generator</h1>
              <p className={styles['section-note']}>
                Upload AutoEngage platform billing debits CSV. Generates an objective-wise Excel workbook (Summary, Voice, WhatsApp, Data) and a 5-slide client PowerPoint presentation.
              </p>
            </div>
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
        {metrics && (
          <div className={styles['results-panel']}>
            {/* Top KPI Cards */}
            <div className={styles['kpi-grid']}>
              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>Total Credits Consumed</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(metrics.totalCredits))}</div>
                <div className={styles['kpi-sub']}>{formatNum(metrics.debitsCount)} debits ({metrics.periodStr})</div>
              </div>

              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>Voice Spend</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(metrics.voiceCredits))}</div>
                <div className={styles['kpi-sub']}>
                  {metrics.voiceShare.toFixed(1)}% share · {formatNum(metrics.callConnectedCount)} connected calls
                </div>
              </div>

              <div className={styles['kpi-card']}>
                <div className={styles['kpi-label']}>WhatsApp Spend</div>
                <div className={styles['kpi-value']}>{formatNum(Math.round(metrics.whatsAppCredits))}</div>
                <div className={styles['kpi-sub']}>
                  {metrics.whatsAppShare.toFixed(1)}% share · {formatNum(metrics.messageDeliveredCount)} delivered
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
            {metrics.qaReport && (
              <div className={styles['qa-box']}>
                <div className={styles['qa-header']}>
                  <div className={styles['qa-title']}>
                    <span>QA Deck Verification & Audit</span>
                    <span className={metrics.qaReport.passed ? styles['qa-badge-pass'] : styles['qa-badge-fail']}>
                      {metrics.qaReport.passed ? 'All Checks Passed (5/5)' : 'Verification Failed'}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Deck: {metrics.qaReport.slideCount} slides · {metrics.qaReport.rowsShown} objectives ({metrics.qaReport.unmappedCount} unmapped)
                  </span>
                </div>
                <div className={styles['qa-grid']}>
                  {metrics.qaReport.checks.map((chk, i) => (
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
            )}

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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h2 style={{ fontSize: '1rem', fontWeight: 700, margin: 0 }}>
                  Objective Wise Credits ({metrics.objectives.length} Objectives)
                </h2>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Period: {metrics.periodStr}
                </span>
              </div>

              <div className={styles['table-wrapper']}>
                <table className={styles['data-table']}>
                  <thead>
                    <tr>
                      <th className={styles['text-center']}>#</th>
                      <th>Objective</th>
                      <th className={styles['text-center']}>Start Date</th>
                      <th className={styles['text-center']}>End Date</th>
                      <th className={styles['text-right']}>Voice Credits</th>
                      <th className={styles['text-right']}>WhatsApp Credits</th>
                      <th className={styles['text-right']}>Total Credits</th>
                      <th className={styles['text-right']}>Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.objectives.map(o => (
                      <tr key={o.objective}>
                        <td className={styles['text-center']}>{o.rank}</td>
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
                      </tr>
                    ))}
                    <tr className={styles['total-row']}>
                      <td className={styles['text-center']}>—</td>
                      <td>Grand Total</td>
                      <td className={styles['text-center']}>{metrics.minDate ? metrics.objectives[0]?.startDate : '-'}</td>
                      <td className={styles['text-center']}>{metrics.maxDate ? metrics.objectives[0]?.endDate : '-'}</td>
                      <td className={styles['text-right']}>{formatNum(metrics.voiceCredits, 2)}</td>
                      <td className={styles['text-right']}>{formatNum(metrics.whatsAppCredits, 2)}</td>
                      <td className={styles['text-right']}>{formatNum(metrics.totalCredits, 2)}</td>
                      <td className={styles['text-right']}>100.0%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Processing Loader */}
      <ProcessingOverlay show={processing} message={processingText} />
    </div>
  );
}
