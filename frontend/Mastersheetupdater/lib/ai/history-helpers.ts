export function detectHistory(obj: Record<string, unknown>): string {
  const keys = Object.keys(obj);
  const candidates = ['history', 'session_history', 'transcript', 'conversation_history', 'chat_history', 'messages'];
  for (const c of candidates) {
    if (keys.includes(c)) return c;
    const rawKey = c + '__raw';
    if (keys.includes(rawKey)) return rawKey;
  }
  return '';
}

export function parseHistoryJson(raw: unknown): unknown[] | null {
  if (raw == null) return null;
  if (Array.isArray(raw)) return raw;
  const s = String(raw).trim();
  if (!s) return null;
  try {
    const parsed = JSON.parse(s);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function formatRelativeOffset(firstTs: number, currentTs: number): string {
  let diff = Math.floor((currentTs - firstTs) / 1000);
  if (diff < 0) diff = 0;
  const mins = Math.floor(diff / 60);
  const secs = diff % 60;
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const m = mins % 60;
    return `[${hrs}:${String(m).padStart(2, '0')}:${String(secs).padStart(2, '0')}]`;
  }
  return `[${mins}:${String(secs).padStart(2, '0')}]`;
}

export function normalizeRoleLabel(role: string): string {
  const r = role.toLowerCase();
  if (r.includes('agent') || r.includes('bot') || r.includes('assistant')) return 'Agent';
  if (r.includes('customer') || r.includes('user') || r.includes('lead') || r.includes('caller')) return 'Customer';
  return role;
}

export function formatHistoryForPrompt(raw: unknown): string {
  const arr = parseHistoryJson(raw);
  if (!arr || !arr.length) return '';

  const getTsMs = (entry: any): number => {
    if (typeof entry === 'object' && entry && 'timestamp' in entry) {
      const val = Number(entry.timestamp);
      if (!isNaN(val)) {
        if (val < 9999999999) return val * 1000;
        return val;
      }
    }
    return 0;
  };

  let firstTs = 0;
  for (const entry of arr) {
    const ts = getTsMs(entry);
    if (ts > 0) {
      firstTs = ts;
      break;
    }
  }
  if (!firstTs) firstTs = Date.now();

  return arr.map((entry, i) => {
    let ts = getTsMs(entry);
    if (!ts) ts = firstTs + i * 1000;
    const role = typeof entry === 'object' && entry && 'role' in entry ? String((entry as Record<string, unknown>).role) : 'Unknown';
    const e = entry as Record<string, unknown>;
    let content = typeof entry === 'object' && entry ? String(e.content || e.message || e.body || e.text || '') : '';
    content = content.replace(/\s+/g, ' ').trim();
    return `${formatRelativeOffset(firstTs, ts)} ${normalizeRoleLabel(role)}: ${content}`;
  }).join('\n');
}
