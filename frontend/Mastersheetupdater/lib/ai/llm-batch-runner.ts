import { getApiEndpoint, getLlmModel } from './ai-config';
import { clientConfig } from '@/lib/client-config';

export interface LlmBatchOptions {
  items: unknown[];
  batchSize: number;
  maxConcurrent: number;
  minGapMs: number;
  maxRetries: number;
  requestTimeoutMs: number;
  getCacheKey?: (items: unknown[]) => string | null;
  cachedData?: unknown[] | null;
  buildPrompt: (batch: unknown[], batchIndex: number) => { system: string; user: string; temperature?: number; maxTokens?: number; model?: string } | null;
  buildHeaders?: () => Record<string, string>;
  parseResponse: (text: string, batch: unknown[], batchIndex: number) => unknown[];
  onProgress?: (done: number, total: number, message: string, pct: number) => void;
  signal?: AbortSignal;
}

export interface LlmBatchResult {
  results: Map<number, unknown>;
  correctedCount: number;
  failedBatches: number[];
  fromCache: boolean;
  aborted: boolean;
}

export async function runLlmBatches(opts: LlmBatchOptions): Promise<LlmBatchResult> {
  const { items, batchSize, maxConcurrent, minGapMs, maxRetries, requestTimeoutMs, getCacheKey, cachedData, buildPrompt, buildHeaders, parseResponse, onProgress, signal } = opts;
  
  const results = new Map<number, unknown>();
  const failedBatches: number[] = [];
  let correctedCount = 0;
  let aborted = false;
  let fromCache = false;
  
  const totalBatches = Math.ceil(items.length / batchSize);
  
  interface ThrottleState { gapMs: number; consecutiveSuccesses: number; cooldownUntil: number; initialGap: number; }
  function createThrottleState(initialGap: number): ThrottleState { return { gapMs: initialGap, consecutiveSuccesses: 0, cooldownUntil: 0, initialGap }; }
  function recordSuccess(state: ThrottleState): void { state.consecutiveSuccesses++; if (state.consecutiveSuccesses >= 5) { state.gapMs = Math.max(minGapMs, Math.floor(state.gapMs * 0.7)); state.consecutiveSuccesses = 0; } }
  function recordThrottle(state: ThrottleState, retryAfterMs?: number): void { state.gapMs = Math.min(5000, state.gapMs * 2); state.consecutiveSuccesses = 0; state.cooldownUntil = Date.now() + (retryAfterMs || 1000); }
  function isRetryableStatus(status: number): boolean { return [408, 409, 425, 429, 500, 502, 503, 504, 523, 524].includes(status); }
  function isClientError(status: number): boolean { return status >= 400 && status < 500 && !isRetryableStatus(status); }
  function sleep(ms: number): Promise<void> { return new Promise(r => setTimeout(r, ms)); }
  function jitter(ms: number): number { return Math.floor(ms * (0.75 + Math.random() * 0.5)); }
  function parseRetryAfter(header: string | null): number | undefined { if (!header) return undefined; const secs = parseInt(header, 10); if (!isNaN(secs)) return secs * 1000; const date = Date.parse(header); return isNaN(date) ? undefined : Math.max(0, date - Date.now()); }
  
  const throttle = createThrottleState(minGapMs);
  const cache = new Map<string, string>();
  if (cachedData) {
    for (const item of cachedData) { const k = getCacheKey ? getCacheKey([item]) : null; if (k) cache.set(k, String(item)); }
  }
  
  let nextBatchIndex = 0;
  let activeWorkers = 0;
  
  async function worker() {
    activeWorkers++;
    while (!aborted && !signal?.aborted) {
      let batchIndex: number;
      const current = nextBatchIndex;
      if (current >= totalBatches) { activeWorkers--; return; }
      batchIndex = current;
      nextBatchIndex++;
      
      const start = batchIndex * batchSize;
      const end = Math.min(start + batchSize, items.length);
      const batch = items.slice(start, end);
      
      const cacheKey = getCacheKey ? getCacheKey(batch) : null;
      if (cacheKey && cache.has(cacheKey)) {
        results.set(start, cache.get(cacheKey)!);
        onProgress?.(end, items.length, 'Cache hit', Math.round((end / items.length) * 100));
        continue;
      }
      
      const prompt = buildPrompt(batch, batchIndex);
      if (!prompt) { failedBatches.push(batchIndex); continue; }
      
      const body = {
        messages: [
          { role: 'system', content: prompt.system },
          { role: 'user', content: prompt.user }
        ],
        temperature: prompt.temperature ?? 0.2,
        max_tokens: prompt.maxTokens ?? clientConfig.defaultMaxOutputTokens,
        model: prompt.model ?? getLlmModel(),
      };
      
      let attempt = 0;
      let success = false;
      let lastError: unknown;
      
      while (attempt <= maxRetries && !aborted && !signal?.aborted) {
        if (throttle.cooldownUntil > Date.now()) await sleep(throttle.cooldownUntil - Date.now());
        const gap = jitter(throttle.gapMs);
        await sleep(gap);
        
        try {
          const headers = { 'Content-Type': 'application/json', ...(buildHeaders?.() || {}) };
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), requestTimeoutMs);
          
          const response = await fetch(getApiEndpoint(), {
            method: 'POST',
            headers,
            body: JSON.stringify(body),
            signal: controller.signal,
          });
          
          clearTimeout(timeout);
          
          if (!response.ok) {
            if (isClientError(response.status)) throw new Error(`Client error: ${response.status}`);
            if (isRetryableStatus(response.status)) {
              const retryAfter = parseRetryAfter(response.headers.get('Retry-After'));
              recordThrottle(throttle, retryAfter);
              attempt++;
              continue;
            }
            throw new Error(`HTTP ${response.status}`);
          }
          
          const rawText = await response.text();
          // Unwrap OpenAI-format envelope: { choices: [{ message: { content: "..." } }] }
          let llmContent = rawText;
          try {
            const envelope = JSON.parse(rawText);
            const content = envelope?.choices?.[0]?.message?.content;
            if (typeof content === 'string' && content.trim()) {
              llmContent = content;
            } else {
              console.warn('[LLM] Unexpected response structure, falling back to raw text:', rawText.slice(0, 200));
            }
          } catch {
            // Not valid JSON envelope — use raw text directly
          }
          const parsed = parseResponse(llmContent, batch, batchIndex);
          
          for (let i = 0; i < parsed.length; i++) { results.set(start + i, parsed[i]); }
          if (cacheKey) cache.set(cacheKey, rawText);
          
          recordSuccess(throttle);
          correctedCount += parsed.filter((_, i) => parsed[i] !== batch[i]).length;
          success = true;
          break;
        } catch (err) {
          lastError = err;
          if (err instanceof Error && err.name === 'AbortError') { aborted = true; break; }
          attempt++;
          if (attempt <= maxRetries) recordThrottle(throttle);
        }
      }
      
      if (!success && !aborted) { failedBatches.push(batchIndex); onProgress?.(end, items.length, `Batch ${batchIndex + 1} failed`, Math.round((end / items.length) * 100)); }
      else if (success) { onProgress?.(end, items.length, `Batch ${batchIndex + 1}/${totalBatches}`, Math.round((end / items.length) * 100)); }
    }
    activeWorkers--;
  }
  
  const workers = Array.from({ length: maxConcurrent }, () => worker());
  await Promise.all(workers);
  
  return { results, correctedCount, failedBatches, fromCache: cache.size > 0, aborted };
}
