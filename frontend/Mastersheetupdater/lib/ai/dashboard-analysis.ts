import { sanitizeForPrompt, hashStr, getApiEndpoint, getLlmModel } from './ai-config';

export interface ColMap {
  phone: string | null;
  outcome: string | null;
  status: string | null;
  date: string | null;
  model: string | null;
  detail: string | null;
  summary: string | null;
  updatedSummary: string | null;
  updatedDisposition: string | null;
  source: string | null;
  nextService: string | null;
  lastService: string | null;
  serviceType: string | null;
  duration: string | null;
}

export interface FunnelData { total: number; connected: number; notConnected: number; booked: number; connectedNotBooked: Record<string, number>; }
export interface DispoData { counts: Record<string, number>; top: [string, number][]; total: number; }
export interface SourceData { name: string; total: number; connected: number; booked: number; invalid: number; connRate: string; bookRate: string; invalidRate: string; }
export interface SourceResult { sources: SourceData[]; total: number; best: SourceData | null; worst: SourceData | null; }
export interface TrendsData { hasData: boolean; delta: number; pctChange: string; direction: string; }
export interface BlockersData { blockers: [string, number][]; total: number; }
export interface ThemeData { id: string; label: string; count: number; explanation: string; interpretation: string; sentiment: string; }
export interface RecData { action: string; reason: string; impact: string; priority: string; }

const ncD = ['no response', 'voicemail', 'call disconnected', 'invalid lead', 'wrong contact number', 'wrong number', 'audio issue', 'call quality issue', 'connection issue', 'customer busy', 'language barrier', 'dnd', 'do not disturb'];

export function nm(v: unknown): string { return String(v || '').trim().toLowerCase(); }
export function nf(n: number): string {
  if (n == null || isNaN(n)) return '0';
  return n.toLocaleString();
}
export function esc(s: unknown): string {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
export function hasAny(text: string, terms: string[]): boolean { return terms.some(t => text.includes(t)); }

export function fd(rows: Record<string, string>[], candidates: string[]): string | null {
  if (!rows.length) return null;
  const h = Object.keys(rows[0]);
  const hl = h.map(x => x.toLowerCase().replace(/[^a-z0-9]/g, ''));
  for (const c of candidates) {
    const cl = c.toLowerCase().replace(/[^a-z0-9]/g, '');
    for (let j = 0; j < hl.length; j++) { if (hl[j] === cl) return h[j]; }
  }
  return null;
}

export function detectCampaignType(rows: Record<string, string>[], cm: ColMap): boolean {
  const sample = rows.slice(0, 300);
  let postSc = 0, preSc = 0;
  sample.forEach(row => {
    const text = (String(cm.summary ? row[cm.summary] : '') + ' ' + String(cm.detail ? row[cm.detail] : '') + ' ' + String(cm.outcome ? row[cm.outcome] : '') + ' ' + String(cm.status ? row[cm.status] : '')).toLowerCase();
    if (hasAny(text, ['service booked', 'service appointment', 'feedback', 'serviced', 'escalation', 'complaint'])) postSc++;
    if (hasAny(text, ['test drive', 'converted', 'interested', 'vehicle inquiry', 'brochure'])) preSc++;
  });
  return postSc > preSc;
}

export function isConnected(row: Record<string, string>, cm: ColMap, isPS: boolean): boolean {
  const ot = nm(row[cm.outcome || '']);
  const st = nm(cm.status ? row[cm.status] : '');
  const ud = cm.updatedDisposition ? nm(row[cm.updatedDisposition]) : '';
  if (isPS) {
    if (st === 'completed') return true;
    if (st === 'busy' || st === 'attempted') return false;
    if (ud && !ncD.some(d => ud === d)) return true;
    if (ot.includes('connected')) return true;
    return false;
  }
  if (ud && !ncD.some(d => ud === d)) return true;
  if (st.includes('completed') || st.includes('attempted') || ot.includes('connected')) return true;
  return false;
}

export function aFunn(rows: Record<string, string>[], cm: ColMap, isPS: boolean): FunnelData {
  let connected = 0, booked = 0;
  const cnb: Record<string, number> = {};
  rows.forEach(r => {
    const dp = nm(cm.detail ? r[cm.detail] : '');
    const ud = cm.updatedDisposition ? nm(r[cm.updatedDisposition]) : '';
    const con = isConnected(r, cm, isPS);
    const bk = ud === 'converted' || ud === 'follow up required' || ud === 'follow-up required' || dp.includes('converted') || dp.includes('follow up required') || dp.includes('follow-up required');
    if (con) connected++;
    if (bk) booked++;
    if (con && !bk) {
      const re = ud || dp || 'No reason';
      if (re !== 'No reason') cnb[re] = (cnb[re] || 0) + 1;
    }
  });
  return { total: rows.length, connected, notConnected: Math.max(0, rows.length - connected), booked, connectedNotBooked: cnb };
}

export function aDisp(rows: Record<string, string>[], cm: ColMap): DispoData {
  const c: Record<string, number> = {};
  rows.forEach(r => {
    const v = String((cm.updatedDisposition ? r[cm.updatedDisposition] : '') || (cm.detail ? r[cm.detail] : '') || (cm.outcome ? r[cm.outcome] : '') || (cm.status ? r[cm.status] : '') || 'Unspecified').trim();
    if (v) c[v] = (c[v] || 0) + 1;
  });
  const s = Object.entries(c).sort((a, b) => b[1] - a[1]);
  return { counts: c, top: s.slice(0, 12), total: rows.length };
}

export function aBlk(rows: Record<string, string>[], cm: ColMap, isPS: boolean): BlockersData {
  const b: Record<string, number> = {};
  rows.forEach(r => {
    const dp = nm(cm.detail ? r[cm.detail] : '');
    const ud = cm.updatedDisposition ? nm(r[cm.updatedDisposition]) : '';
    if (isConnected(r, cm, isPS) && !(dp.includes('booked') || ud.includes('booked') || dp.includes('converted') || ud.includes('converted'))) {
      const re = ud || dp || 'No reason';
      b[re] = (b[re] || 0) + 1;
    }
  });
  const s = Object.entries(b).sort((a, x) => x[1] - a[1]).slice(0, 8);
  return { blockers: s, total: s.reduce((sum, x) => sum + x[1], 0) };
}

export function aTr(rows: Record<string, string>[], dc: Record<string, number>): TrendsData {
  const d = Object.keys(dc).sort();
  if (d.length < 4) return { hasData: false, delta: 0, pctChange: '0', direction: 'flat' };
  const mid = Math.floor(d.length / 2);
  const fh = d.slice(0, mid), sh = d.slice(mid);
  const sum = (a: string[]) => a.reduce((s, x) => s + (dc[x] || 0), 0);
  const fa = fh.length > 0 ? sum(fh) / fh.length : 0;
  const sa = sh.length > 0 ? sum(sh) / sh.length : 0;
  const de = sa - fa;
  return { hasData: true, delta: de, pctChange: fa > 0 ? ((de / fa) * 100).toFixed(0) : '0', direction: de > 0 ? 'up' : de < 0 ? 'down' : 'flat' };
}

export function aSrc(rows: Record<string, string>[], cm: ColMap, isPS: boolean): SourceResult {
  if (!cm.source) return { sources: [], total: 0, best: null, worst: null };
  const g: Record<string, { total: number; connected: number; booked: number; invalid: number }> = {};
  rows.forEach(r => {
    const src = String(r[cm.source!] || 'Unknown').trim();
    if (!src) return;
    if (!g[src]) g[src] = { total: 0, connected: 0, booked: 0, invalid: 0 };
    g[src].total++;
    const ot = nm(cm.outcome ? r[cm.outcome] : '');
    const dp = nm(cm.detail ? r[cm.detail] : '');
    const ud = cm.updatedDisposition ? nm(r[cm.updatedDisposition]) : '';
    if (isConnected(r, cm, isPS)) g[src].connected++;
    if (dp.includes('booked') || ud.includes('booked') || dp.includes('converted') || ud.includes('converted')) g[src].booked++;
    if (dp.includes('invalid') || ud.includes('invalid')) g[src].invalid++;
  });
  const sources = Object.entries(g).map(([name, d]) => ({
    name, total: d.total, connected: d.connected, booked: d.booked, invalid: d.invalid,
    connRate: d.total > 0 ? (d.connected / d.total * 100).toFixed(0) : '0',
    bookRate: d.connected > 0 ? (d.booked / d.connected * 100).toFixed(0) : '0',
    invalidRate: d.total > 0 ? (d.invalid / d.total * 100).toFixed(0) : '0',
  })).sort((a, b) => b.total - a.total);
  const best = sources.length ? sources.reduce((b, s) => parseFloat(s.connRate) > parseFloat(b.connRate) ? s : b) : null;
  const worst = sources.length ? sources.reduce((w, s) => parseFloat(s.invalidRate) > parseFloat(w.invalidRate) ? s : w) : null;
  return { sources, total: sources.length, best, worst };
}

export function analyzeConversionBlockers(rows: Record<string, string>[], cm: ColMap, isPS: boolean): BlockersData {
  return aBlk(rows, cm, isPS);
}

export function analyzeDispositionPatterns(rows: Record<string, string>[], cm: ColMap) {
  return aDisp(rows, cm);
}

export function analyzeDecisionPipeline(rows: Record<string, string>[], cm: ColMap) {
  const buckets: Record<string, number> = { immediate: 0, thisWeek: 0, nextWeek: 0, twoWeeks: 0, monthPlus: 0, unknown: 0 };
  rows.forEach(r => {
    const disp = String(cm.detail ? r[cm.detail] : '').toLowerCase();
    const upd = String(cm.updatedDisposition ? r[cm.updatedDisposition] : '').toLowerCase();
    const summary = String(cm.summary ? r[cm.summary] : '').toLowerCase();
    if (disp.includes('booked') || upd.includes('booked') || disp.includes('converted') || upd.includes('converted') || summary.includes('service booked')) { buckets.immediate++; return; }
    if (summary.includes('today') || summary.includes('tomorrow') || summary.includes('this week')) { buckets.thisWeek++; return; }
    if (summary.includes('next week') || /\bnext\s+\w+day\b/.test(summary)) { buckets.nextWeek++; return; }
    if (upd.includes('deferred') || upd.includes('will decide') || upd.includes('callback') || upd.includes('call back')) { buckets.unknown++; return; }
  });
  return { buckets, active: buckets.thisWeek + buckets.nextWeek + buckets.twoWeeks + buckets.monthPlus, total: rows.length };
}

export function analyzeCallbackBehavior(rows: Record<string, string>[], cm: ColMap) {
  let total = 0;
  rows.forEach(r => {
    const disp = String(cm.detail ? r[cm.detail] : '').toLowerCase();
    const upd = String(cm.updatedDisposition ? r[cm.updatedDisposition] : '').toLowerCase();
    const summary = String(cm.summary ? r[cm.summary] : '').toLowerCase();
    if (disp.includes('callback') || upd.includes('callback') || summary.includes('callback') || summary.includes('call back')) total++;
  });
  return { total, callbacks: [] };
}

export function analyzeCompetitiveLosses(rows: Record<string, string>[], cm: ColMap) {
  const competitors: Record<string, number> = {};
  rows.forEach(r => {
    const combined = (String(cm.detail ? r[cm.detail] : '') + ' ' + String(cm.updatedDisposition ? r[cm.updatedDisposition] : '') + ' ' + String(cm.summary ? r[cm.summary] : '')).toLowerCase();
    if (combined.includes('already serviced') || combined.includes('serviced elsewhere') || combined.includes('done elsewhere')) {
      competitors['Unspecified location'] = (competitors['Unspecified location'] || 0) + 1;
    }
  });
  return { total: Object.values(competitors).reduce((s, v) => s + v, 0), competitors: Object.entries(competitors).sort((a, b) => b[1] - a[1]) };
}

export function analyzeLanguageBarriers(rows: Record<string, string>[], cm: ColMap) {
  let count = 0;
  const languages: Record<string, number> = {};
  rows.forEach(r => {
    const disp = String(cm.detail ? r[cm.detail] : '').toLowerCase();
    const upd = String(cm.updatedDisposition ? r[cm.updatedDisposition] : '').toLowerCase();
    const summary = String(cm.summary ? r[cm.summary] : '').toLowerCase();
    if (disp.includes('language') || upd.includes('language') || summary.includes('language') || summary.includes('only hindi')) {
      count++;
      const m = summary.match(/(?:requested|speak|only)\s+(Hindi|Tamil|Malayalam|Telugu|Kannada)/i);
      if (m) languages[m[1]] = (languages[m[1]] || 0) + 1;
    }
  });
  return { total: count, languages };
}

/* ── Theme Mining ── */

export const DISPO_TO_THEME: Record<string, string> = {
  'voicemail': 'voicemail', 'rejected': 'not_interested', 'language barrier': 'language_barrier',
  'is not decision maker': 'wrong_person', 'will decide later, will purchase within 15 days': 'deferred',
  'will decide later, will purchase within 1 to 3 months': 'deferred', 'will decide later, exploring options': 'deferred',
  'no buying intent': 'not_interested', 'just exploring': 'not_interested', 'will call showroom themselves': 'not_interested',
  'requested callback': 'callback_requested', 'purchased elsewhere': 'already_serviced', 'call disconnected': 'customer_busy',
  'not interested': 'not_interested', 'follow up required': 'follow_up', 'no response': 'customer_busy',
  'lost to competition': 'already_serviced', 'test drive completed': 'booked', 'invalid lead': 'bad_data',
  'purchase postponed': 'deferred', 'audio issue': 'audio_issue', 'showroom visit planned': 'booked',
  'converted': 'booked', 'vehicle is commercial or part of a fleet': 'not_interested',
  'vehicle is not being run': 'sold_vehicle', 'requires special spare parts': 'not_interested',
  'wrong contact number': 'wrong_person', 'has sold/given away the car': 'sold_vehicle',
  'has moved to another location': 'wrong_person', 'cannot make decision on servicing': 'wrong_person',
  'will call workshop themselves': 'not_interested', 'looking for a discount': 'not_interested',
  'has serviced car in another dealership': 'already_serviced', 'will decide tomorrow': 'deferred',
  'will decide within 1 to 3 days': 'deferred', 'will decide within 4 to 7 days': 'deferred',
  'will decide within 8 to 14 days': 'deferred', 'will decide within 15 to 30 days': 'deferred',
  'will decide within 31 to 60 days': 'deferred', 'will decide within 61 to 90 days': 'deferred',
  'will decide after 90 days': 'deferred', 'unsubscribed': 'not_interested', 'call quality issue': 'audio_issue',
  'connection issue': 'audio_issue', 'customer busy': 'customer_busy', 'price inquiry': 'booked',
  'service postponed': 'deferred', 'existing dealer contact': 'already_serviced', 'contact fatigue': 'not_interested',
};

const THEME_LABELS: Record<string, string> = {
  already_serviced: 'Already Serviced Elsewhere', voicemail: 'Voicemail', deferred: 'Deferred Decision',
  not_interested: 'Not Interested', callback_requested: 'Callback Requested', customer_busy: 'Customer Busy',
  wrong_person: 'Wrong Person / Number', sold_vehicle: 'Vehicle Sold / Gone', booked: 'Booked / Converted',
  follow_up: 'Follow Up Required', language_barrier: 'Language Barrier', audio_issue: 'Audio / Call Quality',
  bad_data: 'Invalid Lead / Bad Data',
};

const THEME_SENTIMENT: Record<string, string> = {
  already_serviced: 'negative', voicemail: 'neutral', deferred: 'neutral', not_interested: 'negative',
  callback_requested: 'positive', customer_busy: 'neutral', wrong_person: 'negative', sold_vehicle: 'negative',
  booked: 'positive', follow_up: 'positive', language_barrier: 'neutral', audio_issue: 'negative',
  bad_data: 'negative',
};

const THEME_EXPLANATIONS: Record<string, string> = {
  already_serviced: 'Customers already serviced elsewhere', voicemail: 'Calls landing in voicemail',
  deferred: 'Customers postponing decision', not_interested: 'Customers not interested in offer',
  callback_requested: 'Customers requesting callback', customer_busy: 'Customers unavailable to speak',
  wrong_person: 'Wrong person or contact number', sold_vehicle: 'Vehicle no longer owned',
  booked: 'Customers converted or booked', follow_up: 'Customers needing follow-up',
  language_barrier: 'Language barrier on call', audio_issue: 'Audio or connection issues',
  bad_data: 'Invalid or bad lead data',
};

function getThemeFromDisposition(disp: string): string {
  const lc = disp.toLowerCase().trim();
  return DISPO_TO_THEME[lc] || 'other';
}

export function mineCustomerThemes(rows: Record<string, string>[], cm: ColMap, isPS: boolean): ThemeData[] {
  const counts: Record<string, number> = {};
  rows.forEach(r => {
    const ud = cm.updatedDisposition ? nm(r[cm.updatedDisposition]) : '';
    const dp = nm(cm.detail ? r[cm.detail] : '');
    const disp = ud || dp;
    if (disp) {
      const theme = getThemeFromDisposition(disp);
      counts[theme] = (counts[theme] || 0) + 1;
    }
  });
  return Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([id, count]) => ({
      id,
      label: THEME_LABELS[id] || id,
      count,
      explanation: THEME_EXPLANATIONS[id] || 'Customer pattern detected',
      interpretation: `${count} interactions matched this pattern (${(count / rows.length * 100).toFixed(1)}% of total).`,
      sentiment: THEME_SENTIMENT[id] || 'neutral',
    }));
}

/* ── Narrative ── */

export function generateStoryHeadline(themes: ThemeData[], funnel: FunnelData): string {
  if (funnel.total === 0) return 'Upload a file to see campaign insights';
  if (!themes.length) return `${nf(funnel.total)} leads processed, ${nf(funnel.connected)} connected, ${nf(funnel.booked)} booked`;
  const top = themes[0];
  if (top.count > funnel.total * 0.2) return `${top.count} ${top.label.toLowerCase()} — the biggest pattern affecting outcomes`;
  if (funnel.connected > 0 && funnel.booked / funnel.connected < 0.15) return `${(funnel.booked / funnel.connected * 100).toFixed(0)}% conversion rate — ${funnel.connected - funnel.booked} connected leads did not book`;
  if (funnel.connected / funnel.total > 0.6 && funnel.booked > 5) return `Strong campaign: ${(funnel.connected / funnel.total * 100).toFixed(0)}% connected, ${funnel.booked} bookings`;
  if (funnel.connected / funnel.total < 0.3) return `Only ${(funnel.connected / funnel.total * 100).toFixed(0)}% of ${funnel.total} leads connected — re-examine dialing strategy`;
  return `${nf(funnel.total)} leads processed, ${nf(funnel.connected)} connected, ${nf(funnel.booked)} booked`;
}

export function generateExecutiveNarrative(themes: ThemeData[], funnel: FunnelData, trends: TrendsData, isPostSales: boolean): string {
  const parts: string[] = [];
  const connPct = funnel.total > 0 ? (funnel.connected / funnel.total * 100).toFixed(0) : '0';
  const convPct = funnel.connected > 0 ? (funnel.booked / funnel.connected * 100).toFixed(0) : '0';
  const modeLabel = isPostSales ? 'Service' : 'Test Drive';
  const period = 'this reporting period';

  parts.push(`<strong>Monthly Campaign Performance Report — ${modeLabel}</strong>`);
  parts.push(`This month, the campaign processed <strong>${nf(funnel.total)}</strong> leads, reaching <strong>${nf(funnel.connected)}</strong> customers (${connPct}% connect rate). <strong>${funnel.booked}</strong> converted, yielding a ${convPct}% conversion rate from connected calls.`);

  const notConnected = Math.max(0, funnel.total - funnel.connected);
  if (notConnected > 0) {
    parts.push(`<strong>${nf(notConnected)} leads</strong> (${(notConnected / funnel.total * 100).toFixed(0)}%) were not reached — representing untapped opportunity for follow-up.`);
  }

  const topThemes = themes.slice(0, 5);
  if (topThemes.length > 0) {
    const totalThemeCount = topThemes.reduce((s, t) => s + t.count, 0);
    parts.push(`<strong>Key Customer Insights:</strong> The top signals were ${topThemes.map((t, i) => `<strong>${esc(t.label.toLowerCase())}</strong> (${t.count}×)`).join(', ')}.`);
  }

  if (trends.hasData) {
    const dir = trends.direction === 'up' ? 'increased' : trends.direction === 'down' ? 'decreased' : 'remained steady';
    parts.push(`<strong>Volume Trend:</strong> Call volume ${dir} by <strong>${Math.abs(Number(trends.pctChange))}%</strong> in the latter half of ${period}. ${trends.direction === 'down' ? 'Consider reviewing dialing schedules or lead inventory.' : trends.direction === 'up' ? 'Sustained engagement levels are positive.' : ''}`);
  }

  parts.push(`<strong>Outlook:</strong> ${funnel.booked > 0 ? `With ${funnel.booked} confirmed bookings, the campaign is delivering measurable results. ` : 'Conversion pipeline shows room for improvement. '}Focus on re-engaging not-connected leads and reinforcing what resonates with connected customers.`);

  return parts.join('<br><br>');
}

export function generateRecommendations(themes: ThemeData[], funnel: FunnelData, _competitors: { total: number }, callbacks: { total: number }, trends: TrendsData): RecData[] {
  const recs: RecData[] = [];
  const deferredTheme = themes.find(t => t.id === 'deferred');
  if (deferredTheme && deferredTheme.count >= 3) {
    recs.push({ action: `Re-engage ${deferredTheme.count} customers who deferred`, reason: `${deferredTheme.count} customers said they would decide later. These are active opportunities that need follow-up.`, impact: `Potential: ${Math.ceil(deferredTheme.count * 0.3)}-${Math.ceil(deferredTheme.count * 0.5)} additional bookings`, priority: 'high' });
  }
  if (_competitors.total >= 3) {
    recs.push({ action: 'Investigate competitive losses', reason: `${_competitors.total} customers serviced elsewhere. Mystery shop competitor experience and pricing.`, impact: `Potential: recover ${Math.ceil(_competitors.total * 0.15)}-${Math.ceil(_competitors.total * 0.3)} customers`, priority: 'high' });
  }
  if (callbacks.total >= 3) {
    recs.push({ action: `Follow up on ${callbacks.total} outstanding callback requests`, reason: `${callbacks.total} customers explicitly asked to be called back.`, impact: `Potential: ${Math.ceil(callbacks.total * 0.2)}-${Math.ceil(callbacks.total * 0.4)} additional bookings`, priority: 'high' });
  }
  if (trends.hasData && trends.direction === 'down') {
    recs.push({ action: 'Investigate declining call volume', reason: `Call volume dropped ${Math.abs(Number(trends.pctChange))}% in the second half. Review dialing schedule and lead inventory.`, impact: 'Stabilize daily output', priority: 'medium' });
  }
  return recs;
}

/* ── AI Classification ── */

export function buildLlmSystemPrompt(isPostSales: boolean): string {
  const disps = isPostSales
    ? '"Voicemail":"If the customer has asked to leave a message or voicemail."\n"Rejected":"If the customer has rejected the offer or to even speak with the agent. repeated rejection."\n"Language barrier":"If the customer has asked to speak in a different language and did not finish the conversation or intent of the campaign."\n"Vehicle is commercial or part of a fleet":"The vehicle is a commercial vehicle and not applicable for the campaign purpose."\n"Vehicle is not being run":"Vehicle is unused and not being run."\n"Requires special spare parts":"The vehicle requires special spare parts for repair."\n"Others":"All other disposition details not listed above."\n"Wrong contact number":"Customer tells the agent they have the wrong person or number that was contacted"\n"Has sold/given away the car":"The customer has sold or given away the vehicle."\n"Has moved to another location":"The customer has moved to another location."\n"Cannot make decision on servicing":"The customer the agent has called is not the right person to make the decision."\n"Will call workshop themselves":"The customer will contact the workshop themselves."\n"Requested Callback":"The customer asked the agent to call back at a later date and or time."\n"Looking for a discount":"The customer is looking for a discount on the campaign purpose."\n"Has serviced car in another dealership":"The customer has serviced the vehicle in another dealership."\n"Will decide tomorrow":"The customer said they would decide to service the vehicle tomorrow."\n"Will decide within 1 to 3 days":"The customer said they would decide to service the vehicle within 1 to 3 days."\n"Will decide within 4 to 7 days":"The customer said they would decide to service the vehicle within 4 to 7 days."\n"Will decide within 8 to 14 days":"The customer said they would decide to service the vehicle within 8 to 14 days."\n"Will decide within 15 to 30 days":"The customer said they would decide to service the vehicle within 15 to 30 days."\n"Will decide within 31 to 60 days":"The customer said they would decide to service the vehicle within 31 to 60 days."\n"Will decide within 61 to 90 days":"The customer said they would decide to service the vehicle within 61 to 90 days."\n"Will decide after 90 days":"The customer said they would decide to service the vehicle after 90 days."\n"Unsubscribed":"The customer asked to unsubscribed from the campaign."\n"Call Disconnected":"The call ended abruptly without completing the campaign objective."\n"Audio Issue":"There was issues with hearing the customer or the agent for either party."\n"Call Quality Issue":"There was issues with the quality of the call."\n"Connection Issue":"There was issues with the connection between the customer and the agent."\n"Customer Busy":"The customer was busy."\n"No Response":"The customer did not say anything at all."\n"Price Inquiry":"The customer is interested in the price of the service."\n"Lost to Competition":"the customer already did the campaign objective from a competitors workshop"\n"Invalid Lead":"Not a valid lead."\n"Purchase Postponed":"They decided or implied they will postpone the service."\n"Showroom Visit Planned":"Already booked a showroom visit."\n"Existing Dealer Contact":"The customer already did the campaign objective from an existing dealership."\n"Contact Fatigue":"customer implied they were being contacted too many times by the agent."\n"Converted":"The customer completes the purpose of the campaign and provides the necessary information."'
    : '"Voicemail":"If the customer has asked to leave a message or voicemail."\n"Rejected":"If the customer has rejected the offer or to even speak with the agent."\n"Language barrier":"If the customer has asked to speak in a different language and did not finish the conversation or intent of the campaign."\n"Is not decision maker":"the customer said they are not the right person to speak to about this in their family."\n"Will decide later, will purchase within 15 days":"The customer said they would decide to buy the vehicle within 15 days."\n"Will decide later, will purchase within 1 to 3 months":"The customer said they would decide to buy the vehicle within 1 to 3 months."\n"Will decide later, exploring options":"The customer said they will decide on the purchase of the vehicle at a later time and are only exploring all their options now."\n"No buying intent":"the customer Do not want to purchase a car. Neither are the interested in the car."\n"Just Exploring":"the customer Only want to know about the vehicle but do not show intent to buy."\n"Will call showroom themselves":"the customer will contact the dealership or showroom themselves."\n"Requested Callback":"the customer Asked to call back at a later date and or time."\n"Purchased elsewhere":"the customer Already purchased a vehicle elsewhere."\n"Enquired for Pricing":"the customer by themselves asked for the price of the vehicle."\n"Enquired for Specifications":"the customer by themselves asked for the specifications of the vehicle."\n"Enquired for Test Drive":"the customer by themselves asked for a test drive of the vehicle."\n"Enquired for Showroom Visit":"the customer by themselves asked for a showroom visit of the vehicle."\n"Enquired for Brochure":"the customer by themselves asked for a brochure of the vehicle."\n"Enquired for Dealership Details":"the customer by themselves asked for dealership details."\n"Enquired for Others":"the customer by themselves asked for other details not listed above."\n"Comparing with another brand":"The customer by themselves is comparing the vehicle with another brand."\n"Call Disconnected":"The customer by themselves has disconnected the call."\n"Others":"All other disposition details not listed above."\n"General Inquiry":"the customer is Asking generic questions not specific to the purpose of the campaign or the vehicle."\n"Not Interested":"the customer Specifically said they are not interested in the vehicle."\n"Follow Up Required":"the customer Needs a follow up to convince them to complete the campaign objective."\n"No Response":"the customer did not say anything at all."\n"Lost to Competition":"the customer Bought a competitor brands vehicle."\n"Test Drive Completed":"the customer Already completed a test drive."\n"Invalid Lead":"the customer Not a valid lead."\n"Purchase Postponed":"the customer indicates that the Purchase has been postponed"\n"Audio Issue":"There was issues with hearing the customer or the agent for either party."\n"Showroom Visit Planned":"the customer Already booked a showroom visit."\n"Converted":"The customer completes the purpose of the campaign and provides the necessary information."';
  const modeLabel = isPostSales ? 'post-sales' : 'pre-sales';
  return `You classify ${modeLabel} vehicle campaign call summaries into Zoho dispositions.\n\nRules:\n- Use only the supplied summary text. Do not infer from row order or campaign context.\n- Return exactly one JSON item for every input row, preserving the original rowIndex.\n- Use only exact disposition names from the list below.\n- Choose the best disposition. Use up to 2 dispositions only when both are clearly present.\n- If the evidence is weak, generic, or no listed disposition fits, return an empty dispositions array.\n- Do not explain your reasoning.\n\nRespond ONLY with a valid JSON array. No markdown, no comments, no wrapper object.\n\nDISPOSITIONS:\n${disps}\n\nADDITIONAL:\n"Talk to Human"\n"Interested in another car same dealership"\n\nReturn format: [{"rowIndex":0,"dispositions":["Disposition Name"]},{"rowIndex":1,"dispositions":[]}]`;
}

export function keywordFallback(summary: { rowIndex: number; text: string }) {
  const lc = summary.text.toLowerCase();
  const disp: string[] = [];
  if (lc.includes('already serviced') || lc.includes('already done') || lc.includes('already completed') || lc.includes('serviced elsewhere') || lc.includes('bike was recently serviced') || lc.includes('bike had already been serviced') || lc.includes('service had already been')) disp.push('Has serviced car in another dealership');
  else if (lc.includes('do not speak english') || lc.includes('only hindi') || lc.includes('requested hindi') || lc.includes('language barrier') || lc.includes('speak in a different language')) disp.push('Language barrier');
  else if (lc.includes('voicemail') || lc.includes('at the tone') || lc.includes('record your message') || lc.includes('automated voicemail')) disp.push('Voicemail');
  else if (lc.includes('requested a callback') || lc.includes('call back later') || lc.includes('will call back') || lc.includes('asked to call back') || lc.includes('callback requested')) disp.push('Requested Callback');
  else if (lc.includes('deferred') || lc.includes('will decide') || lc.includes('out of station') || lc.includes('out of town') || lc.includes('not ready')) disp.push('Will decide later, exploring options');
  else if (lc.includes('declined') || lc.includes('not interested') || lc.includes('not required') || lc.includes('refused') || lc.includes('repeatedly declined')) disp.push('Not Interested');
  else if (lc.includes('driving') || lc.includes('in a meeting') || lc.includes('was busy') || lc.includes('unavailable to speak') || lc.includes('not a good time')) disp.push('Customer Busy');
  else if (lc.includes('not the right person') || lc.includes('not the decision maker') || lc.includes('not the owner') || lc.includes('not the correct person')) disp.push('Is not decision maker');
  else if (lc.includes('audio issue') || lc.includes('unclear audio') || lc.includes('could not hear') || lc.includes('difficulty hearing') || lc.includes('poor voice')) disp.push('Audio Issue');
  else if (lc.includes('sold the bike') || lc.includes('no longer own') || lc.includes('given away') || lc.includes('sold it') || lc.includes('no longer have')) disp.push('Has sold/given away the car');
  else if (lc.includes('appointment was successfully booked') || lc.includes('service confirmed') || lc.includes('booking confirmed') || lc.includes('successfully confirmed')) disp.push('Converted');
  else if (lc.includes('dissatisfied') || lc.includes('complaint') || lc.includes('unhappy') || lc.includes('negative feedback') || lc.includes('poor service') || lc.includes('bad experience')) disp.push('Complaint');
  return { rowIndex: summary.rowIndex, dispositions: disp };
}

export async function classifyWithLlm(allSummaries: { rowIndex: number; text: string }[], _isPostSales: boolean, _apiKey: string) {
  const results: { rowIndex: number; dispositions: string[] }[] = [];
  for (const summary of allSummaries) {
    results.push(keywordFallback(summary));
  }
  return { results, engine: 'local' };
}

export async function generateLlmRecommendations(_funnel: FunnelData, _themes: ThemeData[], _isPostSales: boolean): Promise<RecData[] | null> {
  return null;
}

export const DISPO_DESCRIPTIONS: Record<string, string> = {
  'Voicemail': 'Customer reached voicemail or automated recording',
  'Rejected': 'Customer explicitly rejected the offer',
  'Language barrier': 'Communication hindered by language differences',
  'Is not decision maker': 'Person reached is not the vehicle owner',
  'No buying intent': 'Customer has no intention to purchase',
  'Not Interested': 'Customer explicitly declined',
  'Follow Up Required': 'Customer needs follow-up to decide',
  'No Response': 'Customer did not respond at all',
  'Requested Callback': 'Customer asked to be called back later',
  'Invalid Lead': 'Lead information is incorrect or outdated',
  'Audio Issue': 'Poor audio quality hindered conversation',
  'Showroom Visit Planned': 'Customer has a visit scheduled',
  'Converted': 'Customer completed the campaign objective',
  'Customer Busy': 'Customer was occupied and could not speak',
  'Call Disconnected': 'Call ended abruptly or was disconnected',
};

export function maybeGetDataHash(rows: Record<string, string>[], cm: ColMap, isPS: boolean): string {
  return hashStr(JSON.stringify({
    count: rows.length,
    phoneCol: !!cm.phone,
    dateCol: !!cm.date,
    summaryCol: !!cm.summary,
    mode: isPS,
    contentPreview: rows.slice(0, 50).map(x => (x[cm.summary || ''] || x[cm.detail || ''] || '').slice(0, 30)).join(''),
  }));
}
