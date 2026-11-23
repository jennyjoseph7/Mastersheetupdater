import XLSXStyle from 'xlsx-js-style';

export type CampaignChannel = 'voice' | 'whatsapp';
export type CampaignType = 'due_overdue' | 'expiry' | 'checkup' | 'paid' | 'unknown';

export interface CampaignMeta {
  channel: CampaignChannel;
  type: CampaignType;
  displayName: string;
  servicePlanName: string;
}

export interface KeerthiLeadRecord {
  name: string;
  phoneNumber: string;
  leadCategory: string;
  serviceBooked: 'Yes' | 'No';
  regNumber: string;
  vinNumber: string;
  vehicleModel: string;
  showroomLocation: string;
  servicePlan: string;
  checkupDueDateRecords: string;
  confirmedDateReply: string;
  confirmedTimeReply: string;
  disposition: string;
  dispositionDetail: string;
  messageDateTime: string;
  messageReplySummary: string;
  recommendedAction: string;
  appointmentBookedLocation: string;
  // internal tracking
  rawRow: Record<string, string>;
  originalDisposition: string;
  isCorrected: boolean;
  isDelivered: boolean;
  priorityScore: number;
}

export interface DateSummaryRow {
  date: string;
  triggers: number;
  delivered: number;
  hotWarmLeads: number;
}

export interface DispositionBreakdownRow {
  disposition: string;
  originalCount: number;
  finalCount: number;
  deliveredCount: number;
  failedCount: number;
  countedAs?: 'Delivered' | 'Failed / Undelivered';
}

export interface CorrectionLogRow {
  name: string;
  phoneNumber: string;
  originalDisposition: string;
  correctedDisposition: string;
  correctionSource: string;
}

export interface KeerthiReportDataset {
  meta: CampaignMeta;
  sourceFileName: string;
  dateRangeStr: string;
  totalTriggers: number;
  deliveredCount: number;
  failedCount: number;
  hotCount: number;
  warmCount: number;
  hotWarmTotal: number;
  hotWarmPercent: number;
  correctionsCount: number;
  categoryCounts: Record<string, number>;
  dateSummary: DateSummaryRow[];
  dispositionBreakdown: DispositionBreakdownRow[];
  correctionsLog: CorrectionLogRow[];
  hotWarmLeads: KeerthiLeadRecord[];
  allProcessedRows: KeerthiLeadRecord[];
}

// -------------------------------------------------------------------------
// Helper Utilities
// -------------------------------------------------------------------------

export function cleanString(val: unknown): string {
  if (val == null) return '';
  return String(val).trim();
}

export function excelSafe(str: unknown): string {
  const s = cleanString(str);
  if (/^[+\-=@]/.test(s)) return "'" + s;
  return s;
}

export function normalizePhone(raw: unknown): string {
  if (raw == null) return '';
  let s = String(raw).trim();
  if (!s) return '';

  // Handle scientific notation from Excel (e.g. 9.1789E+11)
  if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) {
    const parsed = parseFloat(s);
    if (!isNaN(parsed)) {
      s = String(Math.round(parsed));
    }
  }

  const digits = s.replace(/\D/g, '');
  if (!digits) return '';

  if (digits.startsWith('91') && digits.length === 12) return digits;
  if (digits.length === 10) return `91${digits}`;
  if (digits.startsWith('0') && digits.length === 11) return `91${digits.slice(1)}`;
  if (digits.length > 10) return `91${digits.slice(-10)}`;
  return digits;
}

export function formatPhoneDisplay(phoneWithCountry: string): string {
  if (!phoneWithCountry) return '';
  // Sample outputs have format: 917019100381 (number or string)
  const digits = phoneWithCountry.replace(/\D/g, '');
  if (digits.startsWith('91') && digits.length === 12) return digits;
  if (digits.length === 10) return `91${digits}`;
  return digits;
}

export function normalizeHeaderKey(key: string): string {
  return String(key || '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

export function getField(row: Record<string, string>, candidates: string[]): string {
  if (!row) return '';
  for (const c of candidates) {
    if (row[c] !== undefined && row[c] !== null && String(row[c]).trim() !== '') {
      return String(row[c]).trim();
    }
  }
  const normTargets = candidates.map(normalizeHeaderKey);
  for (const [rk, rv] of Object.entries(row)) {
    if (rv === undefined || rv === null || String(rv).trim() === '') continue;
    if (normTargets.includes(normalizeHeaderKey(rk))) {
      return String(rv).trim();
    }
  }
  return '';
}

// -------------------------------------------------------------------------
// Campaign Detection
// -------------------------------------------------------------------------

export function detectCampaignMeta(headers: string[], fileName: string): CampaignMeta {
  const normHeaders = headers.map(normalizeHeaderKey);
  const fnLower = fileName.toLowerCase();

  const isVoice = normHeaders.includes('workshopcode') || normHeaders.includes('updateddisposition') || normHeaders.includes('recordings');
  const isWhatsapp = normHeaders.includes('leadid') || normHeaders.includes('cohort') || normHeaders.includes('calltriggered');

  const channel: CampaignChannel = isWhatsapp && !isVoice ? 'whatsapp' : 'voice';

  let type: CampaignType = 'due_overdue';
  let displayName = 'Service Reminder - Due / Overdue (Voice)';
  let servicePlanName = 'Due / overdue service';

  if (channel === 'voice') {
    if (fnLower.includes('expiry') || fnLower.includes('coupon')) {
      type = 'expiry';
      displayName = 'Service Reminder - Expiry (Voice)';
      servicePlanName = 'Service coupon expiry';
    } else {
      type = 'due_overdue';
      displayName = 'Service Reminder - Due / Overdue (Voice)';
      servicePlanName = 'Due / overdue service';
    }
  } else {
    if (fnLower.includes('checkup') || fnLower.includes('check-up') || fnLower.includes('health')) {
      type = 'checkup';
      displayName = 'Check-up (WhatsApp)';
      servicePlanName = 'Check up';
    } else {
      type = 'paid';
      displayName = 'Annual / Paid Service (WhatsApp)';
      servicePlanName = 'Annual / paid service';
    }
  }

  return {
    channel,
    type,
    displayName,
    servicePlanName,
  };
}

// -------------------------------------------------------------------------
// Date Parsing & Extraction
// -------------------------------------------------------------------------

export function formatDateToDDMMYYYY(val: unknown): string {
  if (!val) return '';
  const s = String(val).trim();
  if (!s) return '';

  // Already dd/mm/yyyy
  if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(s)) {
    const parts = s.split('/');
    const d = parts[0].padStart(2, '0');
    const m = parts[1].padStart(2, '0');
    return `${d}/${m}/${parts[2]}`;
  }

  // yyyy-mm-dd
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) {
    const parts = s.split('T')[0].split('-');
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  // dd-mm-yyyy
  if (/^\d{1,2}-\d{1,2}-\d{4}/.test(s)) {
    const parts = s.split(' ')[0].split('-');
    const d = parts[0].padStart(2, '0');
    const m = parts[1].padStart(2, '0');
    return `${d}/${m}/${parts[2]}`;
  }

  // Excel serial number
  const num = Number(s);
  if (!isNaN(num) && num > 30000 && num < 60000) {
    const d = new Date(Math.round((num - 25569) * 86400 * 1000));
    if (!isNaN(d.getTime())) {
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      return `${day}/${month}/${d.getFullYear()}`;
    }
  }

  const d = new Date(s);
  if (!isNaN(d.getTime()) && d.getFullYear() > 2000 && d.getFullYear() < 2100) {
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    return `${day}/${month}/${d.getFullYear()}`;
  }

  return s;
}

export function extractAppointmentDetailsFromSummary(summary: string): {
  confirmedDate: string;
  confirmedTime: string;
  location: string;
} {
  if (!summary) return { confirmedDate: '', confirmedTime: '', location: '' };
  const text = summary.toLowerCase();

  // 1. Extract location
  let location = '';
  if (text.includes('srinivas nagar')) {
    location = 'Srinivas Nagar';
  } else if (text.includes('hbr layout') || text.includes('hbr')) {
    location = 'HBR Layout';
  } else if (text.includes('jp nagar')) {
    location = 'JP Nagar';
  } else if (text.includes('residency road')) {
    location = 'Residency Road';
  } else if (text.includes('kanakapura road') || text.includes('kanakapura')) {
    location = 'Kanakapura Road';
  } else if (text.includes('8 mile') || text.includes('8th mile')) {
    location = '8 Mile';
  }

  // 2. Extract Date
  let confirmedDate = '';
  // Check patterns like: 20-11-2026, 20/11/2026, 2026-11-20
  const dateMatch = summary.match(/\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b/);
  if (dateMatch) {
    const day = dateMatch[1].padStart(2, '0');
    const month = dateMatch[2].padStart(2, '0');
    confirmedDate = `${day}/${month}/${dateMatch[3]}`;
  } else {
    // Check written month: "november 22nd, 2026" or "21st november 2026"
    const writtenDate = summary.match(/\b(?:(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})|(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(20\d{2}))\b/i);
    if (writtenDate) {
      const months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
      if (writtenDate[1]) {
        const d = writtenDate[1].padStart(2, '0');
        const m = String(months.indexOf(writtenDate[2].toLowerCase()) + 1).padStart(2, '0');
        confirmedDate = `${d}/${m}/${writtenDate[3]}`;
      } else if (writtenDate[4]) {
        const d = writtenDate[5].padStart(2, '0');
        const m = String(months.indexOf(writtenDate[4].toLowerCase()) + 1).padStart(2, '0');
        confirmedDate = `${d}/${m}/${writtenDate[6]}`;
      }
    }
  }

  // 3. Extract Time
  let confirmedTime = '';
  const timeMatch = summary.match(/\b([01]?\d:[0-5]\d\s*(?:am|pm)?|[01]?\d\s*(?:am|pm))\b/i);
  if (timeMatch) {
    confirmedTime = timeMatch[1].toUpperCase();
  }

  return { confirmedDate, confirmedTime, location };
}

// -------------------------------------------------------------------------
// Disposition Mapping & Classification
// -------------------------------------------------------------------------

export function normalizeDispositionSlug(raw: string): string {
  const s = (raw || '').trim().toLowerCase();
  if (s.includes('converted') || s.includes('vehicle booked for service')) return 'converted';
  if (s.includes('follow up') || s.includes('follow_up')) return 'follow_up_required';
  if (s.includes('callback') || s.includes('call back')) return 'requested_callback';
  if (s.includes('talk to human') || s.includes('talk_to_human') || s.includes('human agent')) return 'talk_to_human';
  if (s.includes('enquired for others') || s.includes('enquired_for_others')) return 'enquired_for_others';
  if (s.includes('dealership details') || s.includes('enquired_for_dealership_details')) return 'enquired_for_dealership_details';
  if (s.includes('will call') || s.includes('self-initiated') || s.includes('will_call_showroom')) return 'will_call_showroom_workshop_themselves';
  return s.replace(/\s+/g, '_');
}

export function classifyLeadCategory(dispSlug: string): string {
  if (dispSlug === 'converted') return 'Hot - Converted';
  if (dispSlug === 'follow_up_required') return 'Warm - Follow-up Required';
  if (dispSlug === 'requested_callback') return 'Warm - Requested Callback';
  if (dispSlug === 'talk_to_human') return 'Warm - Requested Human Agent';
  if (dispSlug === 'enquired_for_others' || dispSlug === 'enquired_for_dealership_details') return 'Warm - Enquired (Other)';
  if (dispSlug === 'will_call_showroom_workshop_themselves') return 'Warm - Self-initiated Visit';
  return '';
}

export function getDispositionPriorityScore(slug: string): number {
  switch (slug) {
    case 'converted': return 100;
    case 'follow_up_required': return 80;
    case 'requested_callback': return 75;
    case 'talk_to_human': return 70;
    case 'will_call_showroom_workshop_themselves': return 65;
    case 'enquired_for_dealership_details': return 60;
    case 'enquired_for_others': return 55;
    default: return 10;
  }
}

export function formatShowroomLocation(rawWorkshopCode: string, channel: CampaignChannel): string {
  const s = cleanString(rawWorkshopCode);
  if (!s) return channel === 'voice' ? 'Keerthi Triumph' : '';
  if (s.toLowerCase().startsWith('keerthi')) return s;
  if (/hbr/i.test(s)) return 'Keerthi HBR Layout';
  if (/jp\s*nagar/i.test(s)) return 'Keerthi JP Nagar';
  if (/residency/i.test(s)) return 'Keerthi Residency Road';
  if (/kanakapura/i.test(s)) return 'Keerthi Kanakapura Road';
  if (/srinivas/i.test(s)) return 'Keerthi Srinivas Nagar';
  return s;
}

export function generateRecommendedAction(
  category: string,
  confirmedDate: string,
  location: string
): string {
  if (category === 'Hot - Converted') {
    const datePart = confirmedDate ? ` for ${confirmedDate}` : '';
    const locPart = location ? ` at ${location}` : '';
    return `Confirm the service appointment in the CRM/DMS${datePart}${locPart} and send the customer a booking confirmation.`;
  }
  if (category === 'Warm - Follow-up Required') {
    return 'Follow up with the customer as requested regarding their service schedule.';
  }
  if (category === 'Warm - Requested Callback') {
    return 'Call back the customer at the requested time to schedule the service.';
  }
  if (category === 'Warm - Requested Human Agent') {
    return 'Arrange a human agent callback to address the customer queries.';
  }
  if (category === 'Warm - Enquired (Other)') {
    return 'Document customer enquiry and provide requested vehicle or dealership details.';
  }
  if (category === 'Warm - Self-initiated Visit') {
    return 'Alert workshop reception that customer plans to visit directly for service.';
  }
  return 'Follow up with customer regarding service reminder.';
}

// -------------------------------------------------------------------------
// Dataset Processing Engine
// -------------------------------------------------------------------------

export function processKeerthiReport(
  rawRows: Record<string, string>[],
  meta: CampaignMeta,
  fileName: string
): KeerthiReportDataset {
  const isVoice = meta.channel === 'voice';

  // Corrections log
  const correctionsLog: CorrectionLogRow[] = [];

  // Group raw rows into parsed representation
  const allParsedRows: KeerthiLeadRecord[] = [];
  const distinctDates = new Set<string>();

  for (const row of rawRows) {
    const name = isVoice
      ? getField(row, ['PERSON_NAME', 'person_name', 'Full_Name', 'customer_name', 'name'])
      : getField(row, ['Full_Name', 'full_name', 'Name', 'person_name', 'customer_name']);

    const phoneRaw = isVoice
      ? getField(row, ['PHONE_NUMBER', 'phone_number', 'Phone', 'mobile'])
      : getField(row, ['Phone', 'phone', 'PHONE_NUMBER', 'mobile']);
    const phone = normalizePhone(phoneRaw);

    const regNumber = getField(row, ['REG_NUMBER', 'reg_number', 'registration_number', 'vehicle_number']);
    const vinNumber = getField(row, ['VIN_NUMBER', 'vin_number', 'vin', 'chassis_number']);
    const vehicleModel = getField(row, ['VEHICLE_MODEL', 'vehicle_model', 'model']);

    // Disposition resolving
    const rawDisp = isVoice
      ? getField(row, ['DISPOSITION_DETAILS', 'disposition_details', 'STATUS', 'status', 'disposition'])
      : getField(row, ['Disposition', 'disposition', 'Outcome', 'outcome']);

    const updatedDisp = isVoice
      ? getField(row, ['Updated Disposition', 'updated_disposition', 'manual_disposition'])
      : '';

    let resolvedDisp = rawDisp;
    let isCorrected = false;

    if (updatedDisp && updatedDisp.trim() !== '') {
      if (updatedDisp.trim().toLowerCase() !== rawDisp.trim().toLowerCase()) {
        isCorrected = true;
        correctionsLog.push({
          name: name || 'Customer',
          phoneNumber: phone,
          originalDisposition: rawDisp,
          correctedDisposition: updatedDisp.toUpperCase(),
          correctionSource: 'Manual (Updated Disposition)',
        });
      }
      resolvedDisp = updatedDisp;
    }

    const dispSlug = normalizeDispositionSlug(resolvedDisp);
    const category = classifyLeadCategory(dispSlug);

    const summary = getField(row, ['SUMMARY', 'summary', 'Message / Reply Summary']);
    const callDateRaw = isVoice
      ? getField(row, ['CALL_DATE', 'call_date', 'date'])
      : getField(row, ['Call_Date', 'call_date', 'date']);
    const messageDate = formatDateToDDMMYYYY(callDateRaw);
    if (messageDate) distinctDates.add(messageDate);

    const recordings = isVoice ? getField(row, ['RECORDINGS', 'recordings', 'recording']) : '';
    const outcome = isVoice ? getField(row, ['STATUS', 'status']) : getField(row, ['Outcome', 'outcome']);

    // Delivery check
    let isDelivered = false;
    if (isVoice) {
      isDelivered = Boolean(recordings && recordings.trim() !== '') || resolvedDisp.toLowerCase() === 'contacted' || category !== '';
    } else {
      const failPatterns = ['not delivered', 'attempted', 'something went wrong', 'experiment', 'unable to deliver', 'opted out', 'message undeliverable'];
      const dispLower = resolvedDisp.toLowerCase();
      isDelivered = !failPatterns.some(p => dispLower.includes(p));
    }

    const nextServiceDateRaw = isVoice ? getField(row, ['NEXT_SERVICE_DATE', 'next_service_date', 'service_due_date']) : '';
    const checkupDueDateRecords = formatDateToDDMMYYYY(nextServiceDateRaw);

    const appointment = extractAppointmentDetailsFromSummary(summary);
    const showroomLocation = formatShowroomLocation(
      isVoice ? getField(row, ['WORKSHOP_CODE', 'workshop_code']) : getField(row, ['City', 'city']),
      meta.channel
    );

    const finalLocation = appointment.location || showroomLocation.replace(/^Keerthi\s+/i, '');
    const serviceBooked = (dispSlug === 'converted' || category === 'Hot - Converted') ? 'Yes' : 'No';
    const recommendedAction = generateRecommendedAction(category, appointment.confirmedDate, finalLocation);

    allParsedRows.push({
      name,
      phoneNumber: phone,
      leadCategory: category,
      serviceBooked,
      regNumber,
      vinNumber,
      vehicleModel,
      showroomLocation,
      servicePlan: meta.servicePlanName,
      checkupDueDateRecords,
      confirmedDateReply: appointment.confirmedDate,
      confirmedTimeReply: appointment.confirmedTime,
      disposition: dispSlug,
      dispositionDetail: resolvedDisp.toUpperCase(),
      messageDateTime: messageDate,
      messageReplySummary: summary,
      recommendedAction,
      appointmentBookedLocation: finalLocation,
      rawRow: row,
      originalDisposition: rawDisp,
      isCorrected,
      isDelivered,
      priorityScore: getDispositionPriorityScore(dispSlug),
    });
  }

  // De-duplicate Hot & Warm leads by Phone Number (one row per lead: best disposition)
  const leadsByPhone = new Map<string, KeerthiLeadRecord>();

  for (const record of allParsedRows) {
    if (!record.leadCategory) continue; // Only Hot & Warm leads
    const key = record.phoneNumber || record.regNumber || record.name;
    if (!key) continue;

    if (!leadsByPhone.has(key)) {
      leadsByPhone.set(key, record);
    } else {
      const existing = leadsByPhone.get(key)!;
      if (record.priorityScore > existing.priorityScore) {
        leadsByPhone.set(key, record);
      }
    }
  }

  // Sort: Hot - Converted first, then by date descending
  const hotWarmLeads = Array.from(leadsByPhone.values()).sort((a, b) => {
    if (a.leadCategory === 'Hot - Converted' && b.leadCategory !== 'Hot - Converted') return -1;
    if (b.leadCategory === 'Hot - Converted' && a.leadCategory !== 'Hot - Converted') return 1;
    return b.priorityScore - a.priorityScore;
  });

  // Calculate Metrics
  const totalTriggers = allParsedRows.length;
  const deliveredCount = allParsedRows.filter(r => r.isDelivered).length;
  const failedCount = totalTriggers - deliveredCount;

  const categoryCounts: Record<string, number> = {
    'Hot - Converted': 0,
    'Warm - Follow-up Required': 0,
    'Warm - Requested Callback': 0,
    'Warm - Requested Human Agent': 0,
    'Warm - Enquired (Other)': 0,
    'Warm - Self-initiated Visit': 0,
  };

  for (const l of hotWarmLeads) {
    if (categoryCounts[l.leadCategory] !== undefined) {
      categoryCounts[l.leadCategory]++;
    } else {
      categoryCounts[l.leadCategory] = 1;
    }
  }

  const hotCount = categoryCounts['Hot - Converted'] || 0;
  const warmCount = (categoryCounts['Warm - Follow-up Required'] || 0) +
    (categoryCounts['Warm - Requested Callback'] || 0) +
    (categoryCounts['Warm - Requested Human Agent'] || 0) +
    (categoryCounts['Warm - Enquired (Other)'] || 0) +
    (categoryCounts['Warm - Self-initiated Visit'] || 0);

  const hotWarmTotal = hotWarmLeads.length;
  const hotWarmPercent = totalTriggers > 0 ? (hotWarmTotal / totalTriggers) * 100 : 0;

  // Date summary
  const sortedDates = Array.from(distinctDates).sort((a, b) => {
    const parseD = (s: string) => {
      const p = s.split('/');
      return new Date(Number(p[2]), Number(p[1]) - 1, Number(p[0])).getTime();
    };
    return parseD(a) - parseD(b);
  });

  const dateSummary: DateSummaryRow[] = sortedDates.map(date => {
    const rowsOnDate = allParsedRows.filter(r => r.messageDateTime === date);
    const triggers = rowsOnDate.length;
    const delivered = rowsOnDate.filter(r => r.isDelivered).length;
    const leadsOnDate = hotWarmLeads.filter(r => r.messageDateTime === date).length;
    return {
      date,
      triggers,
      delivered,
      hotWarmLeads: leadsOnDate,
    };
  });

  const dateRangeStr = sortedDates.length > 0
    ? `${sortedDates[0]} to ${sortedDates[sortedDates.length - 1]}`
    : new Date().toLocaleDateString('en-GB');

  // Disposition Breakdown
  const dispoMap = new Map<string, { orig: number; final: number; delivered: number; failed: number }>();
  for (const r of allParsedRows) {
    const origKey = (r.originalDisposition || 'BLANK').toUpperCase();
    const finalKey = (r.dispositionDetail || 'BLANK').toUpperCase();

    if (!dispoMap.has(finalKey)) {
      dispoMap.set(finalKey, { orig: 0, final: 0, delivered: 0, failed: 0 });
    }
    const stat = dispoMap.get(finalKey)!;
    stat.final++;
    if (r.isDelivered) stat.delivered++;
    else stat.failed++;
  }

  for (const r of allParsedRows) {
    const origKey = (r.originalDisposition || 'BLANK').toUpperCase();
    if (dispoMap.has(origKey)) {
      dispoMap.get(origKey)!.orig++;
    }
  }

  const dispositionBreakdown: DispositionBreakdownRow[] = Array.from(dispoMap.entries())
    .map(([disp, stats]) => ({
      disposition: disp,
      originalCount: stats.orig || stats.final,
      finalCount: stats.final,
      deliveredCount: stats.delivered,
      failedCount: stats.failed,
      countedAs: (stats.delivered > stats.failed ? 'Delivered' : 'Failed / Undelivered') as 'Delivered' | 'Failed / Undelivered',
    }))
    .sort((a, b) => b.finalCount - a.finalCount);

  return {
    meta,
    sourceFileName: fileName,
    dateRangeStr,
    totalTriggers,
    deliveredCount,
    failedCount,
    hotCount,
    warmCount,
    hotWarmTotal,
    hotWarmPercent,
    correctionsCount: correctionsLog.length,
    categoryCounts,
    dateSummary,
    dispositionBreakdown,
    correctionsLog,
    hotWarmLeads,
    allProcessedRows: allParsedRows,
  };
}

// -------------------------------------------------------------------------
// Styled Excel Workbook Generator (All 4 Sheets)
// -------------------------------------------------------------------------

export function exportKeerthiExcelWorkbook(dataset: KeerthiReportDataset): void {
  const wb = XLSXStyle.utils.book_new();

  // Common Styles
  const navyHeaderStyle = {
    fill: { fgColor: { rgb: '1F4E78' } },
    font: { name: 'Calibri', sz: 11, bold: true, color: { rgb: 'FFFFFF' } },
    alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
    border: {
      top: { style: 'thin', color: { rgb: '103554' } },
      bottom: { style: 'medium', color: { rgb: '103554' } },
      left: { style: 'thin', color: { rgb: '2B5B84' } },
      right: { style: 'thin', color: { rgb: '2B5B84' } },
    },
  };

  const dataCellStyle = {
    font: { name: 'Calibri', sz: 10, color: { rgb: '000000' } },
    alignment: { horizontal: 'left', vertical: 'center' },
    border: {
      top: { style: 'thin', color: { rgb: 'E0E0E0' } },
      bottom: { style: 'thin', color: { rgb: 'E0E0E0' } },
      left: { style: 'thin', color: { rgb: 'E0E0E0' } },
      right: { style: 'thin', color: { rgb: 'E0E0E0' } },
    },
  };

  const centerCellStyle = {
    ...dataCellStyle,
    alignment: { horizontal: 'center', vertical: 'center' },
  };

  const hotPillStyle = {
    ...dataCellStyle,
    fill: { fgColor: { rgb: 'F8CBAD' } }, // Peach / soft coral
    alignment: { horizontal: 'center', vertical: 'center' },
  };

  const warmPillStyle = {
    ...dataCellStyle,
    fill: { fgColor: { rgb: 'FFF2CC' } }, // Soft warm yellow
    alignment: { horizontal: 'center', vertical: 'center' },
  };

  // =========================================================================
  // Sheet 1: Hot & Warm Leads
  // =========================================================================
  const sheet1Headers = [
    'Name',
    'Phone Number',
    'Lead Category',
    'Service Booked?',
    'Registration Number',
    'VIN Number',
    'Vehicle Model',
    'Showroom/Location',
    'Service Plan',
    'Check-up Due Date (Records)',
    'Confirmed/Stated Date (Reply)',
    'Confirmed/Stated Time (Reply)',
    'Disposition',
    'Disposition Detail',
    'Message Date/Time',
    'Message / Reply Summary',
    'Recommended Action',
    'appointment_booked_location',
  ];

  const titleRow = [`Keerthi Triumph — ${dataset.meta.displayName}: Hot & Warm Lead Report (${dataset.dateRangeStr})`];
  const sourceRow = [
    `Source: ${dataset.sourceFileName} | Call date ${dataset.dateRangeStr} | Dispositions corrected using the Updated (manual) Disposition column | Appointment date/time/location read from the reply summary | One row per lead (best disposition, latest interaction)`,
  ];
  const blankRow: string[] = [];

  const ws1Data: unknown[][] = [titleRow, sourceRow, blankRow, sheet1Headers];

  for (const lead of dataset.hotWarmLeads) {
    ws1Data.push([
      excelSafe(lead.name),
      lead.phoneNumber ? Number(lead.phoneNumber) || lead.phoneNumber : '',
      lead.leadCategory,
      lead.serviceBooked,
      excelSafe(lead.regNumber),
      excelSafe(lead.vinNumber),
      excelSafe(lead.vehicleModel),
      excelSafe(lead.showroomLocation),
      excelSafe(lead.servicePlan),
      excelSafe(lead.checkupDueDateRecords),
      excelSafe(lead.confirmedDateReply),
      excelSafe(lead.confirmedTimeReply),
      lead.disposition,
      lead.dispositionDetail,
      lead.messageDateTime,
      excelSafe(lead.messageReplySummary),
      excelSafe(lead.recommendedAction),
      excelSafe(lead.appointmentBookedLocation),
    ]);
  }

  const ws1 = XLSXStyle.utils.aoa_to_sheet(ws1Data);

  // Apply styles to Sheet 1
  const numRows1 = ws1Data.length;
  const numCols1 = sheet1Headers.length;

  for (let c = 0; c < numCols1; c++) {
    const cellRef = XLSXStyle.utils.encode_cell({ r: 3, c });
    if (ws1[cellRef]) ws1[cellRef].s = navyHeaderStyle;
  }

  for (let r = 4; r < numRows1; r++) {
    for (let c = 0; c < numCols1; c++) {
      const cellRef = XLSXStyle.utils.encode_cell({ r, c });
      if (!ws1[cellRef]) continue;

      if (c === 1) {
        // Phone number
        ws1[cellRef].t = 'n';
        ws1[cellRef].z = '0';
        ws1[cellRef].s = centerCellStyle;
      } else if (c === 2) {
        // Category pill
        const cat = ws1[cellRef].v;
        ws1[cellRef].s = cat === 'Hot - Converted' ? hotPillStyle : warmPillStyle;
      } else if ([3, 4, 8, 9, 10, 11, 12, 14].includes(c)) {
        ws1[cellRef].s = centerCellStyle;
      } else if (c === 15 || c === 16) {
        ws1[cellRef].s = {
          ...dataCellStyle,
          alignment: { horizontal: 'left', vertical: 'center', wrapText: true },
        };
      } else {
        ws1[cellRef].s = dataCellStyle;
      }
    }
  }

  ws1['!rows'] = [
    { hpt: 20 },
    { hpt: 16 },
    { hpt: 10 },
    { hpt: 30 },
    ...Array(numRows1 - 4).fill({ hpt: 45 }),
  ];

  ws1['!cols'] = [
    { wch: 25 }, // Name
    { wch: 14 }, // Phone
    { wch: 27 }, // Category
    { wch: 12 }, // Service Booked?
    { wch: 18 }, // Reg
    { wch: 20 }, // VIN
    { wch: 18 }, // Model
    { wch: 25 }, // Showroom
    { wch: 18 }, // Plan
    { wch: 20 }, // Due date
    { wch: 20 }, // Confirmed Date
    { wch: 16 }, // Confirmed Time
    { wch: 24 }, // Disposition
    { wch: 30 }, // Detail
    { wch: 20 }, // Call date
    { wch: 55 }, // Summary
    { wch: 45 }, // Action
    { wch: 26 }, // Location
  ];

  const lastColLetter1 = XLSXStyle.utils.encode_col(numCols1 - 1);
  ws1['!autofilter'] = { ref: `A4:${lastColLetter1}${numRows1}` };
  XLSXStyle.utils.book_append_sheet(wb, ws1, 'Hot & Warm Leads');

  // =========================================================================
  // Sheet 2: Summary
  // =========================================================================
  const s2Title = [`Keerthi Triumph — ${dataset.meta.displayName}: Lead Category Breakdown (${dataset.dateRangeStr})`];
  const s2Headers = [
    'Lead Category',
    'Count',
    '',
    'Date',
    'Triggers',
    'Delivered',
    'Hot & Warm Leads (unique)',
    '',
    'Overall Metric',
    'Count',
  ];

  const catRows = [
    ['Hot - Converted', dataset.categoryCounts['Hot - Converted'] || 0],
    ['Warm - Follow-up Required', dataset.categoryCounts['Warm - Follow-up Required'] || 0],
    ['Warm - Requested Callback', dataset.categoryCounts['Warm - Requested Callback'] || 0],
    ['Warm - Requested Human Agent', dataset.categoryCounts['Warm - Requested Human Agent'] || 0],
    ['Warm - Enquired (Other)', dataset.categoryCounts['Warm - Enquired (Other)'] || 0],
    ['Warm - Self-initiated Visit', dataset.categoryCounts['Warm - Self-initiated Visit'] || 0],
    ['Total Hot & Warm Leads', dataset.hotWarmTotal],
  ];

  const overallMetrics = [
    ['Total Triggers', dataset.totalTriggers],
    ['Failed / Undelivered', dataset.failedCount],
    ['Delivered / Connected', dataset.deliveredCount],
    ['Hot Leads (Converted)', dataset.hotCount],
    ['Warm Leads', dataset.warmCount],
    ['Hot + Warm Leads', dataset.hotWarmTotal],
    ['Hot + Warm as % of Triggers', dataset.totalTriggers > 0 ? (dataset.hotWarmTotal / dataset.totalTriggers) : 0],
    ['Dispositions corrected (vs original)', dataset.correctionsCount],
  ];

  const ws2Data: unknown[][] = [
    s2Title,
    [],
    s2Headers,
  ];

  const maxRows = Math.max(catRows.length, dataset.dateSummary.length + 1, overallMetrics.length);

  for (let i = 0; i < maxRows; i++) {
    const row: unknown[] = [];

    // Left table (Category)
    if (i < catRows.length) {
      row[0] = catRows[i][0];
      row[1] = catRows[i][1];
    } else {
      row[0] = '';
      row[1] = '';
    }
    row[2] = '';

    // Middle table (Date Summary)
    if (i < dataset.dateSummary.length) {
      const ds = dataset.dateSummary[i];
      row[3] = ds.date;
      row[4] = ds.triggers;
      row[5] = ds.delivered;
      row[6] = ds.hotWarmLeads;
    } else if (i === dataset.dateSummary.length) {
      row[3] = 'Total';
      row[4] = dataset.totalTriggers;
      row[5] = dataset.deliveredCount;
      row[6] = dataset.hotWarmTotal;
    } else {
      row[3] = '';
      row[4] = '';
      row[5] = '';
      row[6] = '';
    }
    row[7] = '';

    // Right table (Overall Metrics)
    if (i < overallMetrics.length) {
      row[8] = overallMetrics[i][0];
      row[9] = overallMetrics[i][1];
    } else {
      row[8] = '';
      row[9] = '';
    }

    ws2Data.push(row);
  }

  ws2Data.push([]);
  const channelNote = dataset.meta.channel === 'voice'
    ? 'Note: Voice - dispositions use the Updated (manual) Disposition where filled. Delivered/Connected = call with a recording (call connected); Failed = call with no recording. Dates dd/mm/yyyy.'
    : 'Note: WhatsApp - Failed/Undelivered = message undeliverable, attempted, something went wrong, and system/non-disposition outcomes; everything else = Delivered. Dates dd/mm/yyyy.';
  ws2Data.push([channelNote]);

  const ws2 = XLSXStyle.utils.aoa_to_sheet(ws2Data);

  // Apply styles to Summary headers
  for (let c = 0; c < 10; c++) {
    if ([2, 7].includes(c)) continue;
    const cellRef = XLSXStyle.utils.encode_cell({ r: 2, c });
    if (ws2[cellRef]) ws2[cellRef].s = navyHeaderStyle;
  }

  ws2['!cols'] = [
    { wch: 28 }, // Category
    { wch: 10 }, // Count
    { wch: 4 },  // spacing
    { wch: 14 }, // Date
    { wch: 12 }, // Triggers
    { wch: 12 }, // Delivered
    { wch: 24 }, // Hot/warm
    { wch: 4 },  // spacing
    { wch: 34 }, // Overall Metric
    { wch: 14 }, // Count
  ];

  XLSXStyle.utils.book_append_sheet(wb, ws2, 'Summary');

  // =========================================================================
  // Sheet 3: Disposition Breakdown
  // =========================================================================
  const isVoice = dataset.meta.channel === 'voice';
  const ws3Headers = isVoice
    ? ['Disposition (final)', 'Original Count', 'Final Count', 'Delivered (call recorded)', 'Failed (no recording)']
    : ['Disposition (final)', 'Original Count', 'Final Count', 'Counted As'];

  const ws3Data: unknown[][] = [ws3Headers];

  for (const d of dataset.dispositionBreakdown) {
    if (isVoice) {
      ws3Data.push([
        d.disposition,
        d.originalCount,
        d.finalCount,
        d.deliveredCount,
        d.failedCount,
      ]);
    } else {
      ws3Data.push([
        d.disposition,
        d.originalCount,
        d.finalCount,
        d.countedAs || 'Delivered',
      ]);
    }
  }

  const ws3 = XLSXStyle.utils.aoa_to_sheet(ws3Data);
  for (let c = 0; c < ws3Headers.length; c++) {
    const cellRef = XLSXStyle.utils.encode_cell({ r: 0, c });
    if (ws3[cellRef]) ws3[cellRef].s = navyHeaderStyle;
  }

  ws3['!cols'] = [
    { wch: 45 },
    { wch: 16 },
    { wch: 16 },
    { wch: 24 },
    { wch: 24 },
  ];
  XLSXStyle.utils.book_append_sheet(wb, ws3, 'Disposition Breakdown');

  // =========================================================================
  // Sheet 4: Corrections Log
  // =========================================================================
  const ws4Headers = ['Name', 'Phone Number', 'Original Disposition', 'Corrected Disposition', 'Correction Source'];
  const ws4Data: unknown[][] = [ws4Headers];

  for (const c of dataset.correctionsLog) {
    ws4Data.push([
      excelSafe(c.name),
      c.phoneNumber ? Number(c.phoneNumber) || c.phoneNumber : '',
      c.originalDisposition,
      c.correctedDisposition,
      c.correctionSource,
    ]);
  }

  const ws4 = XLSXStyle.utils.aoa_to_sheet(ws4Data);
  for (let c = 0; c < ws4Headers.length; c++) {
    const cellRef = XLSXStyle.utils.encode_cell({ r: 0, c });
    if (ws4[cellRef]) ws4[cellRef].s = navyHeaderStyle;
  }

  ws4['!cols'] = [
    { wch: 30 },
    { wch: 16 },
    { wch: 26 },
    { wch: 26 },
    { wch: 28 },
  ];
  XLSXStyle.utils.book_append_sheet(wb, ws4, 'Corrections Log');

  // Generate filename
  const cleanBaseName = dataset.sourceFileName.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9_-]/g, '_');
  const exportFileName = `${cleanBaseName}_Report_${new Date().toISOString().slice(0, 10)}.xlsx`;

  XLSXStyle.writeFile(wb, exportFileName);
}
