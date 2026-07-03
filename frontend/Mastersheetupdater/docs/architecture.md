# AutoNage Architecture — Complete Project Brain

> **Purpose**: The single source of truth for this project. Every file, function,
> dependency, data flow, config, and migration plan is documented here.
> Read this BEFORE making any change.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Quick Start](#2-quick-start)
3. [Directory Tree](#3-directory-tree)
4. [File Inventory & Role Map](#4-file-inventory--role-map)
5. [Script Load Order (CRITICAL)](#5-script-load-order-critical)
6. [Authentication System](#6-authentication-system)
7. [Data Flow Diagrams](#7-data-flow-diagrams)
8. [Complete Function Inventory — By File](#8-complete-function-inventory--by-file)
9. [CSS Architecture](#9-css-architecture)
10. [Storage Schema](#10-storage-schema)
11. [API Contract Reference](#11-api-contract-reference)
12. [Security Model](#12-security-model)
13. [Error Handling Patterns](#13-error-handling-patterns)
14. [Known Bugs & Gotchas](#14-known-bugs--gotchas)
15. [Danger Zones — Change Ripple Effects](#15-danger-zones--change-ripple-effects)
16. [Configuration Reference](#16-configuration-reference)
17. [Deployment Guide](#17-deployment-guide)
18. [Next.js Migration Blueprint](#18-nextjs-migration-blueprint)

---

## 1. Project Overview

**AutoNage** is a browser-based tool suite for automotive lead operations.
It processes AutoEngage and Zoho CRM exports, performing data merging,
disposition classification, AI-powered validation, and batch export.

### Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Vanilla HTML + CSS + JS | 10 HTML pages, all client-side |
| Styling | CSS custom properties + per-file theme tokens | NO preprocessor, NO Tailwind |
| Data Parsing | SheetJS (`xlsx`) | NPM / vendored copy |
| AI / LLM | Gryd AI backend (Gemini-based) | Proxied via Cloudflare Worker or local Node.js proxy |
| ZIP | JSZip | Vendored copy |
| PDF | html2canvas + jsPDF | Vendored copy |
| Auth | gryd login API | sessionStorage + localStorage |
| Server | Cloudflare Worker (prod) / Node.js (dev) | Proxy only — no backend logic |

### What the tools do

| Tool | Input | Output |
|------|-------|--------|
| Pre-Sales Sync | 2 Excel files (Audience & Leads + Sessions) | Merged Zoho Master Sheet-ready table |
| Post-Sales Sync | 2 Excel files (leads + sessions) | Classified dispositions with quality report |
| Dashboard | Zoho export (Excel) | Visual KPIs, charts, AI analysis, PDF |
| Re-Attempt Filter | Multi-day Zoho export (Excel) | Cleaned re-attempt CSV batches |
| AutoEngage Formatter | Client column data | Dealership-specific AutoEngage upload files |
| Recording Renamer | Processed sync file (XLSX) | Renamed recording ZIP |
| Call Analysis Summary | Processed sync export | Daily call analysis summary |
| Campaign Generator | Form input (no file) | Structured 20-field campaign JSON |

### Browser Support

Chrome, Firefox, Edge (latest 2 versions). Safari has partial support.
The `file://` protocol has known sessionStorage isolation issues — requires a local web server.

---

## 2. Quick Start

### Prerequisites

- Node.js >= 18 (for local proxy server)
- npm (comes with Node.js)
- A modern browser (Chrome recommended)

### Setup (Local Dev)

```bash
# 1. Clone and install proxy dependencies
cd server
npm install
cd ..

# 2. Configure secrets
cp config.example.js config.js
# Edit config.js with your gryd signup token

cp server/.env.example server/.env
# Edit server/.env with your NVIDIA API key (if using NVIDIA fallback)

# 3. Start the local proxy server
cd server && npm start
# Proxy runs on http://localhost:3456

# 4. Serve the frontend (use any static server)
# Option A: VS Code Live Server
# Option B: Python
python -m http.server 5500
# Option C: npx
npx serve .
```

Then open `http://localhost:5500` (or whatever port your server uses) in a browser.

### Important: file:// Protocol Warning

The app MUST be served via HTTP (local web server). Opening `index.html` directly
via `file://` causes sessionStorage isolation issues — login state from one page
won't be available on another page. The login page shows a warning if detected.

### Deployment

The frontend is deployed as **static files** (no build step) via Cloudflare Pages
or any static hosting. The Cloudflare Worker at `worker/worker.js` serves as
the production API proxy.

---

## 3. Directory Tree

```
MASTERSHEETUPDATER/
├── index.html                     # Landing page + auth gate
├── login.html                     # Login page (root)
├── nav.html                       # Shared navigation HTML (injected via fetch)
├── config.js                      # GITIGNORED — API keys and settings
├── config.example.js              # Template for config.js
├── package.json                   # Root package (empty — no build)
├── package-lock.json
│
├── pages/                         # All 8 tool pages
│   ├── login.html                 # Login page (for /pages/ sub-path)
│   ├── disposition_sync_v2.html   # Pre-Sales Sync
│   ├── post_sales_disposition.html# Post-Sales Sync
│   ├── dashboardv2.html           # Campaign Dashboard
│   ├── dashboard.html             # Older dashboard version
│   ├── reattempt_filter.html      # Re-Attempt Filter
│   ├── autongage_formatter.html   # AutoEngage Formatter
│   ├── recording_renamer.html     # Recording Renamer
│   ├── call_analysis_summary.html # Call Analysis Summary
│   └── campaign_generator.html    # Campaign Objective Generator
│
├── assets/
│   ├── styles/                    # CSS files
│   │   ├── index.css              # Landing page styles + theme tokens
│   │   ├── login.css              # Login page styles (standalone)
│   │   ├── campaign-generator.css # Campaign gen styles (standalone cyan theme)
│   │   ├── dashboard.css          # Dashboard styles + theme (yellow accent)
│   │   ├── disposition-sync-v2.css# Pre-Sales Sync styles (red accent)
│   │   ├── post-sales-disposition.css # Post-Sales Sync (orange accent)
│   │   ├── reattempt-filter.css   # Re-Attempt Filter (pink accent)
│   │   ├── autongage-formatter.css# Formatter (blue accent)
│   │   ├── recording-renamer.css  # Recording Renamer (green accent)
│   │   └── call-analysis-summary.css # Call Summary (purple accent)
│   │
│   ├── js/
│   │   ├── init.js                # Theme + auth gate (loaded first)
│   │   ├── nav-init.js            # Navigation init helpers
│   │   ├── lib/                   # Shared utility libraries
│   │   │   ├── logger.js          # Structured console logging
│   │   │   ├── theme.js           # Dark/light theme management
│   │   │   ├── data-pipeline.js   # Excel parsing + data normalization
│   │   │   ├── date-utils.js      # Multi-format date parsing
│   │   │   ├── excel-safe.js      # Formula injection protection
│   │   │   ├── batch-export.js    # localStorage-based batch export
│   │   │   ├── ai-config.js       # AI config readers + sanitizer
│   │   │   ├── ai-validator.js    # AI validation pipeline + StatusBar DOM
│   │   │   ├── llm-batch-runner.js# Adaptive LLM batch engine
│   │   │   └── history-helpers.js # Session history parsing
│   │   └── vendor/                # Vendored third-party (DUPLICATE of assets/lib/)
│   │       ├── xlsx.full.min.js
│   │       ├── jszip.min.js
│   │       ├── html2canvas.min.js
│   │       └── jspdf.umd.min.js
│   │
│   ├── lib/                       # LEGACY vendored libs (duplicate)
│   │   ├── xlsx.full.min.js
│   │   ├── jszip.min.js
│   │   ├── html2canvas.min.js
│   │   └── jspdf.umd.min.js
│   │
│   ├── scripts/
│   │   └── index.js               # Landing page theme toggle
│   │
│   ├── images/
│   │   ├── AN.png                 # Brand logo (light theme)
│   │   └── AN Dark.png            # Brand logo (dark theme)
│   │
│   └── fonts/
│       ├── fonts.css              # @font-face definitions
│       ├── Manrope-latin.woff2
│       ├── Manrope-latin-ext.woff2
│       ├── Inter-latin.woff2
│       ├── Inter-latin-ext.woff2
│       ├── Inter-italic-latin.woff2
│       ├── Inter-italic-latin-ext.woff2
│       ├── IBMPlexMono-400-latin.woff2
│       ├── IBMPlexMono-500-latin.woff2
│       ├── IBMPlexMono-600-latin.woff2
│       ├── IBMPlexMono-700-latin.woff2
│       └── ... (latin-ext variants)
│
├── server/                        # Local development proxy
│   ├── package.json               # Node.js proxy deps (zero external deps)
│   ├── proxy.js                   # Node.js HTTP proxy server
│   ├── .env                       # GITIGNORED — proxy secrets
│   └── .env.example               # Template for .env
│
├── worker/
│   └── worker.js                  # Cloudflare Worker (production proxy)
│
├── docs/
│   ├── architecture.md            # THIS FILE — project brain
│   ├── disposition.md             # Disposition classification reference
│   ├── AN_format.md               # AutoEngage format reference
│   └── freebuff.md                # Freebuff documentation
│
├── .gitignore                     # Ignores config.js, .env, .agents/, etc.
├── .nojekyll                      # GitHub Pages config
└── NEXTJS_MIGRATION_PLAN.md       # Migration implementation plan
```

---

## 4. File Inventory & Role Map

### All Files with Dependencies

| # | File | Lines | Role | Depends On | Used By |
|---|------|-------|------|------------|---------|
| 1 | `index.html` | 229 | Landing page + auth gate | config.js, assets/scripts/index.js, assets/styles/index.css, fonts | Login, all 8 tools |
| 2 | `login.html` | 304 | Login page (root path) | config.js, login.css, fonts | Users redirected from index |
| 3 | `pages/login.html` | ~300 | Login page (sub-path) | ../config.js, login.css, fonts | Users redirected from tool pages |
| 4 | `config.js` | 37 | GITIGNORED — config | Nothing | index, login, all AI tools, recording-renamer |
| 5 | `config.example.js` | 26 | Config template | Nothing | Humans copying to config.js |
| 6 | `nav.html` | ~80 | Shared nav links | theme.js (for active state) | All 8 tool pages (via fetch) |
| 7 | `assets/js/init.js` | 56 | Theme + auth gate (blocking) | logger.js | All tool pages (loaded as first script) |
| 8 | `assets/js/nav-init.js` | ~30 | Nav injection helper | init.js | All tool pages |
| 9 | `assets/js/lib/logger.js` | 91 | Structured logging | Nothing | ALL scripts via window.$log |
| 10 | `assets/js/lib/theme.js` | 31 | Theme management | logger.js | All pages (3 have inline duplicates) |
| 11 | `assets/js/lib/data-pipeline.js` | 117 | Data parsing + normalization | XLSX (window.XLSX) | All 7 tool pages |
| 12 | `assets/js/lib/date-utils.js` | ~280 | Multi-format date parsing | Nothing | Pages with date handling |
| 13 | `assets/js/lib/excel-safe.js` | ~50 | Formula injection protection | Nothing | 5 export pages |
| 14 | `assets/js/lib/batch-export.js` | ~120 | localStorage batch export | Nothing | reattempt_filter, autongage_formatter |
| 15 | `assets/js/lib/ai-config.js` | 188 | AI config + sanitizer | config.js (via JEJO_CONFIG) | All 3 AI pages |
| 16 | `assets/js/lib/ai-validator.js` | ~200 | AI validation + StatusBar | ai-config.js | All 3 AI pages |
| 17 | `assets/js/lib/llm-batch-runner.js` | 452 | Adaptive LLM batch engine | ai-config.js | All 3 AI pages |
| 18 | `assets/js/lib/history-helpers.js` | ~150 | Session history parsing | Nothing | disposition_sync_v2, post_sales_disposition |
| 19 | `assets/styles/*.css` (9 files) | 1500-5000 each | Per-tool CSS + duplicated theme tokens | fonts.css | Corresponding tool page |
| 20 | `assets/fonts/fonts.css` | 125 | @font-face definitions | Nothing | ALL HTML pages |
| 21 | `server/proxy.js` | 495 | Local Node.js proxy server | .env file | config.js (apiEndpoint) |
| 22 | `worker/worker.js` | 242 | Cloudflare Worker proxy | Cloudflare env vars | config.js (apiEndpoint) |

### Duplicate Files (Legacy Copies)

| Current Location | Legacy Duplicate | Why Duplicate Exists |
|-----------------|-----------------|---------------------|
| `assets/js/lib/llm-batch-runner.js` | `assets/lib/llm-batch-runner.js` | Path migration — some pages still reference old path |
| `assets/js/lib/history-helpers.js` | `assets/lib/history-helpers.js` | Path migration |
| `assets/js/vendor/xlsx.full.min.js` | `assets/lib/xlsx.full.min.js` | Path migration |
| `assets/js/vendor/jszip.min.js` | `assets/lib/jszip.min.js` | Path migration |
| `assets/js/vendor/html2canvas.min.js` | `assets/lib/html2canvas.min.js` | Path migration |
| `assets/js/vendor/jspdf.umd.min.js` | `assets/lib/jspdf.umd.min.js` | Path migration |
| `login.html` | `pages/login.html` | Two copies for different relative asset paths |

---

## 5. Script Load Order (CRITICAL)

The script loading order is **hardcoded** in each HTML page's `<head>` and
**must be maintained**. Scripts register globals on `window.*` that downstream
scripts depend on.

### Base Load Order (ALL tool pages)

```html
1. <script src="assets/js/lib/logger.js">       — sets window.$log, $warn, $error
2. <script src="assets/js/init.js">              — sets data-theme, checks auth
3. <link rel="stylesheet" href="assets/fonts/fonts.css">
4. <script src="../config.js">                   — sets window.JEJO_CONFIG
5. <script src="assets/js/lib/ai-config.js">     — sets window.getConfigNumber, etc.
6. <script src="assets/js/vendor/xlsx.full.min.js"> — sets window.XLSX
7. <script src="assets/js/lib/history-helpers.js">   — sets window.detectHistory, etc.
8. <script src="assets/js/lib/llm-batch-runner.js">  — sets window.runLlmBatches
9. <link rel="stylesheet" href="assets/styles/[page].css">
```

### Per-Page Script Matrix

| Page | Config | theme.js | ai-config | history-helpers | llm-batch-runner | data-pipeline | date-utils | excel-safe | Extras |
|------|--------|-----------|--------|-----------------|-------------------|--------------|------------|------------|--------|
| disposition_sync_v2 | after xlsx | inline+file | yes | yes | yes | yes | yes | yes | — |
| post_sales_disposition | **LAST** | inline+file | yes | yes | yes | yes | yes | yes | — |
| dashboardv2 | after xlsx | inline+file | yes | no | yes | no | no | no | html2canvas, jspdf |
| recording_renamer | after xlsx | inline+file | no | no | no | yes | yes | yes | jszip |
| call_analysis_summary | after xlsx | inline+file | no | no | no | yes | yes | no | — |
| reattempt_filter | **NOT LOADED** | inline+file | no | no | no | yes | yes | yes | — |
| autongage_formatter | **NOT LOADED** | inline+file | no | no | no | yes | yes | yes | — |
| campaign_generator | **NOT LOADED** | inline only | no | no | no | no | no | no | — |
| login (root) | **FIRST** | inline only | no | no | no | no | no | no | — |
| login (pages/) | **FIRST** | inline only | no | no | no | no | no | no | — |

### Key Anomalies

1. **`post_sales_disposition.html`** loads `config.js` LAST (after all other scripts).
   If any script tries to access `window.JEJO_CONFIG` at parse time, it breaks.
   This is a known bug pattern.

2. **`reattempt_filter.html` & `autongage_formatter.html`** never load `config.js` at all.
   They have no AI functionality, so this is intentional.

3. **`campaign_generator.html`** has ALL its JS logic inline (no external script files at all,
   except nav injection). It's self-contained.

4. **`login.html` & `pages/login.html`** load `config.js` FIRST (before theme.js, before
   any other script) because login needs `grydEndpoint` for the login API call.

5. **Theme FOUC prevention**: Every page has an inline blocking `<script>` as the **very first
   thing** in `<head>` that reads `localStorage` and sets `data-theme` on `<html>`.
   This runs before ANY CSS loads.

### How Nav Injection Works

```html
<!-- In each tool page -->
<div id="navContainer"></div>
<script>loadNavSafe("navContainer");</script>
```

`loadNavSafe()` (defined in `assets/js/nav-init.js`) fetches `../nav.html`,
injects it into the container, and re-attaches click handlers. The nav.html
contains 8 links with SVG icons and auto-activation logic based on `window.location.pathname`.

---

## 6. Authentication System

### Architecture

```
User → index.html → check gryd_token + gryd_expiry in sessionStorage
   ├── Valid? → Show tool catalog
   └── Missing/expired? → redirect → login.html

login.html → User submits credentials → POST to /gryd/login
   ├── Success? → Store token in sessionStorage + localStorage → redirect to index.html
   └── Failure? → Show error message
```

### Login Request

```http
POST <GRYD_ENDPOINT>/gryd/login
Headers:
  Content-Type: application/json
  X-GRYD-ENTERPRISE-ID: autocrm
  X-GRYD-SIGNUP-TOKEN: <from config.js>

Body:
{
  "user_id": "user@example.com",
  "password": "********",
  "role": "human_agent",
  "attribute": "email",
  "application_id": "autocrm"
}
```

### Login Response

```json
{
  "token": "eyJ...",
  "session_id": "sess_...",
  "enterprise_id": "autocrm",
  "user_id": "user@example.com",
  "expiry": 1734567890
}
```

The `expiry` field can be:
- Unix epoch seconds (< 30000000000)
- Milliseconds (> 30000000000 — divided by 1000)
- Duration in seconds (< 31536000 — added to current time)
- ISO date string (parsed via Date.parse)

### Storage Persistence

| Key | Storage | Set By | Used By | Format |
|-----|---------|--------|---------|--------|
| `gryd_token` | sessionStorage + localStorage | login.html | index.html, all pages | JWT string |
| `gryd_session_id` | sessionStorage + localStorage | login.html | AI pages (forwarded as header) | string |
| `gryd_enterprise_id` | sessionStorage + localStorage | login.html | AI pages (forwarded as header) | `"autocrm"` |
| `gryd_user_id` | sessionStorage + localStorage | login.html | Display | string |
| `gryd_expiry` | sessionStorage + localStorage | login.html | Auth checks | Unix epoch seconds |
| `jejo-theme` | localStorage | theme.js | All pages | `"dark"` or `"light"` |
| `jejo-ae-batch-export-{prefix}` | localStorage | BatchExporter | reattempt_filter, formatter | JSON |
| `last_login_redirect_time` | sessionStorage | handleLogin | Redirect loop detection | Unix epoch ms |

### Multi-Tab Sync

Login writes to BOTH `sessionStorage` and `localStorage`. When a page loads and
finds no `sessionStorage` token (new tab), it falls back to `localStorage` and
re-populates `sessionStorage`.

### Redirect Loop Detection

A redirect loop can happen when `sessionStorage` is isolated (file:// protocol
or cross-origin iframes). The login page tracks `last_login_redirect_time` and
if redirected back to login within 3 seconds, it clears session data and shows
a warning.

### Auth Guard Implementation

Two layers:
1. **`assets/js/init.js`** — blocking script in `<head>` that checks auth on every page load
2. **`index.html` inline script** — same check, plus `pageshow` and `visibilitychange` listeners

---

## 7. Data Flow Diagrams

### Pre-Sales Sync (disposition_sync_v2.html) — ~88 functions

```
User Uploads File 1 (Audience & Leads) ─┐
User Uploads File 2 (Sessions) ─────────┘
         ↓
  readFileAsArrayBuffer() → XLSX.read() → parseSheet()
         ↓
  Score files: count columns, detect which is leads vs sessions
         ↓
  mergeData(): join on phone number + date window
    → detectHistory() → formatHistoryForPrompt()
         ↓
  buildQualityReport() → renderQualityReport()
    → quality score per lead (A/B/C/D/F)
         ↓
  renderTable() + renderStats()
    → User reviews merged data
         ↓
  [Optional: AI Validation]
    validateDispositionsWithLLM()
      → runLlmBatches()
        → buildPrompt() → POST /gryd/v1/chat/completions
        → parseResponse() → renderTable()
         ↓
  exportToExcel() or copyData() or copyConvertedData()
```

**Output schemas**: 2 modes — "Master Sheet" (18 fields) and "Converted" (5 fields).

### Post-Sales Sync (post_sales_disposition.html) — ~85 functions

```
User Uploads File 1 ─┐
User Uploads File 2 ─┘
         ↓
  parseSheet() → scoreFileRole() [auto-detect leads vs sessions]
    → heuristic: session columns = history/transcript/conversation_history
         ↓
  evaluateFileRoles() → may swap files if auto-detected wrong
         ↓
  buildSessionMap() ← detectHistory() + formatHistoryForPrompt()
         ↓
  classifyDisposition() for each lead (keyword-based)
    → maps call outcomes to disposition categories
         ↓
  buildQualityReport() → score each lead
         ↓
  renderAll() → Stats + Quality + Table + Preview tables
         ↓
  [Optional: AI Validation] → runLlmBatches()
         ↓
  exportToExcel() or copyData() or copyPreviewRows()
```

**Output schemas**: Mirrors `docs/disposition.md`.

### Dashboard (dashboardv2.html) — ~65 functions

```
User Uploads Zoho Export → parse → normalize
         ↓
  generateDashboard()
    ├── computeKpis()         → 4x2 KPI cards (total leads, connected, etc.)
    ├── computeDailyChart()   → Daily trend bar chart
    ├── computeVehicleModels()→ Vehicle-wise breakdown table
    ├── computePendingFollowups() → Pending items table
    └── computeExecutiveSummary() → Summary text
         ↓
  analyzeConversionFunnel()
  analyzeDispositionPatterns()
  analyzeTrends()
         ↓
  [Optional: AI Analysis]
    runAiAnalysis()
      → classifyWithLlm()   (via runLlmBatches) — disposition themes
      → generateVoiceInsights() (single LLM call) — customer voice quotes
      → renderCustomerVoice() + renderRecommendations()
         ↓
  [Optional: PDF Export]
    html2canvas → capture DOM → jsPDF → download
```

**DISPO_TO_THEME mapping** — maps over 200 disposition strings to 9 themes
(Booking, Info, Follow-up, Lost, etc.). Defined inline in dashboard.html.

### Re-Attempt Filter (reattempt_filter.html) — ~57 functions

```
User Uploads Multi-Day Zoho Export
         ↓
  parseSheet() → normalize → detect columns
         ↓
  Group by Phone Number → getLatestRow() per group
         ↓
  For each phone group:
    ├── Has Terminal disposition? (e.g., "Booked", "Not Interested", "Invalid No")
    │   → EXCLUDE
    ├── Has Connected outcome NOT re-attemptable?
    │   → EXCLUDE (e.g., already re-attempted)
    └── Otherwise
        → INCLUDE in re-attempt list
         ↓
  renderStats() + renderIncludedTable() + renderExcludedTable()
         ↓
  User downloads CSV batches (100 leads per file)
    → BatchExporter.saveProgress() for resume support
```

**Terminal dispositions**: "Booked", "Not Interested", "Invalid Number",
"Switching Off", "Already Own", "Number Busy", "Call Later", "Already Connected",
"Test Drive Done", "Test Drive Booked", "Follow-up", "Callback Later",
"Call Not Picked", "Ringing Not Answered".

### Recording Renamer (recording_renamer.html) — ~46 functions

```
User Uploads Processed Sync File (XLSX)
         ↓
  parseDataFile() → read hyperlinks from cells
    → Detect "Recordings" column with embedded URLs
         ↓
  buildResults() → match phone + date + recording URL
    → Each row: { phone, date, url, status }
         ↓
  processBatch() → for each row with URL:
    ├── buildFetchUrl() → use corsProxyUrl if configured
    └── fetchRecordingWithRetry() → download + rename
         ↓
  renderResults() → show progress table per row
         ↓
  downloadZip() → JSZip → ZIP all recordings with metadata filenames
```

**Security limits**: MAX 100 recordings, 50MB per file, 500MB total.

### Campaign Generator (campaign_generator.html) — ~26 functions

```
User Selects Campaign Family (tabs):
  ├── presales_voice (Test Drive Booking)
  │   └── Sub-types: TDB Outbound, Follow-up, Re-engagement
  ├── service_voice (Service Reminder)
  │   └── Sub-types: Due, Overdue, Feedback
  └── whatsapp (WhatsApp Template)
      └── Sub-types: Promotional, Service Reminder, Feedback
         ↓
  User fills form fields:
    ├── Basic Info (campaign_name, dealer_name, etc.)
    ├── Who/Why (target_audience, campaign_goal, etc.)
    ├── Conversation Flow (conversation_objective, script_sections, etc.)
    └── Guardrails (disallowed_topics, escalation_rules, etc.)
         ↓
  Auto-generated fields update in real-time:
    ├── UUID (camelCase UUID v4)
    ├── search_term (generated from family + sub-type)
    ├── doc_data (JSON with metadata)
    └── stats (field count, filled count, percentage)
         ↓
  buildCampaignObjective() → assembles 20-field structured JSON
         ↓
  Preview JSON syntax-highlighted in real-time
         ↓
  User downloads .json or copies to clipboard
```

---

## 8. Complete Function Inventory — By File

### 8.1 index.html — Landing Page (~5 functions)

| Function | Lines | Purpose |
|----------|-------|---------|
| Theme IIFE | 1-5 | Sets `data-theme` before render |
| `requireAuth()` | inline | Checks token, redirects to login |
| `logAuthEvent()` | inline | Debug logging to localStorage |
| `visibilitychange` handler | inline | Re-check auth on tab focus |
| `pageshow` handler | inline | Re-check auth on bfcache restore |

**Inline scripts**: auth gate + theme FOUC prevention.
**Connected to**: All 8 tool pages via `<a>` tags + login redirect.

### 8.2 login.html / pages/login.html — Login Pages (~16 functions)

Duplicated identically in both files (same code, different relative paths):

| Function | Purpose | Called By |
|----------|---------|-----------|
| `syncBrandLogo(t)` | Logo swap between dark/light | Init / toggleTheme |
| `applyTheme(t)` | Set data-theme, localStorage, logo | Init / toggleTheme |
| `toggleTheme()` | Dark/light toggle | onclick on theme-toggle button |
| `togglePassword()` | Show/hide password | onclick on eye icon |
| `showError(msg)` | Show error message, auto-dismiss 5s | handleLogin |
| `showWarning(msg)` | Show warning banner | Init, handleLogin |
| `setLoading(loading)` | Button spinner + disabled state | handleLogin |
| `parseExpiry(expiryVal)` | Parse various expiry formats | handleLogin |
| `updateSessionInfo()` | Show "Xh Ym remaining" | Init, handleLogin |
| `checkSession()` | Check for existing valid session | Init |
| `handleLogin(event)` | POST to gryd, store session data | onsubmit on form |
| `handleLogout()` | Clear all gryd keys | onclick |
| `goToDashboard()` | Redirect to index.html | onclick |
| `escapeHtml(str)` | HTML entity encoding | Rendering helpers |

### 8.3 config.js — Global Configuration

**File**: `config.js` (GITIGNORED — not tracked in git)

**Format**:
```js
window.JEJO_CONFIG = {
  grydEndpoint: "https://...",
  grydModel: "gcp-gemini-3.1-flash-lite-preview",
  grydSignupToken: "YXV0b2NybTE3...",
  useGrydLlm: true,
  apiEndpoint: "https://...",
  proxyHandshakeToken: "autonage-2026-...",
  llmBatchSize: 30,
  llmMaxConcurrent: 5,
  llmMaxRetries: 1,
  llmRequestTimeoutMs: 45000,
  llmPromptCharLimit: 1200,
  llmMaxOutputTokens: 1600,
  llmDispositionBatchSize: 25,
  llmDispositionMaxConcurrent: 5,
  llmDispositionTimeoutMs: 60000,
  llmDispositionPromptCharLimit: 2500,
  llmDispositionMaxOutputTokens: 1800,
  corsProxyUrl: ""
};
```

| Property | Type | Purpose | Used By |
|----------|------|---------|---------|
| `grydEndpoint` | string | Gryd AI backend base URL | All AI pages, login, proxy routes |
| `grydModel` | string | Model name | All AI pages |
| `grydSignupToken` | string | Auth token for gryd login | login.html, proxy routes |
| `useGrydLlm` | boolean | Use gryd (always true) | AI pages |
| `apiEndpoint` | string | Proxy URL (Worker or local) | AI pages |
| `proxyHandshakeToken` | string | Auth header for proxy | AI pages |
| `llmBatchSize` | number | Dashboard AI batch size | dashboard |
| `llmMaxConcurrent` | number | Dashboard concurrent requests | dashboard |
| `llmMaxRetries` | number | Max retries per batch | dashboard |
| `llmRequestTimeoutMs` | number | Per-request timeout | dashboard |
| `llmPromptCharLimit` | number | Max prompt characters | dashboard |
| `llmMaxOutputTokens` | number | Max output tokens | dashboard |
| `llmDispositionBatchSize` | number | Disposition batch size | pre/post sales |
| `llmDispositionMaxConcurrent` | number | Disposition concurrent | pre/post sales |
| `llmDispositionTimeoutMs` | number | Disposition timeout | pre/post sales |
| `llmDispositionPromptCharLimit` | number | Max prompt for disposition | pre/post sales |
| `llmDispositionMaxOutputTokens` | number | Max output for disposition | pre/post sales |
| `corsProxyUrl` | string | Recording download proxy | recording_renamer |

### 8.4 nav.html — Shared Navigation

**File**: `nav.html` (~80 lines)

**Links** (in order):
1. Pre-Sales Sync → `pages/disposition_sync_v2.html`
2. Post-Sales Sync → `pages/post_sales_disposition.html`
3. Re-Attempt Filter → `pages/reattempt_filter.html`
4. Dashboard → `pages/dashboardv2.html`
5. Call Summary → `pages/call_analysis_summary.html`
6. Formatter → `pages/autongage_formatter.html`
7. Campaign Gen → `pages/campaign_generator.html`
8. Recording Renamer → `pages/recording_renamer.html`

Each link has an SVG icon + text. Active page gets `class="nav-link active"` + `href="#"`.

### 8.5 assets/js/lib/llm-batch-runner.js — AI Batch Engine (452 lines)

**Exports**: `window.runLlmBatches(opts)`

**Internal Functions**:

| Function | Purpose |
|----------|---------|
| `isRetryableStatus(status)` | True for 408, 409, 425, 429, 500, 502, 503, 504, 523, 524 |
| `isClientError(status)` | 4xx non-retryable — throws immediately |
| `sleep(ms)` | Promise-based setTimeout |
| `jitter(ms)` | Random jitter (75%–125% of ms) |
| `parseRetryAfter(header)` | Parse Retry-After (seconds or HTTP-date) |
| `createThrottleState(initialGap)` | State: `{ gapMs, consecutiveSuccesses, cooldownUntil, initialGap }` |
| `recordSuccess(state)` | After 5 consecutive successes, tighten gap by 70% |
| `recordThrottle(state, retryAfterMs)` | Double gap (cap 5000ms), set cooldown |
| `isProxyEndpoint(endpoint)` | Always true (gryd-only) |
| `getConfiguredModel()` | Reads `window.getLlmModel()` → config → gryd model |
| `sendBatch(batch, batchIndex)` | Core: retry loop → split-on-failure → half-retry |
| `worker()` | Concurrent worker pulling next batch index |

**Configuration**: `MIN_SPLIT_SIZE = 5` — won't split batches smaller than this.

**Behavior**: Each page provides `getApiEndpoint()`, `getApiKey()`, `getLlmModel()`
as inline functions. The same engine behaves differently per page.

**API Format** (NVIDIA-compatible, translated to Gryd by proxy):
```json
POST /gryd/v1/chat/completions
{
  "messages": [
    { "role": "system", "content": "..." },
    { "role": "user", "content": "..." }
  ]
}
```

**Response** (NVIDIA format):
```json
{
  "choices": [{ "message": { "content": "..." } }]
}
```

### 8.6 assets/js/lib/history-helpers.js — Session History Parser (~150 lines)

| Function | Purpose |
|----------|---------|
| `detectHistory(obj)` | Find history column by key name |
| `parseHistoryJson(raw)` | Safely parse JSON string or return array |
| `formatRelativeOffset(firstTs, currentTs)` | `[m:ss]` or `[h:mm:ss]` format |
| `normalizeRoleLabel(role)` | Standardize agent/customer labels |
| `formatHistoryForPrompt(raw)` | Full transcript for LLM prompt |

**Column detection order**: `history`, `session_history`, `transcript`,
`conversation_history`, `chat_history`, `messages` + `__raw` JSON fallback.

### 8.7 assets/js/lib/ai-config.js — Shared AI Config (188 lines)

| Function | Purpose |
|----------|---------|
| `getConfigNumber(key, fallback)` | Read number from `JEJO_CONFIG` |
| `isProxyEndpoint()` | Always returns `true` |
| `hashStr(str)` | Fast non-crypto hash for cache keys |
| `sanitizeForPrompt(text, charLimit)` | Strip control chars, redact injection, truncate |

**Cache**: In-memory `RESPONSE_CACHE` Map used by `runLlmBatches` to avoid re-sending
identical prompts.

### 8.8 assets/js/lib/ai-validator.js — AI Validator (~200 lines)

| Method | Purpose |
|--------|---------|
| `showStatusBar(total)` | Creates DOM status bar, returns AbortSignal |
| `updateStatusBar(done, total, msg, pct, correctedResults)` | Updates progress |
| `hideStatusBar(correctedResults, aborted, rerunFn)` | Final state |
| `dismissStatusBar()` | Quick dismiss |
| `cancel()` | Abort current AbortController |
| `isCancelled()` / `getSignal()` | Abort state |

**Auth helpers**:
| Function | Purpose |
|----------|---------|
| `buildHeaders()` | X-Handshake-Token or Bearer auth |
| `getCachedSessionToken()` | Legacy — no-op |
| `fetchSessionToken(endpoint)` | GET /session — legacy |
| `isRetryableStatus(status)` | Duplicate of same in batch-runner |

### 8.9 assets/js/lib/data-pipeline.js — Data Pipeline (117 lines)

| Function | Purpose |
|----------|---------|
| `cellToString(val)` | Cell value to string, handles scientific notation |
| `normalizePhone(raw)` | Phone to 10-digit, handles 91/0 prefixes |
| `readFileAsArrayBuffer(file)` | File to ArrayBuffer (Promise) |
| `parseSheet(ab)` | XLSX to row objects with `__raw` and `__rowIndex` |
| `esc(value)` / `escapeHtml(value)` | HTML entity encoding |
| `clean(value)` / `lower(value)` | Trim / lowercase |
| `canonicalHeader(h)` / `normalizeHeader(h)` | Header normalization |
| `findCol(row, candidates)` | First non-empty cell from candidates |
| `phoneKey(value)` | Last 10 digits for grouping |
| `isPhoneLike(val)` | Phone pattern check |
| `excelSafe(v)` / `excelSafeCsvCell(v)` / `excelSafeTsvCell(v)` | Formula injection protection |
| `rowsToTsv(rows, keys)` | Rows to tab-separated text |

### 8.10 assets/js/lib/date-utils.js — Date Utilities (~280 lines)

| Function | Purpose |
|----------|---------|
| `detectDateFormat(dateStrings)` | Auto-detect DMY vs MDY |
| `updateDateParserNote()` | UI note for current format |
| `handleDateFormatChange(onFormatChange)` | Read select, update `dateParseOrder` |
| `applyDateFormat(getDateStrings)` | Auto-detect or set `dateParseOrder` |
| `parseExcelSerialDate(value)` | Excel serial number to Date |
| `buildValidatedDate(year, month, day, h, m, s)` | Validated Date constructor |
| `parseDate(value)` | Multi-format date parser |
| `formatDateDisplay(date)` | DD/MM/YYYY |
| `formatDateToken(date)` | "1Jan" style token |
| `formatSerialDate(val)` | Serial to DD/MM/YYYY |

**Date parse order**: Uses `window.dateParseOrder` set by UI toggle (DMY vs MDY).

### 8.11 assets/js/lib/excel-safe.js — Formula Injection Protection (~50 lines)

| Function | Purpose |
|----------|---------|
| `excelSafe(v)` | Prefix `=`, `+`, `-`, `@` with `'` |
| `excelSafeCsvCell(v)` | CSV-safe with quoting |
| `excelSafeTsvCell(v)` | TSV-safe with tab/newline stripping |

### 8.12 assets/js/lib/batch-export.js — Batch Export (~120 lines)

**Class**: `window.BatchExporter`

| Method | Purpose |
|--------|---------|
| `constructor(prefix)` | Sets localStorage key `jejo-ae-batch-export-{prefix}` |
| `createFingerprint(file, rowCount)` | Unique file identity (name + size + rowCount) |
| `readStore()` | Read from localStorage |
| `writeStore(store)` | Write to localStorage (try/catch for quota) |
| `getSavedProgress(fp, templateId, inputRowCount)` | Resume point |
| `saveProgress(fp, templateId, inputRowCount, nextLeadIndex)` | Save point |
| `clearProgressForFingerprint(fp)` | Clear saved progress |

**Migration**: On first constructor call, migrates from old shared key
`jejo-ae-batch-export-v1` to prefix-isolated keys.

**Used by**: reattempt_filter.html (prefix: `'reattempt'`),
autongage_formatter.html (prefix: `'formatter'`).

### 8.13 assets/js/lib/theme.js — Theme Management (31 lines)

| Function | Purpose |
|----------|---------|
| `getStoredTheme()` | Read from localStorage, default `'dark'` |
| `syncBrandLogo(theme)` | Swap `<img>` src between light/dark |
| `applyTheme(theme)` | Set `data-theme`, localStorage, logo |
| `toggleTheme()` | Toggle dark/light |

### 8.14 assets/js/lib/logger.js — Logger (91 lines)

| Function | Purpose |
|----------|---------|
| `$log(tag, msg, data?)` | Tagged console.log |
| `$warn(tag, msg, data?)` | Tagged console.warn |
| `$error(tag, msg, data?)` | Tagged console.error |
| `$start(tag, msg)` | console.group |
| `$end()` | console.groupEnd |
| `$mask(val, type)` | PII-safe masking (phone, email) |

**Tags used**: `App`, `Auth`, `Theme`, `Nav`, `API`, `AI`, `Conf`.
Tags are padded to 5 characters for alignment.

### 8.15 worker/worker.js — Cloudflare Worker (242 lines)

**Env vars**: `NVIDIA_API_KEY`, `HANDSHAKE_TOKEN`, `UPSTREAM_TIMEOUT_MS`

**Routes**:
| Method | Path | Purpose |
|--------|------|---------|
| OPTIONS | `*` | CORS preflight (200 with headers) |
| GET | `/health` | Health check |
| POST | `/gryd/*` | Proxy to gryd backend (30s timeout) |
| POST | `*` | Forward to NVIDIA with Bearer auth |

**Gryd proxy**: Strips Origin header, forwards gryd-specific headers, 30s timeout.
**Security**: Handshake token validation, rate limiting (1000/min per IP), 1MB body limit.

Deployed at: `https://autongagetools.jennyjoseph-k.workers.dev`

### 8.16 server/proxy.js — Local Dev Proxy (495 lines)

**Env vars**: `NVIDIA_API_KEY`, `PORT` (default 3456), `HANDSHAKE_TOKEN`,
`UPSTREAM_TIMEOUT_MS` (default 90000), `ALLOWED_ORIGINS`, `CORS_ORIGIN`

**Routes**:
| Method | Path | Purpose |
|--------|------|---------|
| OPTIONS | `*` | CORS preflight (204) |
| GET | `/health` | Health check |
| GET | `/session` | Create one-time-use session token (5 min TTL) |
| POST | `/gryd/*` | Proxy to gryd backend, strips Origin |
| POST | `/gryd/v1/chat/completions` | Translates NVIDIA-format requests to Gryd format and back |
| POST | `/v1/chat/completions` | Proxy to NVIDIA API |

**Session auth**: `X-Session-Token` header required for NVIDIA proxy. Token via GET /session.
**Rate limiting**: 60 req/min per IP.
**CORS**: Configurable origins, defaults to localhost:5500, 127.0.0.1:5500, localhost:8080.

### 8.17–8.22 Tool Pages

Each tool page has 25–88 inline functions (too many to list individually here).
See [Data Flow Diagrams](#7-data-flow-diagrams) for the functional flow of each tool.

| Tool Page | Lines | Functions | Unique Features |
|-----------|-------|-----------|-----------------|
| disposition_sync_v2 | ~5154 | ~88 | AI validation, dual file merge, quality scoring |
| post_sales_disposition | ~5000 | ~85 | Auto file role detection, keyword classification |
| dashboardv2 | ~3000 | ~65 | KPI cards, bar charts, AI analysis, PDF export |
| recording_renamer | ~2000 | ~46 | Recording download, ZIP creation, retry logic |
| call_analysis_summary | ~2000 | ~58 | KPI tables, date format detection |
| reattempt_filter | ~2000 | ~57 | Phone grouping, batch export with resume |
| autongage_formatter | ~1500 | ~35 | 9 dealership templates, column mapping |
| campaign_generator | ~1500 | ~26 | Tabs, sub-types, JSON preview, stats |

---

## 9. CSS Architecture

### Key Finding: NO Shared Design System File

Each tool page's CSS file contains **its own copy** of the same design tokens.
There is NO `design-system.css` file anywhere in the project. The earlier
documentation reference to it was incorrect.

### Pattern: "Design System Via Duplication"

Every tool CSS file (except index.css, login.css, campaign-generator.css) follows
this pattern:

```css
/* Each tool CSS file starts with: */
:root, [data-theme="dark"] {
  --bg: #0a0a0a;
  --surface: #111111;
  --accent: <per-tool-color>;
  --text: #f5f5f5;
  /* ... ~25 more vars */
}

[data-theme="light"] {
  --bg: #f3f5f8;
  --surface: #ffffff;
  --accent: <per-tool-color-light>;
  /* ... same vars, light values */
}

/* Then: CSS reset (*, html, body) */

/* Then: Header styles */

/* Then: Page-specific component styles */
```

### Theme Tokens (Duplicated in Each Tool CSS)

All tool CSS files share these common variables (exact values vary slightly):

| Variable | Dark | Light | Purpose |
|----------|------|-------|---------|
| `--bg` | #0a0a0a | #f3f5f8 | Page background |
| `--surface` | #111111 | #ffffff | Card/header background |
| `--surface2` | #1a1a1a | #f7f8fa | Secondary surface |
| `--surface3` | #222222 | #eef0f4 | Tertiary surface |
| `--border` | rgba(255,255,255,0.08) | rgba(0,20,50,0.08) | Borders |
| `--accent` | Per-tool | Per-tool lighter | Primary accent |
| `--accent-dim` | Darker accent | Darker accent | Hover/pressed accent |
| `--accent-soft` | rgba(...,0.13) | rgba(...,0.1) | Subtle accent bg |
| `--success` | #63d6a3 / #5ad7a1 | #1a9960 | Success state |
| `--warn` | #ffc857 / #f2c464 | #c89520 | Warning state |
| `--danger` | #ff6b6b / #f16f6f | #d63636 | Danger state |
| `--text` | #f5f5f5 | #1a1e26 | Primary text |
| `--text-dim` | #adaaaa | #4a5568 | Secondary text |
| `--text-muted` | #6b6b6b | #8896a6 | Muted text |
| `--mono` | 'IBM Plex Mono' | same | Monospace font |
| `--sans` | 'Manrope', 'Inter' | same | Sans-serif font |
| `--body` | 'Inter' | same | Body font |
| `--radius` | 12px | 12px | Default border radius |
| `--radius-sm` | 8px | 8px | Small border radius |
| `--radius-lg` | 16px | 16px | Large border radius |

### Per-Tool Accent Colors

| CSS File | Tool | Accent Color (dark) | Light Variation |
|----------|------|--------------------|-----------------|
| index.css | Landing page | `#ef4444` (red) | `#dc2626` |
| login.css | Login | `#eab308` (yellow) | `#ca8a04` |
| disposition-sync-v2.css | Pre-Sales Sync | `#ef4444` (red) | `#dc2626` |
| post-sales-disposition.css | Post-Sales Sync | `#f97316` (orange) | `#ea580c` |
| dashboard.css | Dashboard | `#eab308` (yellow) | `#ca8a04` |
| call-analysis-summary.css | Call Summary | `#a855f7` (purple) | `#7c3aed` |
| reattempt-filter.css | Re-Attempt Filter | `#f472b6` (pink) | `#db2777` |
| recording-renamer.css | Recording Renamer | `#22c55e` (green) | `#16a34a` |
| autongage-formatter.css | Formatter | `#3b82f6` (blue) | `#2563eb` |
| campaign-generator.css | Campaign Gen | `#06b6d4` (cyan) | `#0891b2` |

### Standalone CSS Files (NOT following the pattern)

Three CSS files have their **own completely separate theme systems**:

1. **`index.css`** — 8 accent color pairs for tool cards, gradient backgrounds,
   grid overlay pattern, brand animation. Full custom design.

2. **`login.css`** — Yellow accent, glass card effect, grid background,
   password toggle icon styles. Full custom design.

3. **`campaign-generator.css`** — Cyan accent, family tabs, form grids,
   auto-fields display, JSON syntax highlighting, stats bar, toast notifications.
   Full custom design.

### Shared Components (Duplicated in Each Tool CSS)

These component styles appear in every tool CSS file:

- Header (`header`, `.header-inner`, `.header-left`, `.header-sub`)
- Brand mark (`.brand-mark`, `.brand-mark img`)
- Theme toggle (`.theme-toggle`, `.icon-moon`, `.icon-sun`)
- Navigation (`.nav-container`, `.nav-link`, `.nav-link.active`)
- Status messages (`.status-msg`, `.status-msg.info/warn/success/error`)
- Drop zone (`.drop-zone`, `.dz-icon`, `.dz-text`, `.dz-status`)
- Buttons (`.btn-generate`, `button`, `.btn-secondary`, `.btn-danger`)
- AI status bar (`.ai-status-bar`, `.ai-status-msg`, `.ai-status-badge`)
- Processing overlay (`.processing-overlay`, `.processing-card`, `.spinner`)

### Font Strategy

Self-hosted via `assets/fonts/fonts.css` with `@font-face` declarations:

| Font | Weights | Used For |
|------|---------|----------|
| Inter | 400, 500, 600, 700 | Body text (`--body`) |
| Manrope | 600, 700, 800 | Headings (`--sans`) |
| IBM Plex Mono | 400, 500, 600, 700 | Code/monospace (`--mono`) |

Each font has latin and latin-ext variants for each weight.

---

## 10. Storage Schema

### localStorage Keys

| Key | Set By | Format | Example | Purpose |
|-----|--------|--------|---------|---------|
| `jejo-theme` | theme.js | `"dark"` or `"light"` | `"dark"` | Theme persistence |
| `gryd_token` | login.html | JWT string | `"eyJhbGci..."` | Auth token (synced from session) |
| `gryd_session_id` | login.html | string | `"sess_abc123"` | Gryd session ID (synced) |
| `gryd_enterprise_id` | login.html | string | `"autocrm"` | Enterprise ID (synced) |
| `gryd_user_id` | login.html | string | `"user@example.com"` | User ID (synced) |
| `gryd_expiry` | login.html | Unix epoch seconds | `"1734567890"` | Token expiry (synced) |
| `jejo-ae-batch-export-{prefix}` | BatchExporter | JSON object | `{...}` | Batch export progress |
| `jejo-ae-batch-export-v1` | BatchExporter (legacy) | JSON object | `{...}` | Old shared key (migrated) |

### sessionStorage Keys

| Key | Set By | Format | Example | Purpose |
|-----|--------|--------|---------|---------|
| `gryd_token` | login.html | JWT string | `"eyJhbGci..."` | Auth token (primary) |
| `gryd_session_id` | login.html | string | `"sess_abc123"` | Gryd session ID |
| `gryd_enterprise_id` | login.html | string | `"autocrm"` | Enterprise ID |
| `gryd_user_id` | login.html | string | `"user@example.com"` | User ID |
| `gryd_expiry` | login.html | Unix epoch seconds | `"1734567890"` | Token expiry |
| `last_login_redirect_time` | login.html | Unix epoch ms | `"1734567890123"` | Redirect loop detection |

### auth Debug Log (localStorage)

| Key | Format | Example |
|-----|--------|---------|
| `jejo_auth_log` | Multi-line timestamped log | `[2026-06-24T10:00:00.000Z] index:requireAuth: token=exists` |

### Cache (In-Memory Only)

| Cache | Type | Key | Value |
|-------|------|-----|-------|
| `RESPONSE_CACHE` | `Map<string, string>` | `hashStr(prompt)` | LLM response text |

---

## 11. API Contract Reference

### 11.1 Login

```
POST {grydEndpoint}/gryd/login
```

**Request Headers**:
```http
Content-Type: application/json
X-GRYD-ENTERPRISE-ID: autocrm
X-GRYD-SIGNUP-TOKEN: <from config.js>
```

**Request Body**:
```json
{
  "user_id": "user@example.com",
  "password": "sekret123",
  "role": "human_agent",
  "attribute": "email",
  "application_id": "autocrm"
}
```

**Response (200)**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "session_id": "sess_abc123",
  "enterprise_id": "autocrm",
  "user_id": "user@example.com",
  "expiry": 1734567890
}
```

**Response (4xx)**:
```json
{
  "error": "Invalid credentials",
  "message": "User ID or password is incorrect."
}
```

**Expiry parsing rules**:
| Condition | Treatment | Example |
|-----------|-----------|---------|
| `> 30000000000` | Milliseconds → divide by 1000 | `1734567890123` → `1734567890` |
| `< 31536000` | Duration → `now + value` | `3600` → `now + 3600` |
| Between | Treated as absolute epoch seconds | `1734567890` |
| NaN | Try Date.parse() | `"2026-06-24T10:00:00Z"` |

### 11.2 Gryd LLM Proxy (NVIDIA-Compatible Format)

```
POST {proxyEndpoint}/gryd/v1/chat/completions
```

**Purpose**: The `/gryd/v1/chat/completions` route (in server/proxy.js) translates
NVIDIA-format requests to Gryd format, forwards, and translates back.

**Request** (NVIDIA format — what the frontend sends):
```json
{
  "messages": [
    { "role": "system", "content": "You are an AI assistant..." },
    { "role": "user", "content": "Analyze this data: ..." }
  ]
}
```

**Translation** (what proxy sends to gryd):
```json
POST {grydEndpoint}/gryd/execute/get_llm_response/ai_service
Headers:
  x-gryd-enterprise-id: autocrm
  x-gryd-application-id: autocrm
  x-gryd-token: <from frontend>
  x-gryd-session-id: <from frontend>
  x-gryd-signup-token: <from frontend>
Body:
{
  "kwargs": {
    "user_query": "...user message content...",
    "system_prompt": "...system message content...",
    "model_identifier": "gcp-gemini-3.1-flash-lite-preview"
  }
}
```

**Response** (Gryd → translated to NVIDIA format):
```json
{
  "choices": [
    {
      "message": {
        "content": "Analysis result..."
      }
    }
  ]
}
```

**Timeouts**: 90s default (proxy), 30s (worker).

### 11.3 Gryd Generic Proxy

```
POST {proxyEndpoint}/gryd/{path}
```

Forwards any `/gryd/*` request to the gryd backend. Strips browser `Origin` header.
Forwards gryd-specific headers. Returns upstream status + body directly (no translation).

**Headers forwarded**: `x-gryd-enterprise-id`, `x-gryd-token`, `x-gryd-session-id`,
`x-gryd-signup-token`, `x-gryd-application-id`.

**Timeouts**: 30s (both worker and proxy).
**Body limit**: 1 MB.

### 11.4 Session Endpoint (Local Proxy Only)

```
GET {proxyEndpoint}/session
```

**Purpose**: Creates a one-time-use session token for NVIDIA proxy access.

**Response (200)**:
```json
{
  "token": "a3f8b2c1d4e5...",
  "expiresInMs": 300000,
  "message": "Use this token in X-Session-Token header for POST requests."
}
```

**Response (429)**:
```json
{
  "error": "Too Many Requests",
  "message": "Session limit reached. Try again later."
}
```

### 11.5 Health Check

```
GET {proxyEndpoint}/health
```

**Response**:
```json
{
  "status": "ok",
  "proxy": "autonage-local"
}
```

### 11.6 Frontend AI Call Flow

```
Page JS → runLlmBatches()
  → buildPrompt() → builds array of { system, user } prompt objects
  → sendBatch() → POST {apiEndpoint}/gryd/v1/chat/completions
    → proxy forwards to gryd backend
    → parseResponse() → extracts per-item results
  → onProgress() → updates UI via AiValidator
  → returns { results, correctedCount, failedBatches }
```

Each AI page defines its own:
- `getApiEndpoint()` — reads from `JEJO_CONFIG.apiEndpoint`
- `getApiKey()` — reads `JEJO_CONFIG.proxyHandshakeToken`
- `getLlmModel()` — reads `JEJO_CONFIG.grydModel`
- `buildPrompt(batch)` — page-specific prompt construction
- `parseResponse(text, batch)` — page-specific response parser

### 11.7 Recording Download

```
fetch(fetchUrl, { mode: 'cors' })
```

**Behavior**:
1. If `corsProxyUrl` is set in config, prepend it to the recording URL
2. Otherwise, fetch directly (may fail due to CORS)
3. Retry up to 3 times on failure with 1s delay
4. Stream response to blob
5. Rename file as `{phone}_{date}_{originalName}`

---

## 12. Security Model

### 12.1 Content Security Policy (CSP)

Each HTML page has a meta CSP tag:
```html
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  font-src 'self';
  img-src 'self' data:;
  connect-src 'self'
    https://autobot-webapp-dev.gryd.in
    https://autongagetools.jennyjoseph-k.workers.dev
    http://localhost:3456;
  form-action 'self';
  base-uri 'self';
  object-src 'none';
">
```

**Note**: Uses `unsafe-inline` for both scripts and styles because the codebase
is vanilla HTML+JS with no build step. This is a known limitation.

### 12.2 Formula Injection Protection

All cell values exported from any tool are sanitized via `excelSafe()`:
- Cells starting with `=`, `+`, `-`, `@` get prefixed with `'`
- CSV cells with commas/quotes/newlines are wrapped in double quotes
- TSV cells have tabs/newlines stripped

### 12.3 Auth Token Protection

- Tokens stored in sessionStorage (cleared on tab close)
- Also in localStorage as fallback for multi-tab sync
- Proxy validates handshake token for all AI requests
- Gryd adds enterprise-scoped auth layer
- Session tokens are one-time-use (local proxy) or JWT-based

### 12.4 CORS Protection (Local Proxy)

- Origin header validated against allowed list
- Default: localhost:5500, 127.0.0.1:5500, localhost:8080
- Browser Origin stripped when forwarding to gryd (avoids gryd-side validation issues)

### 12.5 Rate Limiting

- Local proxy: 60 req/min per IP
- Cloudflare Worker: 1000 req/min per IP
- Gryd backend: Unknown (managed by gryd)

### 12.6 Body Size Limits

- Local proxy: 1 MB (checked via Content-Length and actual body)
- Cloudflare Worker: 1 MB

### 12.7 Recording Download Limits

- Max 100 recordings per batch
- Max 50 MB per file
- Max 500 MB total

### 12.8 PII Masking

Logger provides `$mask(val, type)` for safe logging:
- Phone: Shows last 4 digits only (`"******3210"`)
- Email: Shows first char + `***` + domain (`"j***@example.com"`)

---

## 13. Error Handling Patterns

### 13.1 UI Error Display

**Login page**: `showError(msg)` → auto-dismiss after 5s
**Tool pages**: Status messages with classes:
- `.status-msg.info` — blue/neutral
- `.status-msg.warn` — yellow/orange
- `.status-msg.success` — green
- `.status-msg.error` — red

### 13.2 LLM Batch Error Handling

Errors during AI validation follow this hierarchy:
1. **Client errors** (4xx non-retryable): thrown immediately with `nonRetryable` flag
2. **Transient errors** (408, 429, 5xx): retry with exponential backoff + jitter
3. **429 specifically**: double gap, respect Retry-After header, cooldown period
4. **AbortError**: request timeout → retry or split batch
5. **Split-on-failure**: if a batch fails after all retries, split into halves (min 5 items)

### 13.3 File Upload Errors

- Invalid file type → show error message
- Missing required sheets → show error message
- File read failure → show error with details
- Empty data → show warning

### 13.4 Network Error Handling

- All fetch calls wrapped in try/catch
- AI calls show "network error" in status bar
- Login shows "Network error: " + error.message
- Recording download shows per-file failure with retry

### 13.5 localStorage Quota Errors

`BatchExporter.writeStore()` wraps setItem in try/catch to handle quota exceeded.

---

## 14. Known Bugs & Gotchas

### Critical Known Bugs

| Bug | File | Description | Status |
|-----|------|-------------|--------|
| `btnValidateAI` rebound | disposition_sync_v2.html | Click handler bound in 2 places (force=true/false) | Known |
| `btnValidateAI` rebound ×3 | post_sales_disposition.html | Click handler bound in 3 places | Known |
| Config loaded LAST | post_sales_disposition.html | `config.js` loads AFTER all other scripts | Known inconsistency |
| `} else { {` brace pattern | disposition_sync_v2.html | Double brace after else (recently fixed) | Fixed |
| Cache write scoping | disposition_sync_v2.html | Cache write in wrong scope (recently fixed) | Fixed |
| `'nvidia'` label strings | dashboard.html | 3 cosmetic references to 'nvidia' engine label (non-functional) | Known |

### Environment Gotchas

| Issue | Cause | Workaround |
|-------|-------|------------|
| sessionStorage isolation | `file://` protocol | Use local web server |
| Login redirect loop | Cross-origin sessionStorage isolation | Clear browser data, use proper URL |
| CORS errors on AI calls | Wrong proxy URL | Check config.js apiEndpoint |
| Fonts not loading | Wrong MIME types on some servers | Configure .woff2 MIME types |

### Code Smells

1. **Design system duplication**: Every CSS file duplicates the same ~30 theme variables
2. **Global namespace pollution**: ~50+ functions on `window.*`
3. **Duplicate lib files**: `assets/lib/` and `assets/js/lib/` and `assets/js/vendor/`
4. **Duplicate login pages**: `login.html` and `pages/login.html` — identical code
5. **Massive inline scripts**: Tool pages have 1500–5154 lines of inline JS
6. **No error monitoring**: No error tracking or logging beyond console
7. **No tests**: Zero test files in the entire codebase
8. **Mixed path references**: Some pages use old `assets/lib/` path, some use `assets/js/lib/`

---

## 15. Danger Zones — Change Ripple Effects

### If I change `config.js` → affects:
- `dashboard.html` / `dashboardv2.html` (AI config: batchSize, concurrent, timeout, model)
- `disposition_sync_v2.html` (AI config: llmDispositionBatchSize etc.)
- `post_sales_disposition.html` (AI config)
- `recording_renamer.html` (corsProxyUrl)
- `login.html` + `pages/login.html` (grydEndpoint, grydSignupToken)
- `call_analysis_summary.html` (loaded but unused — no effect)
- `worker/worker.js`, `server/proxy.js` (grydEndpoint must match)

### If I change `llm-batch-runner.js` → affects:
- `dashboard.html` / `dashboardv2.html` → `classifyWithLlm()` uses `runLlmBatches()`
- `disposition_sync_v2.html` → `validateDispositionsWithLLM()` uses `runLlmBatches()`
- `post_sales_disposition.html` → `validateDispositionsWithLLM()` uses `runLlmBatches()`

### If I change `history-helpers.js` → affects:
- `disposition_sync_v2.html` → `detectHistory()`, `formatHistoryForPrompt()`
- `post_sales_disposition.html` → `detectHistory()`, `formatHistoryForPrompt()`

### If I change theme functions → affects:
- `assets/js/lib/theme.js` — all 8 main pages
- `login.html`, `pages/login.html`, `pages/campaign_generator.html` — inline duplicates

### If I change `BatchExporter` → affects:
- `reattempt_filter.html` (prefix: `'reattempt'`)
- `autongage_formatter.html` (prefix: `'formatter'`)

### If I change shared CSS → affects:
- **per-tool CSS** changes only that tool
- Changing a variable name in `:root` must be done in ALL 10 CSS files
- The 3 standalone CSS files (index.css, login.css, campaign-generator.css) have independent variables

### If I change `docs/disposition.md` → affects:
- `post_sales_disposition.html` — OUTPUT_SCHEMAS mirror this doc
- `call_analysis_summary.html` — disposition lists
- `dashboard.html` — DISPO_TO_THEME mapping

### If I change `docs/AN_format.md` → affects:
- `autongage_formatter.html` — template definitions mirror this doc

### If I change `nav.html` → affects:
- All 8 tool pages (nav is injected via fetch) — 1 source of truth

### If I change `worker/worker.js` or `server/proxy.js` gryd proxy routes → affects:
- `login.html` / `pages/login.html` — login flow depends on `/gryd/login` endpoint
- `config.js` — `grydEndpoint` must match

---

## 16. Configuration Reference

### config.js (GITIGNORED)

Copy `config.example.js` to `config.js` and fill in secrets.

| Setting | Default | Required | Notes |
|---------|---------|----------|-------|
| `grydEndpoint` | `"http://localhost:3456"` | Yes | Local proxy or CF Worker URL |
| `grydModel` | `"gcp-gemini-3.1-flash-lite-preview"` | Yes | Gryd model identifier |
| `grydSignupToken` | `""` | Yes | From team/gryd admin |
| `useGrydLlm` | `true` | No | Always true (NVIDIA removed) |
| `apiEndpoint` | (not in example) | Yes | Same as grydEndpoint usually |
| `proxyHandshakeToken` | (not in example) | Yes | Matches server/.env HANDSHAKE_TOKEN |
| `llmBatchSize` | `30` | No | Dashboard batch size |
| `llmMaxConcurrent` | `5` | No | Dashboard concurrency |
| `llmMaxRetries` | `1` | No | Retry count |
| `llmRequestTimeoutMs` | `45000` | No | Dashboard timeout |
| `llmPromptCharLimit` | `1200` | No | Dashboard prompt limit |
| `llmMaxOutputTokens` | `1600` | No | Dashboard output limit |
| `llmDispositionBatchSize` | `25` | No | Disposition batch size |
| `llmDispositionMaxConcurrent` | `5` | No | Disposition concurrency |
| `llmDispositionTimeoutMs` | `60000` | No | Disposition timeout |
| `llmDispositionPromptCharLimit` | `2500` | No | Disposition prompt limit |
| `llmDispositionMaxOutputTokens` | `1800` | No | Disposition output limit |
| `corsProxyUrl` | `""` | No | Recording download proxy |

### server/.env (GITIGNORED)

Copy `server/.env.example` to `server/.env`.

| Setting | Default | Required | Notes |
|---------|---------|----------|-------|
| `NVIDIA_API_KEY` | — | Yes | NVIDIA API key |
| `PORT` | `3456` | No | Server port |
| `HANDSHAKE_TOKEN` | — | Yes | Matches config.js proxyHandshakeToken |
| `GRYD_MODEL` | `"gcp-gemini-3.1-flash-lite-preview"` | No | Gryd model |
| `ALLOWED_ORIGINS` | `"http://localhost:5500,..."` | No | CORS origins |
| `UPSTREAM_TIMEOUT_MS` | `90000` | No | Upstream timeout |

### Cloudflare Worker Env

Set in Cloudflare dashboard:

| Setting | Required | Notes |
|---------|----------|-------|
| `NVIDIA_API_KEY` | Yes | NVIDIA API key |
| `HANDSHAKE_TOKEN` | Yes | Matches config.js |
| `UPSTREAM_TIMEOUT_MS` | No | Default: 30000 |

### Deployed Files (No Build Step)

The entire project is static HTML+CSS+JS. No build step needed.
Deploy by uploading the entire repo root to a static host.

---

## 17. Deployment Guide

### Option A: Cloudflare Pages (Recommended)

1. Connect GitHub repo to Cloudflare Pages
2. Build command: None (leave empty)
3. Build output: `/` (root directory)
4. Environment variables: None needed
5. Custom domain: Optional

### Option B: Cloudflare Worker (Production Proxy)

```bash
npm install -g wrangler
cd worker
wrangler deploy worker.js
```

Set environment variables in Cloudflare dashboard.

### Option C: GitHub Pages

1. Go to repo Settings → Pages
2. Source: Deploy from branch → main → / (root)
3. The `.nojekyll` file ensures GitHub Pages serves `assets/` without Jekyll processing

### Option D: Any Static Host

Upload the entire repo to any static file server.
The app needs no server-side processing — all logic is client-side.

### Local Development

```bash
# Terminal 1: Proxy server
cd server && npm install && npm start

# Terminal 2: Static file server
python -m http.server 5500
# OR: npx serve .
# OR: VS Code Live Server
```

---

## 18. Next.js Migration Blueprint

> This section maps every file/function/dependency to its Next.js equivalent.
> Full step-by-step implementation plan in `NEXTJS_MIGRATION_PLAN.md`.

### Migration Strategy

| Aspect | Decision |
|--------|----------|
| **Router** | App Router (`app/`) |
| **Rendering** | Client Components for tools, Server Components for landing page |
| **API Routes** | Route Handlers (`app/api/`) replacing `server/proxy.js` |
| **Auth** | Next.js Middleware + cookies (replacing sessionStorage/localStorage) |
| **CSS** | CSS Modules per-page + `app/globals.css` (design system, finally centralized) |
| **Shared JS libs** | ES modules in `lib/` — imported, not `window.*` globals |
| **Static assets** | `public/` directory |
| **Config** | `lib/config.ts` (typed) + `.env.local` for secrets |
| **Vendor libs** | npm `xlsx`, `jszip`, `html2canvas`, `jspdf` |

### File Mapping: Current → Next.js

**Pages**:
| Current | Next.js Route | Effort |
|---------|--------------|--------|
| `index.html` | `app/page.tsx` | 🟢 Easy |
| `login.html` / `pages/login.html` | `app/login/page.tsx` | 🟢 Easy |
| `pages/disposition_sync_v2.html` | `app/pre-sales-sync/page.tsx` | 🔴 Hard |
| `pages/post_sales_disposition.html` | `app/post-sales-sync/page.tsx` | 🔴 Hard |
| `pages/dashboardv2.html` | `app/dashboard/page.tsx` | 🔴 Hard |
| `pages/reattempt_filter.html` | `app/reattempt-filter/page.tsx` | 🟡 Medium |
| `pages/autongage_formatter.html` | `app/formatter/page.tsx` | 🟡 Medium |
| `pages/recording_renamer.html` | `app/recording-renamer/page.tsx` | 🟡 Medium |
| `pages/call_analysis_summary.html` | `app/call-analysis/page.tsx` | 🟡 Medium |
| `pages/campaign_generator.html` | `app/campaign-generator/page.tsx` | 🟡 Medium |

**Shared Libs** → `lib/` (ES modules, typed):
| Current | Next.js Dest |
|---------|-------------|
| `theme.js` | `lib/theme.ts` |
| `logger.js` | `lib/logger.ts` |
| `data-pipeline.js` | `lib/data-pipeline.ts` |
| `date-utils.js` | `lib/date-utils.ts` |
| `excel-safe.js` | `lib/excel-safe.ts` |
| `batch-export.js` | `lib/batch-export.ts` |
| `ai-config.js` | `lib/ai/ai-config.ts` |
| `ai-validator.js` (logic) | `lib/ai/ai-validator.ts` |
| `ai-validator.js` (DOM) | `components/StatusBar.tsx` |
| `llm-batch-runner.js` | `lib/ai/llm-batch-runner.ts` |
| `history-helpers.js` | `lib/ai/history-helpers.ts` |

**Server/Proxy** → Route Handlers:
| Current | Next.js Equivalent |
|---------|-------------------|
| `server/proxy.js` (POST /v1/chat/completions) | `app/api/chat/route.ts` |
| `server/proxy.js` (POST /gryd/*) | `app/api/gryd/[...path]/route.ts` |
| `server/proxy.js` (GET /session) | `app/api/session/route.ts` |
| `server/proxy.js` (POST /gryd/login) | `app/api/gryd/login/route.ts` |
| `server/proxy.js` (GET /health) | `app/api/health/route.ts` |
| `worker/worker.js` | **KEEP AS-IS** (separate deployment) |

### CSS Migration: The Biggest Win

The biggest improvement of migration is **centralizing the design system**:
- 10 duplicated CSS files → 1 `globals.css` + 10 CSS Modules
- Theme tokens defined ONCE in `globals.css` instead of 10 times
- Per-page accent colors via CSS Module variables
- `fonts.css` → `next/font` + `@font-face` in `globals.css`

### Auth Migration

| Current | Next.js |
|---------|---------|
| `sessionStorage` + `localStorage` | Cookies (httpOnly for token) |
| Inline `<script>` auth redirect | `middleware.ts` |
| Two login page copies | Single `app/login/page.tsx` |
| Redirect loop detection | Handled by middleware flow |

### Pattern Migration Reference

| Old Pattern | New Pattern |
|------------|-------------|
| `window.runLlmBatches(...)` | `import { runLlmBatches } from '@/lib/ai/llm-batch-runner'` |
| `window.JEJO_CONFIG.llmBatchSize` | `import { config } from '@/lib/config'` |
| `document.getElementById('foo')` | `useRef<HTMLElement>(null)` |
| `element.innerHTML = html` | JSX |
| `onclick="handleClick()"` | `onClick={handleClick}` |
| `fetch("../nav.html")` | `<Nav />` import |
| `sessionStorage.getItem('gryd_token')` | `useAuth()` hook / `cookies()` |
| `<link rel="stylesheet" href="...">` | `import styles from './page.module.css'` |

### Migration Phases

| Phase | Scope | Hours |
|-------|-------|-------|
| 0 — Scaffold | Next.js setup, folders, deps, globals.css, layout, middleware | 1-2 |
| 1 — Config/Auth/API | lib/config, useAuth hook, all API routes, login page | 3-4 |
| 2 — Shared Components | Nav, ThemeToggle, ThemeProvider, StatusBar, etc. | 4-6 |
| 3 — Landing + Campaign Gen | Easiest pages first | 4-6 |
| 4 — Filter/Formatter/Call Sum | Medium complexity | 8-12 |
| 5 — Recording Renamer | Medium with ZIP | 3-5 |
| 6 — Dashboard | KPIs, charts, PDF, AI | 6-10 |
| 7 — Pre/Post Sales Sync | Heaviest tools (~173 functions combined) | 16-24 |
| 8 — Cleanup & Verify | Remove old files, build check | 3-5 |
| **Total** | | **~48-74h** |

> **Incremental migration**: Old HTML files can coexist with Next.js routes using `next.config.ts` rewrites.
> Migrate one tool at a time while others remain functional.

---

## Appendix: Key Data Types & Interfaces

### Row Object (from parseSheet)
```json
{
  "__rowIndex": 5,
  "__raw": ["cell1", "cell2", "cell3"],
  "name": "John Doe",
  "phone": "9876543210",
  "date": "2026-06-24",
  ...
}
```

### Campaign Objective (campaign_generator)
```json
{
  "id": "generateLead_9876543210",
  "campaign_name": "Test Drive Booking - June",
  "campaign_family": "presales_voice",
  "sub_type": "tdb_outbound",
  "target_audience": "Lead who visited showroom",
  "campaign_goal": "Book test drive appointment",
  "search_term": "presales_voice_tdb_outbound",
  "uuid": "a1b2c3d4e5f6g7h8i9j0k1l2",
  "doc_data": { "version": 1, "created": "2026-06-24" },
  "filter_params": { "city": "Mumbai", "model": "Hyryder" },
  ...
}
```

### BatchExporter Store
```json
{
  "jejo-ae-batch-export-reattempt": {
    "fingerprints": {
      "file123|1000": {
        "templates": {
          "default": {
            "nextLeadIndex": 500,
            "inputRowCount": 1000,
            "savedAt": 1734567890123
          }
        }
      }
    },
    "version": 2
  }
}
```

### LLM Batch Runner Options
```typescript
{
  items: Array<any>,           // Data items to process
  batchSize: 25,               // Items per API request
  maxConcurrent: 5,            // Parallel requests
  minGapMs: 300,               // Min spacing between requests
  maxRetries: 3,               // Retries per batch
  requestTimeoutMs: 60000,     // Per-request timeout
  getCacheKey: (items) => string | null,
  cachedData: Map<string, string>,
  buildPrompt: (batch, index) => { system: string, user: string },
  buildHeaders: () => object,
  parseResponse: (text, batch) => Array<any>,
  onProgress: (done, total, msg, pct) => void,
  signal: AbortSignal | undefined
}
// Returns: { results: Map<index, result>, correctedCount: number, failedBatches: number[] }
```

---

> **Last updated**: 2026-06-24
> **Purpose**: Complete project brain — read before any change
> **Next action**: See `NEXTJS_MIGRATION_PLAN.md` for migration implementation
