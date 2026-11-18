// ponytail: route through grydEndpoint worker proxy (same as useAuth) so api.autongage.com
// never sees Origin: http://localhost:3000 — the worker makes the upstream call server-side.
export type EnvironmentMode = 'prod' | 'dev';

export type DatePreset = 'today' | 'yesterday' | 'this_week' | 'last_week' | 'month_to_date' | 'custom';

export interface BillingApiParams {
  dealershipId: string;
  environment: EnvironmentMode;
  token: string;
  sessionId: string;
  enterpriseId?: string;
  startDate?: Date | null;
  endDate?: Date | null;
  channel?: 'all' | 'voice_phone' | 'whatsapp_chat';
  pageSize?: number;
}

export interface ProgressInfo {
  page: number;
  fetched: number;
  total: number;
}

/**
 * Returns the billing API base URL.
 *
 * Origin validation: api.autongage.com rejects Origin: http://localhost:3000.
 * Fix: in dev (localhost), use relative paths that Next.js rewrites server-side,
 * so the upstream request carries the Next.js server origin, not localhost.
 * In prod (static export), the deployed GitHub Pages origin is accepted.
 */
function getBillingBaseUrl(environment: EnvironmentMode): string {
  const isLocalhost = typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

  if (isLocalhost) {
    // ponytail: relative path → Next.js dev rewrite → api.autongage.com / dev gryd (server-side, no browser Origin)
    return environment === 'dev' ? '/api-proxy/billing-dev' : '/api-proxy/billing';
  }

  // Prod static export: direct fetch, deployed origin is trusted by api.autongage.com
  return environment === 'dev'
    ? 'https://autobot-webapp-dev.gryd.in'
    : 'https://api.autongage.com';
}

/**
 * Calculates start and end timestamps for preset intervals in local/IST time.
 */
export function getDatePresetBounds(preset: DatePreset, customStart?: string, customEnd?: string): { startDate: Date | null; endDate: Date | null; label: string } {
  const now = new Date();
  
  if (preset === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
    return { startDate: start, endDate: end, label: 'Today' };
  }

  if (preset === 'yesterday') {
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const start = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 0, 0, 0, 0);
    const end = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 23, 59, 59, 999);
    return { startDate: start, endDate: end, label: 'Yesterday' };
  }

  if (preset === 'this_week') {
    const current = new Date(now);
    const day = current.getDay();
    // Monday as start of week: day 0 is Sunday, so offset is (day === 0 ? 6 : day - 1)
    const diffToMonday = day === 0 ? 6 : day - 1;
    const monday = new Date(current.setDate(current.getDate() - diffToMonday));
    const start = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate(), 0, 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
    return { startDate: start, endDate: end, label: 'This Week' };
  }

  if (preset === 'last_week') {
    const current = new Date(now);
    const day = current.getDay();
    const diffToMonday = (day === 0 ? 6 : day - 1) + 7;
    const lastMonday = new Date(current.setDate(current.getDate() - diffToMonday));
    const start = new Date(lastMonday.getFullYear(), lastMonday.getMonth(), lastMonday.getDate(), 0, 0, 0, 0);
    const lastSunday = new Date(start.getTime() + 6 * 24 * 60 * 60 * 1000);
    const end = new Date(lastSunday.getFullYear(), lastSunday.getMonth(), lastSunday.getDate(), 23, 59, 59, 999);
    return { startDate: start, endDate: end, label: 'Last Week' };
  }

  if (preset === 'month_to_date') {
    const start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
    return { startDate: start, endDate: end, label: 'Month to Date' };
  }

  if (preset === 'custom' && customStart && customEnd) {
    const [sY, sM, sD] = customStart.split('-').map(Number);
    const [eY, eM, eD] = customEnd.split('-').map(Number);
    const start = new Date(sY, sM - 1, sD, 0, 0, 0, 0);
    const end = new Date(eY, eM - 1, eD, 23, 59, 59, 999);
    return { startDate: start, endDate: end, label: `${customStart} to ${customEnd}` };
  }

  return { startDate: null, endDate: null, label: 'All Time' };
}

/**
 * Normalizes raw API response item into standard row dictionary consumed by processCreditData().
 * ponytail: preserves column aliases expected by existing 2300-line credit-utils parser.
 */
export function normalizeBillingItem(item: any): Record<string, any> {
  const billingId = item.billing_id || '';
  const dateRaw = item.transaction_date || (item.created ? new Date(item.created * 1000).toISOString() : '');
  const itemName = item.item_name || '';
  const channel = item.channel || '';
  const description = item.item_description || '';
  const quantity = Number(item.item_quantity) || 0;
  const creditsSpent = Number(item.item_total) || 0;
  const status = item.status || 'success';
  const dealershipId = item.dealership_id || '';

  return {
    'billing id': billingId,
    'billing_id': billingId,
    'date & time': dateRaw,
    'date and time': dateRaw,
    'transaction_date': dateRaw,
    'item name': itemName,
    'item_name': itemName,
    'channel': channel,
    'description': description,
    'desc': description,
    'quantity': quantity,
    'credits spent': creditsSpent,
    'credits_spent': creditsSpent,
    'credit': creditsSpent,
    'status': status,
    'dealership_id': dealershipId,
    'created': item.created,
  };
}

/**
 * Fetches billing debits from Autobot API across pages with exponential backoff.
 */
export async function fetchBillingDebits(
  params: BillingApiParams,
  onProgress?: (info: ProgressInfo) => void,
  signal?: AbortSignal
): Promise<{ rows: Record<string, any>[]; totalCount: number; dealershipId: string }> {
  const baseUrl = getBillingBaseUrl(params.environment);
  const dealershipId = params.dealershipId.trim();

  if (!dealershipId) {
    throw new Error('Dealership ID is required');
  }

  if (!params.token) {
    throw new Error('Authentication token missing. Please sign in or provide a valid Gryd token.');
  }

  const accumulatedRaw: any[] = [];
  const pageSize = params.pageSize || 100;
  let pageNumber = 1;
  let totalServerCount = 0;
  // ponytail: cap computed dynamically after first page response (ceil(total/pageSize) + 1),
  // fallback hard ceiling of 500 pages (50,000 records) to prevent infinite loops
  let maxPages = 500;

  while (pageNumber <= maxPages) {
    if (signal?.aborted) {
      throw new Error('Fetch aborted by user');
    }

    const queryParams = new URLSearchParams({
      page_number: String(pageNumber),
      page_size: String(pageSize),
      dealership_id: dealershipId,
      transaction_type: 'debit',
      sort_by: 'created',
      sort_reverse: 'true',
    });

    if (params.channel && params.channel !== 'all') {
      queryParams.set('channel', params.channel);
    }

    if (params.startDate && params.endDate) {
      const startSec = Math.floor(params.startDate.getTime() / 1000);
      const endSec = Math.floor(params.endDate.getTime() / 1000);
      queryParams.set('created', `${startSec},${endSec}`);
    }

    // ponytail: dev proxy path is the full URL already; prod appends gryd path
    const isDevProxy = baseUrl.startsWith('/api-proxy/');
    const requestUrl = isDevProxy
      ? `${baseUrl}?${queryParams.toString()}`
      : `${baseUrl}/gryd/db/objects/billing?${queryParams.toString()}`;

    // Retry loop with exponential backoff (max 3 retries)
    let batchData: any = null;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const response = await fetch(requestUrl, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-GRYD-ENTERPRISE-ID': params.enterpriseId || 'autocrm',
            'X-GRYD-ROLE': 'agent',
            'X-GRYD-TOKEN': params.token,
            'X-GRYD-SESSION-ID': params.sessionId || '',
          },
          signal,
        });

        if (response.status === 401 || response.status === 403) {
          throw new Error('Gryd session expired or unauthorized. Please re-login.');
        }

        if (!response.ok) {
          throw new Error(`API error ${response.status}: ${response.statusText}`);
        }

        const json = await response.json();
        batchData = json;
        break;
      } catch (err: any) {
        lastError = err;
        if (err.name === 'AbortError' || signal?.aborted) throw err;
        if (err.message?.includes('session expired') || err.message?.includes('unauthorized')) throw err;
        // Exponential backoff
        await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 400));
      }
    }

    if (!batchData) {
      throw lastError || new Error(`Failed to fetch page ${pageNumber} after 3 attempts`);
    }

    const items = Array.isArray(batchData.data)
      ? batchData.data
      : (Array.isArray(batchData.items) ? batchData.items : []);
    
    totalServerCount = typeof batchData.total_number === 'number'
      ? batchData.total_number
      : (typeof batchData.total === 'number' ? batchData.total : items.length);

    // Tighten the ceiling dynamically once we know total_number from the first page response
    if (pageNumber === 1 && totalServerCount > 0) {
      maxPages = Math.ceil(totalServerCount / pageSize) + 1; // +1 for safety
    }

    accumulatedRaw.push(...items);

    if (onProgress) {
      onProgress({
        page: pageNumber,
        fetched: accumulatedRaw.length,
        total: totalServerCount,
      });
    }

    // Termination conditions
    if (batchData.is_last === true || items.length === 0 || accumulatedRaw.length >= totalServerCount) {
      break;
    }

    if (items.length < pageSize) {
      break;
    }

    pageNumber++;
  }

  const normalizedRows = accumulatedRaw.map(normalizeBillingItem);

  return {
    rows: normalizedRows,
    totalCount: totalServerCount || normalizedRows.length,
    dealershipId,
  };
}

