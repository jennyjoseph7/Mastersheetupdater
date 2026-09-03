import { normalizePhone, canonicalHeader, clean } from '@/lib/data-pipeline';

export type MatchKeyType = 'reg_number' | 'phone_number' | 'vin_number' | 'smart_fallback' | 'custom';
export type MergeMode = 'enriched_client' | 'matched_only' | 'full_audit';

export interface DealershipPreset {
  id: string;
  name: string;
  workflow: string;
  defaultMatchKey: MatchKeyType;
  expectedRegCol?: string;
  expectedPhoneCol?: string;
  expectedVinCol?: string;
  defaultMasterCols?: string[];
}

export const DEALERSHIP_PRESETS: Record<string, DealershipPreset> = {
  kt_psf: {
    id: 'kt_psf',
    name: 'KT PSF (Keerthi Triumph)',
    workflow: 'Post Service Feedback',
    defaultMatchKey: 'reg_number',
    expectedRegCol: 'Registration No',
    expectedPhoneCol: 'Mobile',
    expectedVinCol: 'Chassis No',
    defaultMasterCols: [
      'Call_Date',
      'Call_Triggered',
      'Outcome',
      'Disposition',
      'Disposition_detail',
      'Summary',
      'Call_Duration',
      'Recordings',
      'Sentiment',
      'Number_of_attempts',
    ],
  },
  ambal_service: {
    id: 'ambal_service',
    name: 'Ambal',
    workflow: 'Post-Sales Service Reminder',
    defaultMatchKey: 'reg_number',
    expectedRegCol: 'Registration Num',
    expectedPhoneCol: 'Customer Mobile No.',
    expectedVinCol: 'VIN',
  },
  bullmen_service: {
    id: 'bullmen_service',
    name: 'Bullmen',
    workflow: 'Post-Sales Service Reminder',
    defaultMatchKey: 'reg_number',
    expectedRegCol: 'Vehicle Number',
    expectedPhoneCol: 'Phone No',
    expectedVinCol: 'Chassis No',
  },
  fortune_service: {
    id: 'fortune_service',
    name: 'Fortune Toyota',
    workflow: 'Post-Sales Service Reminder',
    defaultMatchKey: 'reg_number',
    expectedRegCol: 'Reg No.',
    expectedPhoneCol: 'Contact Number',
    expectedVinCol: 'VIN No.',
  },
  icare_feedback: {
    id: 'icare_feedback',
    name: 'ICare',
    workflow: 'Post Service Feedback',
    defaultMatchKey: 'phone_number',
    expectedPhoneCol: 'Mobile No',
    expectedRegCol: 'Registration No',
  },
  perfect_riders_service: {
    id: 'perfect_riders_service',
    name: 'Perfect Riders',
    workflow: 'Post-Sales Service Reminder',
    defaultMatchKey: 'reg_number',
    expectedRegCol: 'REG_NUMBER',
    expectedPhoneCol: 'PHONE_NUMBER',
  },
  suryabala_service: {
    id: 'suryabala_service',
    name: 'Suryabala Honda',
    workflow: 'Post-Sales Service Reminder',
    defaultMatchKey: 'reg_number',
    expectedRegCol: 'Registration No.',
    expectedPhoneCol: 'Contact Number',
  },
  anant_cars: {
    id: 'anant_cars',
    name: 'Anant Cars',
    workflow: 'Sales / Pre-Sales',
    defaultMatchKey: 'phone_number',
    expectedPhoneCol: 'Customer Phone',
  },
  singhal: {
    id: 'singhal',
    name: 'Singhal Volkswagen',
    workflow: 'Sales / Pre-Sales',
    defaultMatchKey: 'phone_number',
    expectedPhoneCol: 'MOBILE NUMBER',
  },
  custom_dealership: {
    id: 'custom_dealership',
    name: 'Custom / Other Dealership',
    workflow: 'General Merging',
    defaultMatchKey: 'reg_number',
  },
};

export interface ColumnOption {
  header: string;
  normalizedKey: string;
}

export interface MatchedRecord {
  _matchStatus: 'matched' | 'unmatched_client' | 'unmatched_master';
  _matchKeyUsed?: string;
  _matchValue?: string;
  [key: string]: unknown;
}

export interface MergeStats {
  totalClientRows: number;
  totalMasterRows: number;
  matchedCount: number;
  unmatchedClientCount: number;
  unmatchedMasterCount: number;
  matchRatePercent: number;
}

export const REG_CANDIDATES = [
  'reg_number',
  'registration_num',
  'registration_number',
  'registration_no',
  'registration_no.',
  'vehicle_number',
  'vehicle_num',
  'veh_no',
  'veh_number',
  'reg_no',
  'reg_no.',
  'rc_number',
  'registration',
];

export const PHONE_CANDIDATES = [
  'phone_number',
  'phone',
  'mobile',
  'mobile_number',
  'customer_mobile_no.',
  'customer_mobile_no',
  'customer_mobile',
  'contact_number',
  'contact_no',
  'phone_no',
  'customer_phone',
  'car_user_phone',
  'mi_contact_no',
  'contact',
  'alt_phone_number_2',
];

export const VIN_CANDIDATES = [
  'vin_number',
  'vin',
  'chassis_no',
  'chassis_number',
  'chassis',
  'frame_#',
  'frame_no',
  'frame_number',
  'vin_no',
];

export const DEFAULT_MASTER_COLUMNS_TO_APPEND = [
  'Call_Date',
  'Call_Triggered',
  'Outcome',
  'Disposition',
  'Disposition_detail',
  'Manual_Disposition_detail',
  'Summary',
  'Call_Duration',
  'Recordings',
  'Sentiment',
  'Number_of_attempts',
  'Lead_Timeline',
  'Language',
  'Lead_Id',
];

export function normalizeRegNumber(raw: unknown): string {
  if (raw == null) return '';
  const s = String(raw).trim().toUpperCase();
  return s.replace(/[^A-Z0-9]/g, '');
}

export function normalizeVin(raw: unknown): string {
  if (raw == null) return '';
  const s = String(raw).trim().toUpperCase();
  return s.replace(/[^A-Z0-9]/g, '');
}

export function normalizeMatchValue(val: unknown, keyType: 'phone' | 'reg' | 'vin' | 'raw'): string {
  if (val == null) return '';
  if (keyType === 'phone') {
    return normalizePhone(val) || '';
  }
  if (keyType === 'reg') {
    return normalizeRegNumber(val);
  }
  if (keyType === 'vin') {
    return normalizeVin(val);
  }
  return String(val).trim().toLowerCase();
}

export function detectColumnCandidate(headers: string[], candidates: string[]): string {
  const normCandidates = candidates.map(c => canonicalHeader(c));
  for (const h of headers) {
    const norm = canonicalHeader(h);
    if (normCandidates.includes(norm)) {
      return h;
    }
  }
  for (const h of headers) {
    const norm = canonicalHeader(h);
    for (const c of normCandidates) {
      if (norm.includes(c) || c.includes(norm)) {
        return h;
      }
    }
  }
  return '';
}

export interface MergeOptions {
  clientRows: Record<string, string>[];
  clientHeaders: string[];
  masterRows: Record<string, string>[];
  masterHeaders: string[];
  matchKeyType: MatchKeyType;
  clientMatchCol: string;
  masterMatchCol: string;
  clientPhoneColFallback?: string;
  masterPhoneColFallback?: string;
  selectedMasterColsToAppend: string[];
  mergeMode: MergeMode;
}

export interface MergeResult {
  outputRows: MatchedRecord[];
  outputHeaders: string[];
  stats: MergeStats;
}

export function executeMerge(options: MergeOptions): MergeResult {
  const {
    clientRows,
    clientHeaders,
    masterRows,
    masterHeaders,
    matchKeyType,
    clientMatchCol,
    masterMatchCol,
    clientPhoneColFallback,
    masterPhoneColFallback,
    selectedMasterColsToAppend,
    mergeMode,
  } = options;

  const keyTypeForNormalization =
    matchKeyType === 'reg_number'
      ? 'reg'
      : matchKeyType === 'phone_number'
      ? 'phone'
      : matchKeyType === 'vin_number'
      ? 'vin'
      : 'raw';

  // Build lookup index for Master Rows
  const masterLookup = new Map<string, Record<string, string>[]>();
  const masterPhoneFallbackLookup = new Map<string, Record<string, string>[]>();
  const masterUsedIndices = new Set<number>();

  masterRows.forEach((row, idx) => {
    const rawVal = row[masterMatchCol];
    const key = normalizeMatchValue(rawVal, keyTypeForNormalization);
    if (key) {
      if (!masterLookup.has(key)) masterLookup.set(key, []);
      masterLookup.get(key)!.push({ ...row, __originalMasterIndex: String(idx) });
    }

    if (matchKeyType === 'smart_fallback' && masterPhoneColFallback) {
      const pVal = row[masterPhoneColFallback];
      const pKey = normalizePhone(pVal) || '';
      if (pKey) {
        if (!masterPhoneFallbackLookup.has(pKey)) masterPhoneFallbackLookup.set(pKey, []);
        masterPhoneFallbackLookup.get(pKey)!.push({ ...row, __originalMasterIndex: String(idx) });
      }
    }
  });

  const outputRows: MatchedRecord[] = [];
  let matchedCount = 0;
  let unmatchedClientCount = 0;

  // Process Client Rows
  clientRows.forEach(clientRow => {
    const rawVal = clientRow[clientMatchCol];
    const key = normalizeMatchValue(rawVal, keyTypeForNormalization);

    let matchingMasterRow: Record<string, string> | null = null;
    let matchKeyUsed = '';
    let matchValUsed = '';

    if (key && masterLookup.has(key)) {
      const candidates = masterLookup.get(key)!;
      matchingMasterRow = candidates[0]; // First or highest priority
      matchKeyUsed = masterMatchCol;
      matchValUsed = key;
    } else if (matchKeyType === 'smart_fallback' && clientPhoneColFallback) {
      const pVal = clientRow[clientPhoneColFallback];
      const pKey = normalizePhone(pVal) || '';
      if (pKey && masterPhoneFallbackLookup.has(pKey)) {
        const candidates = masterPhoneFallbackLookup.get(pKey)!;
        matchingMasterRow = candidates[0];
        matchKeyUsed = masterPhoneColFallback || 'phone';
        matchValUsed = pKey;
      }
    }

    if (matchingMasterRow) {
      matchedCount++;
      const masterIdx = Number(matchingMasterRow.__originalMasterIndex);
      if (!isNaN(masterIdx)) masterUsedIndices.add(masterIdx);

      const combined: MatchedRecord = {
        _matchStatus: 'matched',
        _matchKeyUsed: matchKeyUsed,
        _matchValue: matchValUsed,
        ...clientRow,
      };

      // Append selected master columns
      selectedMasterColsToAppend.forEach(col => {
        // If column exists in master, append it
        // Ensure no overwriting of client columns by using clean names or preserving
        combined[col] = matchingMasterRow![col] ?? '';
      });

      outputRows.push(combined);
    } else {
      unmatchedClientCount++;
      if (mergeMode === 'enriched_client' || mergeMode === 'full_audit') {
        const combined: MatchedRecord = {
          _matchStatus: 'unmatched_client',
          _matchKeyUsed: '',
          _matchValue: key || '',
          ...clientRow,
        };

        selectedMasterColsToAppend.forEach(col => {
          combined[col] = '';
        });

        outputRows.push(combined);
      }
    }
  });

  // If Full Audit, also append Master Rows that were never matched
  let unmatchedMasterCount = 0;
  if (mergeMode === 'full_audit') {
    masterRows.forEach((mRow, idx) => {
      if (!masterUsedIndices.has(idx)) {
        unmatchedMasterCount++;
        const combined: MatchedRecord = {
          _matchStatus: 'unmatched_master',
          _matchKeyUsed: masterMatchCol,
          _matchValue: normalizeMatchValue(mRow[masterMatchCol], keyTypeForNormalization),
        };

        // Blank out client headers
        clientHeaders.forEach(cHeader => {
          combined[cHeader] = '';
        });

        // Fill in master columns
        selectedMasterColsToAppend.forEach(col => {
          combined[col] = mRow[col] ?? '';
        });

        outputRows.push(combined);
      }
    });
  } else {
    unmatchedMasterCount = masterRows.length - masterUsedIndices.size;
  }

  // Build ordered output headers: Client headers first, followed by selected master columns
  const outputHeaders: string[] = [...clientHeaders];
  selectedMasterColsToAppend.forEach(col => {
    if (!outputHeaders.includes(col)) {
      outputHeaders.push(col);
    }
  });

  const totalClient = clientRows.length;
  const matchRate = totalClient > 0 ? (matchedCount / totalClient) * 100 : 0;

  const stats: MergeStats = {
    totalClientRows: totalClient,
    totalMasterRows: masterRows.length,
    matchedCount,
    unmatchedClientCount,
    unmatchedMasterCount,
    matchRatePercent: Math.round(matchRate * 10) / 10,
  };

  return {
    outputRows,
    outputHeaders,
    stats,
  };
}
