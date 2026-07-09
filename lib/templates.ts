'use client';
import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Base interface for any saved config/template.
 * Tools extend this with their own data fields.
 */
export interface SavedConfig {
  id: string;
  name: string;
  description: string;
  savedAt: string;
}

/** Generate a UUID v4 */
export function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

/** Download a config as a JSON blob */
export function downloadConfig(config: SavedConfig, name?: string): void {
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const safeName = (name || config.name).replace(/[^a-z0-9]+/gi, '_').replace(/^_+|_+$/g, '').toLowerCase() || 'config';
  a.href = url;
  a.download = safeName + '_config.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Read a JSON file and parse it into a config */
export function readConfigFile<T extends SavedConfig>(
  file: File
): Promise<{ config: T | null; error?: string }> {
  return new Promise(resolve => {
    if (!file.name.endsWith('.json')) {
      resolve({ config: null, error: 'Only .json files are supported' });
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const text = ev.target?.result as string;
        const obj = JSON.parse(text);
        if (!obj || typeof obj !== 'object') {
          resolve({ config: null, error: 'Invalid JSON structure' });
          return;
        }
        resolve({ config: obj as T });
      } catch {
        resolve({ config: null, error: 'Failed to parse JSON file' });
      }
    };
    reader.onerror = () => resolve({ config: null, error: 'Failed to read file' });
    reader.readAsText(file);
  });
}

/** Reorder an array — move item from `from` index to `to` index */
export function reorderArray<T>(arr: T[], from: number, to: number): T[] {
  const updated = [...arr];
  const [moved] = updated.splice(from, 1);
  const target = to > from ? to - 1 : to;
  updated.splice(target, 0, moved);
  return updated;
}

/**
 * Lightweight localStorage-backed config store.
 *
 * Usage:
 * ```ts
 * interface MyTemplate extends SavedConfig {
 *   data: Record<string, string>;
 * }
 * const store = useConfigs<MyTemplate>('my-tool-templates');
 * // store.configs, store.save({...}), store.remove(id),
 * // store.reorder(from, to), store.exportConfig(tpl), store.importConfig() -> T|null
 * ```
 */
export function useConfigs<T extends SavedConfig>(
  storageKey: string
) {
  const [configs, setConfigs] = useState<T[]>([]);
  const importFileRef = useRef<HTMLInputElement>(null);

  // Load on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) setConfigs(JSON.parse(raw));
    } catch { /* ignore */ }
  }, [storageKey]);

  // Persist on change
  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(configs)); }
    catch { /* ignore */ }
  }, [configs, storageKey]);

  /** Save a new config (prepended) */
  const save = useCallback((config: T) => {
    setConfigs(prev => [config, ...prev]);
  }, []);

  /** Remove a config by id */
  const remove = useCallback((id: string) => {
    setConfigs(prev => prev.filter(c => c.id !== id));
  }, []);

  /** Overwrite a config by id */
  const update = useCallback((id: string, updates: Partial<T>) => {
    setConfigs(prev => prev.map(c => c.id === id ? { ...c, ...updates } : c));
  }, []);

  /** Move a config from one index to another */
  const reorder = useCallback((from: number, to: number) => {
    setConfigs(prev => reorderArray(prev, from, to));
  }, []);

  /** Download a config as a .json file */
  const exportConfig = useCallback((config: T, name?: string) => {
    downloadConfig(config, name);
  }, []);

  /** Open file picker and return the parsed config (or null if failed) */
  const importConfig = useCallback(async (): Promise<T | null> => {
    return new Promise(resolve => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.json';
      input.onchange = async () => {
        const file = input.files?.[0];
        if (!file) { resolve(null); return; }
        const { config, error } = await readConfigFile<T>(file);
        if (config) {
          setConfigs(prev => [config!, ...prev]);
          resolve(config);
        } else {
          resolve(null);
        }
        input.value = '';
      };
      input.click();
    });
  }, []);

  /** Clear all configs */
  const clear = useCallback(() => {
    setConfigs([]);
    try { localStorage.removeItem(storageKey); } catch { /* ignore */ }
  }, [storageKey]);

  return {
    configs,
    setConfigs,
    save,
    remove,
    update,
    reorder,
    exportConfig,
    importConfig,
    clear,
    importFileRef,
    count: configs.length,
  };
}
