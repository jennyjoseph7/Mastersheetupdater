export class BatchExporter {
  private prefix: string;
  private storageKey: string;
  readonly LEADS_PER_BATCH = 100;

  constructor(prefix: string) {
    this.prefix = prefix;
    this.storageKey = `jejo-ae-batch-export-${prefix}`;
  }

  createFingerprint(file: File, inputRowCount: number): string {
    return `${file.name}|${file.size}|${inputRowCount}`;
  }

  readStore(): Record<string, unknown> {
    if (typeof window === 'undefined') return {};
    try {
      const raw = localStorage.getItem(this.storageKey);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  }

  writeStore(store: Record<string, unknown>): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(store));
    } catch {
      // quota exceeded
    }
  }

  getSavedProgress(fp: string, templateId: string, inputRowCount: number): { nextLeadIndex: number } | null {
    const store = this.readStore();
    const fpData = store[fp];
    if (!fpData) return null;
    const tmpl = (fpData as Record<string, unknown>).templates?.[templateId];
    if (!tmpl) return null;
    const data = tmpl as Record<string, unknown>;
    if (data.inputRowCount !== inputRowCount) return null;
    return { nextLeadIndex: Number(data.nextLeadIndex) || 0 };
  }

  saveProgress(fp: string, templateId: string, inputRowCount: number, nextLeadIndex: number): void {
    const store = this.readStore();
    if (!store[fp]) store[fp] = { fingerprints: {}, templates: {} };
    const fpData = store[fp] as Record<string, unknown>;
    if (!fpData.templates) fpData.templates = {};
    (fpData.templates as Record<string, unknown>)[templateId] = {
      nextLeadIndex,
      inputRowCount,
      savedAt: Date.now(),
    };
    this.writeStore(store);
  }

  clearProgressForFingerprint(fp: string): void {
    const store = this.readStore();
    delete store[fp];
    this.writeStore(store);
  }
}
