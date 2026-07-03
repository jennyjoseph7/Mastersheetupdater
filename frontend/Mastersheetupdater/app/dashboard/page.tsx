'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import Nav from '@/components/Nav';
import BrandLogo from '@/components/BrandLogo';
import ThemeToggle from '@/components/ThemeToggle';
import ProcessingOverlay from '@/components/ProcessingOverlay';
import StatusBar from '@/components/StatusBar';
import { readFileAsArrayBuffer, validateFileSync } from '@/lib/data-pipeline';
import { getApiEndpoint, getLlmModel } from '@/lib/ai/ai-config';
import {
  ColMap, FunnelData, DispoData, SourceResult, TrendsData, BlockersData, ThemeData, RecData,
  fd, nm, nf, esc, hasAny, detectCampaignType, aFunn, aDisp, aBlk, aTr, aSrc,
  isConnected, mineCustomerThemes, generateStoryHeadline, generateExecutiveNarrative,
  generateRecommendations, analyzeCompetitiveLosses, analyzeCallbackBehavior,
  DISPO_DESCRIPTIONS, DISPO_TO_THEME, maybeGetDataHash, keywordFallback,
} from '@/lib/ai/dashboard-analysis';
import * as XLSX from 'xlsx';
import styles from './dashboard.module.css';

let ChartModule: any = null;

function sanitizeHtml(html: string): string {
  return html.replace(/<script[\s\S]*?<\/script>/gi, '').replace(/<[^>]*>/g, (match) => {
    if (/^<\/?(strong|b|em|i|br\s*\/?)>$/i.test(match)) return match;
    return match.replace(/[<>]/g, (c) => (c === '<' ? '&lt;' : '&gt;'));
  });
}

const MONTH_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const LLM_CACHE_VERSION = 'gryd-dispo-v1';
const LLM_REQUEST_TIMEOUT_MS = 70000;

interface KpiCard {
  label: string;
  value: number | string;
  sub?: string;
  badge?: { text: string; color: string } | null;
}

interface KpiEditState {
  editing: boolean;
  inputValue: string;
}

export default function DashboardPage() {
  const log = (...args) => console.log('[Dashboard]', ...args);
  log('Page mounted');
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [colMap, setColMap] = useState<ColMap>({ phone: null, outcome: null, status: null, date: null, model: null, detail: null, summary: null, updatedSummary: null, updatedDisposition: null, source: null, nextService: null, lastService: null, serviceType: null, duration: null });
  const [fileStatus, setFileStatus] = useState('No file selected');
  const [hasFile, setHasFile] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [mode, setMode] = useState('auto');
  const [isPostSales, setIsPostSales] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const [kpiCards, setKpiCards] = useState<KpiCard[]>([]);
  const [kpiOverrides, setKpiOverrides] = useState<Record<string, number>>({});
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
  const [dispoData, setDispoData] = useState<DispoData | null>(null);
  const [sourceData, setSourceData] = useState<SourceResult | null>(null);
  const [trendsData, setTrendsData] = useState<TrendsData | null>(null);
  const [blockersData, setBlockersData] = useState<BlockersData | null>(null);
  const [dailyCounts, setDailyCounts] = useState<Record<string, number>>({});
  const [modelCounts, setModelCounts] = useState<Record<string, number>>({});
  const [uniqueLeadCount, setUniqueLeadCount] = useState(0);
  const [avgCallsPerLead, setAvgCallsPerLead] = useState(0);
  const [vmCount, setVmCount] = useState(0);
  const [cbCount, setCbCount] = useState(0);
  const [bookings, setBookings] = useState(0);
  const [followUpReq, setFollowUpReq] = useState(0);
  const [serviceCompleted, setServiceCompleted] = useState(0);
  const [invalidLead, setInvalidLead] = useState(0);
  const [kpiEditState, setKpiEditState] = useState<Record<string, KpiEditState>>({});
  const [chartReady, setChartReady] = useState(false);
  const [kpiApplyCounter, setKpiApplyCounter] = useState(0);

  // AI state
  const [aiRunning, setAiRunning] = useState(false);
  const [aiAborted, setAiAborted] = useState(false);
  const [aiCompleted, setAiCompleted] = useState(false);
  const [aiProgress, setAiProgress] = useState({ done: 0, total: 0, message: '' });
  const [aiThemes, setAiThemes] = useState<ThemeData[]>([]);
  const [aiRecs, setAiRecs] = useState<RecData[]>([]);
  const [aiNarrative, setAiNarrative] = useState('');
  const [aiHeadline, setAiHeadline] = useState('');
  const [aiResultsCached, setAiResultsCached] = useState(false);

  const dailyChartRef = useRef<HTMLCanvasElement>(null);
  const ratesChartRef = useRef<HTMLCanvasElement>(null);
  const connDispChartRef = useRef<HTMLCanvasElement>(null);
  const notConnChartRef = useRef<HTMLCanvasElement>(null);
  const modelChartRef = useRef<HTMLCanvasElement>(null);
  const dispoChartRef = useRef<HTMLCanvasElement>(null);
  const sourceChartRef = useRef<HTMLCanvasElement>(null);
  const chartInstancesRef = useRef<Record<string, any>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const aiCancelRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) router.push('/login');
  }, [loading, isAuthenticated, router]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      import('chart.js/auto').then(mod => { ChartModule = mod; setChartReady(true); });
    }
  }, []);

  useEffect(() => {
    if (showContent && chartReady) renderCharts();
  }, [showContent, chartReady, kpiApplyCounter]);

  if (!isAuthenticated && !loading) return null;

  function destroyCharts() {
    Object.values(chartInstancesRef.current).forEach((c: any) => { if (c?.destroy) c.destroy(); });
    chartInstancesRef.current = {};
  }

  function getKpi(label: string, defaultVal: number | string): number | string {
    const upper = label.toUpperCase();
    for (const [k, v] of Object.entries(kpiOverrides)) {
      if (k.toUpperCase() === upper) return v;
    }
    return defaultVal;
  }

  function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return { text: isDark ? '#c9c8c2' : '#3a3a38', muted: isDark ? '#9b9a94' : '#6b6a65', grid: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)', border: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' };
  }

  function formatDateShort(d: Date): string {
    return d.getDate() + ' ' + MONTH_SHORT[d.getMonth()] + ' ' + d.getFullYear();
  }

  function formatDateLabelFromKey(key: string): string {
    const parts = key.split('-').map(Number);
    if (parts.length !== 3) return key;
    return formatDateShort(new Date(parts[0], parts[1] - 1, parts[2]));
  }

  function renderDailyChart() {
    if (!ChartModule || !dailyChartRef.current) return;
    if (chartInstancesRef.current.fdaily) chartInstancesRef.current.fdaily.destroy();
    const entries = Object.entries(dailyCounts).sort((a, b) => a[0].localeCompare(b[0]));
    if (!entries.length) return;
    const colors = getChartColors();
    chartInstancesRef.current.fdaily = new ChartModule.Chart(dailyChartRef.current, {
      type: 'bar',
      data: { labels: entries.map(e => formatDateLabelFromKey(e[0])), datasets: [{ label: 'Calls', data: entries.map(e => e[1]), backgroundColor: '#3b82f6', borderRadius: 5 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: any) => ' ' + ctx.parsed.x + ' calls' } } }, scales: { x: { beginAtZero: true, ticks: { color: colors.muted }, grid: { color: colors.grid } }, y: { ticks: { color: colors.text }, grid: { display: false } } } }
    });
  }

  function renderCharts() {
    if (!ChartModule) return;
    const colors = getChartColors();
    if (dailyChartRef.current && Object.keys(dailyCounts).length) {
      if (chartInstancesRef.current.daily) chartInstancesRef.current.daily.destroy();
      const entries = Object.entries(dailyCounts).sort((a, b) => a[0].localeCompare(b[0]));
      chartInstancesRef.current.daily = new ChartModule.Chart(dailyChartRef.current, {
        type: 'bar', data: { labels: entries.map(e => e[0]), datasets: [{ label: 'Calls', data: entries.map(e => e[1]), backgroundColor: '#3b82f6', borderRadius: 5 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { color: colors.muted }, grid: { color: colors.grid } }, y: { ticks: { color: colors.text }, grid: { display: false } } } }
      });
    }
    if (ratesChartRef.current && funnelData) {
      if (chartInstancesRef.current.rc) chartInstancesRef.current.rc.destroy();
      const total = getKpi('TOTAL ATTEMPTS', funnelData.total) as number;
      const connected = getKpi('CONNECTED', funnelData.connected) as number;
      const nc = getKpi('NOT CONNECTED', funnelData.notConnected) as number;
      chartInstancesRef.current.rc = new ChartModule.Chart(ratesChartRef.current, {
        type: 'bar', data: { labels: ['Connected', 'Not Connected'], datasets: [{ data: total > 0 ? [(connected / total * 100).toFixed(1), (nc / total * 100).toFixed(1)] : [0, 0], backgroundColor: ['#63d6a3', '#6b6b6b'], borderRadius: 5 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { max: 100, ticks: { callback: (v: number) => v + '%' } } } }
      });
    }
    if (dispoChartRef.current && dispoData) {
      if (chartInstancesRef.current.d) chartInstancesRef.current.d.destroy();
      const pal = ['#5b9cf5', '#a78bfa', '#63d6a3', '#eab308', '#f16f6f', '#f472b6', '#5eead4', '#6b6b6b', '#adaaaa'];
      chartInstancesRef.current.d = new ChartModule.Chart(dispoChartRef.current, {
        type: 'bar', data: { labels: dispoData.top.map(e => e[0]), datasets: [{ data: dispoData.top.map(e => e[1]), backgroundColor: dispoData.top.map((_, i) => pal[i % pal.length]), borderRadius: 4 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx: any) => { const pct = dispoData!.total > 0 ? (ctx.parsed.x / dispoData!.total * 100).toFixed(1) : '0.0'; const desc = DISPO_DESCRIPTIONS[ctx.label] || ''; return (desc ? ' ' + desc + ': ' : ' ') + ctx.parsed.x + ' (' + pct + '%)'; } } } }, scales: { x: { beginAtZero: true }, y: { grid: { display: false } } } }
      });
    }
    if (modelChartRef.current) {
      if (chartInstancesRef.current.rmc) chartInstancesRef.current.rmc.destroy();
      const entries = Object.entries(modelCounts).sort((a, b) => b[1] - a[1]).slice(0, 10);
      const pal = ['#5b9cf5', '#a78bfa', '#63d6a3', '#eab308', '#f16f6f', '#f472b6', '#5eead4', '#6b6b6b', '#adaaaa', '#8896a6'];
      chartInstancesRef.current.rmc = new ChartModule.Chart(modelChartRef.current, {
        type: 'bar', data: { labels: entries.map(e => e[0]), datasets: [{ data: entries.map(e => e[1]), backgroundColor: pal.slice(0, entries.length), borderRadius: 4 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
      });
    }
    // Connected dispositions chart
    if (connDispChartRef.current && dispoData && funnelData) {
      if (chartInstancesRef.current.rdc) chartInstancesRef.current.rdc.destroy();
      let vmD = 0, wnD = 0, niD = 0, bkD = 0, otD = 0;
      dispoData.top.forEach(([l, c]) => {
        const lc = l.toLowerCase();
        if (lc.includes('voicemail') || lc.includes('vm')) vmD += c;
        else if (lc.includes('callback') || lc.includes('follow') || lc.includes('warm')) wnD += c;
        else if (lc.includes('not interested') || lc.includes('rejected') || lc.includes('unsubscribed') || lc.includes('no interest')) niD += c;
        else if (lc.includes('booked') || lc.includes('converted') || lc.includes('confirmed') || lc.includes('book')) bkD += c;
        else otD += c;
      });
      chartInstancesRef.current.rdc = new ChartModule.Chart(connDispChartRef.current, {
        type: 'bar', data: { labels: ['Voicemail', 'Warm', 'Not interested', 'Booked', 'Others'], datasets: [{ data: [vmD, wnD, niD, bkD, otD], backgroundColor: ['#a78bfa', '#63d6a3', '#adaaaa', '#1a9960', '#5b9cf5'], borderRadius: 4 }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: colors.muted }, grid: { color: colors.grid } }, y: { grid: { display: false } } } }
      });
    }
    // Not-connected breakdown chart
    if (notConnChartRef.current && dispoData && funnelData) {
      if (chartInstancesRef.current.rnc) chartInstancesRef.current.rnc.destroy();
      let busy = 0, noAns = 0, othNC = 0;
      dispoData.top.forEach(([l, c]) => {
        const lc = l.toLowerCase();
        if (lc.includes('busy') || lc.includes('engaged')) busy += c;
        else if (lc.includes('no answer') || lc.includes('unavailable') || lc.includes('no response') || lc.includes('no ans')) noAns += c;
        else if (!lc.includes('voicemail') && !lc.includes('callback') && !lc.includes('follow') && !lc.includes('booked') && !lc.includes('converted') && !lc.includes('interested')) othNC += c;
      });
      const ncT = busy + noAns + othNC;
      if (ncT === 0 && funnelData.notConnected > 0) { noAns = funnelData.notConnected; busy = 0; othNC = 0; }
      const ncLabels: string[] = [], ncData: number[] = [], ncColors: string[] = [];
      if (busy > 0) { ncLabels.push('Busy'); ncData.push(busy); ncColors.push('#6b6b6b'); }
      if (noAns > 0) { ncLabels.push('No Answer'); ncData.push(noAns); ncColors.push('#adaaaa'); }
      if (othNC > 0) { ncLabels.push('Other'); ncData.push(othNC); ncColors.push('#8896a6'); }
      if (ncData.length) {
        chartInstancesRef.current.rnc = new ChartModule.Chart(notConnChartRef.current, {
          type: 'bar', data: { labels: ncLabels, datasets: [{ data: ncData, backgroundColor: ncColors, borderRadius: 4 }] },
          options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { color: colors.muted }, grid: { color: colors.grid } }, y: { grid: { display: false } } } }
        });
      }
    }
    // Source comparison chart
    if (sourceChartRef.current && sourceData && sourceData.sources.length > 0) {
      if (chartInstancesRef.current.src) chartInstancesRef.current.src.destroy();
      const labels = sourceData.sources.map(s => s.name);
      chartInstancesRef.current.src = new ChartModule.Chart(sourceChartRef.current, {
        type: 'polarArea',
        data: {
          labels,
          datasets: [{
            data: sourceData.sources.map(s => parseFloat(s.connRate)),
            backgroundColor: sourceData.sources.map((_, i) => {
              const pal = ['#63d6a3', '#3b82f6', '#eab308', '#a78bfa', '#f472b6', '#5eead4', '#f97316', '#ef4444', '#8896a6'];
              return pal[i % pal.length] + 'CC';
            }),
            borderColor: sourceData.sources.map((_, i) => {
              const pal = ['#63d6a3', '#3b82f6', '#eab308', '#a78bfa', '#f472b6', '#5eead4', '#f97316', '#ef4444', '#8896a6'];
              return pal[i % pal.length];
            }),
            borderWidth: 1,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { position: 'right', labels: { boxWidth: 12, padding: 8, color: colors.text, font: { size: 10 } } },
            tooltip: { callbacks: { label: (ctx: any) => ' ' + ctx.label + ': ' + ctx.parsed.r + '%' } },
          },
          scales: { r: { beginAtZero: true, max: 100, ticks: { color: colors.muted, backdropColor: 'transparent', font: { size: 9 }, callback: (v: any) => v + '%' }, grid: { color: colors.grid } } },
        },
      });
    }
  }

  // KPI editing
  function handleKpiEditStart(label: string, currentVal: number | string) {
    setKpiEditState(prev => ({ ...prev, [label]: { editing: true, inputValue: String(currentVal) } }));
  }

  function handleKpiEditChange(label: string, value: string) {
    setKpiEditState(prev => ({ ...prev, [label]: { ...prev[label], inputValue: value } }));
  }

  function handleKpiEditApply(label: string) {
    const state = kpiEditState[label];
    if (!state) return;
    const n = Math.max(0, parseInt(state.inputValue.replace(/[^\d]/g, ''), 10) || 0);
    setKpiOverrides(prev => ({ ...prev, [label.toUpperCase()]: n }));
    setKpiEditState(prev => ({ ...prev, [label]: { ...prev[label], editing: false } }));
    setKpiApplyCounter(c => c + 1);
  }

  function handleKpiEditCancel(label: string) {
    setKpiEditState(prev => ({ ...prev, [label]: { ...prev[label], editing: false } }));
  }

  function handleKpiEditReset(label: string, original: number | string) {
    setKpiOverrides(prev => {
      const next = { ...prev };
      delete next[label.toUpperCase()];
      return next;
    });
    setKpiEditState(prev => ({ ...prev, [label]: { editing: false, inputValue: String(original) } }));
  }

  function generateDashboard() {
    if (!rows.length) { setErrorMsg('Upload a file first.'); return; }
    setProcessing(true);
    setErrorMsg('');
    destroyCharts();
    setShowContent(false);
    setAiThemes([]);
    setAiRecs([]);
    setAiNarrative('');
    setAiHeadline('');
    setAiCompleted(false);
    setAiAborted(false);
    setKpiOverrides({});

    const cm: ColMap = {
      phone: fd(rows, ['phone_number', 'phonenumber', 'phone', 'mobile']),
      outcome: fd(rows, ['outcome', 'disposition', 'call_outcome', 'calloutcome']),
      status: fd(rows, ['status', 'call_status', 'session_status']),
      date: fd(rows, ['call_date', 'calldate']),
      model: fd(rows, ['vehicle_model', 'vehiclemodel', 'model', 'model_preference', 'car_model']),
      detail: fd(rows, ['disposition_detail', 'dispositiondetail', 'detail', 'disposition_details']),
      summary: fd(rows, ['summary', 'call_summary', 'callsummary']),
      updatedSummary: fd(rows, ['updated_summary', 'updatedsummary', 'updated summary']),
      updatedDisposition: fd(rows, ['updated_disposition', 'updated disposition', 'updated_disposition_details', 'updated disposition details']),
      source: fd(rows, ['campaign_id', 'campaign', 'workshop_code', 'dealer_code', 'showroom_code', 'source', 'campaignid']),
      nextService: fd(rows, ['next_service_due', 'next_service_date', 'next_service']),
      lastService: fd(rows, ['last_service_date', 'last_service']),
      serviceType: fd(rows, ['service_type', 'next_service_type']),
      duration: fd(rows, ['call_duration', 'duration', 'talk_time', 'conversation_duration', 'call_duration_seconds']),
    };
    if (!cm.date) { setProcessing(false); setErrorMsg('Required column Call_Date not found.'); return; }
    setColMap(cm);

    const isPS = mode === 'post' || (mode === 'auto' && detectCampaignType(rows, cm));
    setIsPostSales(isPS);

    let vm = 0, followUpReq_ = 0, serviceCompleted_ = 0, cb = 0, iL = 0, ct = 0, totalConvDuration = 0;
    const dc: Record<string, number> = {}, mc: Record<string, number> = {};
    const attemptsPerPhone = new Map<string, number>();
    const connectedPhones = new Set<string>();

    for (const x of rows) {
      const dt = nm(x[cm.detail || ''] || '');
      const su = nm(x[cm.summary || ''] || '');
      const ud = cm.updatedDisposition ? nm(x[cm.updatedDisposition]) : '';
      ct++;
      if (cm.duration && isConnected(x, cm, isPS) && (ud === 'converted' || ud === 'follow up required' || ud === 'follow-up required' || dt.includes('converted') || dt.includes('follow up required') || dt.includes('follow-up required'))) {
        const raw = String(x[cm.duration] || '').trim();
        const sec = parseInt(raw, 10);
        totalConvDuration += (isNaN(sec) ? 0 : sec);
      }
      if (ud === 'voicemail' || dt.includes('voicemail')) vm++;
      if (ud === 'requested callback' || dt.includes('callback') || su.includes('callback') || su.includes('call back')) cb++;
      if (isPS) {
        if (ud === 'follow up required' || dt.includes('follow up required')) followUpReq_++;
      } else {
        if (ud === 'follow up required' || ud === 'follow-up required') followUpReq_++;
        if (ud === 'existing dealer contact' || ud === 'has serviced car in another dealership') serviceCompleted_++;
      }
      if (dt.includes('invalid') || ud.includes('invalid')) iL++;
      const dv = cm.date ? String(x[cm.date] || '').trim() : '';
      if (dv) dc[dv] = (dc[dv] || 0) + 1;
      const mv = cm.model ? String(x[cm.model] || '').trim() : '';
      if (mv) mc[mv] = (mc[mv] || 0) + 1;
      if (cm.phone) {
        const phoneRaw = String(x[cm.phone] || '').replace(/\D/g, '');
        const phoneKey = phoneRaw.length > 10 ? phoneRaw.slice(-10) : phoneRaw;
        if (phoneKey) {
          attemptsPerPhone.set(phoneKey, (attemptsPerPhone.get(phoneKey) || 0) + 1);
          if (isConnected(x, cm, isPS)) connectedPhones.add(phoneKey);
        }
      }
    }

    const uniqueLeads = attemptsPerPhone.size;
    const uniqueConnected = connectedPhones.size;
    const avgAttempts = uniqueLeads > 0 ? Math.round((ct / uniqueLeads) * 10) / 10 : 0;
    let oneAttempt = 0, twoAttempts = 0, threeToFive = 0, sixPlus = 0;
    attemptsPerPhone.forEach(calls => {
      if (calls === 1) oneAttempt++;
      else if (calls === 2) twoAttempts++;
      else if (calls <= 5) threeToFive++;
      else sixPlus++;
    });
    const callDistParts: string[] = [];
    if (oneAttempt > 0) callDistParts.push(`1×: ${nf(oneAttempt)}`);
    if (twoAttempts > 0) callDistParts.push(`2×: ${nf(twoAttempts)}`);
    if (threeToFive > 0) callDistParts.push(`3–5×: ${nf(threeToFive)}`);
    if (sixPlus > 0) callDistParts.push(`6+×: ${nf(sixPlus)}`);
    const callDist = callDistParts.join(' · ');

    const funnel = aFunn(rows, cm, isPS);
    const dispos = aDisp(rows, cm);
    const srcQ = aSrc(rows, cm, isPS);
    const trends = aTr(rows, dc);
    const blockers = aBlk(rows, cm, isPS);

    setDailyCounts(dc);
    setModelCounts(mc);
    setFunnelData(funnel);
    setDispoData(dispos);
    setSourceData(srcQ);
    setTrendsData(trends);
    setBlockersData(blockers);
    setVmCount(vm);
    setCbCount(cb);
    setBookings(funnel.booked);
    setFollowUpReq(followUpReq_);
    setServiceCompleted(serviceCompleted_);
    setUniqueLeadCount(uniqueLeads);
    setAvgCallsPerLead(avgAttempts);
    setInvalidLead(iL);

    const bookingLabel = isPS ? 'SERVICE BOOKED' : 'TEST DRIVE BOOKED';
    const connPct = funnel.total ? (funnel.connected / funnel.total * 100).toFixed(0) : '0';
    const notConnPct = funnel.total ? (funnel.notConnected / funnel.total * 100).toFixed(0) : '0';
    const vmPct = funnel.connected ? (vm / funnel.connected * 100).toFixed(0) : '0';
    const bkPct = funnel.connected ? (funnel.booked / funnel.connected * 100).toFixed(0) : '0';
    const fuPct = funnel.connected ? (followUpReq_ / funnel.connected * 100).toFixed(0) : '0';
    const cbPct = funnel.connected ? (cb / funnel.connected * 100).toFixed(0) : '0';
    const avgConv = funnel.booked && totalConvDuration ? Math.round(totalConvDuration / funnel.booked) : 0;
    const avgConvStr = avgConv >= 60 ? Math.floor(avgConv / 60) + 'm ' + (avgConv % 60) + 's' : (avgConv || '--') + 's';
    const cards: KpiCard[] = [
      { label: 'TOTAL ATTEMPTS', value: ct },
      { label: 'UNIQUE CALLS', value: uniqueLeads },
      { label: 'ATTEMPTS PER LEAD', value: avgAttempts, sub: `${nf(uniqueLeads)} leads · ${callDist}` },
      { label: 'CONNECTED', value: funnel.connected, badge: { text: connPct + '%', color: 'green' } },
      { label: 'UNIQUE CONNECTED', value: uniqueConnected, badge: { text: (uniqueLeads ? (uniqueConnected / uniqueLeads * 100).toFixed(0) : '0') + '%', color: 'green' } },
      { label: 'AVG CONVERSATION', value: avgConvStr, sub: avgConv ? `${avgConv}s · per ${funnel.booked} bookings` : 'no duration data' },
      { label: 'NOT CONNECTED', value: funnel.notConnected, badge: { text: notConnPct + '%', color: 'red' } },
      { label: 'VOICEMAIL', value: vm, sub: vmPct + '%' },
      { label: bookingLabel, value: funnel.booked, badge: funnel.booked ? { text: bkPct + '%', color: 'green' } : null },
      { label: 'FOLLOW-UP REQUIRED', value: followUpReq_, sub: fuPct + '%' },
      { label: 'REQUESTED CALLBACK', value: cb, sub: cbPct + '%' },
      { label: 'INVALID LEAD', value: iL },
    ];
    if (isPS) cards.push({ label: 'SERVICE COMPLETED', value: serviceCompleted_ });
    setKpiCards(cards);
    setShowContent(true);
    setProcessing(false);
  }

  // AI Analysis
  async function runAiAnalysis() {
    if (!rows.length || !colMap.date) return;
    setAiRunning(true);
    setAiAborted(false);
    setAiCompleted(false);
    setAiProgress({ done: 0, total: 1, message: 'Analyzing campaign data...' });
    aiCancelRef.current = new AbortController();

    const isPS = isPostSales;
    const themes = mineCustomerThemes(rows, colMap, isPS);
    const funnel = aFunn(rows, colMap, isPS);
    const trends = aTr(rows, dailyCounts);
    const competitors = analyzeCompetitiveLosses(rows, colMap);
    const callbacks = analyzeCallbackBehavior(rows, colMap);
    const headline = generateStoryHeadline(themes, funnel);
    const execNarrative = generateExecutiveNarrative(themes, funnel, trends, isPS);
    const recs = generateRecommendations(themes, funnel, competitors, callbacks, trends);

    // Try to get LLM-based recommendations
    try {
      const llmRecs = await fetchLlmRecommendations(funnel, themes, isPS);
      if (llmRecs && llmRecs.length > 0) {
        setAiRecs(llmRecs);
      } else {
        setAiRecs(recs);
      }
    } catch {
      setAiRecs(recs);
    }

    if (!aiCancelRef.current?.signal.aborted) {
      setAiThemes(themes);
      setAiHeadline(headline);
      setAiNarrative(execNarrative);
      setAiCompleted(true);
      setAiRunning(false);
      setAiProgress({ done: 1, total: 1, message: 'AI analysis complete.' });

      // Cache
      try {
        const dataHash = maybeGetDataHash(rows, colMap, isPS);
        localStorage.setItem('dashAiCache', JSON.stringify({ hash: dataHash, themes, headline, execNarrative, recs, ts: Date.now() }));
      } catch {}
    }
  }

  async function fetchLlmRecommendations(funnel: FunnelData, themes: ThemeData[], isPS: boolean): Promise<RecData[] | null> {
    try {
      const topThemes = themes.slice(0, 5).map(t => esc(t.label) + ': ' + t.count).join(', ');
      const connPct = funnel.connected > 0 ? (funnel.booked / funnel.connected * 100).toFixed(1) : '0';
      const summary = `Campaign: ${isPS ? 'Post-Sales' : 'Pre-Sales'}. Total leads: ${funnel.total}, Connected: ${funnel.connected}, Booked: ${funnel.booked} (${connPct}% conversion). Top themes: ${topThemes}.`;
      const prompt = `As a senior campaign analyst, generate 3-5 specific, actionable recommendations based on this data. For each: specify what to do, why (with data support), and estimated impact.\n\n${summary}\n\nRespond ONLY with a valid JSON array: [{"action":"...","reason":"...","impact":"..."}]`;
      const response = await fetch(getApiEndpoint(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-GRYD-TOKEN': sessionStorage.getItem('gryd_token') || '', 'X-GRYD-SESSION-ID': sessionStorage.getItem('gryd_session_id') || '', 'X-GRYD-APPLICATION-ID': 'autocrm' },
        signal: aiCancelRef.current?.signal,
        body: JSON.stringify({
          model: getLlmModel(),
          messages: [{ role: 'system', content: 'You are a campaign analyst. Generate 3-5 specific, actionable recommendations. Output ONLY valid JSON array.' }, { role: 'user', content: prompt }],
          temperature: 0.3, max_tokens: 1200,
        }),
      });
      if (!response.ok) return null;
      const data = await response.json();
      const text = data?.choices?.[0]?.message?.content;
      if (!text) return null;
      const cleaned = text.replace(/```json\s*/gi, '').replace(/```/g, '').trim();
      const match = cleaned.match(/\[[\s\S]*\]/);
      if (!match) return null;
      return JSON.parse(match[0]);
    } catch { return null; }
  }

  function cancelAi() {
    aiCancelRef.current?.abort();
    setAiAborted(true);
    setAiRunning(false);
    setAiProgress({ done: 0, total: 0, message: 'Cancelled.' });
  }

  function dismissAi() {
    setAiCompleted(false);
    setAiAborted(false);
    setAiProgress({ done: 0, total: 0, message: '' });
  }

  function handleFileUpload(file: File) {
    const v = validateFileSync(file);
    if (!v.valid) { setFileStatus(v.error!); return; }
    setProcessing(true);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const wb = XLSX.read(e.target?.result, { type: 'array', cellDates: false, raw: true });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const j = XLSX.utils.sheet_to_json(ws, { defval: '' }) as Record<string, string>[];
        if (!j || !j.length) { setFileStatus('Empty'); setProcessing(false); return; }
        setRows(j);
        setFileStatus(`${j.length} rows`);
        setHasFile(true);
        log('File processed:', file.name, j.length, 'rows');
        // Try restore cached AI
        tryRestoreCachedAi(j, cm => {
          setColMap(cm);
          // Need to run gen to see if we can auto-restore
        });
      } catch (ex: unknown) {
        setFileStatus('Parse error');
        setErrorMsg(`Parse: ${ex instanceof Error ? ex.message : 'Unknown'}`);
      }
      setProcessing(false);
    };
    reader.readAsArrayBuffer(file);
  }

  function tryRestoreCachedAi(j: Record<string, string>[], setCm: (cm: ColMap) => void) {
    try {
      const cached = localStorage.getItem('dashAiCache');
      if (!cached) return;
      const cc = JSON.parse(cached);
      if (!cc || !cc.hash) return;
      const isPS = mode === 'post' || false;
      const cm: ColMap = {
        phone: fd(j, ['phone_number', 'phonenumber', 'phone', 'mobile']),
        outcome: fd(j, ['outcome', 'disposition', 'call_outcome', 'calloutcome']),
        status: fd(j, ['status', 'call_status', 'session_status']),
        date: fd(j, ['call_date', 'calldate']),
        model: fd(j, ['vehicle_model', 'vehiclemodel', 'model', 'model_preference', 'car_model']),
        detail: fd(j, ['disposition_detail', 'dispositiondetail', 'detail', 'disposition_details']),
        summary: fd(j, ['summary', 'call_summary', 'callsummary']),
        updatedSummary: fd(j, ['updated_summary', 'updatedsummary', 'updated summary']),
        updatedDisposition: fd(j, ['updated_disposition', 'updated disposition', 'updated_disposition_details', 'updated disposition details']),
        source: fd(j, ['campaign_id', 'campaign', 'workshop_code', 'dealer_code', 'showroom_code', 'source', 'campaignid']),
        nextService: fd(j, ['next_service_due', 'next_service_date', 'next_service']),
        lastService: fd(j, ['last_service_date', 'last_service']),
        serviceType: fd(j, ['service_type', 'next_service_type']),
        duration: fd(j, ['call_duration', 'duration', 'talk_time', 'conversation_duration', 'call_duration_seconds']),
      };
      const currentHash = maybeGetDataHash(j, cm, isPS);
      if (cc.hash === currentHash && Date.now() - cc.ts < 86400000) {
        if (cc.themes) setAiThemes(cc.themes);
        if (cc.headline) setAiHeadline(cc.headline);
        if (cc.execNarrative) setAiNarrative(cc.execNarrative);
        if (cc.recs) setAiRecs(cc.recs);
        if (cc.themes || cc.headline) setAiResultsCached(true);
      }
    } catch {}
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) { log('File selected:', f.name); handleFileUpload(f); }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileUpload(f);
  }

  // PDF export
  async function printPDF() {
    try {
      const dti = await import('dom-to-image-more');
      const { jsPDF } = await import('jspdf');
      setProcessing(true);

      // Swap chart canvases to images so they render in the capture
      const chartRefs = [dailyChartRef, ratesChartRef, connDispChartRef, notConnChartRef, modelChartRef, dispoChartRef, sourceChartRef];
      const saved: { canvas: HTMLCanvasElement; img: HTMLImageElement; parent: HTMLElement | null }[] = [];
      for (const ref of chartRefs) {
        const canvas = ref.current;
        if (!canvas || !canvas.parentNode) continue;
        const img = document.createElement('img');
        img.src = canvas.toDataURL();
        img.style.cssText = canvas.style.cssText;
        canvas.parentNode.replaceChild(img, canvas);
        saved.push({ canvas, img, parent: canvas.parentNode as HTMLElement });
      }

      const el = document.getElementById('dashboard-content');
      if (!el) { setProcessing(false); return; }
      const capCanvas = await dti.toCanvas(el, { scale: 2, filter: n => !(n instanceof HTMLElement && n.dataset.print === 'hide') });

      // Restore chart canvases
      for (const { canvas, img, parent } of saved) {
        if (parent) parent.replaceChild(canvas, img);
      }
      const imgData = capCanvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pw = pdf.internal.pageSize.getWidth();
      const ph = pdf.internal.pageSize.getHeight();

      // Accent header bar
      const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim();
      const m = accent.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
      if (m) pdf.setFillColor(parseInt(m[1],16), parseInt(m[2],16), parseInt(m[3],16));
      else pdf.setFillColor(239, 68, 68);
      const barH = 8;
      pdf.rect(0, 0, pw, barH, 'F');
      pdf.setFontSize(8);
      pdf.setTextColor(255,255,255);
      pdf.text('Campaign Dashboard — ' + new Date().toLocaleDateString('en-IN'), 3, 5.5);

      const r = capCanvas.width / capCanvas.height;
      const availH = ph - barH - 2;
      let iw = pw, ih = pw / r;
      if (ih > availH) { ih = availH; iw = availH * r; }
      pdf.addImage(imgData, 'PNG', (pw - iw) / 2, barH + 2, iw, ih);
      pdf.save('campaign-dashboard.pdf');
      setProcessing(false);
    } catch (e) {
      console.error('[PDF] Error:', e);
      setProcessing(false);
    }
  }

  const topModels = Object.entries(modelCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const topModelName = topModels[0]?.[0] || '--';
  const topModelCount = topModels[0]?.[1] || 0;
  const dateKeys = Object.keys(dailyCounts).sort();
  const bookingLabel = isPostSales ? 'SERVICE BOOKED' : 'TEST DRIVE BOOKED';
  const fTotal = funnelData ? (getKpi('TOTAL ATTEMPTS', funnelData.total) as number) : 0;
  const fConnected = funnelData ? (getKpi('CONNECTED', funnelData.connected) as number) : 0;
  const fBookLabel = bookingLabel;
  const fBooked = funnelData ? (getKpi(fBookLabel, funnelData.booked) as number) : 0;

  // Metric audit
  const metricAudit = [
    { label: 'Phone', found: !!colMap.phone, name: colMap.phone || '--' },
    { label: 'Status', found: !!(colMap.outcome || colMap.status), name: colMap.outcome || colMap.status || '--' },
    { label: 'Date', found: !!colMap.date, name: colMap.date || '--' },
    { label: 'Model', found: !!colMap.model, name: colMap.model || '--' },
    { label: 'Disposition', found: !!(colMap.detail || colMap.updatedDisposition), name: colMap.detail || colMap.updatedDisposition || '--' },
    { label: 'Summary', found: !!colMap.summary, name: colMap.summary || '--' },
    { label: 'Source', found: !!colMap.source, name: colMap.source || '--' },
  ];

  log('Rendering with', rows?.length || 0, 'processed rows');

  return (
    <div className="sub-page">
      <header>
        <div className="header-inner">
          <div className="header-left">
            <BrandLogo />
            <div>
              <h1>Campaign Dashboard</h1>
              <div className="header-sub">Upload Zoho export to generate insights</div>
            </div>
          </div>
          <div className="header-right">
            <Nav />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem' }}>
        {/* Upload Section */}
        <div className={styles['upload-section']}>
          <div className={styles['section-title']}>Upload Zoho Master Sheet Export</div>
          <div className={styles['upload-controls']}>
            <span className={styles['mode-label']}>Dashboard Mode</span>
            <select className={styles['mode-select']} value={mode} onChange={e => setMode(e.target.value)}>
              <option value="auto">Auto Detect</option>
              <option value="pre">Pre-Sales</option>
              <option value="post">Post-Sales</option>
            </select>
          </div>
          <div className={styles['upload-row']}>
            <div
              className={`${styles['drop-zone']} ${dragOver ? styles['drag-over'] : ''} ${hasFile ? styles['has-file'] : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <div className={styles['dz-icon']}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
              </div>
              <div className={styles['dz-text']}>
                <strong>Zoho Master Sheet (.xlsx / .csv)</strong>
                <small>Drop file here or click to browse</small>
              </div>
              <span className={`${styles['dz-status']} ${hasFile ? styles['ok'] : ''}`}>{fileStatus}</span>
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={handleFileChange} style={{ display: 'none' }} />
            </div>
            <button className={styles['btn-generate']} onClick={generateDashboard} disabled={!rows.length || processing}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              Generate Dashboard
            </button>
            <button className={styles['btn-ai']} onClick={runAiAnalysis} disabled={!rows.length || aiRunning} style={{ background: 'linear-gradient(135deg,#a78bfa,#5b9cf5)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', padding: '0.65rem 1.5rem', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.5rem', opacity: !rows.length || aiRunning ? 0.4 : 1 }}>
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>
              AI Summary
            </button>
            {showContent && (
              <button className={styles['btn-generate']} onClick={printPDF} style={{ background: 'var(--surface)' }}>
                <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path d="M6 9V2h12v7M6 18h12v4H6v-4zm0-6h12a2 2 0 012 2v4H4v-4a2 2 0 012-2z"/></svg>
                PDF
              </button>
            )}
          </div>
          {errorMsg && <div className={styles['error-msg']}>{errorMsg}</div>}
        </div>

        {/* AI Status */}
        {aiRunning && (
          <StatusBar
            total={aiProgress.total}
            done={aiProgress.done}
            message={aiProgress.message}
            onCancel={cancelAi}
          />
        )}
        {aiAborted && (
          <StatusBar total={0} done={0} message="AI cancelled." aborted onDismiss={dismissAi} onRerun={runAiAnalysis} />
        )}
        {aiCompleted && (
          <StatusBar total={1} done={1} message="AI analysis complete." completed onDismiss={dismissAi} onRerun={runAiAnalysis} />
        )}
        {aiResultsCached && !aiRunning && !aiCompleted && (
          <div className={styles['cache-notice']}>Cached AI results restored from previous session.</div>
        )}

        {/* Empty State */}
        {!showContent && !processing && (
          <div className={styles['empty-state']}>
            <div className={styles['empty-icon']}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/></svg>
            </div>
            <h2>Upload a Zoho Export to See Your Dashboard</h2>
            <p>Drop your Zoho Master Sheet export above. The dashboard will automatically compute KPIs, call breakdowns, and conversion analysis.</p>
          </div>
        )}

        {/* Dashboard Content */}
        {showContent && (
          <div id="dashboard-content">
            {/* Campaign Bar */}
            <div className={styles['campaign-bar']}>
              <div className={styles['campaign-info']}>
                <div className={styles['campaign-name']}>Campaign <span>Analysis</span></div>
                <div className={styles['campaign-subtitle']}>{isPostSales ? 'Post-Sales Campaign' : 'Pre-Sales Campaign'}</div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
                <div className={styles['date-range-label']}>DATE RANGE</div>
                <div className={styles['date-range-value']}>{dateKeys.length ? `${dateKeys[0]} — ${dateKeys[dateKeys.length - 1]}` : '—'}</div>
                {trendsData?.hasData && (
                  <span className={`${styles['trend-badge']} ${trendsData.direction === 'up' ? 'good' : trendsData.direction === 'down' ? 'crit' : ''}`}>
                    {trendsData.direction === 'up' ? '▲' : trendsData.direction === 'down' ? '▼' : '▶'} {Math.abs(Number(trendsData.pctChange))}%
                  </span>
                )}
              </div>
            </div>

            {/* Metric Audit */}
            <div className={styles['metric-audit']} data-print="hide">
              <div className={styles['section-title']}>Metric Audit</div>
              <div className={styles['audit-strip']}>
                {metricAudit.map((m, i) => (
                  <div key={i} className={`${styles['metric-chip']} ${!m.found ? styles['chip-err'] : ''}`}>
                    <div className={styles['chip-label']}>{m.label}</div>
                    <div className={styles['chip-value']}>{m.name}</div>
                  </div>
                ))}
              </div>
              <div className={styles['audit-summary']}>
                {metricAudit.filter(m => !m.found).length ? `Missing: ${metricAudit.filter(m => !m.found).map(m => m.label).join(', ')}` : 'All columns found.'}
              </div>
            </div>

            {/* Executive Narrative */}
            {aiNarrative && (
              <div className={styles['exec-narrative']} dangerouslySetInnerHTML={{ __html: sanitizeHtml(aiNarrative) }} />
            )}

            {/* KPIs */}
            <div className={styles['kpi-grid']}>
              {kpiCards.map((card, i) => {
                const overrideVal = getKpi(card.label, card.value);
                const isOverridden = overrideVal !== card.value;
                const editState = kpiEditState[card.label] || { editing: false, inputValue: '' };
                return (
                  <div key={i} className={`${styles.kpi} ${editState.editing ? styles['kpi-editing'] : ''}`}>
                    <div className={styles['kpi-top']}>
                      <div className={styles['kpi-label']}>{card.label}</div>
                      <button className={styles['kpi-edit-btn']} onClick={() => handleKpiEditStart(card.label, overrideVal)} title="Adjust value">
                        <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                    </div>
                    <div className={styles['kpi-vals']}>
                      <span className={styles['kpi-value-display']}>{typeof overrideVal === 'string' ? overrideVal : nf(overrideVal)}</span>
                      {card.badge && <span className={`${styles.badge} ${styles[card.badge.color]}`}>{card.badge.text}</span>}
                      {!card.badge && card.sub && <span className={styles['kpi-sub']}>{card.sub}</span>}
                    </div>
                    {isOverridden && <span className={styles['kpi-adj-badge']}>Adjusted</span>}
                    {editState.editing && (
                      <div className={styles['kpi-edit-panel']}>
                        <input className={styles['kpi-edit-input']} type="text" inputMode="numeric" value={editState.inputValue} onChange={e => handleKpiEditChange(card.label, e.target.value)} onKeyDown={e => { if (e.key === 'Enter') handleKpiEditApply(card.label); if (e.key === 'Escape') handleKpiEditCancel(card.label); }} autoFocus />
                        <div className={styles['kpi-edit-actions']}>
                          <button className={styles['kpi-btn-apply']} onClick={() => handleKpiEditApply(card.label)}>Apply</button>
                          <button className={styles['kpi-btn-reset']} onClick={() => handleKpiEditReset(card.label, card.value)}>Reset</button>
                          <button className={styles['kpi-btn-cancel']} onClick={() => handleKpiEditCancel(card.label)}>Cancel</button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Charts Grid */}
            <div className={styles['charts-grid']}>
              {dateKeys.length > 0 && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Daily Calls Breakdown</div>
                  <div className={styles['chart-wrap']} style={{ height: 250 }}>
                    <canvas ref={dailyChartRef}></canvas>
                  </div>
                </div>
              )}
              {funnelData && fTotal > 0 && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Conversion Funnel</div>
                  <div className={styles['funnel-content']}>
                    <div className={styles['funnel-step']}>
                      <div className={styles['funnel-label']}>
                        <span>Total Leads</span>
                        <span className={styles['funnel-pct']}>100%</span>
                      </div>
                      <div className={styles['funnel-track']}>
                        <div className={`${styles['funnel-fill']} ${styles['fill-total']}`} style={{ width: '100%' }}>
                          <span className={styles['funnel-val']}>{fTotal}</span>
                        </div>
                      </div>
                    </div>
                    <div className={styles['funnel-arrow']}></div>
                    <div className={styles['funnel-step']}>
                      <div className={styles['funnel-label']}>
                        <span>Connected</span>
                        <span className={styles['funnel-pct']}>{fTotal > 0 ? (fConnected / fTotal * 100).toFixed(0) : 0}%</span>
                      </div>
                      <div className={styles['funnel-track']}>
                        <div className={`${styles['funnel-fill']} ${styles['fill-connected']}`} style={{ width: `${Math.max(40, fTotal > 0 ? fConnected / fTotal * 100 : 0)}%` }}>
                          <span className={styles['funnel-val']}>{fConnected}</span>
                        </div>
                      </div>
                    </div>
                    <div className={styles['funnel-arrow']}></div>
                    <div className={styles['funnel-step']}>
                      <div className={styles['funnel-label']}>
                        <span>Booked</span>
                        <span className={styles['funnel-pct']}>{fConnected > 0 ? (fBooked / fConnected * 100).toFixed(0) : 0}%</span>
                      </div>
                      <div className={styles['funnel-track']}>
                        <div className={`${styles['funnel-fill']} ${styles['fill-booked']}`} style={{ width: `${Math.max(25, fConnected > 0 ? fBooked / fConnected * 65 : 0)}%` }}>
                          <span className={styles['funnel-val']}>{fBooked}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {funnelData && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Connection vs Not-Connected</div>
                  <div className={styles['chart-wrap']} style={{ height: 200 }}><canvas ref={ratesChartRef}></canvas></div>
                </div>
              )}
              {dispoData && dispoData.top.length > 0 && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Disposition Intelligence</div>
                  <div className={styles['chart-wrap']} style={{ height: 260 }}><canvas ref={dispoChartRef}></canvas></div>
                </div>
              )}
              {dispoData && funnelData && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Connected Dispositions</div>
                  <div className={styles['chart-wrap']} style={{ height: 200 }}><canvas ref={connDispChartRef}></canvas></div>
                </div>
              )}
              {dispoData && funnelData && funnelData.notConnected > 0 && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Not-Connected Breakdown</div>
                  <div className={styles['chart-wrap']} style={{ height: 160 }}><canvas ref={notConnChartRef}></canvas></div>
                </div>
              )}
              {Object.keys(modelCounts).length > 0 && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Top Vehicle Models</div>
                  <div className={styles['chart-wrap']} style={{ height: 260 }}><canvas ref={modelChartRef}></canvas></div>
                </div>
              )}
              {sourceData && sourceData.sources.length > 0 && (
                <div className={styles['chart-card']}>
                  <div className={styles['chart-title']}>Source Connect Rate</div>
                  <div className={styles['chart-wrap']} style={{ height: 280 }}><canvas ref={sourceChartRef}></canvas></div>
                </div>
              )}
            </div>

            {/* Qualitative Insights */}
            {aiThemes.length > 0 && (
              <div className={styles['insight-panel']}>
                <div className={styles['insight-section-title']}>Customer Voice — Key Themes</div>
                <div className={styles['themes-grid']}>
                  {aiThemes.slice(0, 6).map((t, i) => (
                    <div key={i} className={`${styles['theme-card']} ${styles[t.sentiment]}`}>
                      <div className={styles['theme-top']}><span className={styles['theme-count']}>{t.count}</span><span className={styles['theme-label']}>{t.label}</span></div>
                      <h4>{t.explanation}</h4>
                      <p>{t.interpretation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Recommendations */}
            {aiRecs.length > 0 && (
              <div className={styles['insight-panel']}>
                <div className={styles['insight-section-title']}>
                  AI-Powered Recommendations <span className={styles['ai-badge']}>AI</span>
                </div>
                <div className={styles['recs-list']}>
                  {aiRecs.map((r, i) => (
                    <div key={i} className={`${styles['rec-card']} ${styles[r.priority]}`}>
                      <div className={styles['rec-action']}>{r.action}</div>
                      <div className={styles['rec-reason']}>{r.reason}</div>
                      <div className={styles['rec-impact']}>{r.impact}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Blockers */}
            {blockersData && blockersData.blockers.length > 0 && (
              <div className={styles['insight-panel']}>
                <div className={styles['insight-section-title']}>Conversion Blockers</div>
                <div className={styles['blockers-list']}>
                  {blockersData.blockers.map(([name, count], i) => (
                    <div key={i} className={styles['blocker-row']}>
                      <span className={styles['blocker-name']}>{name}</span>
                      <div className={styles['blocker-track']}><span className={styles['blocker-fill']} style={{ width: `${(count / blockersData.blockers[0][1] * 100).toFixed(0)}%` }}></span></div>
                      <span className={styles['blocker-count']}>{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Highlights */}
            <div className={styles['highlights']}>
              <div className={`${styles['highlight-item']} green`}>
                <strong>{nf(funnelData?.total || 0)} call attempts &middot; {nf(uniqueLeadCount)} unique leads</strong>
                {avgCallsPerLead} avg attempts per lead across {dateKeys.length} days. {nf(funnelData?.connected || 0)} connected ({(funnelData?.total ? ((funnelData?.connected || 0) / funnelData.total * 100).toFixed(0) : 0)}%). Top models: {topModels.map(([k, v]) => `${k} (${v})`).join(', ')}.
              </div>
              <div className={`${styles['highlight-item']} green`}>
                <strong>{bookings} bookings generated</strong>
                The campaign directly generated {bookings} new {isPostSales ? 'service' : 'test drive'} bookings.
              </div>
              <div className={`${styles['highlight-item']} amber`}>
                <strong>{cbCount} callback requests</strong>
                {cbCount ? ((cbCount / (funnelData?.connected || 1)) * 100).toFixed(1) : 0}% of connected callers asked for a callback.
              </div>
              <div className={`${styles['highlight-item']} green`}>
                <strong>Lead validation flagged {invalidLead} issues</strong>
                {invalidLead} invalid contact numbers across {funnelData?.total || 0} records.
              </div>
            </div>
          </div>
        )}
      </main>

      <footer>AutoNage — Campaign Dashboard</footer>
      <ProcessingOverlay show={processing} message={processing ? 'Generating...' : ''} />
    </div>
  );
}

