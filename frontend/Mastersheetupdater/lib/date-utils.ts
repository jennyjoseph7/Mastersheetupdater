export type DateParseOrder = 'DMY' | 'MDY';

export function detectDateFormat(dateStrings: string[]): DateParseOrder {
  let dmy = 0, mdy = 0;
  for (const s of dateStrings) {
    const m = s.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})$/);
    if (!m) continue;
    const a = parseInt(m[1], 10), b = parseInt(m[2], 10);
    if (a > 12 && b <= 12) dmy++;
    else if (b > 12 && a <= 12) mdy++;
    else if (a <= 12 && b <= 12) dmy++;
  }
  return dmy >= mdy ? 'DMY' : 'MDY';
}

export function parseExcelSerialDate(value: number): Date {
  const utcDays = Math.floor(value - 25569);
  const utcValue = utcDays * 86400;
  const dateInfo = new Date(utcValue * 1000);
  const fractionalDay = value - Math.floor(value);
  const totalSeconds = Math.round(fractionalDay * 86400);
  dateInfo.setUTCHours(0, 0, 0, 0);
  dateInfo.setUTCSeconds(dateInfo.getUTCSeconds() + totalSeconds);
  return dateInfo;
}

export function buildValidatedDate(
  year: number, month: number, day: number,
  h: number, m: number, s: number
): Date {
  const d = new Date(year, month - 1, day, h, m, s);
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) {
    throw new Error('Invalid date');
  }
  return d;
}

export function parseDate(value: unknown, order: DateParseOrder = 'DMY'): Date | null {
  if (value == null) return null;
  if (value instanceof Date) return isNaN(value.getTime()) ? null : value;
  if (typeof value === 'number') {
    if (value > 1000000000000) return new Date(value);
    if (value > 1000000000) return new Date(value * 1000);
    if (value > 30000) return parseExcelSerialDate(value);
    return null;
  }
  const s = String(value).trim();
  if (!s) return null;
  const iso = Date.parse(s);
  if (!isNaN(iso)) return new Date(iso);
  const m = s.match(/^(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/);
  if (!m) return null;
  const [, a, b, c, h, mi, se] = m;
  const day = order === 'DMY' ? parseInt(a, 10) : parseInt(b, 10);
  const month = order === 'DMY' ? parseInt(b, 10) : parseInt(a, 10);
  const year = parseInt(c, 10) < 100 ? 2000 + parseInt(c, 10) : parseInt(c, 10);
  const hour = h ? parseInt(h, 10) : 0;
  const min = mi ? parseInt(mi, 10) : 0;
  const sec = se ? parseInt(se, 10) : 0;
  try {
    return buildValidatedDate(year, month, day, hour, min, sec);
  } catch {
    return null;
  }
}

export function formatDateDisplay(date: Date): string {
  const d = String(date.getDate()).padStart(2, '0');
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const y = date.getFullYear();
  return `${d}/${m}/${y}`;
}

export function formatDateToken(date: Date): string {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${date.getDate()}${months[date.getMonth()]}`;
}

export function formatSerialDate(val: unknown): string {
  if (typeof val === 'number' && val > 30000 && val < 100000) {
    return formatDateDisplay(parseExcelSerialDate(val));
  }
  const d = parseDate(val);
  return d ? formatDateDisplay(d) : String(val ?? '');
}
