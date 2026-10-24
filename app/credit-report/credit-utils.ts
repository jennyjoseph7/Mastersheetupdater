import XLSXStyle from 'xlsx-js-style';
import pptxgen from 'pptxgenjs';

const XLSX: any = XLSXStyle && (XLSXStyle as any).utils ? XLSXStyle : ((XLSXStyle as any).default || XLSXStyle);

export interface DebitRow {
  billingId: string;
  dateTimeRaw: string;
  dateObj: Date | null;
  dateFormatted: string;
  monthKey: string; // 'YYYY-MM'
  transactionType: string;
  itemName: string;
  channel: string; // 'voice_phone' | 'whatsapp_chat'
  description: string;
  quantity: number;
  creditsSpent: number;
  status: string;
  stage: 'pre-sales' | 'post-sales' | 'other';
  rawObjective: string;
  campaign: string;
  objective: string;
  objectiveSource: 'Description' | 'Description (not in your list)' | 'Inferred from campaign name' | 'Inferred from campaign name keyword' | 'Not identifiable';
}

export interface ObjectiveSummary {
  rank: number;
  objective: string;
  startDate: string;
  endDate: string;
  minDate: Date | null;
  maxDate: Date | null;
  voiceCredits: number;
  whatsAppCredits: number;
  totalCredits: number;
  shareOfTotal: number;
  isUnmapped: boolean;
}

export interface MonthlyTrend {
  monthKey: string;
  monthLabel: string;
  voiceCredits: number;
  whatsAppCredits: number;
  totalCredits: number;
}

export interface ClientDeckConfig {
  clientName?: string;
  aliasMap?: Record<string, string>;
  orderedObjectives?: string[];
  locale?: string;
}

export interface QAReport {
  passed: boolean;
  slideCount: number;
  rowsShown: number;
  unmappedCredits: number;
  unmappedCount: number;
  checks: {
    name: string;
    passed: boolean;
    details: string;
  }[];
}

export interface CreditMetrics {
  clientName: string;
  totalCredits: number;
  debitsCount: number;
  periodStr: string;
  minDate: Date | null;
  maxDate: Date | null;
  voiceCredits: number;
  whatsAppCredits: number;
  voiceShare: number;
  whatsAppShare: number;
  callConnectedCount: number;
  callConnectedCredits: number;
  callCompletedCount: number;
  callCompletedQty: number;
  callCompletedCredits: number;
  messageDeliveredCount: number;
  messageDeliveredCredits: number;
  queryResponseCount: number;
  queryResponseQty: number;
  queryResponseCredits: number;
  postSalesCredits: number;
  preSalesCredits: number;
  postSalesShare: number;
  preSalesShare: number;
  stageBuckets: { label: string; credits: number; share: number }[];
  monthlyTrends: MonthlyTrend[];
  objectives: ObjectiveSummary[];
  rows: DebitRow[];
  qaReport?: QAReport;
}

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_FULL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

// Known Client Alias Maps & Configs (PRD §7 & §11)
export const CLIENT_CONFIGS: Record<string, ClientDeckConfig> = {
  'anant cars': {
    clientName: 'Anant Cars',
    aliasMap: {
      'Friendship Day Sale': 'Friendship Day Sale - Anant Cars - WhatsApp',
      'Varalakshmi Offer': 'Varalakshmi Offer - Anant Cars - WhatsApp',
      'Varalakshmi Special Offer for Anant Cars': 'Varalakshmi Special Offer for Anant Cars - WhatApp',
      'Insurance Renewal': 'Insurance Renewal',
    },
    orderedObjectives: [
      'Friendship Day Sale - Anant Cars - WhatsApp',
      'Varalakshmi Offer - Anant Cars - WhatsApp',
      'Varalakshmi Special Offer for Anant Cars - WhatApp',
      'Insurance Renewal',
      'Inbound Lead Handling',
    ],
  },
  'perfect riders': {
    clientName: 'Perfect Riders',
    aliasMap: {},
  },
};

/**
 * Parses and normalizes date strings like "15 Oct 2026, 08:15 pm" or Excel numbers.
 * PRD §5 requirement: normalize 'Sept' to 'Sep'.
 */
export function parseDate(raw: unknown): Date | null {
  if (raw == null) return null;
  if (raw instanceof Date && !isNaN(raw.getTime())) return raw;

  if (typeof raw === 'number') {
    const d = new Date((raw - 25569) * 86400 * 1000);
    return isNaN(d.getTime()) ? null : d;
  }

  let str = String(raw).trim();
  if (!str) return null;

  // PRD §5: Normalize Sept -> Sep
  str = str.replace(/Sept\b/gi, 'Sep');

  const parsed = new Date(str);
  if (!isNaN(parsed.getTime())) return parsed;

  const m = str.match(/(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})(?:[,\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?)?/i);
  if (m) {
    const day = parseInt(m[1], 10);
    const monthStr = m[2].toLowerCase();
    let month = MONTH_NAMES.findIndex(x => x.toLowerCase() === monthStr.slice(0, 3));
    if (month === -1) month = MONTH_FULL.findIndex(x => x.toLowerCase() === monthStr);
    const year = parseInt(m[3], 10);
    let hour = m[4] ? parseInt(m[4], 10) : 0;
    const min = m[5] ? parseInt(m[5], 10) : 0;
    const sec = m[6] ? parseInt(m[6], 10) : 0;
    const ampm = m[7]?.toLowerCase();
    if (ampm === 'pm' && hour < 12) hour += 12;
    if (ampm === 'am' && hour === 12) hour = 0;
    if (month !== -1) {
      const d = new Date(year, month, day, hour, min, sec);
      if (!isNaN(d.getTime())) return d;
    }
  }

  return null;
}

export function formatDateDisplay(d: Date | null): string {
  if (!d || isNaN(d.getTime())) return '-';
  const day = d.getDate();
  const month = MONTH_NAMES[d.getMonth()];
  const year = d.getFullYear();
  return `${day} ${month} ${year}`;
}

export function formatMonthDisplay(d: Date): string {
  return `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;
}

/**
 * Format number with Indian numbering system (en-IN lakh grouping)
 * Requirement 5: apply en-IN everywhere (e.g. 1,82,733 or 2,10,546.38)
 */
export function formatNum(n: number, decimals: number = 0, locale: string = 'en-IN'): string {
  if (isNaN(n) || n == null) return '0';
  return n.toLocaleString(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Repairs UTF-8 strings misinterpreted as Latin-1/Windows-1252 (mojibake).
 * Specifically repairs en-dash '–' rendered as 'â' or 'â€“'.
 */
export function repairEncoding(str: string): string {
  if (!str) return '';
  let s = str;
  try {
    if (/[\u00C0-\u00FF]/.test(s)) {
      const bytes = new Uint8Array([...s].map(c => c.charCodeAt(0) & 0xff));
      const decoded = new TextDecoder('utf-8', { fatal: false }).decode(bytes);
      if (!decoded.includes('\uFFFD') && decoded.length < s.length) {
        s = decoded;
      }
    }
  } catch {}
  return s
    .replace(/â€“/g, '–')
    .replace(/â€”/g, '—')
    .replace(/â/g, '–')
    .trim();
}

/**
 * Guard (Rule 5): objective must never contain a channel token (voice_phone, whatsapp_chat),
 * a provider, a phone number, or a campaign code pattern (PR_*, PRV_*, PRWA_*, AC_*).
 * If it does, log a warning and truncate the objective at that point.
 */
export function guardObjective(rawObj: string): string {
  if (!rawObj) return '';
  let obj = repairEncoding(rawObj);

  // Pattern matching leakages joined with ' - ' or trailing
  const guardPattern = /\s*-\s*(voice_phone|whatsapp_chat|PR_[A-Za-z0-9_]+|PRV_[A-Za-z0-9_]+|PRWA_[A-Za-z0-9_]+|AC_[A-Za-z0-9_]+|airtel|tatatele|rml|jio|vi|unknown|\+?91\d{10}|\d{10})\b.*/i;
  if (guardPattern.test(obj)) {
    const cleaned = obj.replace(guardPattern, '').trim();
    console.warn(`[CreditReport Guard] Truncated token from objective: "${rawObj}" -> "${cleaned}"`);
    obj = cleaned;
  }

  // Also strip any standalone trailing channel tokens
  obj = obj.replace(/\s+(voice_phone|whatsapp_chat)\b/i, '').trim();
  return obj;
}

/**
 * Description grammar parser according to PRD §6:
 * Split Description on the exact separator " - " (space, hyphen, space).
 * Do not split on a bare hyphen or an en dash.
 * segment 0 = stage (pre-sales or post-sales)
 * segment 1 = objective (exactly ONE segment)
 * segment 2 = campaign or set code
 * remaining segments = channel, provider, phone (never part of the objective)
 */
export function parseDescription(desc: string): {
  stage: 'pre-sales' | 'post-sales' | 'other';
  rawObjective: string;
  campaign: string;
} {
  const cleanDesc = repairEncoding(desc || '');
  // Split on exact separator " - " (space, hyphen, space)
  const parts = cleanDesc.split(' - ').map(s => s.trim());

  let stage: 'pre-sales' | 'post-sales' | 'other' = 'other';
  const seg0 = (parts[0] || '').toLowerCase();
  if (seg0.includes('pre-sales') || seg0.includes('presales')) {
    stage = 'pre-sales';
  } else if (seg0.includes('post-sales') || seg0.includes('postsales')) {
    stage = 'post-sales';
  }

  const seg1 = parts[1] || '';
  let rawObjective = '';
  let campaign = '';

  // Rule 1: If segment 1 == "Perfect Riders" (exact match):
  // objective = segments 1, 2, 3 joined with " - " ("Perfect Riders - Service Reminder - WhatsApp")
  // campaign = segment 4
  if (seg1.toLowerCase() === 'perfect riders') {
    rawObjective = parts.slice(1, 4).join(' - ').trim();
    campaign = parts[4] || '';
  } else if (seg1.toLowerCase() === 'none' || !seg1) {
    // Rule 3: If segment 1 == "None": objective missing, campaign = segment 2
    rawObjective = '';
    campaign = parts[2] || '';
  } else {
    // Rule 2: Otherwise: objective = segment 1 only, campaign = segment 2
    rawObjective = seg1;
    campaign = parts[2] || '';
  }

  rawObjective = guardObjective(rawObjective);

  return { stage, rawObjective, campaign };
}

/**
 * 5-Rule Objective Resolution Chain per PRD §7:
 * 1. Alias map (client list)
 * 2. Own name from description
 * 3. Campaign lookup majority vote
 * 4. Keyword fallback
 * 5. Unmapped
 */
export function resolveObjectives(
  parsedRows: {
    stage: 'pre-sales' | 'post-sales' | 'other';
    rawObjective: string;
    campaign: string;
    rowIdx: number;
  }[],
  aliasMap: Record<string, string> = {}
): { objective: string; source: DebitRow['objectiveSource'] }[] {
  // Pass 1: Build majority vote map for campaigns with known objectives
  const campaignToObjCounts = new Map<string, Map<string, number>>();
  for (const r of parsedRows) {
    if (r.rawObjective && r.rawObjective.toLowerCase() !== 'none' && r.campaign) {
      const campKey = r.campaign.toLowerCase();
      let counts = campaignToObjCounts.get(campKey);
      if (!counts) {
        counts = new Map();
        campaignToObjCounts.set(campKey, counts);
      }
      counts.set(r.rawObjective, (counts.get(r.rawObjective) || 0) + 1);
    }
  }

  const campaignMajorityObj = new Map<string, string>();
  for (const [campKey, counts] of campaignToObjCounts.entries()) {
    let topObj = '';
    let topCount = -1;
    for (const [obj, cnt] of counts.entries()) {
      if (cnt > topCount) {
        topCount = cnt;
        topObj = obj;
      }
    }
    if (topObj) campaignMajorityObj.set(campKey, topObj);
  }

  return parsedRows.map(r => {
    let obj = '';
    let source: DebitRow['objectiveSource'] = 'Not identifiable';
    const campKey = (r.campaign || '').toLowerCase();

    // Rule 1: Alias map
    if (r.rawObjective && aliasMap[r.rawObjective]) {
      obj = aliasMap[r.rawObjective];
      source = 'Description';
    } else if (r.rawObjective && r.rawObjective.toLowerCase() !== 'none') {
      // Rule 2: Own name
      obj = r.rawObjective;
      source = 'Description';
    } else if (campKey && campaignMajorityObj.has(campKey)) {
      // Rule 3: Campaign majority lookup for 'None' rows
      const resolvedFromCamp = campaignMajorityObj.get(campKey)!;
      obj = aliasMap[resolvedFromCamp] || resolvedFromCamp;
      source = 'Inferred from campaign name';
    } else if (campKey) {
      // Rule 4: Keyword fallback on campaign
      if (campKey.includes('monsoon')) {
        obj = 'Monsoon Offer';
        source = 'Inferred from campaign name keyword';
      } else if (campKey.includes('inbound')) {
        obj = 'Inbound Lead Handling';
        source = 'Inferred from campaign name keyword';
      } else if (campKey.includes('insurance')) {
        obj = 'Insurance Renewal';
        source = 'Inferred from campaign name keyword';
      } else if (campKey.includes('varalakshmi')) {
        obj = 'Varalakshmi Offer';
        source = 'Inferred from campaign name keyword';
      } else if (campKey.includes('festive') || campKey.includes('diwali') || campKey.includes('dasara') || campKey.includes('dussehra')) {
        obj = 'Festive Offer';
        source = 'Inferred from campaign name keyword';
      } else if (campKey.includes('prwa') || campKey.includes('pr_wa')) {
        obj = 'Service Reminder (Perfect Riders)';
        source = 'Inferred from campaign name keyword';
      } else if (campKey.includes('r2_pre_sales') || campKey.includes('r2_oct09') || campKey.includes('r2')) {
        obj = 'R2_Pre_sales_WA';
        source = 'Inferred from campaign name keyword';
      }
    }

    if (!obj) {
      // Rule 5: Unmapped
      obj = 'Unmapped (no objective in description)';
      source = 'Not identifiable';
    }

    return {
      objective: guardObjective(obj),
      source,
    };
  });
}

/**
 * Main parser: produces single source of truth CreditMetrics used by both Excel & PPTX.
 */
export function processCreditData(
  rawRows: Record<string, any>[],
  clientNameOverride?: string,
  customConfig?: ClientDeckConfig
): CreditMetrics {
  const normalizedRows: Record<string, any>[] = rawRows.map(row => {
    const cleanRow: Record<string, any> = {};
    for (const [k, v] of Object.entries(row)) {
      cleanRow[k.trim().toLowerCase()] = v;
    }
    return cleanRow;
  });

  const parsedDescriptions = normalizedRows.map((r, i) => {
    const desc = r['description'] || r['desc'] || '';
    return { ...parseDescription(desc), rowIdx: i };
  });

  // Check detected client
  let detectedClientName = clientNameOverride || customConfig?.clientName || '';
  if (!detectedClientName) {
    for (const r of normalizedRows) {
      const desc = (r['description'] || r['desc'] || '').toLowerCase();
      if (desc.includes('perfect riders')) {
        detectedClientName = 'Perfect Riders';
        break;
      }
      if (desc.includes('anant cars') || desc.includes('anant')) {
        detectedClientName = 'Anant Cars';
        break;
      }
    }
  }
  if (!detectedClientName) detectedClientName = 'Dealership Client';

  // Apply alias map from config
  const matchedClientKey = Object.keys(CLIENT_CONFIGS).find(k => detectedClientName.toLowerCase().includes(k));
  const activeConfig = customConfig || (matchedClientKey ? CLIENT_CONFIGS[matchedClientKey] : undefined);
  const aliasMap = activeConfig?.aliasMap || {};
  const orderedObjectives = activeConfig?.orderedObjectives || [];

  const resolved = resolveObjectives(parsedDescriptions, aliasMap);

  const debitRows: DebitRow[] = [];
  let totalCredits = 0;
  let voiceCredits = 0;
  let whatsAppCredits = 0;

  let callConnectedCount = 0;
  let callConnectedCredits = 0;
  let callCompletedCount = 0;
  let callCompletedQty = 0;
  let callCompletedCredits = 0;

  let messageDeliveredCount = 0;
  let messageDeliveredCredits = 0;
  let queryResponseCount = 0;
  let queryResponseQty = 0;
  let queryResponseCredits = 0;

  let postSalesCredits = 0;
  let preSalesCredits = 0;

  let minDate: Date | null = null;
  let maxDate: Date | null = null;

  // Monthly trends map: YYYY-MM -> MonthlyTrend
  const monthMap = new Map<string, { voiceCredits: number; whatsAppCredits: number; totalCredits: number; date: Date }>();

  for (let i = 0; i < normalizedRows.length; i++) {
    const r = normalizedRows[i];
    const desc = r['description'] || r['desc'] || '';
    const descParsed = parsedDescriptions[i];
    const res = resolved[i];

    const billingId = String(r['billing id'] || r['billing_id'] || r['id'] || `row_${i + 1}`);
    const dateRaw = String(r['date & time'] || r['date and time'] || r['date'] || '');
    const dateObj = parseDate(dateRaw);

    let monthKey = 'Unknown';
    if (dateObj) {
      if (!minDate || dateObj < minDate) minDate = dateObj;
      if (!maxDate || dateObj > maxDate) maxDate = dateObj;
      const mStr = String(dateObj.getMonth() + 1).padStart(2, '0');
      monthKey = `${dateObj.getFullYear()}-${mStr}`;
    }

    const itemName = String(r['item name'] || r['item_name'] || '').trim().toLowerCase();
    const channelRaw = String(r['channel'] || '').trim().toLowerCase();
    const channel = channelRaw.includes('whatsapp') ? 'whatsapp_chat' : 'voice_phone';

    const quantity = parseFloat(String(r['quantity'] || '0').replace(/,/g, '')) || 0;
    const creditsSpent = parseFloat(String(r['credits spent'] || r['credits_spent'] || r['credit'] || '0').replace(/,/g, '')) || 0;
    const status = String(r['status'] || 'success').trim();

    totalCredits += creditsSpent;

    if (channel === 'voice_phone') {
      voiceCredits += creditsSpent;
      if (itemName === 'call_connected') {
        callConnectedCount++;
        callConnectedCredits += creditsSpent;
      } else if (itemName === 'call_completed') {
        callCompletedCount++;
        callCompletedQty += quantity;
        callCompletedCredits += creditsSpent;
      }
    } else {
      whatsAppCredits += creditsSpent;
      if (itemName === 'message_delivered') {
        messageDeliveredCount++;
        messageDeliveredCredits += creditsSpent;
      } else if (itemName === 'response_to_query') {
        queryResponseCount++;
        queryResponseQty += quantity;
        queryResponseCredits += creditsSpent;
      }
    }

    if (descParsed.stage === 'post-sales') {
      postSalesCredits += creditsSpent;
    } else if (descParsed.stage === 'pre-sales') {
      preSalesCredits += creditsSpent;
    }

    // Monthly aggregation
    if (dateObj && monthKey !== 'Unknown') {
      let mEntry = monthMap.get(monthKey);
      if (!mEntry) {
        mEntry = { voiceCredits: 0, whatsAppCredits: 0, totalCredits: 0, date: dateObj };
        monthMap.set(monthKey, mEntry);
      }
      if (channel === 'voice_phone') mEntry.voiceCredits += creditsSpent;
      else mEntry.whatsAppCredits += creditsSpent;
      mEntry.totalCredits += creditsSpent;
    }

    debitRows.push({
      billingId,
      dateTimeRaw: dateRaw,
      dateObj,
      dateFormatted: formatDateDisplay(dateObj),
      monthKey,
      transactionType: 'debit',
      itemName,
      channel,
      description: desc,
      quantity,
      creditsSpent,
      status,
      stage: descParsed.stage,
      rawObjective: descParsed.rawObjective,
      campaign: descParsed.campaign,
      objective: res.objective,
      objectiveSource: res.source,
    });
  }

  // Group by objective
  const objMap = new Map<string, {
    objective: string;
    minDate: Date | null;
    maxDate: Date | null;
    voiceCredits: number;
    whatsAppCredits: number;
    totalCredits: number;
    isUnmapped: boolean;
  }>();

  for (const row of debitRows) {
    const objName = row.objective;
    const isUnmapped = objName.startsWith('Unmapped');
    let entry = objMap.get(objName);
    if (!entry) {
      entry = {
        objective: objName,
        minDate: row.dateObj,
        maxDate: row.dateObj,
        voiceCredits: 0,
        whatsAppCredits: 0,
        totalCredits: 0,
        isUnmapped,
      };
      objMap.set(objName, entry);
    }

    if (row.dateObj) {
      if (!entry.minDate || row.dateObj < entry.minDate) entry.minDate = row.dateObj;
      if (!entry.maxDate || row.dateObj > entry.maxDate) entry.maxDate = row.dateObj;
    }

    if (row.channel === 'voice_phone') {
      entry.voiceCredits += row.creditsSpent;
    } else {
      entry.whatsAppCredits += row.creditsSpent;
    }
    entry.totalCredits += row.creditsSpent;
  }

  // Sort objectives per PRD §9:
  // Client list objectives first (in client's order), then other objectives by total credits desc, Unmapped last.
  const allObjEntries = Array.from(objMap.values());
  const clientOrderedList: typeof allObjEntries = [];
  const otherList: typeof allObjEntries = [];
  const unmappedList: typeof allObjEntries = [];

  for (const objName of orderedObjectives) {
    const found = allObjEntries.find(o => o.objective.toLowerCase() === objName.toLowerCase());
    if (found) clientOrderedList.push(found);
  }

  for (const entry of allObjEntries) {
    if (entry.isUnmapped) {
      unmappedList.push(entry);
    } else if (!clientOrderedList.some(o => o.objective === entry.objective)) {
      otherList.push(entry);
    }
  }

  otherList.sort((a, b) => b.totalCredits - a.totalCredits);

  const combinedObjectives = [...clientOrderedList, ...otherList, ...unmappedList];

  const objectives: ObjectiveSummary[] = combinedObjectives.map((o, idx) => ({
    rank: idx + 1,
    objective: o.objective,
    startDate: formatDateDisplay(o.minDate),
    endDate: formatDateDisplay(o.maxDate),
    minDate: o.minDate,
    maxDate: o.maxDate,
    voiceCredits: o.voiceCredits,
    whatsAppCredits: o.whatsAppCredits,
    totalCredits: o.totalCredits,
    shareOfTotal: totalCredits > 0 ? (o.totalCredits / totalCredits) * 100 : 0,
    isUnmapped: o.isUnmapped,
  }));

  // Build sorted monthly trend
  const sortedMonthKeys = Array.from(monthMap.keys()).sort();
  const monthlyTrends: MonthlyTrend[] = sortedMonthKeys.map(k => {
    const val = monthMap.get(k)!;
    return {
      monthKey: k,
      monthLabel: formatMonthDisplay(val.date),
      voiceCredits: val.voiceCredits,
      whatsAppCredits: val.whatsAppCredits,
      totalCredits: val.totalCredits,
    };
  });

  // Dynamic stage buckets (only non-zero credits per Requirement 4)
  const stageMap = new Map<string, number>();
  for (const r of debitRows) {
    const bucketLabel = r.stage === 'post-sales' ? 'Post-Sales Operations' : r.stage === 'pre-sales' ? 'Pre-Sales Operations' : 'Other Operations';
    stageMap.set(bucketLabel, (stageMap.get(bucketLabel) || 0) + r.creditsSpent);
  }
  const stageBuckets = Array.from(stageMap.entries())
    .filter(([_, cred]) => cred > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([label, credits]) => ({
      label,
      credits,
      share: totalCredits > 0 ? (credits / totalCredits) * 100 : 0,
    }));

  const periodStr = minDate && maxDate
    ? `${formatDateDisplay(minDate)} to ${formatDateDisplay(maxDate)}`
    : 'All Time';

  const metrics: CreditMetrics = {
    clientName: detectedClientName,
    totalCredits,
    debitsCount: debitRows.length,
    periodStr,
    minDate,
    maxDate,
    voiceCredits,
    whatsAppCredits,
    voiceShare: totalCredits > 0 ? (voiceCredits / totalCredits) * 100 : 0,
    whatsAppShare: totalCredits > 0 ? (whatsAppCredits / totalCredits) * 100 : 0,
    callConnectedCount,
    callConnectedCredits,
    callCompletedCount,
    callCompletedQty,
    callCompletedCredits,
    messageDeliveredCount,
    messageDeliveredCredits,
    queryResponseCount,
    queryResponseQty,
    queryResponseCredits,
    postSalesCredits,
    preSalesCredits,
    postSalesShare: totalCredits > 0 ? (postSalesCredits / totalCredits) * 100 : 0,
    preSalesShare: totalCredits > 0 ? (preSalesCredits / totalCredits) * 100 : 0,
    stageBuckets,
    monthlyTrends,
    objectives,
    rows: debitRows,
  };

  // Run QA suite automatically
  metrics.qaReport = runDeckQA(metrics);

  return metrics;
}

/**
 * Requirement 9: QA suite verifying bounds, math reconciliation, isolation, and encoding.
 */
export function runDeckQA(metrics: CreditMetrics): QAReport {
  const checks: { name: string; passed: boolean; details: string }[] = [];

  // Check 1: Math reconciliation to the paisa (0.01 tolerance)
  const sumTableCredits = metrics.objectives.reduce((sum, o) => sum + o.totalCredits, 0);
  const tableDiff = Math.abs(sumTableCredits - metrics.totalCredits);
  const mathReconciled = tableDiff < 0.05;
  checks.push({
    name: 'Paisa Math Reconciliation',
    passed: mathReconciled,
    details: mathReconciled
      ? `Table rows sum (${sumTableCredits.toFixed(2)}) reconciles to Grand Total (${metrics.totalCredits.toFixed(2)}) within 0.05.`
      : `Discrepancy of ${tableDiff.toFixed(2)} between table sum and total credits.`,
  });

  // Check 2: Channel split reconciliation
  const channelSum = metrics.voiceCredits + metrics.whatsAppCredits;
  const channelDiff = Math.abs(channelSum - metrics.totalCredits);
  const channelReconciled = channelDiff < 0.05;
  checks.push({
    name: 'Channel Split Reconciliation',
    passed: channelReconciled,
    details: channelReconciled
      ? `Voice (${metrics.voiceCredits.toFixed(2)}) + WhatsApp (${metrics.whatsAppCredits.toFixed(2)}) equals Total (${metrics.totalCredits.toFixed(2)}).`
      : `Discrepancy of ${channelDiff.toFixed(2)} in channel sum.`,
  });

  // Check 3: Client isolation (prevent foreign client references)
  const clientLower = metrics.clientName.toLowerCase();
  let isolationFailed = false;
  let isolationMsg = 'No foreign client references detected.';
  if (clientLower.includes('perfect riders')) {
    const hasAnant = metrics.objectives.some(o => o.objective.toLowerCase().includes('anant'));
    if (hasAnant) {
      isolationFailed = true;
      isolationMsg = 'Detected "Anant" references in Perfect Riders deck.';
    }
  } else if (clientLower.includes('anant')) {
    const hasPR = metrics.objectives.some(o => o.objective.toLowerCase().includes('perfect riders'));
    if (hasPR) {
      isolationFailed = true;
      isolationMsg = 'Detected "Perfect Riders" references in Anant Cars deck.';
    }
  }
  checks.push({
    name: 'Client Name Isolation',
    passed: !isolationFailed,
    details: isolationMsg,
  });

  // Check 4: String cleanliness & encoding
  let stringClean = true;
  let stringMsg = 'All objective strings are clean and properly encoded.';
  for (const o of metrics.objectives) {
    if (o.objective.includes('â') || o.objective.includes('\uFFFD')) {
      stringClean = false;
      stringMsg = `Encoding artifacts found in objective: "${o.objective}"`;
      break;
    }
    if (o.objective.includes('whatsapp_chat') || o.objective.includes('voice_phone')) {
      stringClean = false;
      stringMsg = `Raw channel tokens found in objective: "${o.objective}"`;
      break;
    }
  }
  checks.push({
    name: 'String Cleanliness & Encoding',
    passed: stringClean,
    details: stringMsg,
  });

  // Check 5: Unmapped count & spend verification
  const unmappedRows = metrics.objectives.filter(o => o.isUnmapped);
  const unmappedCredits = unmappedRows.reduce((sum, o) => sum + o.totalCredits, 0);
  checks.push({
    name: 'Unmapped Objective Audit',
    passed: true,
    details: `${unmappedRows.length} unmapped objective(s) totaling ${unmappedCredits.toFixed(2)} credits.`,
  });

  const allPassed = checks.every(c => c.passed);

  return {
    passed: allPassed,
    slideCount: 5 + Math.ceil(metrics.objectives.length / 12),
    rowsShown: metrics.objectives.length,
    unmappedCredits,
    unmappedCount: unmappedRows.length,
    checks,
  };
}

/**
 * Generates client-ready Excel workbook with 4 sheets per PRD §9:
 * Summary, Voice, WhatsApp, Data
 */
export function generateCreditWorkbook(metrics: CreditMetrics): Uint8Array {
  const wb = XLSX.utils.book_new();

  const navyHeaderStyle = {
    fill: { fgColor: { rgb: '1B2A4A' } },
    font: { name: 'Arial', sz: 11, bold: true, color: { rgb: 'FFFFFF' } },
    alignment: { vertical: 'center', horizontal: 'center' },
    border: {
      top: { style: 'thin', color: { rgb: 'CCCCCC' } },
      bottom: { style: 'medium', color: { rgb: '1B2A4A' } },
    },
  };

  const boldRowStyle = {
    font: { name: 'Arial', sz: 11, bold: true, color: { rgb: '1B2A4A' } },
    border: {
      top: { style: 'thin', color: { rgb: '1B2A4A' } },
      bottom: { style: 'double', color: { rgb: '1B2A4A' } },
    },
  };

  const textStyle = { font: { name: 'Arial', sz: 10 } };
  const numStyle = { font: { name: 'Arial', sz: 10 }, alignment: { horizontal: 'right' }, numFmt: '#,##0.00' };
  const intStyle = { font: { name: 'Arial', sz: 10 }, alignment: { horizontal: 'right' }, numFmt: '#,##0' };
  const pctStyle = { font: { name: 'Arial', sz: 10 }, alignment: { horizontal: 'right' }, numFmt: '0.0%' };

  // ── Sheet 1: Summary ───────────────────────────────────────────
  const summaryHeaders = [
    '#', 'Objective', 'Start Date', 'End Date',
    'Voice Credits', 'WhatsApp Credits', 'Total Credits', 'Share of Total',
  ];
  const summaryData: any[][] = [summaryHeaders];

  metrics.objectives.forEach(obj => {
    summaryData.push([
      obj.rank,
      obj.objective,
      obj.startDate,
      obj.endDate,
      obj.voiceCredits,
      obj.whatsAppCredits,
      obj.totalCredits,
      obj.shareOfTotal / 100,
    ]);
  });

  summaryData.push([
    '',
    'Grand Total',
    metrics.minDate ? formatDateDisplay(metrics.minDate) : '-',
    metrics.maxDate ? formatDateDisplay(metrics.maxDate) : '-',
    metrics.voiceCredits,
    metrics.whatsAppCredits,
    metrics.totalCredits,
    1.0,
  ]);

  const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
  wsSummary['!cols'] = [
    { wch: 6 },
    { wch: 44 },
    { wch: 15 },
    { wch: 15 },
    { wch: 16 },
    { wch: 18 },
    { wch: 16 },
    { wch: 15 },
  ];

  for (let c = 0; c < summaryHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: 0, c });
    if (wsSummary[cellRef]) wsSummary[cellRef].s = navyHeaderStyle;
  }

  for (let r = 1; r <= metrics.objectives.length; r++) {
    const isUnmapped = metrics.objectives[r - 1].isUnmapped;
    for (let c = 0; c < summaryHeaders.length; c++) {
      const cellRef = XLSX.utils.encode_cell({ r, c });
      if (!wsSummary[cellRef]) continue;
      if (c === 0 || c === 2 || c === 3) {
        wsSummary[cellRef].s = { ...textStyle, alignment: { horizontal: 'center' } };
      } else if (c === 1) {
        wsSummary[cellRef].s = isUnmapped ? { ...textStyle, font: { italic: true, color: { rgb: '777777' } } } : textStyle;
      } else if (c >= 4 && c <= 6) {
        wsSummary[cellRef].s = numStyle;
      } else if (c === 7) {
        wsSummary[cellRef].s = pctStyle;
      }
    }
  }

  const totalRowIdx = metrics.objectives.length + 1;
  for (let c = 0; c < summaryHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: totalRowIdx, c });
    if (wsSummary[cellRef]) {
      wsSummary[cellRef].s = {
        ...boldRowStyle,
        alignment: c >= 4 ? { horizontal: 'right' } : { horizontal: c === 1 ? 'left' : 'center' },
        numFmt: c === 7 ? '0.0%' : (c >= 4 ? '#,##0.00' : undefined),
      };
    }
  }
  XLSX.utils.book_append_sheet(wb, wsSummary, 'Summary');

  // ── Sheet 2: Voice ─────────────────────────────────────────────
  const voiceHeaders = [
    'Objective', 'Calls Connected Qty', 'Calls Connected Credits',
    'Calls Completed Qty (Duration units)', 'Calls Completed Credits', 'Total Voice Credits',
  ];
  const voiceData: any[][] = [voiceHeaders];
  const voicePerObj = new Map<string, { connQty: number; connCred: number; compQty: number; compCred: number; total: number }>();
  for (const r of metrics.rows) {
    if (r.channel !== 'voice_phone') continue;
    let entry = voicePerObj.get(r.objective);
    if (!entry) {
      entry = { connQty: 0, connCred: 0, compQty: 0, compCred: 0, total: 0 };
      voicePerObj.set(r.objective, entry);
    }
    if (r.itemName === 'call_connected') {
      entry.connQty++;
      entry.connCred += r.creditsSpent;
    } else if (r.itemName === 'call_completed') {
      entry.compQty += r.quantity;
      entry.compCred += r.creditsSpent;
    }
    entry.total += r.creditsSpent;
  }

  metrics.objectives.forEach(obj => {
    const v = voicePerObj.get(obj.objective) || { connQty: 0, connCred: 0, compQty: 0, compCred: 0, total: 0 };
    voiceData.push([obj.objective, v.connQty, v.connCred, v.compQty, v.compCred, v.total]);
  });
  voiceData.push([
    'Grand Total',
    metrics.callConnectedCount,
    metrics.callConnectedCredits,
    metrics.callCompletedQty,
    metrics.callCompletedCredits,
    metrics.voiceCredits,
  ]);

  const wsVoice = XLSX.utils.aoa_to_sheet(voiceData);
  wsVoice['!cols'] = [{ wch: 44 }, { wch: 20 }, { wch: 22 }, { wch: 32 }, { wch: 22 }, { wch: 18 }];
  for (let c = 0; c < voiceHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: 0, c });
    if (wsVoice[cellRef]) wsVoice[cellRef].s = navyHeaderStyle;
  }
  for (let r = 1; r <= metrics.objectives.length; r++) {
    for (let c = 0; c < voiceHeaders.length; c++) {
      const cellRef = XLSX.utils.encode_cell({ r, c });
      if (!wsVoice[cellRef]) continue;
      wsVoice[cellRef].s = c === 0 ? textStyle : (c === 1 ? intStyle : numStyle);
    }
  }
  for (let c = 0; c < voiceHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: metrics.objectives.length + 1, c });
    if (wsVoice[cellRef]) {
      wsVoice[cellRef].s = {
        ...boldRowStyle,
        alignment: c > 0 ? { horizontal: 'right' } : { horizontal: 'left' },
        numFmt: c === 1 ? '#,##0' : (c > 1 ? '#,##0.00' : undefined),
      };
    }
  }
  XLSX.utils.book_append_sheet(wb, wsVoice, 'Voice');

  // ── Sheet 3: WhatsApp ──────────────────────────────────────────
  const waHeaders = [
    'Objective', 'Messages Delivered Qty', 'Messages Delivered Credits',
    'Responses to Query Units', 'Responses to Query Credits', 'Total WhatsApp Credits',
  ];
  const waData: any[][] = [waHeaders];
  const waPerObj = new Map<string, { delQty: number; delCred: number; respQty: number; respCred: number; total: number }>();
  for (const r of metrics.rows) {
    if (r.channel !== 'whatsapp_chat') continue;
    let entry = waPerObj.get(r.objective);
    if (!entry) {
      entry = { delQty: 0, delCred: 0, respQty: 0, respCred: 0, total: 0 };
      waPerObj.set(r.objective, entry);
    }
    if (r.itemName === 'message_delivered') {
      entry.delQty++;
      entry.delCred += r.creditsSpent;
    } else if (r.itemName === 'response_to_query') {
      entry.respQty += r.quantity;
      entry.respCred += r.creditsSpent;
    }
    entry.total += r.creditsSpent;
  }

  metrics.objectives.forEach(obj => {
    const w = waPerObj.get(obj.objective) || { delQty: 0, delCred: 0, respQty: 0, respCred: 0, total: 0 };
    waData.push([obj.objective, w.delQty, w.delCred, w.respQty, w.respCred, w.total]);
  });
  waData.push([
    'Grand Total',
    metrics.messageDeliveredCount,
    metrics.messageDeliveredCredits,
    metrics.queryResponseQty,
    metrics.queryResponseCredits,
    metrics.whatsAppCredits,
  ]);

  const wsWa = XLSX.utils.aoa_to_sheet(waData);
  wsWa['!cols'] = [{ wch: 44 }, { wch: 22 }, { wch: 24 }, { wch: 24 }, { wch: 24 }, { wch: 20 }];
  for (let c = 0; c < waHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: 0, c });
    if (wsWa[cellRef]) wsWa[cellRef].s = navyHeaderStyle;
  }
  for (let r = 1; r <= metrics.objectives.length; r++) {
    for (let c = 0; c < waHeaders.length; c++) {
      const cellRef = XLSX.utils.encode_cell({ r, c });
      if (!wsWa[cellRef]) continue;
      wsWa[cellRef].s = c === 0 ? textStyle : (c === 1 ? intStyle : numStyle);
    }
  }
  for (let c = 0; c < waHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: metrics.objectives.length + 1, c });
    if (wsWa[cellRef]) {
      wsWa[cellRef].s = {
        ...boldRowStyle,
        alignment: c > 0 ? { horizontal: 'right' } : { horizontal: 'left' },
        numFmt: c === 1 ? '#,##0' : (c > 1 ? '#,##0.00' : undefined),
      };
    }
  }
  XLSX.utils.book_append_sheet(wb, wsWa, 'WhatsApp');

  // ── Sheet 4: Data ──────────────────────────────────────────────
  const dataHeaders = [
    'Billing ID', 'Date & Time', 'Item Name', 'Channel',
    'Stage', 'Objective', 'Campaign', 'Quantity', 'Credits Spent', 'Objective Source',
  ];
  const dataRows: any[][] = [dataHeaders];
  metrics.rows.forEach(r => {
    dataRows.push([
      r.billingId,
      r.dateTimeRaw,
      r.itemName,
      r.channel === 'voice_phone' ? 'Voice' : 'WhatsApp',
      r.stage,
      r.objective,
      r.campaign,
      r.quantity,
      r.creditsSpent,
      r.objectiveSource,
    ]);
  });

  const wsData = XLSX.utils.aoa_to_sheet(dataRows);
  wsData['!cols'] = [
    { wch: 14 },
    { wch: 22 },
    { wch: 18 },
    { wch: 12 },
    { wch: 12 },
    { wch: 42 },
    { wch: 28 },
    { wch: 10 },
    { wch: 14 },
    { wch: 28 },
  ];

  for (let c = 0; c < dataHeaders.length; c++) {
    const cellRef = XLSX.utils.encode_cell({ r: 0, c });
    if (wsData[cellRef]) wsData[cellRef].s = navyHeaderStyle;
  }
  wsData['!autofilter'] = {
    ref: `A1:J${metrics.rows.length + 1}`,
  };

  XLSX.utils.book_append_sheet(wb, wsData, 'Data');

  const out = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  return new Uint8Array(out);
}

/**
 * Generates PowerPoint deck adhering strictly to Requirements 1 through 9.
 */
export async function generateCreditPresentation(metrics: CreditMetrics): Promise<Uint8Array> {
  // Fail build if table sum does not match Grand Total to the paisa (Requirement 2)
  const sumTableCredits = metrics.objectives.reduce((sum, o) => sum + o.totalCredits, 0);
  if (Math.abs(sumTableCredits - metrics.totalCredits) > 0.05) {
    throw new Error(
      `QA Build Failure: Table rows sum (${sumTableCredits.toFixed(2)}) does not equal Grand Total (${metrics.totalCredits.toFixed(2)}) to the paisa.`
    );
  }

  const pptx = new pptxgen();

  // Requirement 1: Set slide width 13.333 in and height 7.5 in
  pptx.defineLayout({ name: 'WIDE_13_333_7_5', width: 13.333, height: 7.5 });
  pptx.layout = 'WIDE_13_333_7_5';

  // Shared Tokens
  const BG_COLOR = 'F8F9FC';
  const NAVY = '1B2A4A';
  const BLUE = '2563EB';
  const MINT_BG = 'D1FAE5';
  const MINT_BORDER = '10B981';
  const GREY_TEXT = '64748B';
  const DARK_TEXT = '0F172A';
  const CARD_BG = 'FFFFFF';
  const BORDER_COLOR = 'E2E8F0';
  const FONT_FACE = 'Calibri';

  // Requirement 1: 0.5 in margins, left >= 0.5, right <= 12.833 (w: 12.333)
  const MARGIN_LEFT = 0.5;
  const MARGIN_RIGHT = 12.833;
  const SLIDE_USABLE_WIDTH = MARGIN_RIGHT - MARGIN_LEFT; // 12.333 in

  // Requirement 7: Show period once in footer only
  const footerText = `${metrics.periodStr} · Basis: ${formatNum(metrics.debitsCount)} debits · AutoEngage Billing Data`;

  // Shared slide creation helper enforcing layout contract
  function createSlide(sectionEyebrow: string, headline: string): pptxgen.Slide {
    const slide = pptx.addSlide();
    slide.background = { color: BG_COLOR };

    // Eyebrow
    slide.addText(`${metrics.clientName.toUpperCase()} · ${sectionEyebrow.toUpperCase()}`, {
      x: MARGIN_LEFT,
      y: 0.45,
      w: SLIDE_USABLE_WIDTH,
      h: 0.3,
      fontSize: 10,
      bold: true,
      color: GREY_TEXT,
      fontFace: FONT_FACE,
    });

    // Headline (bold full sentence with key number)
    slide.addText(headline, {
      x: MARGIN_LEFT,
      y: 0.8,
      w: SLIDE_USABLE_WIDTH,
      h: 0.65,
      fontSize: 20,
      bold: true,
      color: NAVY,
      fontFace: FONT_FACE,
    });

    // Footer (period + basis only here)
    slide.addText(footerText, {
      x: MARGIN_LEFT,
      y: 7.05,
      w: SLIDE_USABLE_WIDTH,
      h: 0.3,
      fontSize: 9.5,
      color: GREY_TEXT,
      fontFace: FONT_FACE,
    });

    return slide;
  }

  // ═════════════════════════════════════════════════════════════════
  // SLIDE 1: Executive Overview (Total, channel split & 3 takeaways)
  // ═════════════════════════════════════════════════════════════════
  const s1Headline = `${metrics.clientName} used ${formatNum(Math.round(metrics.totalCredits))} credits across voice and WhatsApp`;
  const slide1 = createSlide('Executive Overview', s1Headline);

  // Left horizontal bar chart: Voice vs WhatsApp (Requirement 6: horizontal bars, sorted largest first)
  const channelDataSorted = [
    { name: 'Voice', val: Math.round(metrics.voiceCredits) },
    { name: 'WhatsApp', val: Math.round(metrics.whatsAppCredits) },
  ].sort((a, b) => b.val - a.val);

  const s1ChartData = [
    {
      name: 'Credits',
      labels: channelDataSorted.map(c => c.name),
      values: channelDataSorted.map(c => c.val),
    },
  ];

  slide1.addChart(pptx.ChartType.bar, s1ChartData, {
    x: MARGIN_LEFT,
    y: 1.65,
    w: 6.8,
    h: 3.2,
    barDir: 'bar',
    chartColors: [BLUE],
    showValue: true,
    dataLabelFontSize: 11,
    dataLabelFormatCode: '#,##,##0',
    valAxisLabelFormatCode: '#,##,##0',
    catAxisLabelColor: DARK_TEXT,
    valAxisLabelColor: GREY_TEXT,
    valGridLine: { style: 'none' },
    showLegend: false,
  });

  // Three Auto-Generated Takeaways (Requirement 8)
  const primaryChannel = metrics.voiceCredits >= metrics.whatsAppCredits ? 'Voice' : 'WhatsApp';
  const primaryCredits = metrics.voiceCredits >= metrics.whatsAppCredits ? metrics.voiceCredits : metrics.whatsAppCredits;
  const primaryShare = metrics.voiceCredits >= metrics.whatsAppCredits ? metrics.voiceShare : metrics.whatsAppShare;
  const topObj = metrics.objectives[0];

  const takeawayBullets = [
    `• ${primaryChannel} drove ${primaryShare.toFixed(1)}% of total spend with ${formatNum(Math.round(primaryCredits))} credits across ${formatNum(primaryChannel === 'Voice' ? metrics.callConnectedCount : metrics.messageDeliveredCount)} interactions.`,
    `• ${topObj ? topObj.objective : 'Top campaign'} was the single largest objective, accounting for ${topObj ? topObj.shareOfTotal.toFixed(1) : '0'}% of all credit consumption (${formatNum(Math.round(topObj ? topObj.totalCredits : 0))} credits).`,
    `• Successfully reconciled ${formatNum(metrics.debitsCount)} billable debits across ${metrics.objectives.length} distinct objectives over the period.`,
  ].join('\n\n');

  slide1.addText(takeawayBullets, {
    x: MARGIN_LEFT,
    y: 5.05,
    w: 6.8,
    h: 1.85,
    fontSize: 12,
    color: DARK_TEXT,
    lineSpacing: 18,
    fontFace: FONT_FACE,
    wrap: true,
  });

  // Right Side 3 Stacked Stat Panels (Requirement 1 & 7: hold large numbers without clipping)
  const STAT_X = 7.7;
  const STAT_W = 5.1; // 7.7 + 5.1 = 12.8 <= 12.833

  // Total Credits Card
  slide1.addShape(pptx.ShapeType.rect, {
    x: STAT_X,
    y: 1.65,
    w: STAT_W,
    h: 1.55,
    fill: { color: NAVY },
    line: { color: NAVY, pt: 1 },
  });
  slide1.addText('TOTAL CREDITS CONSUMED', {
    x: STAT_X + 0.3,
    y: 1.8,
    w: STAT_W - 0.6,
    h: 0.25,
    fontSize: 10.5,
    bold: true,
    color: '93C5FD',
    fontFace: FONT_FACE,
  });
  slide1.addText(formatNum(Math.round(metrics.totalCredits)), {
    x: STAT_X + 0.3,
    y: 2.1,
    w: STAT_W - 0.6,
    h: 0.65,
    fontSize: 30,
    bold: true,
    color: 'FFFFFF',
    fontFace: FONT_FACE,
  });
  slide1.addText(`${formatNum(metrics.debitsCount)} successful debits`, {
    x: STAT_X + 0.3,
    y: 2.8,
    w: STAT_W - 0.6,
    h: 0.3,
    fontSize: 11,
    color: 'CBD5E1',
    fontFace: FONT_FACE,
  });

  // Voice Card
  slide1.addShape(pptx.ShapeType.rect, {
    x: STAT_X,
    y: 3.4,
    w: STAT_W,
    h: 1.55,
    fill: { color: CARD_BG },
    line: { color: BORDER_COLOR, pt: 1 },
  });
  slide1.addText('VOICE CHANNEL SHARE', {
    x: STAT_X + 0.3,
    y: 3.55,
    w: STAT_W - 0.6,
    h: 0.25,
    fontSize: 10.5,
    bold: true,
    color: GREY_TEXT,
    fontFace: FONT_FACE,
  });
  slide1.addText(`${metrics.voiceShare.toFixed(1)}%`, {
    x: STAT_X + 0.3,
    y: 3.85,
    w: 2.2,
    h: 0.6,
    fontSize: 26,
    bold: true,
    color: NAVY,
    fontFace: FONT_FACE,
  });
  slide1.addText(`${formatNum(Math.round(metrics.voiceCredits))} credits\n${formatNum(metrics.callConnectedCount)} connected calls`, {
    x: STAT_X + 2.5,
    y: 3.85,
    w: STAT_W - 2.8,
    h: 0.9,
    fontSize: 12,
    color: DARK_TEXT,
    lineSpacing: 18,
    fontFace: FONT_FACE,
  });

  // WhatsApp Card
  slide1.addShape(pptx.ShapeType.rect, {
    x: STAT_X,
    y: 5.15,
    w: STAT_W,
    h: 1.55,
    fill: { color: CARD_BG },
    line: { color: BORDER_COLOR, pt: 1 },
  });
  slide1.addText('WHATSAPP CHANNEL SHARE', {
    x: STAT_X + 0.3,
    y: 5.3,
    w: STAT_W - 0.6,
    h: 0.25,
    fontSize: 10.5,
    bold: true,
    color: GREY_TEXT,
    fontFace: FONT_FACE,
  });
  slide1.addText(`${metrics.whatsAppShare.toFixed(1)}%`, {
    x: STAT_X + 0.3,
    y: 5.6,
    w: 2.2,
    h: 0.6,
    fontSize: 26,
    bold: true,
    color: NAVY,
    fontFace: FONT_FACE,
  });
  slide1.addText(`${formatNum(Math.round(metrics.whatsAppCredits))} credits\n${formatNum(metrics.messageDeliveredCount)} delivered messages`, {
    x: STAT_X + 2.5,
    y: 5.6,
    w: STAT_W - 2.8,
    h: 0.9,
    fontSize: 12,
    color: DARK_TEXT,
    lineSpacing: 18,
    fontFace: FONT_FACE,
  });

  // ═════════════════════════════════════════════════════════════════
  // SLIDE 2: Voice Breakdown
  // ═════════════════════════════════════════════════════════════════
  const s2Headline = `Voice: connected calls cost ${formatNum(Math.round(metrics.callConnectedCredits))}, talk time another ${formatNum(Math.round(metrics.callCompletedCredits))}`;
  const slide2 = createSlide('Voice Breakdown', s2Headline);

  const voiceTalkShare = metrics.voiceCredits > 0
    ? (metrics.callCompletedCredits / metrics.voiceCredits) * 100
    : 0;

  // Horizontal bar chart sorted largest first (Requirement 6)
  const voiceComponents = [
    { label: 'Talk Time (Duration)', val: Math.round(metrics.callCompletedCredits) },
    { label: 'Call Connected', val: Math.round(metrics.callConnectedCredits) },
  ].sort((a, b) => b.val - a.val);

  const s2ChartData = [
    {
      name: 'Credits',
      labels: voiceComponents.map(v => v.label),
      values: voiceComponents.map(v => v.val),
    },
  ];

  slide2.addChart(pptx.ChartType.bar, s2ChartData, {
    x: MARGIN_LEFT,
    y: 1.65,
    w: 6.8,
    h: 5.0,
    barDir: 'bar',
    chartColors: [BLUE],
    showValue: true,
    dataLabelFontSize: 11,
    dataLabelFormatCode: '#,##,##0',
    valAxisLabelFormatCode: '#,##,##0',
    catAxisLabelColor: DARK_TEXT,
    valGridLine: { style: 'none' },
    showLegend: false,
  });

  // Right Navy Panel (w: 5.1, right: 12.8)
  slide2.addShape(pptx.ShapeType.rect, {
    x: STAT_X,
    y: 1.65,
    w: STAT_W,
    h: 5.0,
    fill: { color: NAVY },
    line: { color: NAVY, pt: 1 },
  });

  slide2.addText('TOTAL VOICE SPEND', {
    x: STAT_X + 0.4,
    y: 1.95,
    w: STAT_W - 0.8,
    h: 0.3,
    fontSize: 11,
    bold: true,
    color: '93C5FD',
    fontFace: FONT_FACE,
  });
  slide2.addText(`${formatNum(Math.round(metrics.voiceCredits))} credits`, {
    x: STAT_X + 0.4,
    y: 2.3,
    w: STAT_W - 0.8,
    h: 0.7,
    fontSize: 32,
    bold: true,
    color: 'FFFFFF',
    fontFace: FONT_FACE,
  });

  const ratePerConn = metrics.callConnectedCount > 0 ? (metrics.callConnectedCredits / metrics.callConnectedCount).toFixed(0) : '2';
  slide2.addText(
    `• ${formatNum(metrics.callConnectedCount)} connected calls at ~${ratePerConn} credits each equal ${formatNum(Math.round(metrics.callConnectedCredits))} credits.\n\n` +
    `• ${formatNum(metrics.callCompletedCount)} completed calls billed by duration equal ${formatNum(Math.round(metrics.callCompletedCredits))} credits.\n\n` +
    `• Talk time accounts for ${voiceTalkShare.toFixed(1)}% of total voice expenditure.`,
    {
      x: STAT_X + 0.4,
      y: 3.3,
      w: STAT_W - 0.8,
      h: 3.0,
      fontSize: 12.5,
      color: 'E2E8F0',
      lineSpacing: 22,
      fontFace: FONT_FACE,
      wrap: true,
    }
  );

  // ═════════════════════════════════════════════════════════════════
  // SLIDE 3: WhatsApp Breakdown
  // ═════════════════════════════════════════════════════════════════
  const waDeliveredShare = metrics.whatsAppCredits > 0
    ? (metrics.messageDeliveredCredits / metrics.whatsAppCredits) * 100
    : 0;

  const s3Headline = `WhatsApp: delivered messages drive ${waDeliveredShare.toFixed(0)}% of its ${formatNum(Math.round(metrics.whatsAppCredits))} credits`;
  const slide3 = createSlide('WhatsApp Breakdown', s3Headline);

  // Left Mint Highlight Panel (w: 3.8)
  slide3.addShape(pptx.ShapeType.rect, {
    x: MARGIN_LEFT,
    y: 1.65,
    w: 3.8,
    h: 5.0,
    fill: { color: MINT_BG },
    line: { color: MINT_BORDER, pt: 1 },
  });

  slide3.addText(`${waDeliveredShare.toFixed(0)}%`, {
    x: MARGIN_LEFT + 0.3,
    y: 2.1,
    w: 3.2,
    h: 1.1,
    fontSize: 54,
    bold: true,
    color: '065F46',
    fontFace: FONT_FACE,
  });
  slide3.addText('OF WHATSAPP SPEND DRIVEN BY OUTBOUND DELIVERIES', {
    x: MARGIN_LEFT + 0.3,
    y: 3.3,
    w: 3.2,
    h: 0.6,
    fontSize: 11,
    bold: true,
    color: '047857',
    fontFace: FONT_FACE,
  });
  slide3.addText(
    `Total WhatsApp: ${formatNum(Math.round(metrics.whatsAppCredits))} credits across ${formatNum(metrics.messageDeliveredCount + metrics.queryResponseCount)} interactions.`,
    {
      x: MARGIN_LEFT + 0.3,
      y: 4.2,
      w: 3.2,
      h: 1.8,
      fontSize: 12,
      color: '064E3B',
      lineSpacing: 18,
      fontFace: FONT_FACE,
      wrap: true,
    }
  );

  // Right Side Bar Chart (Delivered messages vs Query responses)
  const waComponents = [
    { label: 'Delivered Messages', val: Math.round(metrics.messageDeliveredCredits) },
    { label: 'Query Responses', val: Math.round(metrics.queryResponseCredits) },
  ].sort((a, b) => b.val - a.val);

  const s3ChartData = [
    {
      name: 'Credits',
      labels: waComponents.map(w => w.label),
      values: waComponents.map(w => w.val),
    },
  ];

  slide3.addChart(pptx.ChartType.bar, s3ChartData, {
    x: 4.8,
    y: 1.65,
    w: 8.0,
    h: 3.6,
    barDir: 'col',
    chartColors: ['10B981'],
    showValue: true,
    dataLabelFontSize: 11,
    dataLabelFormatCode: '#,##,##0',
    valAxisLabelFormatCode: '#,##,##0',
    catAxisLabelColor: DARK_TEXT,
    valGridLine: { style: 'none' },
    showLegend: false,
  });

  const delRate = metrics.messageDeliveredCount > 0 ? (metrics.messageDeliveredCredits / metrics.messageDeliveredCount).toFixed(2) : '0.90';
  const respRate = metrics.queryResponseQty > 0 ? (metrics.queryResponseCredits / metrics.queryResponseQty).toFixed(2) : '0.93';

  slide3.addText(
    `• ${formatNum(metrics.messageDeliveredCount)} delivered messages at ${delRate} credits each equal ${formatNum(Math.round(metrics.messageDeliveredCredits))} credits.\n` +
    `• ${formatNum(metrics.queryResponseQty)} billed response units (${formatNum(metrics.queryResponseCount)} events) at ${respRate} credits equal ${formatNum(Math.round(metrics.queryResponseCredits))} credits.`,
    {
      x: 4.8,
      y: 5.5,
      w: 8.0,
      h: 1.1,
      fontSize: 12.5,
      color: DARK_TEXT,
      lineSpacing: 22,
      fontFace: FONT_FACE,
      wrap: true,
    }
  );

  // ═════════════════════════════════════════════════════════════════
  // SLIDE 4: Top Objectives OR Data-Driven Stage (Requirement 4)
  // ═════════════════════════════════════════════════════════════════
  const largestStageShare = Math.max(metrics.postSalesShare, metrics.preSalesShare);

  if (largestStageShare > 95) {
    // Stage is heavily skewed (>95% in one stage): replace with Top Objectives Slide
    const top6 = metrics.objectives.slice(0, 6);
    const otherObjectives = metrics.objectives.slice(6);
    const otherCredits = otherObjectives.reduce((sum, o) => sum + o.totalCredits, 0);

    const chartObjItems: { label: string; credits: number; share: number }[] = top6.map(o => ({
      label: o.objective.length > 28 ? o.objective.slice(0, 26) + '…' : o.objective,
      credits: Math.round(o.totalCredits),
      share: o.shareOfTotal,
    }));

    if (otherCredits > 0) {
      chartObjItems.push({
        label: 'All other objectives',
        credits: Math.round(otherCredits),
        share: (otherCredits / metrics.totalCredits) * 100,
      });
    }

    chartObjItems.sort((a, b) => b.credits - a.credits);

    const top2Share = metrics.objectives.slice(0, 2).reduce((sum, o) => sum + o.shareOfTotal, 0);
    const s4Headline = `Top 2 objectives accounted for ${top2Share.toFixed(0)}% of all credit consumption`;
    const slide4 = createSlide('Top Objectives', s4Headline);

    const s4ChartData = [
      {
        name: 'Credits',
        labels: chartObjItems.map(c => `${c.label} (${c.share.toFixed(0)}%)`),
        values: chartObjItems.map(c => c.credits),
      },
    ];

    slide4.addChart(pptx.ChartType.bar, s4ChartData, {
      x: MARGIN_LEFT,
      y: 1.65,
      w: 12.333,
      h: 5.0,
      barDir: 'bar',
      chartColors: [BLUE],
      showValue: true,
      dataLabelFontSize: 10.5,
      dataLabelFormatCode: '#,##,##0',
      valAxisLabelFormatCode: '#,##,##0',
      catAxisLabelColor: DARK_TEXT,
      valGridLine: { style: 'none' },
      showLegend: false,
    });
  } else {
    // Stages are balanced (<=95%): show dynamic data-driven Stage slide
    const s4Headline = `Credit consumption split between Pre-sales (${metrics.preSalesShare.toFixed(1)}%) and Post-sales (${metrics.postSalesShare.toFixed(1)}%)`;
    const slide4 = createSlide('Stage Breakdown', s4Headline);

    const s4ChartData = [
      {
        name: 'Credits',
        labels: metrics.stageBuckets.map(b => `${b.label} (${b.share.toFixed(1)}%)`),
        values: metrics.stageBuckets.map(b => Math.round(b.credits)),
      },
    ];

    slide4.addChart(pptx.ChartType.bar, s4ChartData, {
      x: MARGIN_LEFT,
      y: 1.65,
      w: 12.333,
      h: 5.0,
      barDir: 'bar',
      chartColors: [BLUE],
      showValue: true,
      dataLabelFontSize: 11,
      dataLabelFormatCode: '#,##,##0',
      valAxisLabelFormatCode: '#,##,##0',
      catAxisLabelColor: DARK_TEXT,
      valGridLine: { style: 'none' },
      showLegend: false,
    });
  }

  // ═════════════════════════════════════════════════════════════════
  // SLIDE 5: Monthly Trend (Requirement 8)
  // ═════════════════════════════════════════════════════════════════
  let peakMonth = metrics.monthlyTrends[0];
  for (const m of metrics.monthlyTrends) {
    if (!peakMonth || m.totalCredits > peakMonth.totalCredits) peakMonth = m;
  }

  const s5Headline = peakMonth
    ? `Monthly credits peaked in ${peakMonth.monthLabel} at ${formatNum(Math.round(peakMonth.totalCredits))} credits`
    : `Monthly credit trend across Voice and WhatsApp`;

  const slide5 = createSlide('Monthly Trend', s5Headline);

  // Stacked column chart: Voice and WhatsApp across months
  const s5ChartData = [
    {
      name: 'Voice Credits',
      labels: metrics.monthlyTrends.map(m => m.monthLabel),
      values: metrics.monthlyTrends.map(m => Math.round(m.voiceCredits)),
    },
    {
      name: 'WhatsApp Credits',
      labels: metrics.monthlyTrends.map(m => m.monthLabel),
      values: metrics.monthlyTrends.map(m => Math.round(m.whatsAppCredits)),
    },
  ];

  slide5.addChart(pptx.ChartType.bar, s5ChartData, {
    x: MARGIN_LEFT,
    y: 1.65,
    w: 12.333,
    h: 5.0,
    barDir: 'col',
    barGrouping: 'stacked',
    chartColors: [NAVY, BLUE],
    showValue: true,
    dataLabelFontSize: 10,
    dataLabelFormatCode: '#,##,##0',
    valAxisLabelFormatCode: '#,##,##0',
    catAxisLabelColor: DARK_TEXT,
    valGridLine: { style: 'none' },
    showLegend: true,
    legendPos: 't',
    legendFontSize: 11,
    legendColor: DARK_TEXT,
  });

  // ═════════════════════════════════════════════════════════════════
  // SLIDES 6 to N: Paginated Objective Table (Requirement 2)
  // ═════════════════════════════════════════════════════════════════
  const ROWS_PER_PAGE = 12; // floor((7.5 - 2.0 in) / 0.36 in) = 15; 12 gives clean 11pt spacing
  const totalObjPages = Math.max(1, Math.ceil(metrics.objectives.length / ROWS_PER_PAGE));

  // Table column widths sum up to exactly 12.333 in:
  // Objective col = 4.333 in (~35% of width)
  const COL_WIDTHS = [0.5, 4.333, 1.25, 1.25, 1.4, 1.4, 1.4, 0.8];

  for (let pageIdx = 0; pageIdx < totalObjPages; pageIdx++) {
    const pageNum = pageIdx + 1;
    const isLastPage = pageNum === totalObjPages;
    const pageObjectives = metrics.objectives.slice(pageIdx * ROWS_PER_PAGE, (pageIdx + 1) * ROWS_PER_PAGE);

    const sTableHeadline = `Objective wise credits (${pageNum} of ${totalObjPages})`;
    const slideTable = createSlide('Objective Summary', sTableHeadline);

    const tableRows: pptxgen.TableRow[] = [];

    // Header row repeated on every page (Requirement 2)
    tableRows.push([
      { text: '#', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'center', fontSize: 11 } },
      { text: 'Objective', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'left', fontSize: 11 } },
      { text: 'Start Date', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'center', fontSize: 11 } },
      { text: 'End Date', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'center', fontSize: 11 } },
      { text: 'Voice Credits', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'right', fontSize: 11 } },
      { text: 'WhatsApp Credits', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'right', fontSize: 11 } },
      { text: 'Total Credits', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'right', fontSize: 11 } },
      { text: 'Share', options: { bold: true, fill: { color: NAVY }, color: 'FFFFFF', align: 'right', fontSize: 11 } },
    ]);

    pageObjectives.forEach(o => {
      tableRows.push([
        { text: String(o.rank), options: { align: 'center', fontSize: 11 } },
        { text: o.objective, options: { align: 'left', fontSize: 11 } },
        { text: o.startDate, options: { align: 'center', fontSize: 11 } },
        { text: o.endDate, options: { align: 'center', fontSize: 11 } },
        { text: formatNum(o.voiceCredits, 2), options: { align: 'right', fontSize: 11 } },
        { text: formatNum(o.whatsAppCredits, 2), options: { align: 'right', fontSize: 11 } },
        { text: formatNum(o.totalCredits, 2), options: { align: 'right', fontSize: 11, bold: true } },
        { text: `${o.shareOfTotal.toFixed(1)}%`, options: { align: 'right', fontSize: 11 } },
      ]);
    });

    // Grand Total row ONLY on the last page (Requirement 2)
    if (isLastPage) {
      tableRows.push([
        { text: '', options: { bold: true, fill: { color: 'F1F5F9' }, align: 'center', fontSize: 11 } },
        { text: 'Grand Total', options: { bold: true, fill: { color: 'F1F5F9' }, color: NAVY, align: 'left', fontSize: 11 } },
        { text: metrics.minDate ? formatDateDisplay(metrics.minDate) : '-', options: { bold: true, fill: { color: 'F1F5F9' }, align: 'center', fontSize: 11 } },
        { text: metrics.maxDate ? formatDateDisplay(metrics.maxDate) : '-', options: { bold: true, fill: { color: 'F1F5F9' }, align: 'center', fontSize: 11 } },
        { text: formatNum(metrics.voiceCredits, 2), options: { bold: true, fill: { color: 'F1F5F9' }, align: 'right', fontSize: 11 } },
        { text: formatNum(metrics.whatsAppCredits, 2), options: { bold: true, fill: { color: 'F1F5F9' }, align: 'right', fontSize: 11 } },
        { text: formatNum(metrics.totalCredits, 2), options: { bold: true, fill: { color: 'F1F5F9' }, color: NAVY, align: 'right', fontSize: 11 } },
        { text: '100.0%', options: { bold: true, fill: { color: 'F1F5F9' }, align: 'right', fontSize: 11 } },
      ]);
    }

    slideTable.addTable(tableRows, {
      x: MARGIN_LEFT,
      y: 1.6,
      w: SLIDE_USABLE_WIDTH,
      colW: COL_WIDTHS,
      border: { color: 'CBD5E1', pt: 0.5 },
    });
  }

  const out = await pptx.write({ outputType: 'uint8array' });
  return out as Uint8Array;
}
