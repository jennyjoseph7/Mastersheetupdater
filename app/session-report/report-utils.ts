/**
 * Report generation utilities for Keerthi Session Report
 */

export const REPORT_HEADERS = [
  'Name',
  'Phone Number',
  'Campaign',
  'Lead Category',
  'Service Booked?',
  'Vehicle Number',
  'Vehicle Model',
  'Showroom',
  'Service Plan',
  'Service Due Date (Records)',
  'Confirmed/Stated Date (Call)',
  'Disposition',
  'Disposition Detail',
  'Call Date',
  'Call Summary',
  'Updated Disposition',
  'AI Reason',
  // 'Debug Match', // Uncomment to debug join matches
];

export function cellToString(c: any): string {
  if (c == null) return '';
  return String(c).trim();
}

export function excelSafe(str: any): string {
  const s = cellToString(str);
  if (/^[\+\-\=\@]/.test(s)) return "'" + s;
  return s;
}

export function normalizeKey(k: string): string {
  return String(k || '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '');
}

/**
 * Case-insensitive, punctuation-insensitive field getter.
 * First tries direct candidate keys, then searches row keys ignoring case/symbols.
 */
export function get(row: any, keys: string[]): string {
  if (!row) return '';
  // Direct check
  for (const k of keys) {
    if (row[k] !== undefined && row[k] !== null && String(row[k]).trim() !== '') {
      return String(row[k]).trim();
    }
  }
  // Normalized check
  const normTargets = keys.map(k => normalizeKey(k));
  for (const [rk, rv] of Object.entries(row)) {
    if (rv === undefined || rv === null || String(rv).trim() === '') continue;
    if (normTargets.includes(normalizeKey(rk))) {
      return String(rv).trim();
    }
  }
  return '';
}

/**
 * Normalizes any phone representation (including scientific notation e.g. 9.1789E+11,
 * +91 prefix, 91 prefix, leading zero) to 10 clean digits.
 */
export function normalizePhone(raw: unknown): string | null {
  if (raw == null) return null;
  let s = String(raw).trim();
  if (!s) return null;

  // Handle scientific notation from Excel (e.g. 9.1789E+11 or 9.19822e11)
  if (/^\d[\d.]*[eE][+\-]?\d+$/.test(s)) {
    const parsed = parseFloat(s);
    if (!isNaN(parsed)) {
      s = String(Math.round(parsed));
    }
  }

  const digits = s.replace(/\D/g, '');
  if (!digits) return null;

  // 12 digits starting with 91 -> 10 digits
  if (digits.startsWith('91') && digits.length === 12) return digits.slice(2);
  // 11 digits starting with 0 -> 10 digits
  if (digits.startsWith('0') && digits.length === 11) return digits.slice(1);
  // Exactly 10 digits
  if (digits.length === 10) return digits;
  // If more than 10 digits and starts with 91
  if (digits.startsWith('91') && digits.length > 12) return digits.slice(digits.length - 10);
  if (digits.length > 10) return digits.slice(-10);

  return digits.length >= 7 ? digits : null;
}

/**
 * Robustly extracts all phone number candidates from a row (direct keys, search_term, scanned values).
 */
export function extractAllPhoneCandidates(row: any): string[] {
  const phones = new Set<string>();
  if (!row) return [];

  const phoneKeys = [
    'phone_number', 'phone', 'mobile', 'contact_number', 'contact', 
    'customer_phone', 'mobile_number', 'to', 'recipient', 'destination', 
    'call_to', 'phone_no', 'customer_mobile', 'user_phone', 'phonenumber',
    'contact_no', 'customer_contact'
  ];

  for (const k of phoneKeys) {
    const val = get(row, [k]);
    if (val) {
      const norm = normalizePhone(val);
      if (norm) phones.add(norm);
      const cleanDigits = String(val).replace(/\D/g, '');
      if (cleanDigits) phones.add(cleanDigits);
    }
  }

  // search_term check
  const st = get(row, ['search_term', 'searchterm']);
  if (st) {
    const matches = st.match(/\b(?:\+?91|0)?([6-9]\d{9})\b/g);
    if (matches) {
      for (const m of matches) {
        const norm = normalizePhone(m);
        if (norm) phones.add(norm);
      }
    }
  }

  // Scan row values
  for (const v of Object.values(row)) {
    if (!v) continue;
    const s = String(v).trim();
    if (s.length >= 10 && s.length <= 15) {
      const norm = normalizePhone(s);
      if (norm && /^[6-9]\d{9}$/.test(norm)) {
        phones.add(norm);
      }
    }
  }

  return Array.from(phones);
}

/**
 * Extracts the single primary phone number from a row.
 */
export function extractPhone(row: any): string {
  const candidates = extractAllPhoneCandidates(row);
  return candidates[0] || '';
}

/**
 * Automatically detects whether the two uploaded files were swapped.
 * Leads files contain dealership & vehicle specific columns like workshop_name,
 * vehicle_model, service_plan_type, and next_service_due.
 */
export function detectFileRoles(rows1: any[], rows2: any[]): { leadRows: any[]; sessionRows: any[]; swapped: boolean } {
  const isLeadFile = (rows: any[]) => {
    if (!rows || !rows.length) return 0;
    const keys = Object.keys(rows[0]).map(k => normalizeKey(k));
    const leadSpecificKeys = [
      'vehiclemodel', 'workshopname', 'serviceplantype', 'nextservicedue', 
      'serviceduetimestamp', 'workshopcode', 'workshopcity', 'workshoptype', 'purchasedate'
    ];
    return leadSpecificKeys.filter(k => keys.includes(k)).length;
  };

  const l1 = isLeadFile(rows1);
  const l2 = isLeadFile(rows2);

  if (l2 > l1) {
    return { leadRows: rows2, sessionRows: rows1, swapped: true };
  }
  return { leadRows: rows1, sessionRows: rows2, swapped: false };
}

/**
 * Extracts Vehicle Registration Number with fallbacks:
 * 1. Direct columns in lead or session row
 * 2. vehicle_id parsing (e.g. "india-ka03kt2539-md2b41mx5pnd00248")
 * 3. search_term parsing (e.g. "ka03ks9944-md2b41mx5pnd00279-...")
 */
export function extractVehicleNumber(lead: any, session: any): string {
  const regKeys = [
    'reg_number', 'registration_number', 'vehicle_registration_number', 
    'vehicle_number', 'vehicle_reg_number', 'registration_no', 'reg_no', 
    'vehicle_no', 'regnumber', 'vehiclenumber', 'registration', 'Vehicle Number'
  ];

  // 1. Direct from lead row
  let reg = get(lead, regKeys);
  if (reg) return reg.toUpperCase().replace(/[\s-]+/g, '');

  // 2. Direct from session row
  reg = get(session, regKeys);
  if (reg) return reg.toUpperCase().replace(/[\s-]+/g, '');

  // 3. Fallback: vehicle_id
  const vehId = get(lead, ['vehicle_id', 'vehicleid']) || get(session, ['vehicle_id', 'vehicleid']);
  if (vehId) {
    const parts = vehId.split('-');
    for (const p of parts) {
      if (/^[a-zA-Z]{2}\d{1,2}[a-zA-Z]{1,3}\d{4}$/i.test(p)) {
        return p.toUpperCase().replace(/[\s-]+/g, '');
      }
    }
  }

  // 4. Fallback: search_term
  const st = get(lead, ['search_term', 'searchterm']) || get(session, ['search_term', 'searchterm']);
  if (st) {
    const m = st.match(/\b([A-Za-z]{2}\s*[-]?\s*[0-9]{1,2}\s*[-]?\s*[A-Za-z]{1,3}\s*[-]?\s*[0-9]{4})\b/i);
    if (m && m[1]) {
      return m[1].toUpperCase().replace(/[\s-]+/g, '');
    }
  }

  return '';
}

/**
 * Extracts Vehicle Model:
 * 1. Fetches vehicle_model directly from leads file
 * 2. Checks session row
 * 3. Fallback: parses known models from search_term / campaign
 */
export function extractVehicleModel(lead: any, session: any): string {
  const modelKeys = [
    'vehicle_model', 'existing_vehicle_model', 'model', 'car_model', 
    'bike_model', 'vehicle_name', 'vehiclemodel', 'model_name', 'vehicle', 'Vehicle Model'
  ];

  // 1. Direct from lead file (primary source)
  const leadModel = get(lead, modelKeys);
  if (leadModel) return leadModel;

  // 2. Direct from session file
  const sessionModel = get(session, modelKeys);
  if (sessionModel) return sessionModel;

  // 3. Scan search_term, campaign_name, etc.
  const text = [
    get(lead, ['search_term']),
    get(session, ['search_term']),
    get(lead, ['campaign_name', 'audience_name']),
    get(session, ['campaign_name', 'campaign_model']),
  ].filter(Boolean).join(' ').toLowerCase();

  const knownModels: { pattern: RegExp; name: string }[] = [
    { pattern: /speed\s*t4\s*350/i, name: 'Speed T4 350' },
    { pattern: /speed\s*t4/i, name: 'Speed T4' },
    { pattern: /speed\s*400/i, name: 'Speed 400' },
    { pattern: /scrambler\s*400\s*x/i, name: 'Scrambler 400X' },
    { pattern: /scrambler\s*400/i, name: 'Scrambler 400' },
    { pattern: /trident\s*660/i, name: 'Trident 660' },
    { pattern: /tiger\s*sport\s*660/i, name: 'Tiger Sport 660' },
    { pattern: /tiger\s*900/i, name: 'Tiger 900' },
    { pattern: /tiger\s*1200/i, name: 'Tiger 1200' },
    { pattern: /tiger\s*850/i, name: 'Tiger 850' },
    { pattern: /street\s*triple\s*765/i, name: 'Street Triple 765' },
    { pattern: /street\s*triple/i, name: 'Street Triple' },
    { pattern: /daytona\s*660/i, name: 'Daytona 660' },
    { pattern: /bonneville\s*t120/i, name: 'Bonneville T120' },
    { pattern: /bonneville\s*t100/i, name: 'Bonneville T100' },
    { pattern: /bonneville\s*speedmaster/i, name: 'Bonneville Speedmaster' },
    { pattern: /bonneville\s*bobber/i, name: 'Bonneville Bobber' },
    { pattern: /bonneville/i, name: 'Bonneville' },
    { pattern: /speed\s*twin\s*900/i, name: 'Speed Twin 900' },
    { pattern: /speed\s*twin\s*1200/i, name: 'Speed Twin 1200' },
    { pattern: /speed\s*twin/i, name: 'Speed Twin' },
    { pattern: /scrambler\s*900/i, name: 'Scrambler 900' },
    { pattern: /scrambler\s*1200/i, name: 'Scrambler 1200' },
    { pattern: /rocket\s*3/i, name: 'Rocket 3' },
  ];

  for (const km of knownModels) {
    if (km.pattern.test(text)) return km.name;
  }

  return '';
}

/**
 * Extracts Showroom:
 * Fetches workshop_name from lead file (with formatting/fallbacks)
 */
export function extractShowroom(lead: any, session: any): string {
  // 1. Direct from lead file workshop_name
  let showroom = get(lead, ['workshop_name', 'workshop_full_name', 'workshopname']);
  
  // 2. Fallbacks if blank
  if (!showroom) {
    showroom = get(session, ['workshop_name', 'workshop_full_name']) || 
               get(lead, ['dealership_id', 'showroom_code', 'showroom', 'show_room']) ||
               get(session, ['dealership_id', 'showroom_code', 'showroom']);
  }

  if (showroom) {
    if (showroom.toLowerCase().startsWith('m-s-') || showroom.toLowerCase().startsWith('m/s-')) {
      showroom = showroom.replace(/^m[-/]s[-_]/i, '').replace(/[-_]/g, ' ');
      showroom = showroom.split(' ').filter(Boolean).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    } else if (/[-_]/.test(showroom) && !/\s/.test(showroom)) {
      showroom = showroom.replace(/[-_]/g, ' ').split(' ').filter(Boolean).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    }
  }
  return showroom;
}

/**
 * Extracts Service Plan:
 * Fetches service_plan_type directly from lead file.
 */
export function extractServicePlan(lead: any, session: any): string {
  // 1. Primary: service_plan_type from lead file
  const planType = get(lead, ['service_plan_type', 'serviceplantype']);
  if (planType) return planType;

  // 2. Fallbacks
  const fallback = get(lead, ['service_plan', 'service_type', 'Service Plan']) || 
                   get(session, ['service_plan_type', 'service_plan', 'service_type']);
  if (fallback) return fallback;

  // 3. Infer from search_term / campaign_name if present
  const combined = [
    get(lead, ['campaign_name', 'search_term']),
    get(session, ['campaign_name', 'search_term']),
  ].join(' ').toLowerCase();

  if (combined.includes('_s1') || combined.includes('first service')) return 'First';
  if (combined.includes('_s2') || combined.includes('second service')) return 'Second';
  if (combined.includes('_s3') || combined.includes('third service')) return 'Third';
  if (combined.includes('_s4') || combined.includes('fourth service')) return 'Fourth';
  if (combined.includes('_s5') || combined.includes('fifth service')) return 'Fifth';
  if (combined.includes('_s6') || combined.includes('sixth service')) return 'Sixth';

  return '';
}

/**
 * Extracts Service Due Date (Records):
 * Pulls next_service_due, service_due_timestamp, last_service_date from lead file.
 * Handles timestamps, Excel serial dates, and standard date strings.
 */
export function extractServiceDueDate(lead: any, session: any): string {
  const rawDate = get(lead, [
    'next_service_due', 'service_due_date', 'due_date', 
    'service_due_timestamp', 'serviceduetimestamp', 'nextservicedue',
    'last_service_date', 'lastservicedate', 'warranty_expiry_date', 'warrantyexpirydate'
  ]) || get(session, ['service_due_date', 'next_service_due', 'due_date']);

  if (!rawDate) return '';

  // Numeric checks (Excel serial or epoch)
  const num = Number(rawDate);
  if (!isNaN(num) && num > 0) {
    // Excel serial number (e.g. 44000 - 48000)
    if (num > 30000 && num < 60000) {
      const d = new Date(Math.round((num - 25569) * 86400 * 1000));
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      }
    }
    // Epoch in milliseconds
    if (num > 1000000000000) {
      const d = new Date(num);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      }
    }
    // Epoch in seconds
    if (num > 1000000000) {
      const d = new Date(num * 1000);
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      }
    }
  }

  // Standard date parsing
  const d = new Date(rawDate);
  if (!isNaN(d.getTime()) && d.getFullYear() > 2000 && d.getFullYear() < 2100) {
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  return String(rawDate).trim();
}

/**
 * Determines Lead Category (Hot - Converted, Hot Lead, Warm Lead, Cold Lead)
 */
export function determineLeadCategory(session: any, lead: any): string {
  const directCat = get(lead, ['lead_category', 'prioritization_category', 'Lead Category']) || 
                    get(session, ['lead_category', 'Lead Category']);
  
  const disp = String(get(session, ['disposition'])).toLowerCase();
  const dispDetail = String(get(session, ['disposition_detail', 'disposition_details', 'updated_disposition'])).toLowerCase();
  const dispText = `${disp} ${dispDetail}`.trim();

  const isConverted = disp.includes('converted') || dispDetail.includes('converted');
  if (isConverted) {
    return 'Hot - Converted';
  }

  if (['test drive', 'showroom visit planned', 'vehicle booked for service', 'will decide tomorrow', 'will decide within 1 to 3 days', 'will decide within 4 to 7 days'].some(t => dispText.includes(t))) {
    return 'Hot Lead';
  }
  if (['requested callback', 'follow up required', 'price inquiry', 'talk to human', 'interested in another car', 'will decide within 8 to 14 days', 'will decide within 15 to 30 days'].some(t => dispText.includes(t))) {
    return 'Warm Lead';
  }
  if (['not interested', 'rejected', 'invalid lead', 'wrong contact number', 'has sold/given away the car', 'lost to competition', 'already serviced', 'has moved', 'unsubscribed', 'language barrier'].some(t => dispText.includes(t))) {
    return 'Cold Lead';
  }

  if (directCat) return directCat;
  return disp ? 'Warm Lead' : '';
}
