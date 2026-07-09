export function excelSafe(v: unknown): string {
  const s = String(v ?? '').trim();
  return /^[-+=@]/.test(s) ? "'" + s : s;
}

export function excelSafeCsvCell(v: unknown): string {
  const s = String(v ?? '');
  if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

export function excelSafeTsvCell(v: unknown): string {
  return String(v ?? '').replace(/[\t\n]/g, ' ');
}
