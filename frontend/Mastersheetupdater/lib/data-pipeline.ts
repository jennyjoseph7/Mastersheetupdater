import * as XLSX from 'xlsx';

export function cellToString(val: unknown): string {
  if (val == null) return '';
  if (typeof val === 'number' && !Number.isFinite(val)) return '';
  if (typeof val === 'number' && Math.abs(val) > 1e15) return val.toExponential();
  return String(val);
}

export function normalizePhone(raw: unknown): string | null {
  if (raw == null) return null;
  const s = String(raw).replace(/\D/g, '');
  if (!s) return null;
  if (s.length === 10) return s;
  if (s.length === 11 && s[0] === '0') return s.slice(1);
  if (s.length === 12 && s.startsWith('91')) return s.slice(2);
  if (s.length > 10) return s.slice(-10);
  return s;
}

export function readFileAsArrayBuffer(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

export function parseSheet(ab: ArrayBuffer): Record<string, unknown>[] {
  const wb = XLSX.read(ab, { type: 'array', cellDates: true });
  const ws = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(ws, { raw: false, defval: '' }) as Record<string, unknown>[];
}

export function esc(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export const escapeHtml = esc;

export function clean(value: unknown): string {
  return String(value ?? '').trim();
}

export function lower(value: unknown): string {
  return String(value ?? '').toLowerCase();
}

export function canonicalHeader(h: unknown): string {
  return String(h ?? '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

export const normalizeHeader = canonicalHeader;

export function findCol(row: Record<string, unknown>, candidates: string[]): string {
  for (const c of candidates) {
    const key = canonicalHeader(c);
    if (row[key] != null && String(row[key]).trim() !== '') return key;
  }
  return '';
}

export function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  if (digits.length < 6) return phone;
  return digits.slice(0, digits.length - 4).replace(/\d/g, '*') + digits.slice(-4);
}

export function phoneKey(value: unknown): string {
  const normalized = normalizePhone(value);
  return normalized || '';
}

export function colLetter(n: number): string {
  let s = '';
  while (n >= 0) {
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26) - 1;
  }
  return s;
}

export function isPhoneLike(val: unknown): boolean {
  if (val == null) return false;
  const s = String(val).trim();
  if (!s) return false;
  const digits = s.replace(/\D/g, '');
  return digits.length >= 10;
}

export function excelSafe(v: unknown): string {
  const s = String(v ?? '');
  return /^[-+=@]/.test(s) ? "'" + s : s;
}

export function excelSafeCsvCell(v: unknown): string {
  const s = String(v ?? '');
  if (/[\",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

export function excelSafeTsvCell(v: unknown): string {
  return String(v ?? '').replace(/[\t\n]/g, ' ');
}

export function rowsToTsv(rows: Record<string, unknown>[], keys: string[]): string {
  const header = keys.join('\t');
  const lines = rows.map(r => keys.map(k => excelSafeTsvCell(r[k])).join('\t'));
  return [header, ...lines].join('\n');
}

// ── File Validation ──────────────────────────────────────────────

export const MAX_UPLOAD_SIZE_MB = 50;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

const ALLOWED_EXTENSIONS = new Set(['.csv', '.xlsx', '.xls', '.tsv']);

const EXTENSION_MIME_MAP: Record<string, string[]> = {
  '.csv': ['text/csv', 'text/plain', 'application/csv', 'application/vnd.ms-excel'],
  '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/octet-stream'],
  '.xls': ['application/vnd.ms-excel', 'application/octet-stream'],
  '.tsv': ['text/tab-separated-values', 'text/plain'],
};

// Known file magic bytes for spreadsheet formats
const MAGIC_BYTES: Record<string, (bytes: Uint8Array) => boolean> = {
  '.xlsx': (bytes) => bytes.length >= 4 && bytes[0] === 0x50 && bytes[1] === 0x4B && bytes[2] === 0x03 && bytes[3] === 0x04, // PK\x03\x04 (ZIP)
  '.xls': (bytes) => bytes.length >= 8 && bytes[0] === 0xD0 && bytes[1] === 0xCF && bytes[2] === 0x11 && bytes[3] === 0xE0 && bytes[4] === 0xA1 && bytes[5] === 0xB1 && bytes[6] === 0x1A && bytes[7] === 0xE1, // D0CF11E0 (OLE2)
};

function getFileExtension(filename: string): string {
  const dot = filename.lastIndexOf('.');
  if (dot === -1) return '';
  return filename.slice(dot).toLowerCase();
}

export interface FileValidationResult {
  valid: boolean;
  error?: string;
}

export function validateFileSize(file: File): FileValidationResult {
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return {
      valid: false,
      error: `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum allowed is ${MAX_UPLOAD_SIZE_MB} MB.`,
    };
  }
  return { valid: true };
}

export function validateFileExtension(file: File): FileValidationResult {
  const ext = getFileExtension(file.name);
  if (!ext) {
    return { valid: false, error: 'File has no extension. Accepted: .csv, .xlsx, .xls, .tsv' };
  }
  if (!ALLOWED_EXTENSIONS.has(ext)) {
    return { valid: false, error: `File type "${ext}" not accepted. Use .csv, .xlsx, .xls, or .tsv.` };
  }
  return { valid: true };
}

export function validateFileMimeType(file: File): FileValidationResult {
  const ext = getFileExtension(file.name);
  const allowedMimes = EXTENSION_MIME_MAP[ext];
  if (!allowedMimes) return { valid: true }; // No MIME check for this extension
  // Accept if MIME matches or if it's application/octet-stream (common for Office files)
  if (allowedMimes.includes(file.type)) return { valid: true };
  // If the browser reports a known type we don't accept, flag it
  if (file.type && !file.type.startsWith('application/octet-stream') && file.type !== '') {
    return { valid: false, error: `File MIME type "${file.type}" does not match expected type for ${ext} files.` };
  }
  return { valid: true };
}

export async function validateFileMagicBytes(file: File): Promise<FileValidationResult> {
  const ext = getFileExtension(file.name);
  const checker = MAGIC_BYTES[ext];
  if (!checker) return { valid: true }; // No magic byte check for this extension (e.g. CSV, TSV)

  try {
    const header = await file.slice(0, 16).arrayBuffer();
    const bytes = new Uint8Array(header);
    if (!checker(bytes)) {
      return { valid: false, error: `File header does not match expected format for ${ext} files. File may be corrupted or misnamed.` };
    }
    return { valid: true };
  } catch {
    return { valid: false, error: 'Could not read file header for validation.' };
  }
}

// Synchronous file validation (size + extension + MIME — no magic bytes, no async)
export function validateFileSync(file: File): FileValidationResult {
  const sizeCheck = validateFileSize(file);
  if (!sizeCheck.valid) return sizeCheck;

  const extCheck = validateFileExtension(file);
  if (!extCheck.valid) return extCheck;

  const mimeCheck = validateFileMimeType(file);
  if (!mimeCheck.valid) return mimeCheck;

  return { valid: true };
}

export async function validateFile(file: File): Promise<FileValidationResult> {
  const sizeCheck = validateFileSize(file);
  if (!sizeCheck.valid) return sizeCheck;

  const extCheck = validateFileExtension(file);
  if (!extCheck.valid) return extCheck;

  const mimeCheck = validateFileMimeType(file);
  if (!mimeCheck.valid) return mimeCheck;

  const magicCheck = await validateFileMagicBytes(file);
  if (!magicCheck.valid) return magicCheck;

  return { valid: true };
}


