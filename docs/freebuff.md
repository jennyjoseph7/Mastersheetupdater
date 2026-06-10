# 🧠 Buffy's Memory File — AutoNage / Mastersheetupdater

> This is my personal diary. When I read this file at the start of a session, I instantly
> understand the project's soul — what it does, how it's built, what's been fixed, and
> what patterns to follow. Update this every time I make changes.

---

## 📋 Project Identity

- **Name**: AutoNage (repo: `Mastersheetupdater`)
- **What it does**: Browser-based automotive lead operations automation tools. Takes AutoEngage exports → processes them → outputs Zoho Master Sheet-ready data.
- **Users**: Business Analysts (BAs) at a car dealership group. They upload Excel files, click buttons, download results.
- **No backend required**: Every tool is a self-contained HTML file that runs in the browser.

---

## 🏗️ Architecture

### File Structure

```
/ (root)                      ← Served as static site
├── index.html                ← Landing page / tool catalog
├── config.js                 ← API keys & settings (gitignored!)
├── config.example.js         ← Template for config
│
├── pages/                    ← Each tool = one self-contained HTML file
│   ├── disposition_sync_v2.html  ← PRE-SALES SYNC (most complex, 3000+ lines)
│   ├── post_sales_disposition.html ← POST-SALES SYNC
│   ├── recording_renamer.html     ← RECORDING RENAMER
│   ├── autongage_formatter.html   ← AUTOENGAGE FORMATTER
│   ├── call_analysis_summary.html ← CALL SUMMARY
│   ├── reattempt_filter.html      ← RE-ATTEMPT FILTER
│   └── dashboard.html             ← CAMPAIGN DASHBOARD
│
├── assets/
│   ├── lib/
│   │   ├── ai-config.js           ← Shared AI config (endpoints, keys, sanitizer) — RECENTLY ADDED
│   │   ├── ai-validator.js        ← Shared AI validation pipeline — PROPOSED
│   │   ├── batch-export.js        ← Shared batch export with unique prefix isolation — RECENTLY ADDED
│   │   ├── data-pipeline.js       ← Shared data parsing (parseSheet, cellToString, normalizePhone) — PROPOSED
│   │   ├── date-utils.js          ← Shared date parsing (detectDateFormat, parseExcelSerial) — PROPOSED
│   │   ├── excel-safe.js          ← Formula injection protection — RECENTLY ADDED
│   │   ├── history-helpers.js     ← Session history parsing utils
│   │   ├── llm-batch-runner.js    ← Shared AI batch processor (CRITICAL!)
│   │   ├── theme.js               ← Shared theme toggle — RECENTLY EXTRACTED
│   │   ├── xlsx.full.min.js       ← SheetJS (Excel parsing)
│   │   ├── jszip.min.js           ← ZIP compression
│   │   ├── html2canvas.min.js     ← Screenshots
│   │   └── jspdf.umd.min.js      ← PDF generation
│   ├── styles/                    ← CSS per tool (8 files, plus shared css/design-system.css)
│   ├── scripts/
│   │   └── index.js               ← Theme toggle logic (index.html only)
│   ├── fonts/                     ← Self-hosted Inter, Manrope, IBM Plex Mono
│   └── images/                    ← Logos
│
├── worker/
│   └── worker.js                  ← Cloudflare Worker proxy (production)
├── server/
│   ├── proxy.js                   ← Local Node.js proxy (development)
│   └── package.json
│
├── docs/
│   ├── AN_format.md               ← AutoEngage format reference
│   └── disposition.md             ← Disposition definitions
│
└── docs/freebuff.md                    ← THIS FILE — my memory
```

### Data Flow (Pre-Sales Sync, the main tool)

1. BA uploads AutoEngage exports (Excel files) via browser
2. SheetJS (xlsx.full.min.js) reads the Excel data
3. JS processes/merges the data into a table
4. BA can click "Validate with AI" → sends batches to:
   - **Cloudflare Worker** (production) OR **Local Node.js proxy** (dev) → NVIDIA API
   - OR directly to OpenRouter API (fallback)
5. AI corrects dispositions, identifies themes, etc.
6. BA downloads the final Excel file

---

## ⚙️ AI Pipeline (llm-batch-runner.js)

This is the heart of the AI validation. Key behavior:

- **Batches items** into configurable groups (e.g., 12 per request)
- **Runs concurrent workers** (up to `maxConcurrent`)
- **Adaptive throttling**: starts with `minGapMs` gap, backs off on 429s, recovers after 5 successes
- **Retries with split**: if a batch fails all retries, splits it in half and retries halves
- **Returns ordered results** as `Map<rowIndex, result>`

### Where config lives

All batch settings are in `config.js`:

```js
// Dashboard/themes (shorter prompts)
llmBatchSize: 12,
llmMaxConcurrent: 5,
llmRequestTimeoutMs: 120000,
llmPromptCharLimit: 1200,

// Disposition validation (longer transcripts)
llmDispositionBatchSize: 1,
llmDispositionMaxConcurrent: 5,
llmDispositionTimeoutMs: 90000,
llmDispositionPromptCharLimit: 2500,
```

### API Endpoint Resolution

The code determines endpoint dynamically:
1. `window.getApiEndpoint()` if defined
2. Falls back to `NVIDIA_ENDPOINT`
3. Uses `X-Handshake-Token` header for proxies
4. Direct NVIDIA/OpenRouter endpoints get Bearer auth

---

## 🔧 Common Bugs & Fixes Log

### 1. Syntax Errors in HTML/JS Mix (disposition_sync_v2.html)

- **Problem**: `} else { {` — extra brace after `else` creates a syntax error
- **Fix**: Remove the duplicate `{`
- **Pattern**: This file has 3000+ lines of inline JS. Brace matching is tricky. Always check for `} else { {` patterns.

### 2. Cache Persistence Bug

- **Problem**: Cache block was placed outside the if-else scope, causing localStorage writes even when nothing changed
- **Fix**: Moved cache write inside the correct code path (where corrections are actually applied)
- **Pattern**: Always check scope braces when dealing with localStorage cache writes

### 3. CORS Errors on Deployment

- **Problem**: API calls blocked by CORS when tools are served from CloudFront
- **Solution**: Deploy config.js to GitHub Pages or use Cloudflare Worker as proxy
- **Pattern**: The proxy adds CORS headers; direct NVIDIA API only works without CORS for same-origin

### 4. Performance Tuning Loop

- Workers count has been iterated many times: 2→5→2 workers
- Batch sizes: 15→10→2→1 (for disposition), 12 (for dashboard)
- Timeout: 90s→120s→90s
- **Lesson**: Free API endpoints need conservative settings (batchSize=1, concurrency=2-5, timeout=90-120s)

### 5. Temp Files Cleaned (June 8, 2026)

- Removed 9 temp/scratch files: `_extract_ai_config.py`, `_extract_remaining.py`, `_extract_theme.py`, `_extract_theme2.py`, `_fix_nvidia.py`, `_split_pages.py`, `_syntax_check_ai.js`, `_temp_check.js`, `nul`

### 6. "Unexpected token 'catch'" in dashboard.html (June 8, 2026)

- **Problem**: `SyntaxError: Unexpected token 'catch'` at `dashboard.html:4004`
- **Root Cause**: In `mineCustomerThemes()` function, an `else {` block at line 3858 was never closed with `}`. The `}` before `catch(e) {` was closing the `else` block instead of the `try` block, leaving the `try` unmatched.
- **Fix**: Added `        }` (8-space indent) right before the existing `       } catch(e) {` line to properly close the `else` block first.
- **Brace flow after fix**: `else { ... }` → `try { ... }` → `catch(e) { ... }`
- **Pattern**: When you see "Unexpected token 'catch'", it's often not about the catch itself — look for an unclosed block (if/else/for/forEach) earlier in the function that's "stealing" the `}` meant for the `try`.
- **Verification**: Always run `node -e 'new Function(code)'` to syntax-check inline JS in HTML files.

### 7. Critical Security Fixes — Code Review Batch (June 8, 2026)

**Summary**: Thorough security review found formula injection (CSV/TSV), XSS via innerHTML, unbounded fetches, and permissive CORS across 8+ files. All critical items fixed.

#### 7a. Excel/CSV/TSV Formula Injection — 5 pages fixed
- **Risk**: Values starting with `=`, `+`, `-`, `@` pasted into Excel/Sheets execute formulas
- **Fix**: Created `assets/js/lib/excel-safe.js` with `excelSafe()`, `excelSafeCsvCell()`, `excelSafeTsvCell()` — prefixes dangerous cells with `'`
- **Pages fixed**: `reattempt_filter.html` (CSV + TSV), `autongage_formatter.html` (CSV), `recording_renamer.html` (CSV), `post_sales_disposition.html` (TSV), `disposition_sync_v2.html` (TSV)

#### 7b. Dashboard XSS — LLM output injection
- **Risk**: `generateExecutiveNarrative()` set via `innerHTML` with unescaped LLM-derived values (`t.label`, `explanation`, `interpretation`)
- **Fix**: Wrapped all 3 dynamic LLM values in `esc()` before HTML string concatenation

#### 7c. Recording Renamer — unbounded fetch/DoS
- **Risk**: Downloaded arbitrary recording URLs with no size/volume limits
- **Fix**: Added `RECORDING_MAX_COUNT=100`, `RECORDING_MAX_BYTES_PER_FILE=50MB`, `RECORDING_MAX_TOTAL_BYTES=500MB` — enforced via slice + Content-Length check + total budget

#### 7d. Proxy CORS + Body Limits
- **worker/worker.js**: Added 1MB body size limit (checked via Content-Length before read), documented CORS origin restriction
- **server/proxy.js**: Made CORS origin configurable via `CORS_ORIGIN` env var, added streaming body reader with 1MB max

#### Verification
- Syntax checked all 6 modified HTML pages — **ALL CLEAN**
- Proxy files validated manually

---

### 8. Architecture Review Deepening (June 8, 2026)

Ran `@improve-codebase-architecture` skill. Generated HTML report at:
`C:\Users\sethr\AppData\Local\Temp\architecture-review-2026-06-08-v2.html`

**12 deepening candidates identified:**

| # | Candidate | Strength | Effort | Lines Saved |
|---|-----------|----------|--------|-------------|
| 1 | Shared Data Pipeline | Strong | Medium | ~1,500 |
| 2 | Unify AI Validation | Strong | Medium | ~400 |
| 3 | Shared Navigation | Strong | Low | ~1,600 |
| 4 | Shared Date Utils | Worth Exploring | Low | ~200 |
| 5 | Dashboard AI → Shared Runner | Strong | Low | ~60 |
| 6 | Remove Dead config.js | Strong | Trivial | 1 |
| 7 | Global Namespace Cleanup | Worth Exploring | Large | 0 |
| 8 | CSS Design System | Worth Exploring | Medium | ✅ Created assets/css/design-system.css — shared theme vars, reset, header/nav, theme-toggle, status-msg, drop-zone, btn-generate, ai-status-bar, processing-overlay. Added to all 7 tool pages. Stripped dupes from per-page CSS. |
| 9 | Fix Script Load Order | Strong | Trivial | 1 |
| 10 | Standardize API Key ID | Strong | Trivial | 0 |
| 11 | Guide Overlay Module | Speculative | Medium | ~180 |
| 12 | Batch Export Migration | Worth Exploring | Low | ~20 |

### 8. Architecture Refactoring — Phase 1–3 Complete (June 8, 2026)

Ran `@improve-codebase-architecture` skill. Generated report then implemented changes in phases.

**Phases completed:**

| Phase | Candidates | Status | Change |
|-------|-----------|--------|--------|
| 1 | #6, #9 | ✅ Done | Removed dead `config.js` from call_analysis_summary; fixed config.js load order in post_sales_disposition |
| 2 | #1, #4 | ✅ Done | Created `data-pipeline.js` + `date-utils.js`; removed ~500 lines of duplicated inline functions across 5+ pages |
| 3 | #3 | ✅ Done | Created `nav.html` with fetch injection; replaced ~1,400 lines of duplicate nav markup across 7 pages |
| 4 | #2, #5 | ✅ Done | Created `ai-validator.js` (~244 lines) with StatusBar manager, `buildHeaders()`, `isRetryableStatus()`. All 3 AI pages now use shared module: disposition_sync_v2.js (fully), post_sales_disposition.js (fully), dashboard.js (buildHeaders + signal). Removed 5 duplicated functions from dashboard.js. |
| 5 | #10, #12 | ✅ Done | Standardized API key input ID to `openRouterApiKey` across all 3 AI pages (post_sales used different `nvidiaApiKeyInput`). Added one-time cleanup of old shared batch-export localStorage key `jejo-ae-batch-export-v1` in batch-export.js. |

**Key metrics:**
- `nav.html` created at project root with 7 tool links + auto-activation JS
- 7 pages now load nav via `fetch('../nav.html')` — 1 source of truth
- Shared libs now: `theme.js`, `ai-config.js`, `data-pipeline.js`, `date-utils.js`, `excel-safe.js`, `batch-export.js`, `history-helpers.js`, `llm-batch-runner.js`

---

## 🎯 Tool-Specific Details

### disposition_sync_v2.html (Pre-Sales Sync)

- **Most complex file** in the project (~3000+ lines)
- Merges AutoEngage "Audience & Leads" + "Sessions" exports
- AI validates dispositions against session transcripts
- Has session history parsing (uses history-helpers.js)
- Content-First Scoring System was recently added for session selection
- Has a buggy block in the cache section that was recently cleaned up

### dashboard.html (Campaign Dashboard)

- Generates visual KPIs and charts
- AI theme extraction from call data
- Uses `llmThemeBatchSize: 5` for theme processing
- Uses `llm-batch-runner.js` for batched AI calls
- PDF export via html2canvas + jspdf
- Has own `DISPO_TO_THEME` mapping (40+ dispositions → 9 themes)
- ~3000+ lines (HTML + inline JS + CSS split into separate file)
- Own custom AI pipeline partially duplicates llm-batch-runner.js

### Dashboard UI Improvements (via @frontend-design skill — June 8, 2026)

Applied the `anthropics/skills@frontend-design` (513.5K installs) skill to enhance the dashboard UI:

**Atmosphere & Depth:**
- Added SVG noise grain texture overlay (2.5% opacity) for tactile richness
- Header ambient glow with radial gradient + accent underline sweep
- Empty state has a breathing pulse animation

**Motion & Micro-interactions:**
- `slideUp` animation reworked with `cubic-bezier(0.16, 1, 0.3, 1)` easing + blur reveal
- Button shine sweep effect (`btn-generate::after` slides across on hover)
- Chart bars expand on hover (column flex + bar scaleY)
- All row hover effects translate right with accent color shifts (hbar, disp, src, blk rows)
- KPI pulse-glow animation on adjusted-value cards
- Data panels + insight panels show accent sweep line on hover

**Visual Polish:**
- Card hover states include `box-shadow` accent border glow
- Chart bar labels highlight in accent color on hover
- Voice cards get gradient overlay on hover
- `drag-over` state for drop zone with scale + glow feedback
- Removed unused `shimmer` and `slideInRight` animations

**File changed**: `assets/css/dashboard.css` (~+200 lines of enhancements)
**Skill used**: `@frontend-design` (anthropics/skills)

### recording_renamer.html

- Downloads call recordings via CORS proxy
- Renames and zips them with campaign metadata
- Needs `corsProxyUrl` configured in config.js

### post_sales_disposition.html

- Service campaign sync and validation
- Handles dealership-wise service reminders and feedback reminders
- Similar AI validation pipeline as pre-sales
- ⚠️ config.js loaded LAST — different from all other pages (fix planned)

### call_analysis_summary.html

- Generates KPI summary from processed sync export
- ⚠️ Loads config.js but uses NO AI — dead code (fix planned)
- Has its own inline date formatting logic duplicated from other pages (fix planned)

### reattempt_filter.html / autongage_formatter.html

- Both use BatchExporter class (assets/js/lib/batch-export.js) with unique prefixes
- Previously shared localStorage key 'jejo-ae-batch-export-v1' — now fixed
- reattempt_filter: 100 leads per batch CSV
- autongage_formatter: 9 templates for various dealerships

---

## 🚀 Deployment

- **Production**: CloudFront (S3) or any static host
- **Config**: `config.js` must be deployed separately (gitignored)
- **Cloudflare Worker**: Deploy `worker/worker.js` with env vars:
  - `NVIDIA_API_KEY` — the API key
  - `HANDSHAKE_TOKEN` — secret token for frontend auth
- **Local Dev**: `cd server && npm start` (runs on port 3456, needs `.env` file)

### Security Headers Required
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
```

---

## 📝 Conventions I Must Follow

1. **Never assume libraries exist** — check imports in each file. All JS libs are `<script>` loaded in the HTML.
2. **Vanilla JS everywhere** — no frameworks, no build step. Just raw ES6+.
3. **config.js is gitignored** — never commit API keys. Only edit config.example.js.
4. **Self-contained HTML** — each page in `pages/` includes all its own JS/CSS inline. Shared code is in `assets/js/lib/`.
5. **Brace matching in HTML** — inline JS inside HTML files can hide brace errors. Always double-check `{}` balance.
6. **Theme system** — uses `data-theme` attribute on `<html>`, stores in `localStorage('jejo-theme')`.
7. **Theme functions are shared** — `assets/js/lib/theme.js` contains `getStoredTheme()`, `syncBrandLogo()`, `applyTheme()`, `toggleTheme()`. All 7 pages + index.html load it. The inline blocking `<script>` (IIFE that sets `data-theme` before render) stays in each page for FOUC prevention.
8. **Event handlers** — all use `onclick=` attributes, not addEventListener (legacy pattern).
9. **Path references** — pages in `pages/` reference assets as `../assets/...`.
10. **New shared libs**: extract duplicated functions into `assets/js/lib/` with IIFE pattern, not modules. Add `<script>` tag to each page that needs it.

### 🎯 Multi-Agent Workflow — THE HARD RITUAL (CRITICAL!)

**Every single task starts with this ritual. No exceptions.**

#### Phase 1: Read Memory First (⚡ read_files in parallel)
Before touching ANY code, use `read_files` directly on the known memory files:
- `docs/freebuff.md` — my personal diary (bugs, patterns, conventions)
- `docs/architecture.md` — full architecture map (function connections, data flow)
- Any other relevant .md docs in `docs/`

Then spawn 2-3 `file-pickers` in parallel to FIND other relevant files for the task.

This gives me instant context on what the project is, how it works, and what to watch out for.

#### Phase 2: Spawn a Swarm of Agents
**NEVER do everything in one agent. Spawn 3-5 agents in parallel** to:

| Agent Type | When to Use | How Many |
|------------|-------------|----------|
| `file-picker` | Find relevant files for the task | 2-3 in parallel |
| `code-searcher` | Search for specific patterns across codebase | 2-3 in parallel |
| `researcher-web` | Research APIs, libraries, docs | 1-2 |
| `researcher-docs` | Read framework/library documentation | 1 |
| `basher` | Run terminal commands | As needed (sequentially if dependent) |
| `code-reviewer-deepseek-flash` | Review ALL changes after implementation | Always |

#### Phase 3: Orchestrate
1. **Write todos first** — break the work into clear, independent steps using `write_todos`
2. **Read all relevant files** using `read_files` after agents find them
3. **Implement** using `str_replace` or `write_file`
4. **Validate** — run syntax checks, tests, typechecks in parallel
5. **Review** — spawn `code-reviewer-deepseek-flash` for final review

#### Why This Ritual
- **Memory first** — prevents repeating mistakes, respects project conventions
- **Swarms are fast** — 5 agents in parallel = 5x the context in the same time
- **Focused agents** — each agent handles ONE concern, not everything
- **I orchestrate** — I stay as the coordinator, synthesizing outputs

**TL;DR: Read .md files first → spawn 3-5 agents in parallel → write todos → implement → validate → review.**

---

## 🔄 Recent Git History Summary

| Commit | Change |
|--------|--------|
| Architecture review & deepening | Identified 12 candidates, report generated |
| Cleaned temp files | Removed 9 temp/scratch files from root |
| fixed bugs 67 | Latest bug fixes in disposition sync |
| Session Selection — Content-First Scoring System | New scoring algorithm for sessions |
| fixed bugs 66, 65 | More bug fixes |
| Multiple performance tuning commits | Workers 2→5→2, batchSize 10→2→1, timeout 90s→120s→90s |
| Status bar clarity | Show batch count, worker throttle controls |
| Scale disposition AI | Batch size 15→10→5→1 for reliability |

---

## 🧩 Installed Agent Skills

As of June 8, 2026, the following agent skills are installed:

| Skill | Source | Installs | Purpose |
|-------|--------|----------|---------|
| `@frontend-design` | `anthropics/skills` | 513.5K | Frontend UI design guidelines & polish |
| `@xlsx` | `anthropics/skills` | 104.1K | Excel/CSV processing best practices |
| `@improve-codebase-architecture` | `mattpocock/skills` | 223.3K | Code architecture analysis |
| `@webapp-testing` | `anthropics/skills` | 90.5K | Web app testing |
| `@error-handling` | `affaan-m/everything-claude-code` | 1.2K | Error handling patterns: no silent swallowing, typed errors, retry with backoff, user-facing messages |

**Install commands** (if needed in new env):
```bash
npx skills add anthropics/skills@frontend-design -g -y
npx skills add anthropics/skills@xlsx -g -y
npx skills add mattpocock/skills@improve-codebase-architecture -g -y
npx skills add anthropics/skills@webapp-testing -g -y
npx skills add affaan-m/everything-claude-code@error-handling -g -y
```

**Security**: All passed as Safe/Low Risk.
**Note**: PromptScript does not support global skill installation — this is expected.

---

## 🪲 Error Handling Conventions

Installed `affaan-m/everything-claude-code@error-handling` on June 8, 2026.

### Hard Rules (from the skill)

1. **Never swallow errors silently** — every `catch` block must either handle, re-throw, or log
2. **Fail fast and loudly** — surface errors at the boundary where they occur
3. **User messages ≠ developer messages** — show friendly text to users, log full context server-side
4. **Errors are part of your API contract** — in this project, that means user-facing status messages like `setStatus('...', 'err')`

### Current State After Catch Cleanup (June 8, 2026)

**What was fixed**: 11 silent `catch(e) {}` blocks across 4 files:

| Pattern | Files Fixed | Fix Applied |
|---------|-------------|-------------|
| `catch(e) {}` (empty) | `post_sales_disposition.html`, `dashboard.html` | Added `console.warn("...", e)` |
| `catch(e) { /* quota */ }` (commented) | `reattempt_filter.html`, `autongage_formatter.html` | Replaced comment with `console.warn(...)` |
| `catch(e) { cached = null; }` (no context) | `post_sales_disposition.html` | Added `console.warn("Cache parse failed, clearing:", e)` |
| `catch(e) { return {}; }` (JSON.parse) | `reattempt_filter.html`, `autongage_formatter.html` | Added `console.warn("JSON.parse failed, returning empty:", e)` |

**What remains**: Some catch blocks already had good patterns — `dashboard.html` shows user-facing notices on LLM failure (`showAiNotice(...)`) and `recording_renamer.html` uses `setStatus('Error: ...', 'err')`. These patterns should be followed for new code.

### Future Pattern to Follow

```javascript
// ❌ BAD — silent swallow
try { ... } catch(e) {}

// ✅ GOOD — log with context
try { ... } catch(e) { console.warn("Operation failed:", e); }

// ✅ BETTER — log + user-facing feedback
try { ... } catch(e) {
  console.error("Operation failed:", e);
  showAiNotice("Something went wrong. Check console for details.", true);
}

// ✅ BEST — graceful degradation (dashboard's LLM pattern)
try { ... } catch(e) {
  console.warn('LLM failed, falling back to keywords:', e);
  showAiNotice('AI classification failed. Using local keyword analysis.', true);
}
```

---

## 💡 Things That Took Me a While To Learn

1. **The proxy handshake token**: `X-Handshake-Token` header is checked server-side. Both `config.js` and the proxy/server env must match.
2. **llm-batch-runner.js's split-on-failure**: When a batch fails all retries, it splits in half. This is smart but means sometimes you get partial results.
3. **The `getApiEndpoint()` and `getApiKey()` functions** are defined per-page (in each HTML file) and override the defaults in llm-batch-runner.js. Always check the page for these before assuming the endpoint.
4. **History parsing** uses both `__raw` fallback and key-name detection (`history`, `session_history`, `transcript`, etc.). The `__raw` fallback is for when column names don't match known patterns.
5. **Dashboard's AI pipeline** has its own `fetchLlmCompletion()` and retry logic that partially duplicates `llm-batch-runner.js`. Planned to be migrated to the shared runner.
6. **Script load order matters** — `post_sales_disposition.html` loads config.js LAST while all other pages load it FIRST. This can cause silent config-read failures (fix planned).
7. **call_analysis_summary.html** loads config.js but never uses it — dead code that exposes API keys unnecessarily (fix planned).
8. **Temp files** accumulate in the project root from development scripts — clean them before committing.