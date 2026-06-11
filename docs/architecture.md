# 🏗️ AutoNage Architecture — File-by-File Reference

> **Purpose**: Before making any change, read this file first. It maps every function,
> every connection, and every ripple effect. If I change X, what breaks in Y?

---

## 📌 Quick Reference: What Goes Where

### File Role Map

| File | Role | Depends On | Used By |
|------|------|------------|---------|
| `index.html` | Landing page / catalog | `assets/scripts/index.js`, `assets/css/index.css`, `assets/fonts/fonts.css` | Users opening the site |
| `config.js` | API keys & settings (gitignored) | Nothing | All tools that use AI |
| `assets/js/lib/llm-batch-runner.js` | AI batch processing engine | `config.js` (via `window.JEJO_CONFIG`) | `dashboard.html`, `post_sales_disposition.html`, `disposition_sync_v2.html` |
| `assets/js/lib/history-helpers.js` | Session history parsing | Nothing | `post_sales_disposition.html`, `disposition_sync_v2.html` |
| `assets/js/lib/excel-safe.js` | Formula injection protection | Nothing | `reattempt_filter.html`, `autongage_formatter.html`, `recording_renamer.html`, `post_sales_disposition.html`, `disposition_sync_v2.html` |
| `assets/js/lib/xlsx.full.min.js` | SheetJS — Excel parsing | Nothing | ALL tools |
| `assets/js/lib/jszip.min.js` | ZIP compression | Nothing | `recording_renamer.html` |
| `assets/js/lib/html2canvas.min.js` | Screenshot capture | Nothing | `dashboard.html` |
| `assets/js/lib/jspdf.umd.min.js` | PDF generation | `html2canvas` | `dashboard.html` |
| `assets/scripts/index.js` | Theme toggle (landing page) | Nothing | `index.html` only |
| `assets/fonts/fonts.css` | Self-hosted fonts | Nothing | ALL HTML files |
| `assets/css/design-system.css` | Shared CSS — theme vars, reset, header/nav, theme-toggle, buttons, status bars | Nothing | ALL 7 tool pages |
| `assets/css/*.css` | Per-tool styles (7 files) | `fonts.css`, `design-system.css` | Corresponding page |
| `worker/worker.js` | Production AI proxy | Cloudflare env vars | `config.js` (apiEndpoint) |
| `server/proxy.js` | Local dev AI proxy | `.env` file | `config.js` (apiEndpoint) |

---

## 🔗 Script Load Order (Critical!)

Each HTML page loads `<script>` tags in order. The order matters because scripts depend on each other:

**ALL pages load (processing):**
```html
1. <inline blocking script>        — sets data-theme before render
2. assets/fonts/fonts.css          — font loading
3. assets/js/lib/xlsx.full.min.js     — SheetJS
```

**Then per-page:**

| Page | Config | history-helpers | llm-batch-runner | excel-safe.js | Extras |
|------|--------|-----------------|-------------------|---------------|--------|
| `disposition_sync_v2.html` | 1st | 4th | 5th | ✅ 2nd (after xlsx) | — |
| `post_sales_disposition.html` | **LAST (5th)** | 3rd | 4th | ✅ 2nd (after xlsx) | — |
| `dashboard.html` | 1st | — | 3rd | ❌ Not loaded | html2canvas, jspdf |
| `recording_renamer.html` | after xlsx+excelSafe | — | — | ✅ 2nd (after xlsx) | jszip |
| `call_analysis_summary.html` | after xlsx | — | — | ❌ Not loaded | — |
| `reattempt_filter.html` | ❌ NOT LOADED | — | — | ✅ 2nd (after xlsx) | — |
| `autongage_formatter.html` | ❌ NOT LOADED | — | — | ✅ 2nd (after xlsx) | — |

**⚠️ NOTE:** `post_sales_disposition.html` loads `config.js` LAST — different from everyone else. This means `window.JEJO_CONFIG` is available later in that page's lifecycle. **(Fix planned — see Candidate #9)**

**🆕 `excel-safe.js` load position**: Always loaded right after `xlsx.full.min.js` (before any page-specific libs or `config.js`). The 5 pages that use it insert it in this slot.

**🆕 `ai-config.js` load position**: Loaded right after `theme.js` in `<head>`. Defines shared `getApiEndpoint()`, `getApiKey()`, `getLlmModel()`, `getConfigNumber()`, `hashStr()`, `sanitizeForPrompt()`, `isProxyEndpoint()`. Every page that uses AI loads this. See `assets/js/lib/ai-config.js`.

**🆕 `theme.js` (shared)**: Contains `getStoredTheme()`, `syncBrandLogo()`, `applyTheme()`, `toggleTheme()`. Loaded by all 8 HTML pages. The inline blocking `<script>` (IIFE setting `data-theme` before render) stays in each page for FOUC prevention. See `assets/js/lib/theme.js`.

---

## 🔗 Theme Toggle — NOW SHARED (theme.js)

Theme functions have been **extracted** to `assets/js/lib/theme.js`. All 8 pages now load this single shared file. The inline blocking `<script>` (IIFE) that sets `data-theme` before render is the only remaining duplication — it must stay in each page's `<head>` to prevent FOUC.

| File | Theme Source |
|------|-------------|
| `index.html` | `assets/js/lib/theme.js` (via `<script>`) + inline IIFE for FOUC |
| All 7 `pages/*.html` | `assets/js/lib/theme.js` (via `<script>`) + inline IIFE for FOUC |

**✅ If you fix a theme bug, only `assets/js/lib/theme.js` needs updating!**

---

## 🔄 Data Flow Diagrams

### Pre-Sales Sync (disposition_sync_v2.html)
```
User Uploads File 1 (Audience & Leads) ─┐
                                         ├──→ parseSheet() → detect columns → normalize
User Uploads File 2 (Sessions) ──────────┘
                                                   ↓
                                            mergeData() ← detectHistory() + formatHistoryForPrompt()
                                                   ↓
                                            buildQualityReport() → renderQualityReport()
                                                   ↓
                                            renderTable() + renderStats() → User reviews
                                                   ↓
                                         [Optional: AI Validation]
                                            validateDispositionsWithLLM()
                                              → runLlmBatches() → parseResponse → renderTable()
                                                   ↓
                                            exportToExcel() or copyData() or copyConvertedData()
```

### Post-Sales Sync (post_sales_disposition.html)
```
User Uploads File 1 ─┐
                      ├──→ parseSheet() → scoreFileRole() [auto-detect leads vs sessions]
User Uploads File 2 ─┘            │
                                  ↓
                    evaluateFileRoles() → may swap files if auto-detected
                                  ↓
                    buildSessionMap() ← detectHistory() + formatHistoryForPrompt()
                                  ↓
                    classifyDisposition() for each lead (keyword-based)
                                  ↓
                    buildQualityReport()
                                  ↓
                    renderAll() → Stats + Quality + Table + Preview tables
                                  ↓
                    [Optional: AI Validation] → runLlmBatches()
                                  ↓
                    exportToExcel() or copyData() or copyPreviewRows()
```

### Dashboard Flow (dashboard.html)
```
User Uploads Zoho Export → parse → normalize
              ↓
    generateDashboard()
              ↓
    ┌─────────┼─────────┬──────────────┬──────────────┐
    ↓         ↓         ↓              ↓              ↓
  KPIs      Daily     Vehicle       Pending       Executive
  (4x2)     Chart     Models        Follow-ups    Summary
              ↓
    analyzeConversionFunnel() + analyzeDispositionPatterns() + analyzeTrends() + ...
              ↓
    [Optional: AI Analysis]
    runAiAnalysis() → classifyWithLlm() (via runLlmBatches)
                    → generateVoiceInsights() (single LLM call)
                    → renderCustomerVoice() + renderRecommendations() + ...
```

### Re-Attempt Filter Flow (reattempt_filter.html)
```
User Uploads Multi-Day Zoho Export
              ↓
    parseSheet() → normalize → detect columns
              ↓
    Group by Phone Number → getLatestRow() per group
              ↓
    For each phone group:
    ├── Has Terminal disposition? → EXCLUDE
    ├── Has Connected outcome NOT re-attemptable? → EXCLUDE
    └── Otherwise → INCLUDE in re-attempt list
              ↓
    renderStats() + renderIncludedTable() + renderExcludedTable()
              ↓
    User downloads CSV batches (100 leads per file)
```

### Recording Renamer Flow (recording_renamer.html)
```
User Uploads Processed Sync File (XLSX)
              ↓
    parseDataFile() → read hyperlinks from cells
              ↓
    buildResults() → match phone + date + recording URL
              ↓
    processBatch() → for each row with URL:
      ├── buildFetchUrl() → use CORS proxy or direct
      └── fetchRecordingWithRetry() → download + rename
              ↓
    renderResults() → show progress table
              ↓
    downloadZip() → ZIP all recordings with metadata filenames
```

---

## 🧩 Complete Function Inventory — By File

---

### 1. `index.html` — Landing Page

**Dependencies**: `assets/scripts/index.js`, `assets/css/index.css`, `assets/fonts/fonts.css`

**onclick Handlers**:
| Element | Handler |
|---------|---------|
| `#themeToggle` | `toggleTheme()` |

**Connected to** → Links to ALL `pages/*.html` via `<a>` tags.

---

### 2. `config.js` — Global Configuration (GITIGNORED)

**Exports**: `window.JEJO_CONFIG`

**Properties**:
| Property | Type | Purpose | Used By |
|----------|------|---------|---------|
| `apiEndpoint` | string | Proxy URL (Cloudflare Worker) | Dashboard, Pre/Post-Sales Sync |
| `proxyHandshakeToken` | string | Auth header for proxy | Dashboard, Pre/Post-Sales Sync |
| `nvidiaApiKey` | string | Direct NVIDIA key (fallback) | Dashboard, Pre/Post-Sales Sync |
| `nvidiaModel` | string | Model override | Dashboard, Pre/Post-Sales Sync |
| `openRouterModel` | string | Model override | Dashboard, Pre/Post-Sales Sync |
| `llmBatchSize` | number | Batch size for dashboard AI | Dashboard |
| `llmMaxConcurrent` | number | Concurrent requests | Dashboard |
| `llmRequestTimeoutMs` | number | Timeout per request | Dashboard |
| `llmPromptCharLimit` | number | Max prompt chars | Dashboard |
| `llmMaxOutputTokens` | number | Max output tokens | Dashboard |
| `llmDispositionBatchSize` | number | Batch size for disposition AI | Pre/Post-Sales Sync |
| `llmDispositionMaxConcurrent` | number | Concurrent for disposition | Pre/Post-Sales Sync |
| `llmDispositionTimeoutMs` | number | Timeout for disposition | Pre/Post-Sales Sync |
| `corsProxyUrl` | string | Recording download proxy | Recording Renamer |

**⚠️ CRITICAL**: Gitignored. When I change `config.example.js`, I must also check if `config.js` exists and needs manual update.

---

### 3. `nav.html` — Shared Navigation (Phase 3)

**Created at project root.** Injected via fetch into all 7 tool pages.

**Contains**: 7 nav links (Pre-Sales, Post-Sales, Re-Attempt, Dashboard, Call Summary, Formatter, Recording Renamer) with SVG icons + auto-activation script.

**Injection script** (added to each page's `<div class="header-nav">`):
```html
<script>fetch('../nav.html').then(r=>r.text()).then(html=>{document.querySelector('.header-nav').outerHTML=html}).catch(e=>{console.warn('nav.html failed to load:',e)});</script>
```

**Auto-activation logic** (inside nav.html):
- Reads `window.location.pathname`
- Sets `class="nav-link active"` + `href="#"` on matching page
- All other links keep their original href

**Pages using nav.html**:
- `disposition_sync_v2.html`
- `post_sales_disposition.html`
- `dashboard.html`
- `call_analysis_summary.html`
- `reattempt_filter.html`
- `recording_renamer.html`
- `autongage_formatter.html`

Not used by `index.html` (different layout — no header-nav).

---

### 4. `assets/js/lib/llm-batch-runner.js` — AI Batch Engine

**Exported**: `window.runLlmBatches(opts)`

**Internal Functions**:
| Function | Purpose |
|----------|---------|
| `isRetryableStatus(status)` | Returns true for 408, 409, 425, 429, 500, 502, 503, 504, 523, 524 |
| `isClientError(status)` | 4xx non-retryable (throws immediately with nonRetryable flag) |
| `sleep(ms)` | Promise-based setTimeout |
| `jitter(ms)` | Random jitter (75%–125%) |
| `parseRetryAfter(header)` | Parses Retry-After header (supports seconds and HTTP-date) |
| `createThrottleState(initialGap)` | Creates state: `{ gapMs, consecutiveSuccesses, cooldownUntil, initialGap }` |
| `recordSuccess(state)` | After 5 consecutive successes, tightens gap by 70% |
| `recordThrottle(state, retryAfterMs)` | Doubles gap, caps at 5000ms, sets cooldown |
| `isProxyEndpoint(endpoint)` | Returns true if endpoint ≠ NVIDIA_DIRECT and ≠ OPENROUTER_DIRECT |
| `getConfiguredModel()` | Reads `window.getLlmModel()` → config → default `'mistralai/mistral-medium-3.5-128b'` |
| `sendBatch(batch, batchIndex)` | Core: retry loop → split-on-failure → half-retry |
| `worker()` | Concurrent worker pulling next batch index |

**Defaults**:
- `NVIDIA_ENDPOINT = 'https://integrate.api.nvidia.com/v1/chat/completions'`
- `OPENROUTER_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'`
- `MIN_SPLIT_SIZE = 5` — won't split batches smaller than this

**Things that call `getApiEndpoint()` from llm-batch-runner**:
- `sendBatch()` — determines which URL to fetch
- `isProxyEndpoint()` guards the auth logic

**⚠️ Each page overrides**: `getApiEndpoint()`, `getApiKey()`, `getLlmModel()` are defined inline per HTML file. The SAME llm-batch-runner.js behaves DIFFERENTLY per page.

---

### 4. `assets/js/lib/history-helpers.js` — Session History Parser

**Exported Functions** (`window.*`):
| Function | Purpose |
|----------|---------|
| `detectHistory(obj)` | Find history column: checks `history`, `session_history`, `transcript`, `conversation_history`, `chat_history`, `messages` + `__raw` JSON fallback |
| `parseHistoryJson(raw)` | Safely parse JSON string or return array as-is |
| `formatRelativeOffset(firstTs, currentTs)` | `[m:ss]` or `[h:mm:ss]` from epoch ms |
| `normalizeRoleLabel(role)` | `agent/assistant/bot` → `Agent`, `user/customer` → `Customer` |
| `formatHistoryForPrompt(raw)` | Full transcript: `[timestamp] Role: message` lines |

**Used by**: `disposition_sync_v2.html`, `post_sales_disposition.html`

---

### 5. `assets/scripts/index.js` — Landing Page Theme

**Functions**: `getStoredTheme()`, `syncBrandLogo()`, `applyTheme()`, `toggleTheme()`

**Only loaded by**: `index.html`. Every other HTML page duplicates these inline.

---

### 6. `worker/worker.js` — Production Proxy

**Env vars**: `NVIDIA_API_KEY`, `HANDSHAKE_TOKEN`, `UPSTREAM_TIMEOUT_MS`

**Functions**:
| Function | Purpose |
|----------|---------|
| `checkRateLimit(ip)` | 100 req/min per IP (in-memory Map) |
| `jsonResponse(status, body, extraHeaders)` | JSON response helper with CORS |

**Routes**:
- `GET /health` → `{ status: 'ok' }`
- `POST *` → Forward to NVIDIA with Bearer auth
- `OPTIONS` → CORS preflight (204)

---

### 7. `server/proxy.js` — Local Dev Proxy

**Env vars** (from `.env`): `NVIDIA_API_KEY`, `PORT` (default 3456), `HANDSHAKE_TOKEN`, `UPSTREAM_TIMEOUT_MS`

**Functions**: `loadEnv(path)`, `jsonResponse(res, status, body)`, `readBody(req)`

**Routes**: `POST /v1/chat/completions`, `GET /health`, `OPTIONS`

**Running**: `cd server && npm start`

---

### 8. `pages/disposition_sync_v2.html` — Pre-Sales Sync

**Scripts**: `config.js` → `xlsx.full.min.js` → `history-helpers.js` → `llm-batch-runner.js`

**Complete Function Inventory** (~85 functions):

| # | Function | Purpose | Called By (onclick) |
|---|----------|---------|-------------------|
| 1 | `cancelAiValidation()` | Abort AI controller | `onclick="cancelAiValidation()"` |
| 2 | `getConfigNumber(key, fallback)` | Read number from config | Internal |
| 3 | `getLlmModel()` | Model from page/config | llm-batch-runner |
| 4 | `isProxyEndpoint(endpoint)` | Proxy check | Internal |
| 5 | `getApiEndpoint()` | Endpoint from config | llm-batch-runner |
| 6 | `getApiKey()` | Key from localStorage→input→config | llm-batch-runner |
| 7 | `syncApiKeyControl(message, tone)` | Show/hide API UI | Init |
| 8 | `saveNvidiaApiKey()` | Save key to localStorage | `onclick="saveNvidiaApiKey()"` |
| 9 | `clearNvidiaApiKey()` | Clear saved key | `onclick="clearNvidiaApiKey()"` |
| 10 | `sanitizeForPrompt(text)` | Strip prompt injection | validateDispositionsWithLLM() |
| 11 | `hashStr(str)` | String → cache key hash | Cache |
| 12 | `getActiveDealerConfig()` | Current dealer from select | Multi |
| 13 | `handleDealerChange()` | Dealer change → re-render | Select change |
| 14 | `renderTableHeader()` | Column headers | Init / dealer change |
| 15 | `getDispositionPriority(d)` | Sort priority | Sorting |
| 16 | `normalizePhone(raw)` | Phone → digits | Multi |
| 17 | `isPhoneLike(val)` | Phone check | Column detection |
| 18 | `parseAutoEngageDate(str)` | AutoEngage date → Date | Parsing |
| 19 | `formatCallDate(dateObj)` | Date → display | Rendering |
| 20 | `isDateStr(val)` | Date check | Column detection |
| 21 | `ordinalSuffix(n)` | 1st, 2nd, 3rd… | Rendering |
| 22 | `formatTime12(dateObj)` | 12-hour time | Rendering |
| 23 | `readFileAsArrayBuffer(file)` | File → ArrayBuffer | Multi |
| 24 | `parseSheet(ab)` | Excel → row objects | File handlers |
| 25 | `cellToString(val)` | Cell → string | Data processing |
| 26 | `detectPhones(obj)` | Find phone column | Column detection |
| 27 | `detectRecording(obj)` | Find recording column | Column detection |
| 28 | `cleanLink(str)` | Clean recording URL | detectRecording() |
| 29 | `extractUrl(str)` | Extract URL from text | detectRecording() |
| 30 | `detectDate(obj)` | Find date column | Column detection |
| 31 | `detectSummary(obj)` | Find summary column | Column detection |
| 32 | `detectSentiment(obj)` | Find sentiment column | Column detection |
| 33 | `detectChannel(obj)` | Find channel column | Column detection |
| 34 | `detectDuration(obj)` | Find duration column | Column detection |
| 35 | `detectSessionId(obj)` | Find session ID column | Column detection |
| 36 | `detectSessionDisposition(obj)` | Find session disposition | Column detection |
| 37 | `deriveSeating(seating, model)` | Seating from model name | Data processing |
| 38 | `getColumnNames(rows)` | All column names | Parsing |
| 39 | `getMissingColumnGroups(...)` | Missing columns | Quality check |
| 40 | `addQualityWarning(...)` | Add warning | buildQualityReport() |
| 41 | `isLikelyIndianMobile(phone)` | Indian phone check | Quality check |
| 42 | `buildQualityReport(...)` | Full quality audit | processFiles() |
| 43 | **`processFiles()`** | **Main entry** | **`onclick="processFiles()"`** |
| 44 | `getSessionBucket(s)` | Recency bucket | Session scoring |
| 45 | `scoreSession(s)` | Session quality score | Session selection |
| 46 | `sessionTimestamp(s)` | Extract timestamp | Session scoring |
| 47 | **`validateDispositionsWithLLM(force)`** | **AI validation** | **`onclick="validateDispositionsWithLLM()"`** |
| 48 | `normalizeDisposition(disp)` | Standardize disp name | Validation |
| 49 | `hasValidSummary(r)` | Check for summary | Validation |
| 50 | `toggleSort(key)` | Sort table column | `onclick="toggleSort('key')"` |
| 51 | `updateSortIndicators()` | Sort arrow | toggleSort() |
| 52 | `compareCaseSensitiveStrings(a, b)` | String compare | Sorting |
| 53 | `getSortedData(data)` | Sorted data | renderTable() |
| 54 | `renderTable(data)` | Main table | processFiles() |
| 55 | `renderConvertedTable(data)` | Converted sub-table | processFiles() |
| 56 | `copyConvertedData()` | Copy converted | `onclick="copyConvertedData()"` |
| 57 | `renderTestDriveTable(data)` | Test drive sub-table | processFiles() |
| 58 | `copyTestDriveData()` | Copy test drive | `onclick="copyTestDriveData()"` |
| 59 | `getPrioClass(disp)` | Priority CSS class | Rendering |
| 60 | `esc(str)` | HTML escape | Rendering |
| 61 | `renderStats(data)` | Statistics display | processFiles() |
| 62 | `renderQualityReport(report)` | Quality report modal | processFiles() |
| 63 | `copyQualityReport()` | Copy quality report | `onclick="copyQualityReport()"` |
| 64 | `getDataRows(data, includeHeader)` | Rows for export | Export |
| 65 | `exportToExcel()` | Multi-sheet XLSX export | `onclick="exportToExcel()"` |
| 66 | `copyData()` | TSV copy to clipboard | `onclick="copyData()"` |
| 67 | `showCopyFeedback(type)` | Flash success | Copy functions |
| 68 | **`resetAll()`** | **Full reset** | **`onclick="resetAll()"`** |
| 69 | `setStatus(id, msg, type)` | Status update | Multi |
| 70 | `showOverlay(msg, total)` | Processing overlay | processFiles() |
| 71 | `hideOverlay()` | Hide overlay | processFiles() |
| 72 | `showAiStatusBar(total)` | AI progress (now delegates to AiValidator.showStatusBar) | validateDispositionsWithLLM() |
| 73 | `updateAiStatusBar(...)` | Update AI progress (now delegates to AiValidator.updateStatusBar) | onProgress callback |
| 74 | `hideAiStatusBar(correctedResults)` | Hide AI (now delegates to AiValidator.hideStatusBar) | AI done |
| 75 | `tick()` | Promise micro-delay | Multi |
| 76 | `updateProcessBtn()` | Enable/disable process | File handlers |
| 77 | `setFileStatus(id, filename)` | File status label | File handlers |
| 78 | `updateStepPills()` | Step progress | Multi |
| 79 | `setupDragDrop(dzId, fileInputId)` | DnD setup | Init |
| 80 | `syncBrandLogo(t)` | Logo swap | Theme |
| 81 | `applyTheme(t)` | Theme apply | Theme |
| 82 | `toggleTheme()` | Dark/light toggle | `onclick="toggleTheme()"` |
| 83 | `cleanGuideArrow(...)` | Guide SVG arrow | Guide |
| 84 | `guideRestoreUnhidden()` | Guide cleanup | Guide exit |
| 85 | `startGuide()` | Show guide | `onclick="startGuide()"` |
| 86 | `exitGuide()` | Close guide | `onclick="exitGuide()"` |
| 87 | `nextGuideStep()` | Guide step forward | `onclick="nextGuideStep()"` |
| 88 | `prevGuideStep()` | Guide step backward | `onclick="prevGuideStep()"` |
| 89 | `updateGuideStep()` | Render guide step | Guide step change |

**All onclick Handlers**:
| Element | Handler |
|---------|---------|
| `.guide-btn-header` | `startGuide()` |
| `.theme-toggle` | `toggleTheme()` |
| `#dz1` | `document.getElementById('f1').click()` |
| `#dz2` | `document.getElementById('f2').click()` |
| `#btnProcess` | `processFiles()` |
| API key Save | `saveNvidiaApiKey()` |
| API key Clear | `clearNvidiaApiKey()` |
| `#btnCopy` | `copyData()` |
| `#btnExport` | `exportToExcel()` |
| `#btnValidateAI` | `validateDispositionsWithLLM()` |
| `#btnReset` | `resetAll()` |
| `#aiStatusCancel` | `cancelAiValidation()` |
| `#btnCopyQuality` | `copyQualityReport()` |
| `#btnCopyConverted` | `copyConvertedData()` |
| `#btnCopyTestDrive` | `copyTestDriveData()` |
| `.th-sortable` (name) | `toggleSort('full_name')` |
| `.th-sortable` (phone) | `toggleSort('phone')` |
| `.th-sortable` (disp) | `toggleSort('disposition')` |
| `#guidePrevBtn` | `prevGuideStep()` |
| `#guideNextBtn` | `nextGuideStep()` |
| Guide exit | `exitGuide()` |

**addEventListener Handlers**:
| Element | Event | Handler |
|---------|-------|---------|
| `#f1` | `change` | Parse file 1 (async) |
| `#f2` | `change` | Parse file 2 |
| Drop zones | `dragover`, `dragleave`, `drop`, `keydown` | DnD |
| Document | `keydown` | Escape→exitGuide, Enter→nextGuideStep |
| Window | `resize` | Guide arrow reposition |

**⚠️ Known bugs**:
- `btnValidateAI.onclick` is rebound in **2 places**: line ~3460 (force=true) and line ~4334 (force=false) — depends on state
- Brace pattern `} else { {` was found and recently fixed
- Cache write was scoped incorrectly (recently fixed)

---

### 9. `pages/post_sales_disposition.html` — Post-Sales Sync

**Scripts**: `xlsx.full.min.js` → `history-helpers.js` → `llm-batch-runner.js` → `config.js` (LAST!)

**Key Data**:
- `DEALERSHIPS` — 8 dealers (Max Motors, Bullmenn, Anant Cars, Perfect Riders, Ambal Honda, etc.)
  - Each: `name`, `workflow` (service/feedback), `mode` (pre/post), `leadColumns`, `sessionColumns`
- `OUTPUT_SCHEMAS` — 8 per-dealer output column definitions (based on `docs/disposition.md`)
- `DISPOSITION_RULES` — 10 keyword rules with `terms[]`, `outcome`, `priority`, `terminal`

**Complete Function Inventory** (~85 functions):

| # | Function | Purpose | Called By |
|---|----------|---------|-----------|
| 1 | `getOutputColumnsForDealer(key)` | Column defs for dealer | Rendering |
| 2 | `toggleSort(key)` | Sort table | `onclick="toggleSort('key')"` |
| 3 | `updateSortIndicators()` | Sort arrow | toggleSort() |
| 4 | `compareCaseSensitiveStrings(a, b)` | String compare | Sorting |
| 5 | `getSortedData(data)` | Sorted data | renderTable() |
| 6 | `esc(v)` | HTML escape | Rendering |
| 7 | `safeRecordingHref(value)` | Safe URL | Rendering |
| 8 | `clean(v)` | Trim | Data |
| 9 | `canonicalHeader(h)` | Normalize header | Column matching |
| 10 | `cellToString(val)` | Cell → string | Parsing |
| 11 | `readFileAsArrayBuffer(file)` | File → ArrayBuffer | File handlers |
| 12 | `parseSheet(ab)` | Excel → rows | File handlers |
| 13 | `normalizePhone(raw)` | Phone → digits | Multi |
| 14 | `isPhoneLike(val)` | Phone check | Column detection |
| 15 | `detectPhones(obj)` | Find phone column | Column detection |
| 16 | `get(row, candidates)` | First non-empty cell | Column detection |
| 17 | `detectDate(row)` | Find date column | Column detection |
| 18 | `detectRecording(row)` | Find recording column | Column detection |
| 19 | `parseAutoEngageDate(str)` | AutoEngage date | Parsing |
| 20 | `formatDate(str)` | Date → display | Rendering |
| 21 | `convertEpochToIST(val)` | Epoch → IST | Date parsing |
| 22 | `normalizedText(value)` | Lowercase + trim | classifyDisposition() |
| 23 | `classifyDisposition(disp, status, summary)` | Keyword classification | processFiles() |
| 24 | `isServiceBooked(row)` | Service booked? | processFiles() |
| 25 | `isFeedbackOrEscalation(row)` | Feedback check | processFiles() |
| 26 | `isServiceCompleted(row)` | Service completed? | processFiles() |
| 27 | `isNotInterested(row)` | Not interested? | processFiles() |
| 28 | `extractPerfectRidersLocation(summary)` | Location extract | Post-processing |
| 29 | `extractPerfectRidersCRE(summary)` | CRE extract | Post-processing |
| 30 | `sessionScore(row)` | Session quality | buildSessionMap() |
| 31 | `getSelectedDealer()` | Current dealer | Multi |
| 32 | `buildSessionMap(rows)` | Group sessions by phone | processFiles() |
| 33 | `addQualityIssue(issues, level, text, blocking)` | Add quality issue | buildQualityReport() |
| 34 | `sampleSourceRow(row, label)` | Sample row | buildQualityReport() |
| 35 | `getOutputFieldChecks(dealerKey)` | Field validation | buildQualityReport() |
| 36 | `evaluateFileRoles(role1, role2)` | Auto-detect leads vs sessions | processFiles() |
| 37 | `buildQualityReport({...})` | Full quality audit | processFiles() |
| 38 | `missingColumns(rows, expected)` | Missing columns | buildQualityReport() |
| 39 | `scoreFileRole(rows)` | Score file role | processFiles() |
| 40 | **`processFiles()`** | **Main entry** | **`onclick="processFiles()"`** |
| 41 | `renderAll()` | Full UI | processFiles() |
| 42 | `renderStats()` | Stats bar | renderAll() |
| 43 | `renderQualityReport()` | Quality report | renderAll() |
| 44 | `renderTable()` | Output table | renderAll() |
| 45 | `renderPreviewTables()` | Preview section | renderAll() |
| 46 | `renderPreviewBookedTable()` | Booked preview | renderPreviewTables() |
| 47 | `renderPreviewCompletedTable()` | Completed preview | renderPreviewTables() |
| 48 | `renderPreviewNotInterestedTable()` | Not interested preview | renderPreviewTables() |
| 49 | `rowsToTsv(rows, keys)` | Rows → TSV | Copy |
| 50 | `copyText(text, statusText)` | Clipboard copy | Copy functions |
| 51 | `copyData()` | Copy main table | `onclick="copyData()"` |
| 52 | `copyPreviewRows(type)` | Copy preview table | `onclick="copyPreviewRows('booked')"` etc. |
| 53 | `copyQualityReport()` | Copy quality report | `onclick="copyQualityReport()"` |
| 54 | `exportToExcel()` | Multi-sheet XLSX | `onclick="exportToExcel()"` |
| 55 | **`resetAll()`** | **Full reset** | **`onclick="resetAll()"`** |
| 56 | `setStatus(id, msg, type)` | Status update | Multi |
| 57 | `showOverlay(msg)` | Processing overlay | processFiles() |
| 58 | `hideOverlay()` | Hide overlay | processFiles() |
| 59 | `showAiStatusBar(total)` | AI progress (delegates to AiValidator.showStatusBar) | validateDispositionsWithLLM() |
| 60 | `cancelAiValidation()` | Abort AI (delegates to AiValidator.cancel) | `onclick="cancelAiValidation()"` |
| 61 | `updateAiStatusBar(...)` | Update AI progress (delegates to AiValidator.updateStatusBar) | onProgress |
| 62 | `hideAiStatusBar(correctedResults)` | Hide AI (delegates to AiValidator.hideStatusBar) | AI done |
| 63 | `tick()` | Micro-delay | Multi |
| 64 | `updateProcessButton()` | Enable/disable | File handlers |
| 65 | `setFileStatus(id, filename)` | File status | File handlers |
| 66 | `handleDealerChange()` | Dealer change | Select change |
| 67 | `setupDragDrop(dzId, fileInputId)` | DnD setup | Init |
| 68 | `syncBrandLogo(t)` | Logo swap | Theme |
| 69 | `applyTheme(t)` | Theme apply | Theme |
| 70 | `toggleTheme()` | Toggle | `onclick="toggleTheme()"` |
| 71 | `getConfigNumber(key, fallback)` | Config number | LLM setup |
| 72 | `getLlmModel()` | Model from config | llm-batch-runner |
| 73 | `isProxyEndpoint(endpoint)` | Proxy check | Multi |
| 74 | `sanitizeForPrompt(text)` | Sanitize for LLM | validateDispositionsWithLLM() |
| 75 | `getApiEndpoint()` | Endpoint | llm-batch-runner |
| 76 | `getApiKey()` | API key | llm-batch-runner |
| 77 | `syncApiKeyControl(message, tone)` | Key UI | Init |
| 78 | `saveNvidiaApiKey()` | Save key | `onclick="saveNvidiaApiKey()"` |
| 79 | `clearNvidiaApiKey()` | Clear key | `onclick="clearNvidiaApiKey()"` |
| 80 | `hashStr(str)` | Hash | Cache |
| 81 | `validateDispositionsWithLLM(force)` | AI validation | `onclick="validateDispositionsWithLLM()"` |

**⚠️ Known bugs**:
- `btnValidateAI.onclick` is rebound in **3 places**: ~lines 2733, 3413, 4674 — depending on state
- Loads config.js LAST — if anything depends on `window.JEJO_CONFIG` at parse time, it will fail

---

### 10. `pages/dashboard.html` — Campaign Dashboard

**Scripts**: `config.js` → `xlsx.full.min.js` → `llm-batch-runner.js` → `html2canvas.min.js` → `jspdf.umd.min.js`

**Key Data**:
- `DISPO_TO_THEME` — Maps 40+ Zoho dispositions → 9 themes: `voicemail`, `not_interested`, `language_barrier`, `wrong_person`, `deferred`, `callback_requested`, `already_serviced`, `service_booked`, `customer_busy`, `audio_issue`, `sold_vehicle`, `dissatisfied`

**Complete Function Inventory** (~60+ functions):

| # | Function | Purpose | Called By |
|---|----------|---------|-----------|
| 1 | `getStoredTheme()` | Theme from localStorage | Init |
| 2 | `syncBrandLogo(theme)` | Logo swap | applyTheme() |
| 3 | `applyTheme(theme)` | Apply theme | Init/toggleTheme() |
| 4 | `toggleTheme()` | Dark/light toggle | `onclick="toggleTheme()"` |
| 5 | `parseSummary(text)` | Extract agent/customer/vehicle/dates/language/competitor | Analytics functions |
| 6 | `analyzeConversionFunnel(...)` | Funnel stats | generateDashboard() |
| 7 | `analyzeDispositionPatterns(...)` | Disposition frequency | generateDashboard() |
| 8 | `analyzeDecisionPipeline(...)` | Decision timeline | generateDashboard() |
| 9 | `analyzeCallbackBehavior(...)` | Callback requests | generateDashboard() |
| 10 | `analyzeLanguageBarriers(...)` | Language barriers | generateDashboard() |
| 11 | `analyzeCompetitiveLosses(...)` | Lost to competition | generateDashboard() |
| 12 | `analyzeSentimentFromTranscript(...)` | Sentiment analysis | generateDashboard() |
| 13 | `detectAnomalies(data, dailyCounts)` | Statistical anomalies | generateDashboard() |
| 14 | `analyzeSourceQuality(...)` | Source connect/book rates | generateDashboard() |
| 15 | `analyzeTrends(...)` | Volume trends | generateDashboard() |
| 16 | `analyzeConversionBlockers(...)` | Why connected didn't convert | generateDashboard() |
| 17 | `analyzeAgentPerformance(...)` | Per-agent stats | generateDashboard() |
| 18 | `getConfigNumber(key, fallback)` | Config number | LLM setup |
| 19 | `getLlmModel()` | Model | llm-batch-runner |
| 20 | `isProxyEndpoint(endpoint)` | Proxy check | Multi |
| 21 | `getApiEndpoint()` | Endpoint | llm-batch-runner |
| 22 | `getApiKey()` | API key | llm-batch-runner |
| 23 | `syncApiKeyControl(message, tone)` | Key UI | Init |
| 24 | `saveNvidiaApiKey()` | Save key | `onclick="saveNvidiaApiKey()"` |
| 25 | `clearNvidiaApiKey()` | Clear key | `onclick="clearNvidiaApiKey()"` |
| 26 | `useTypedApiKeyForRun()` | Use input key | classifyWithLlm() |
| 27 | `hashStr(str)` | Hash | Cache |
| 28 | `showAiNotice(msg, isError)` | Transient notice | Multi |
| 29 | `cancelAiValidationDash()` | Abort AI | `onclick="cancelAiValidationDash()"` |
| 30 | `updateAiStatus(current, total, msg, isError)` | AI progress bar | onProgress |
| 31 | `buildPromptForBatch(summaries, systemPrompt)` | Batch prompt | classifyWithLlm() |
| 32 | `buildLlmSystemPrompt(isPostSales)` | System prompt | classifyWithLlm() |
| 33 | `sanitizeForPrompt(text)` | Sanitize | classifyWithLlm() |
| 34 | `buildNvidiaHeaders(apiKey)` | Request headers | Multi |
| 35 | `fetchLlmCompletion(apiKey, body, timeoutMs)` | Single LLM call | generateVoiceInsights() |
| 36 | `getChoiceText(data)` | Extract text from response | classifyWithLlm() |
| 37 | `isRetryableNvidiaError(status)` | Retry check | classifyWithLlm() |
| 38 | `isNonRetryableNvidiaErrorMessage(msg)` | Error check | classifyWithLlm() |
| 39 | `normalizeLlmResults(parsed, summaries)` | Normalize LLM output | parseLlmJsonResults() |
| 40 | `parseLlmJsonResults(text, summaries)` | Parse LLM JSON | classifyWithLlm() |
| 41 | `classifyWithLlm(allSummaries, isPostSales, apiKey)` | Full AI classification | runAiAnalysis() |
| 42 | `generateVoiceInsights(themes)` | AI voice insights | runAiAnalysis() |
| 43 | `generateStoryHeadline(themes, funnel, healthScore)` | Headline | runAiAnalysis() |
| 44 | `generateExecutiveNarrative(...)` | Full narrative | runAiAnalysis() |
| 45 | `generateRecommendations(...)` | Recommendations | runAiAnalysis() |
| 46 | **`generateDashboard()`** | **Main entry** | **`onclick="generateDashboard()"`** |
| 47 | **`runAiAnalysis()`** | **AI analysis** | **`onclick="runAiAnalysis()"`** |
| 48 | `printPDF()` | PDF export | `onclick="printPDF()"` |
| 49 | `renderExecutiveSummary(summary, healthScore, healthClass)` | Executive banner | generateDashboard() |
| 50 | `renderInsightStrip(insights)` | Insight chips | generateDashboard() |
| 51 | `renderConversionFunnel(funnel)` | Funnel visualization | generateDashboard() |
| 52 | `renderDispositionIntelligence(patterns)` | Disposition bars | generateDashboard() |
| 53 | `renderDecisionPipeline(pipeline)` | Pipeline buckets | generateDashboard() |
| 54 | `renderLeadQualityScorecard(lq)` | Quality card | generateDashboard() |
| 55 | `renderAnomalySection(anomalies)` | Anomaly alerts | generateDashboard() |
| 56 | `renderCompetitiveIntel(compData)` | Competitor bars | generateDashboard() |
| 57 | `renderLanguageQuality(langData)` | Language stats | generateDashboard() |
| 58 | `renderSourceQuality(srcData)` | Source quality | generateDashboard() |
| 59 | `renderTrendIndicators(trends)` | Trend badge | generateDashboard() |
| 60 | `renderConversionBlockers(blockerData)` | Blocker bars | generateDashboard() |
| 61 | `renderCustomerVoice(themes, voiceAI)` | Customer voice cards | generateDashboard() |
| 62 | `renderRecommendations(recs)` | Recommendation list | generateDashboard() |
| 63 | `renderAgentTable(agents)` | Agent performance table | generateDashboard() |
| 64 | `renderAnomalyTable(anomalies)` | Anomaly table | generateDashboard() |
| 65 | `renderLlmRecs(recs)` | AI recommendations | generateDashboard() |

**addEventListener Handlers**:
| Element | Event | Handler |
|---------|-------|---------|
| `#fileDash` | `change` | File handler |
| `#dzDash` | `dragover`, `dragleave`, `drop`, `keydown` | DnD |
| `#campaignMode` | `change` | Campaign mode switch |
| `#dateFormatMode` | `change` | Date format switch |
| Window | `afterprint`, `beforeprint` | PDF print |

**Unique Features**:
- Own complete AI pipeline (`classifyWithLlm`) — separate from disposition sync
- Uses `llmThemeBatchSize` (separate from `llmBatchSize`)
- PDF export with html2canvas + jspdf
- `DISPO_TO_THEME` mapping for internal theme classification

---

### 11. `pages/call_analysis_summary.html` — Call Analysis Summary

**Scripts**: `config.js` → `xlsx.full.min.js`

**Key Data**:
- `PRE_SALES_DISPOSITIONS` — 35 dispositions with descriptions
- `POST_SALES_DISPOSITIONS` — 42 dispositions with descriptions
- `POST_SALES_KPI_GROUPS` — Maps KPI labels to disposition arrays

**Complete Function Inventory** (~45 functions):

| # | Function | Purpose | Called By |
|---|----------|---------|-----------|
| 1 | `getPostDispositionKey(row)` | Post-sales matching | Post analysis |
| 2 | `isDispositionMatch(row, keys)` | Row matches dispositions | Post analysis |
| 3 | `getPreDispositionKey(row)` | Pre-sales matching | Pre analysis |
| 4 | `isPreDispositionMatch(row, keys)` | Pre check | Pre analysis |
| 5 | `detectDateFormat(dateStrings)` | Auto-detect format | handleFile() |
| 6 | `updateDateParserNote()` | Show parser info | handleFile() |
| 7 | `handleDateFormatChange()` | User change | Select change |
| 8 | `normalizeDateString(raw)` | Normalize date | Analysis |
| 9 | `handleFile(file)` | Parse file | File input |
| 10 | `normalizeRows(rows)` | Normalize columns | handleFile() |
| 11 | `getWorkbookRows(workbook)` | Read all sheets | handleFile() |
| 12 | `readSheetRows(workbook, sheetName)` | Single sheet | getWorkbookRows() |
| 13 | `mergeWorkbookRows(primary, supplement)` | Merge sheets | getWorkbookRows() |
| 14 | `getSummarySheetName(workbook)` | Find summary sheet | handleFile() |
| 15 | `rowHasData(row)` | Has content? | normalizeRows() |
| 16 | `makeGetter(row)` | Column getter | normalizeRows() |
| 17-19 | `normalizeKey(value)`, `clean(value)`, `lower(value)` | Header/text helpers | normalizeRows() |
| 20 | `phoneKey(value)` | Phone → digits | Analysis |
| 21 | `getEffectiveSummary(row)` | Best summary | Analysis |
| 22 | `isConnected(row)` | Pre connected | renderSummary() |
| 23 | `isNotConnected(row)` | Pre not connected | renderSummary() |
| 24 | `isTestDriveBooking(row)` | Pre booking | renderSummary() |
| 25 | `isTestDriveCompleted(row)` | Pre TD completed | renderSummary() |
| 26 | `hasAny(text, terms)` | Text check | Multi |
| 27 | `detectCampaignModeFromRows(rows)` | Auto pre/post | handleFile() |
| 28 | `resolveCampaignMode(selectValue, rows)` | Resolve mode | handleFile() |
| 29-35 | Various post checks: `isPostConnected`, `hasPostVoicemail`, `isPostServiceBooked`, etc. | Post checks | renderSummary() |
| 36 | `countPostUniqueCalls(data)` | Unique calls | renderSummary() |
| 37 | `detectPostLocation(row)` | Post location | renderSummary() |
| 38 | `renderSummary(data)` | Main KPI rendering | handleFile() |
| 39 | `renderRuleAudit(rules)` | Rule definitions | renderSummary() |
| 40-42 | `renderPreviewTables()`, `renderBookingTable()`, `renderCompletedTable()` | Preview tables | renderSummary() |
| 43-46 | `getBookingColumns`, `getCompletedColumns`, `getBookingDisposition`, etc. | Column helpers | Rendering |
| 47 | `hidePreviewTables()` | Hide previews | handleFile() |
| 48 | `copyBookingData()` | Copy bookings | `onclick="copyBookingData()"` |
| 49 | `copyCompletedData()` | Copy completed | `onclick="copyCompletedData()"` |
| 50 | `copySummaryText()` | Copy summary | `onclick="copySummaryText()"` |
| 51-53 | `toTsvCell`, `copyText`, `escapeHtml` | Helpers | Copy functions |
| 54 | `setStatus(message, type)` | Status | Multi |
| 55-58 | Theme functions (getStored, syncBrandLogo, applyTheme, toggleTheme) | Theme | Init/`onclick` |

**addEventListener Handlers**:
| Element | Event | Handler |
|---------|-------|--------|
| `#fileInput` | `change` | handleFile() |
| `#dropZone` | `dragover`, `dragleave`, `drop`, `keydown` | DnD handlers |
| `#campaignMode` | `change` | Campaign mode switch |
| `#dealerSelectCallAnalysis` | `change` | Dealer change |
| `#dateFormatSelect` | `change` | handleDateFormatChange() |

**Notes**:
- `config.js` is loaded but **appears unused** — no AI calls in this page
- No `llm-batch-runner.js` dependency

---

### 12. `pages/reattempt_filter.html` — Re-Attempt Filter

**Scripts**: `xlsx.full.min.js` (**NO config.js**)

**Key Data**:
- `DEALERSHIPS` — 2 dealers (Anant Cars, Perfect Riders)
- `TERMINAL_DISPOSITIONS` — Set: `invalid lead`, `purchased elsewhere`, `not interested`, `purchase postponed`
- `CONNECTED_OUTCOMES` — Set: `connected`, `completed`
- `REATTEMPT_CONNECTED_SUMMARY_PHRASES` — 7 phrases
- `AE_LEADS_PER_BATCH` = 100

**Complete Function Inventory** (~55 functions):

| # | Function | Purpose | Called By |
|---|----------|---------|-----------|
| 1 | `isConnectedOutcome(outcome)` | Check connected | processFile() |
| 2 | `normalizeSummaryText(summary)` | Normalize summary | isReattemptConnectedSummary() |
| 3 | `isReattemptConnectedSummary(summary)` | Re-attempt check | processFile() |
| 4 | `normalizePhone(raw)` | Phone → digits | Multi |
| 5 | `readFileAsArrayBuffer(file)` | File → ArrayBuffer | File handler |
| 6 | `parseSheet(ab)` | Excel → rows | File handler |
| 7 | `cellToString(val)` | Cell → string | Multi |
| 8 | `findCol(row, candidates)` | Find column | Column detection |
| 9-18 | `detectPhone`, `detectOutcome`, `detectDisposition`, `detectSummary`, `detectFullName`, `detectModel`, `detectSeating`, `detectCity`, `detectPincode`, `detectCallDate`, `detectAttempts` | Column detection | processFile() |
| 19 | `parseExcelSerialDate(value)` | Serial → Date | parseCallDate() |
| 20 | `buildValidatedDate(...)` | Safe date | parseCallDate() |
| 21 | `parseCallDate(value)` | Multi-format date | processFile() |
| 22 | `getRowRank(row)` | Priority rank | compareRowsByRecency() |
| 23 | `compareRowsByRecency(a, b)` | Sort by recency | getLatestRow() |
| 24 | `getLatestRow(rows)` | Best row from group | processFile() |
| 25 | `formatRankDate(row)` | Date for rank | getLatestRow() |
| 26 | **`processFile()`** | **Main logic** | **`onclick="processFile()"`** |
| 27 | `renderStats(...)` | Stats bar | processFile() |
| 28 | `renderDedupSummary(...)` | Dedup summary | processFile() |
| 29 | `formatSerialDate(val)` | Serial → string | Row formatting |
| 30 | `getOutputSchema(dealershipKey)` | Output headers | Multi |
| 31 | `renderIncludedTable(data)` | Included rows | processFile() |
| 32 | `renderExcludedTable(data)` | Excluded rows | processFile() |
| 33-37 | Batch system: `fileBatchFingerprint`, `readAeBatchStore`, `writeAeBatchStore`, `getSavedBatchProgress`, `saveBatchProgress`, `clearBatchProgressForFingerprint` | Batch progress | Batch system |
| 38 | `hideBatchPanel()` | Hide batch | processFile() |
| 39 | `refreshBatchHint()` | Batch hint | processFile() |
| 40 | `syncResumeBannerAndActions()` | Resume UI | processFile() |
| 41 | `configureBatchPanelAfterFormat(...)` | Setup batch | processFile() |
| 42 | `setupBatchExportControls()` | Export inputs | Init |
| 43 | **`downloadOutput()`** | **Batch CSV** | **`onclick="downloadOutput()"`** |
| 44 | **`copyOutputData()`** | **TSV copy** | **`onclick="copyOutputData()"`** |
| 45 | **`resetAll()`** | **Full reset** | **`onclick="resetAll()"`** |
| 46 | `esc(str)` | HTML escape | Rendering |
| 47 | `setStatus(id, msg, type)` | Status | Multi |
| 48-49 | `showOverlay(msg)`, `hideOverlay()` | Overlay | processFile() |
| 50 | `tick()` | Micro-delay | processFile() |
| 51 | `detectDateFormat(dateStrings)` | Auto-detect format | processFile() |
| 52 | `updateDateParserNote()` | Parser info | processFile() |
| 53 | `applyDateFormat(rawRows)` | Apply format | processFile() |
| 54 | `handleDateFormatChange()` | User change | Select change |
| 55-57 | Theme functions (syncBrandLogo, applyTheme, toggleTheme) | Theme | Init/`onclick` |

**Shared Batch System**: Same localStorage key `'jejo-ae-batch-export-v1'` as `autongage_formatter.html`.

---

### 13. `pages/autongage_formatter.html` — AutoEngage Formatter

**Scripts**: `xlsx.full.min.js` (**NO config.js**)

**Key Data**:
- `TEMPLATES` — 9 templates: Bullmenn, Ambal ERODE, Ambal SAIBABA, Suryabala, ICARE, Anant Cars, Singhal, Fortune Hyryder, Fortune Toyota
  - Each with: `sourceToTarget`, `outputOrder`, `defaults`, `multiSource`, `normalizeToyotaModels`, `normalizeMahindraModels`
- `AE_LEADS_PER_BATCH` = 100

**Complete Function Inventory** (~35 functions):

| # | Function | Purpose | Called By |
|---|----------|---------|-----------|
| 1 | `normalizeToyotaVehicleModel(raw)` | Toyota model norm | parseSheet() |
| 2 | `normalizeMahindraVehicleName(raw)` | Mahindra model norm | parseSheet() |
| 3 | `buildTargetSources(template)` | Reverse mapping | processFile() |
| 4 | `firstMappedCell(inputRow, canonicalKeys)` | First non-empty | buildTargetSources() |
| 5-10 | Batch system: `fileBatchFingerprint`, `readAeBatchStore`, `writeAeBatchStore`, `getSavedBatchProgress`, `saveBatchProgress`, `clearBatchProgressForFingerprint` | Batch progress | Batch system |
| 11 | `hideBatchPanel()` | Hide batch | processFile() |
| 12 | `refreshBatchHint()` | Batch hint | processFile() |
| 13 | `syncResumeBannerAndActions()` | Resume UI | processFile() |
| 14 | `configureBatchPanelAfterFormat(...)` | Setup batch | processFile() |
| 15 | `setupBatchExportControls()` | Export inputs | Init |
| 16 | `normalizeHeader(text)` | Clean header | parseSheet() |
| 17 | `cellToString(value)` | Cell → string | Multi |
| 18 | `setStatus(msg, type)` | Status | Multi |
| 19 | `setCounts(inRows, outRows, mapped, defaults)` | Stats display | processFile() |
| 20 | `readFileAsArrayBuffer(file)` | File → ArrayBuffer | File handler |
| 21 | `parseSheet(ab, template)` | Smart Excel parser | processFile() |
| 22 | `buildMappingHint()` | Column mapping hint | processFile() |
| 23 | `limitedRows(rows, emptyText)` | First rows | buildMappingAudit() |
| 24 | `buildMappingAudit(template, parsed, rows)` | Mapping report | processFile() |
| 25 | `renderMappingAudit(audit)` | Show audit | processFile() |
| 26 | `clearOutput()` | Clear state | processFile() |
| 27 | **`processFile()`** | **Main processing** | **`onclick="processFile()"`** |
| 28 | `renderPreview(headers, rows)` | Preview table | processFile() |
| 29 | **`downloadOutput()`** | **Batch CSV** | **`onclick="void downloadOutput()"`** |

**Shared Batch System**: Same localStorage key `'jejo-ae-batch-export-v1'` as `reattempt_filter.html`.

---

### 14. `pages/recording_renamer.html` — Recording Renamer

**Scripts**: `xlsx.full.min.js` → `config.js` → `jszip.min.js`

**Complete Function Inventory** (~45 functions):

| # | Function | Purpose | Called By |
|---|----------|---------|-----------|
| 1 | `getCorsProxyUrl()` | Read proxy URL | toggleProxyMode(), syncProxyToggle() |
| 2 | `toggleProxyMode()` | Toggle proxy | `onclick="toggleProxyMode()"` |
| 3 | `syncProxyToggle()` | Sync button to config | Init |
| 4 | `normalizeHeader(value)` | Clean header | parseDataFile() |
| 5 | `normalizePhone(raw)` | Phone → digits | Multi |
| 6 | `cellToString(value)` | Cell → string | parseDataFile() |
| 7 | `parseExcelSerial(value)` | Serial → Date | parseDataFile() |
| 8 | `buildValidatedDate(...)` | Safe date | parseDate() |
| 9 | `parseDate(value)` | Multi-format date | parseDataFile() |
| 10 | `formatDateToken(date)` | Filename token | buildResults() |
| 11 | `formatDateDisplay(date)` | Readable date | buildResults() |
| 12 | `getExtension(name)` | File extension | buildResults() |
| 13 | `getRowValue(row, names)` | Get cell by names | buildResults() |
| 14 | `readFileAsArrayBuffer(file)` | File → ArrayBuffer | File handler |
| 15 | `parseDataFile(file)` | Excel w/ hyperlinks | File handler |
| 16 | `uniqueOutputName(...)` | No dupes | buildResults() |
| 17 | `buildResults(rows)` | Match phone+date+URL | processBatch() |
| 18 | `csvEscape(value)` | CSV safe | makeReportCsv() |
| 19 | `makeReportCsv(results)` | CSV report | processBatch() |
| 20 | **`processBatch()`** | **Main processing** | **`onclick="processBatch()"`** |
| 21 | `wait(ms)` | Promise delay | fetchRecordingWithRetry() |
| 22 | `buildFetchUrl(originalUrl)` | Route via proxy | fetchRecordingWithRetry() |
| 23 | `fetchRecordingWithRetry(row, onAttempt)` | Download with retries | processBatch() |
| 24 | **`downloadZip()`** | **ZIP all recordings** | **`onclick="downloadZip()"`** |
| 25 | `getDownloadFailureMessage(error, timedOut)` | Error text | fetchRecordingWithRetry() |
| 26 | `extensionFromContentType(contentType)` | MIME → ext | fetchRecordingWithRetry() |
| 27 | `replaceExtension(filename, extension)` | Change ext | fetchRecordingWithRetry() |
| 28 | `updateResultStatus(...)` | Update row | fetchRecordingWithRetry() |
| 29 | `downloadReport()` | CSV report | `onclick="downloadReport()"` |
| 30 | `getZipDateToken()` | ZIP name token | downloadZip() |
| 31 | `triggerDownload(blob, filename)` | Force download | Multi |
| 32 | `getUrlCount(rows)` | Count URLs | buildResults() |
| 33 | `renderResults(rows, urlCount)` | Results table | processBatch() |
| 34 | `updateProcessButton()` | Enable/disable | File handler |
| 35 | **`resetAll()`** | **Full reset** | **`onclick="resetAll()"`** |
| 36 | `setBusy(isBusy)` | Loading state | processBatch() |
| 37 | `setStatus(message, type)` | Status | Multi |
| 38 | `esc(value)` | HTML escape | Rendering |
| 39 | `setupDropZone(zoneId, inputId, onFiles)` | DnD setup | Init |
| 40-42 | Theme functions (syncBrandLogo, applyTheme, toggleTheme) | Theme | Init/`onclick` |
| 43 | `detectDateFormat(dateStrings)` | Auto-detect | parseDataFile() |
| 44 | `updateDateParserNote()` | Parser info | parseDataFile() |
| 45 | `applyDateFormat()` | Apply | parseDataFile() |
| 46 | `handleDateFormatChange()` | User change | Select change |

---

## ⚠️ Danger Zones — Change Ripple Effects

### If I change `config.js` → affects:
- `dashboard.html` (AI config: batchSize, concurrent, timeout, model)
- `disposition_sync_v2.html` (AI config: llmDispositionBatchSize etc.)
- `post_sales_disposition.html` (AI config)
- `recording_renamer.html` (corsProxyUrl)
- `call_analysis_summary.html` (loaded but unused — no effect)

### If I change `llm-batch-runner.js` → affects:
- `dashboard.html` → `classifyWithLlm()` uses `runLlmBatches()`
- `disposition_sync_v2.html` → `validateDispositionsWithLLM()` uses `runLlmBatches()`
- `post_sales_disposition.html` → `validateDispositionsWithLLM()` uses `runLlmBatches()`

### If I change `history-helpers.js` → affects:
- `disposition_sync_v2.html` → `detectHistory()`, `formatHistoryForPrompt()`
- `post_sales_disposition.html` → `detectHistory()`, `formatHistoryForPrompt()`

### If I change theme functions → affects:
- ALL 8 HTML files — each has duplicated inline theme functions
- Exception: `index.html` uses shared `assets/scripts/index.js`

### If I change batch download system (localStorage key `'jejo-ae-batch-export-v1'`) → affects:
- `reattempt_filter.html` and `autongage_formatter.html` — both use same key

### If I change `assets/css/design-system.css` → affects:
- ALL 7 tool pages (shared theme vars, reset, header/nav, theme-toggle, buttons, status bars)
- `index.html` is NOT affected (it's excluded from the design system)

### If I change page-specific CSS variables → affects:
- Only the single CSS file for that page

### If I change `docs/AN_format.md` → affects:
- `autongage_formatter.html` — template definitions mirror this doc

### If I change `docs/disposition.md` → affects:
- `post_sales_disposition.html` — OUTPUT_SCHEMAS mirror this doc
- `call_analysis_summary.html` — disposition lists
- `dashboard.html` — DISPO_TO_THEME mapping

### If I change `assets/js/lib/excel-safe.js` → affects:
- `reattempt_filter.html`, `autongage_formatter.html`, `recording_renamer.html`, `post_sales_disposition.html`, `disposition_sync_v2.html` — all 5 use `excelSafe()`, `excelSafeCsvCell()`, or `excelSafeTsvCell()` in CSV/TSV export paths. If I add or rename any exported function, all 5 need updating.

**Where each function is used by page:**
| Page | Function Used | Export Path |
|------|--------------|-------------|
| `reattempt_filter.html` | `excelSafeCsvCell`, `excelSafeTsvCell` | `downloadOutput()` (CSV), `copyOutputData()` (TSV) |
| `autongage_formatter.html` | `excelSafeCsvCell` | `downloadOutput()` (CSV batches) |
| `recording_renamer.html` | `excelSafe` | `makeReportCsv()` (report CSV) |
| `post_sales_disposition.html` | `excelSafeTsvCell` | `rowsToTsv()` (TSV copy) |
| `disposition_sync_v2.html` | `excelSafeTsvCell` | `copyConvertedData()`, `copyTestDriveData()` (TSV copy) |

**⚠️ Not used in these pages** (no CSV/TSV export): `dashboard.html`, `call_analysis_summary.html`, `index.html`.

---

## 📋 File Dependency Graph

```
index.html ──────────────────────────────────────→ pages/*.html (links via <a>)

config.js ←── dashboard.html
         ←── disposition_sync_v2.html
         ←── post_sales_disposition.html
         ←── recording_renamer.html
         (loaded but unused by call_analysis_summary.html)
         (NOT loaded by reattempt_filter.html, autongage_formatter.html)

llm-batch-runner.js ←── dashboard.html
                    ←── disposition_sync_v2.html
                    ←── post_sales_disposition.html

history-helpers.js ←── disposition_sync_v2.html
                    ←── post_sales_disposition.html

excel-safe.js ←── reattempt_filter.html
             ←── autongage_formatter.html
             ←── recording_renamer.html
             ←── post_sales_disposition.html
             ←── disposition_sync_v2.html

xlsx.full.min.js ←── ALL tools
jszip.min.js     ←── recording_renamer.html only
html2canvas      ←── dashboard.html only
jspdf            ←── dashboard.html only

worker/worker.js ←── config.js (apiEndpoint URL)
server/proxy.js             ←── config.js (apiEndpoint URL)
```

---

## 🧠 CSS Architecture

### Design System (`assets/css/design-system.css`)

All 7 tool pages share a single design system loaded FIRST, then overridden by page-specific CSS:

**What the design system provides**:
- Theme tokens (dark/light) — `--bg`, `--surface`, `--accent`, `--text`, etc.
- Reset & base (`*`, `html`, `body`)
- Header, nav links, brand-mark, header-badge, theme-toggle
- Status messages (`.status-msg`)
- Drop zone (`.drop-zone`, `.dz-icon`, `.dz-text`, `.dz-status`)
- `.btn-generate` CTA button
- AI status bar (`.ai-status-bar`, `.ai-status-msg`, `.ai-status-badge`, etc.)
- Processing overlay (`.processing-overlay`, `.processing-msg`)

**How theming works**: Each page defines its accent color in `:root { --accent: ... }`, which cascades through the design system's `var(--accent, #eab308)` fallbacks.

**Landing page (`index.html`)** is intentionally excluded — it has a completely unique design.

### Per-Page CSS Overrides

| CSS File | Used By | Accent Color | Unique Content |
|----------|---------|-------------|----------------|
| `index.css` | Landing page | Red (#ef4444) | Full custom design (no design system) |
| `dashboard.css` | Campaign Dashboard | Yellow (#eab308) | KPI cards, bar charts, voice cards, PDF styles |
| `call-analysis-summary.css` | Call Summary | Purple (#a855f7) | KPI tables, preview tables |
| `disposition-sync-v2.css` | Pre-Sales Sync | Red (#ef4444) | Quality report, step pills, session table |
| `post-sales-disposition.css` | Post-Sales Sync | Orange (#f97316) | Preview tables, dealer selects |
| `reattempt-filter.css` | Re-Attempt Filter | Pink (#f472b6) | Batch export panel, included/excluded tables |
| `recording-renamer.css` | Recording Renamer | Green (#22c55e) | Progress table, zip status |
| `autongage-formatter.css` | AutoEngage Formatter | Blue (#3b82f6) | Mapping audit, batch export panel |

---

## 📋 Summary: Which Pages Use AI (LLM) vs Not

| Page | Uses AI? | AI Engine | Uses config.js? |
|------|----------|-----------|-----------------|
| `dashboard.html` | ✅ Yes | `llm-batch-runner.js` + own classifyWithLlm | ✅ Yes |
| `disposition_sync_v2.html` | ✅ Yes | `llm-batch-runner.js` | ✅ Yes |
| `post_sales_disposition.html` | ✅ Yes | `llm-batch-runner.js` | ✅ Yes |
| `call_analysis_summary.html` | ❌ No | — | ✅ (loaded but unused) |
| `reattempt_filter.html` | ❌ No | — | ❌ No |
| `autongage_formatter.html` | ❌ No | — | ❌ No |
| `recording_renamer.html` | ❌ No | — | ✅ Yes (for corsProxyUrl) |

---

## 💡 Key Insights from This Analysis

1. **Most duplicated code**: Theme functions (8 copies across files)
2. **Most fragile pattern**: `btnValidateAI.onclick` rebound in multiple places (3 in post_sales, 2 in pre_sales)
3. **Best candidates for refactoring**: Extract theme functions into a shared file; unify the 3 AI validation `validateDispositionsWithLLM()` implementations
4. **Dead code**: `call_analysis_summary.html` loads `config.js` but never uses it
5. **Hidden coupling**: `reattempt_filter.html` and `autongage_formatter.html` share localStorage key `'jejo-ae-batch-export-v1'` — changing one's batch system breaks the other
