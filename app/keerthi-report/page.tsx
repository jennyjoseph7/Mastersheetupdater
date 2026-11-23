'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import * as XLSX from 'xlsx';
import { readFileAsArrayBuffer, validateFileSync, cellToString } from '@/lib/data-pipeline';
import {
  CampaignMeta,
  CampaignType,
  KeerthiReportDataset,
  detectCampaignMeta,
  processKeerthiReport,
  exportKeerthiExcelWorkbook,
  cleanString,
} from './keerthi-report-utils';
import styles from './keerthi-report.module.css';

export default function KeerthiReportPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [statusType, setStatusType] = useState<'ok' | 'err' | ''>('');

  const [rawRows, setRawRows] = useState<Record<string, string>[]>([]);
  const [detectedMeta, setDetectedMeta] = useState<CampaignMeta | null>(null);
  const [overrideType, setOverrideType] = useState<CampaignType | ''>('');
  const [dataset, setDataset] = useState<KeerthiReportDataset | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [loading, isAuthenticated, router]);

  if (!isAuthenticated && !loading) return null;

  async function handleFileUpload(uploadedFile: File) {
    try {
      validateFileSync(uploadedFile);
      setProcessing(true);
      setStatusMsg('Parsing campaign spreadsheet...');
      setStatusType('');

      const ab = await readFileAsArrayBuffer(uploadedFile);
      const wb = XLSX.read(ab, { type: 'array', raw: true, cellDates: true });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const rawData = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '', raw: true }) as unknown[][];

      if (rawData.length < 2) {
        throw new Error(`File ${uploadedFile.name} must have a header row and at least 1 row of data.`);
      }

      // Detect header row
      let headerRowIndex = 0;
      for (let i = 0; i < Math.min(5, rawData.length); i++) {
        const row = rawData[i] as unknown[];
        if (row && row.filter(c => c != null && String(c).trim() !== '').length >= 3) {
          headerRowIndex = i;
          break;
        }
      }

      const headers = (rawData[headerRowIndex] as unknown[]).map(h => cleanString(h));
      const parsedRows: Record<string, string>[] = [];

      for (let i = headerRowIndex + 1; i < rawData.length; i++) {
        const rowArr = rawData[i] as unknown[];
        if (!rowArr || !rowArr.some(c => c != null && String(c).trim() !== '')) continue;

        const rowObj: Record<string, string> = {};
        headers.forEach((h, idx) => {
          if (h) rowObj[h] = cellToString(rowArr[idx]);
        });
        parsedRows.push(rowObj);
      }

      const meta = detectCampaignMeta(headers, uploadedFile.name);
      setFile(uploadedFile);
      setRawRows(parsedRows);
      setDetectedMeta(meta);
      setOverrideType(meta.type);

      const generatedDataset = processKeerthiReport(parsedRows, meta, uploadedFile.name);
      setDataset(generatedDataset);

      setStatusMsg(`Successfully loaded ${uploadedFile.name}: ${parsedRows.length} triggers, identified ${generatedDataset.hotWarmTotal} Hot & Warm leads.`);
      setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg((err as Error).message || 'Failed to parse file.');
      setStatusType('err');
    } finally {
      setProcessing(false);
    }
  }

  function handleTypeOverrideChange(newType: CampaignType) {
    setOverrideType(newType);
    if (!detectedMeta || rawRows.length === 0 || !file) return;

    let displayName = detectedMeta.displayName;
    let servicePlanName = detectedMeta.servicePlanName;

    if (newType === 'due_overdue') {
      displayName = 'Service Reminder - Due / Overdue (Voice)';
      servicePlanName = 'Due / overdue service';
    } else if (newType === 'expiry') {
      displayName = 'Service Reminder - Expiry (Voice)';
      servicePlanName = 'Service coupon expiry';
    } else if (newType === 'checkup') {
      displayName = 'Check-up (WhatsApp)';
      servicePlanName = 'Check up';
    } else if (newType === 'paid') {
      displayName = 'Annual / Paid Service (WhatsApp)';
      servicePlanName = 'Annual / paid service';
    }

    const updatedMeta: CampaignMeta = {
      ...detectedMeta,
      type: newType,
      displayName,
      servicePlanName,
    };

    setDetectedMeta(updatedMeta);
    const generated = processKeerthiReport(rawRows, updatedMeta, file.name);
    setDataset(generated);
  }

  function handleExportExcel() {
    if (!dataset) return;
    try {
      setProcessing(true);
      exportKeerthiExcelWorkbook(dataset);
      setStatusMsg('Custom report downloaded successfully.');
      setStatusType('ok');
    } catch (err: unknown) {
      setStatusMsg((err as Error).message || 'Failed to generate Excel report.');
      setStatusType('err');
    } finally {
      setProcessing(false);
    }
  }

  async function handleCopyData() {
    if (!dataset || dataset.hotWarmLeads.length === 0) return;
    const headers = [
      'Name', 'Phone Number', 'Lead Category', 'Service Booked?', 'Registration Number',
      'VIN Number', 'Vehicle Model', 'Showroom/Location', 'Service Plan', 'Check-up Due Date (Records)',
      'Confirmed/Stated Date (Reply)', 'Confirmed/Stated Time (Reply)', 'Disposition', 'Disposition Detail',
      'Message Date/Time', 'Message / Reply Summary', 'Recommended Action', 'appointment_booked_location'
    ];

    const lines = [
      headers.join('\t'),
      ...dataset.hotWarmLeads.map(l => [
        l.name, l.phoneNumber, l.leadCategory, l.serviceBooked, l.regNumber,
        l.vinNumber, l.vehicleModel, l.showroomLocation, l.servicePlan, l.checkupDueDateRecords,
        l.confirmedDateReply, l.confirmedTimeReply, l.disposition, l.dispositionDetail,
        l.messageDateTime, l.messageReplySummary.replace(/\r?\n|\t/g, ' '),
        l.recommendedAction.replace(/\r?\n|\t/g, ' '), l.appointmentBookedLocation
      ].join('\t'))
    ];

    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setStatusMsg(`Copied ${dataset.hotWarmLeads.length} leads to clipboard.`);
      setStatusType('ok');
    } catch {
      setStatusMsg('Clipboard copy failed.');
      setStatusType('err');
    }
  }

  function handleReset() {
    setFile(null);
    setRawRows([]);
    setDetectedMeta(null);
    setDataset(null);
    setStatusMsg('');
    setStatusType('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  const filteredLeads = useMemo(() => {
    if (!dataset) return [];
    if (!searchQuery.trim()) return dataset.hotWarmLeads;
    const q = searchQuery.toLowerCase();
    return dataset.hotWarmLeads.filter(l =>
      l.name.toLowerCase().includes(q) ||
      l.phoneNumber.includes(q) ||
      l.regNumber.toLowerCase().includes(q) ||
      l.leadCategory.toLowerCase().includes(q) ||
      l.vehicleModel.toLowerCase().includes(q) ||
      l.appointmentBookedLocation.toLowerCase().includes(q)
    );
  }, [dataset, searchQuery]);

  return (
    <div className="sub-page">
      <ProcessingOverlay show={processing} message="Generating Keerthi custom report..." />
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Keerthi Custom Report</h1>
              <div className="header-sub">Automated Post-Sales Campaign Deliverables (Voice & WhatsApp)</div>
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
              <div className={styles.eyebrow}>Keerthi Triumph Report Engine</div>
              <h2 className={styles.sectionTitle}>Campaign Master Sheet Ingestion</h2>
              <p className={styles.sectionNote}>
                Upload raw campaign master sheets (Voice Due/Overdue, Expiry or WhatsApp Checkup, Annual Paid). Auto-detects campaign, applies de-duplication, formats appointment dates & locations, and exports the 4-sheet client report.
              </p>
            </div>
            {dataset && (
              <button className={`${styles.btn} ${styles.btnOutline}`} onClick={handleReset}>
                Reset File
              </button>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            aria-label="Upload Master Sheet"
            accept=".xlsx,.xls,.csv"
            style={{ display: 'none' }}
            onChange={e => {
              const f = e.target.files?.[0];
              if (f) handleFileUpload(f);
            }}
          />

          <div
            className={`${styles.dropZone} ${dragOver ? styles.dragOver : ''} ${file ? styles.hasFile : ''}`}
            onDragOver={e => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) handleFileUpload(f);
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <svg className={styles.dzIcon} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.8">
              <path strokeLinecap="round" strokeLinejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <div className={styles.dzLabel}>
              {file ? file.name : 'Upload Keerthi Campaign Master Sheet'}
            </div>
            <div className={styles.dzSublabel}>
              {file ? `${rawRows.length} raw rows parsed` : 'Drag & drop Excel (.xlsx, .xls) or CSV'}
            </div>
          </div>

          {statusMsg && (
            <div className={`${styles.statusMsg} ${statusType === 'ok' ? styles.statusOk : styles.statusErr}`}>
              {statusMsg}
            </div>
          )}

          {/* Campaign Selector / Metadata Bar */}
          {detectedMeta && (
            <div className={styles.campaignBar}>
              <div className={styles.campaignLeft}>
                <span className={styles.campaignBadge}>
                  {detectedMeta.displayName}
                </span>
                <span className={styles.campaignChannelBadge}>
                  {detectedMeta.channel.toUpperCase()}
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Campaign Type:</span>
                  <select
                    value={overrideType}
                    onChange={e => handleTypeOverrideChange(e.target.value as CampaignType)}
                    style={{
                      background: 'var(--surface)',
                      color: 'var(--text)',
                      border: '1px solid var(--border)',
                      borderRadius: '6px',
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.8rem',
                    }}
                  >
                    <option value="due_overdue">Due / Overdue (Voice)</option>
                    <option value="expiry">Coupon Expiry (Voice)</option>
                    <option value="checkup">Check-up (WhatsApp)</option>
                    <option value="paid">Annual / Paid Service (WhatsApp)</option>
                  </select>
                </div>
              </div>
              <div className={styles.campaignInfo}>
                Date Range: <strong>{dataset?.dateRangeStr}</strong> • Service Plan: <strong>{detectedMeta.servicePlanName}</strong>
              </div>
            </div>
          )}

          {/* Metrics Summary Cards */}
          {dataset && (
            <div className={styles.metricsGrid}>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Total Triggers</div>
                <div className={styles.metricValue}>{dataset.totalTriggers}</div>
                <div className={styles.metricSub}>{dataset.deliveredCount} Delivered ({Math.round((dataset.deliveredCount / dataset.totalTriggers) * 100)}%)</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Hot Leads (Converted)</div>
                <div className={styles.metricValue} style={{ color: '#ea580c' }}>{dataset.hotCount}</div>
                <div className={styles.metricSub}>Service Booked = Yes</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Warm Leads</div>
                <div className={styles.metricValue} style={{ color: '#d97706' }}>{dataset.warmCount}</div>
                <div className={styles.metricSub}>Follow-up, Callback, Inquiry</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Hot + Warm Total</div>
                <div className={styles.metricValue} style={{ color: 'var(--accent-p)' }}>{dataset.hotWarmTotal}</div>
                <div className={styles.metricSub}>{dataset.hotWarmPercent.toFixed(1)}% Conversion Rate</div>
              </div>
              <div className={styles.metricCard}>
                <div className={styles.metricLabel}>Dispositions Corrected</div>
                <div className={styles.metricValue}>{dataset.correctionsCount}</div>
                <div className={styles.metricSub}>Logged in Corrections Sheet</div>
              </div>
            </div>
          )}

          {/* Action Bar & Controls */}
          {dataset && (
            <div className={styles.actionBar}>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={handleExportExcel}>
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Export Custom Report (.xlsx)
                </button>
                <button className={`${styles.btn} ${styles.btnOutline}`} onClick={handleCopyData}>
                  <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                  </svg>
                  Copy Leads (TSV)
                </button>
              </div>

              <div className={styles.searchBox}>
                <svg className={styles.searchIcon} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  className={styles.searchInput}
                  placeholder="Filter leads by name, phone, reg..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Live Preview Table */}
          {dataset && (
            <div className={styles.tableContainer}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Name</th>
                    <th>Phone Number</th>
                    <th>Lead Category</th>
                    <th>Service Booked?</th>
                    <th>Registration No.</th>
                    <th>Vehicle Model</th>
                    <th>Showroom</th>
                    <th>Confirmed Date</th>
                    <th>Confirmed Time</th>
                    <th>Disposition</th>
                    <th>Booked Location</th>
                    <th>Message Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.slice(0, 100).map((lead, idx) => (
                    <tr key={`${lead.phoneNumber}_${idx}`}>
                      <td style={{ color: 'var(--text-muted)' }}>{idx + 1}</td>
                      <td style={{ fontWeight: 600 }}>{lead.name}</td>
                      <td style={{ fontFamily: 'var(--mono)' }}>{lead.phoneNumber}</td>
                      <td>
                        <span className={lead.leadCategory === 'Hot - Converted' ? styles.pillHot : styles.pillWarm}>
                          {lead.leadCategory}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center', fontWeight: 600, color: lead.serviceBooked === 'Yes' ? '#22c55e' : 'inherit' }}>
                        {lead.serviceBooked}
                      </td>
                      <td style={{ fontFamily: 'var(--mono)' }}>{lead.regNumber}</td>
                      <td>{lead.vehicleModel}</td>
                      <td>{lead.showroomLocation}</td>
                      <td>{lead.confirmedDateReply}</td>
                      <td>{lead.confirmedTimeReply}</td>
                      <td>{lead.dispositionDetail}</td>
                      <td style={{ fontWeight: 600 }}>{lead.appointmentBookedLocation}</td>
                      <td style={{ maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {lead.messageReplySummary}
                      </td>
                    </tr>
                  ))}
                  {filteredLeads.length === 0 && (
                    <tr>
                      <td colSpan={13} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                        No leads match search filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
