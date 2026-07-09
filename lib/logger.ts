const TAG_WIDTH = 5;
function padTag(tag: string): string {
  return tag.padEnd(TAG_WIDTH);
}

export function $log(tag: string, msg: string, data?: unknown): void {
  console.log(`[${padTag(tag)}] ${msg}`, data ?? '');
}

export function $warn(tag: string, msg: string, data?: unknown): void {
  console.warn(`[${padTag(tag)}] ${msg}`, data ?? '');
}

export function $error(tag: string, msg: string, data?: unknown): void {
  console.error(`[${padTag(tag)}] ${msg}`, data ?? '');
}

export function $start(tag: string, msg: string): void {
  console.group(`[${padTag(tag)}] ${msg}`);
}

export function $end(): void {
  console.groupEnd();
}

export function $mask(val: string, type: 'phone' | 'email' | 'user'): string {
  if (!val) return '';
  switch (type) {
    case 'phone':
      return val.length > 4 ? '*'.repeat(val.length - 4) + val.slice(-4) : '*'.repeat(val.length);
    case 'email': {
      const [local, domain] = val.split('@');
      return `${local?.[0] || '*'}***@${domain || '***'}`;
    }
    case 'user':
      return val.length > 2 ? val[0] + '*'.repeat(val.length - 2) + val.slice(-1) : '*'.repeat(val.length);
  }
}
