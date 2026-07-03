# 🧠 Buffy's Memory File — AutoNage / Mastersheetupdater

> This is my personal diary. When I read this file at the start of a session, I instantly
> understand the project's soul — what it does, how it's built, what's been fixed, and
> what patterns to follow. Update this every time I make changes.

---

## 📋 Project Identity

- **Name**: AutoNage (repo: `Mastersheetupdater`)
- **What it does**: Next.js application for automotive lead operations automation. Takes AutoEngage exports → processes them → outputs Zoho Master Sheet-ready data.
- **Users**: Business Analysts (BAs) at a car dealership group. They upload Excel files, click buttons, download results.
- **AI Backend**: **Gryd AI** only — direct from client (no proxy). Model: `gcp-gemini-3.1-flash-lite-preview`.
- **Auth**: Client-side — sessionStorage + localStorage. Login POSTs directly to Gryd endpoint. No cookies, no middleware, no API routes.
- **Hosting**: GitHub Pages (static export via GitHub Actions).
- **Framework**: Next.js 16 with React 19 — statically exported (`output: 'export'`).

---

## 🏗️ Architecture (Current — June 2026)

### File Structure

```
/ (root)                      ← Next.js project root
├── app/                      ← App Router pages
│   ├── layout.tsx            ← Root layout (theme provider, config.js, fonts)
│   ├── page.tsx              ← Landing page (tool catalog + auth gate)
│   ├── globals.css           ← Design system + shared component styles
│   ├── index.css             ← Landing page styles
│   ├── login/                ← Login page
│   ├── disposition-sync-v2/  ← PRE-SALES SYNC
│   ├── post-sales-sync/      ← POST-SALES SYNC
│   ├── dashboard/            ← CAMPAIGN DASHBOARD
│   ├── recording-renamer/    ← RECORDING RENAMER
│   ├── formatter/            ← AUTOENGAGE FORMATTER
│   ├── call-analysis/        ← CALL ANALYSIS SUMMARY
│   ├── reattempt-filter/     ← RE-ATTEMPT FILTER
│   ├── campaign-generator/   ← CAMPAIGN OBJECTIVE GENERATOR
│   └── pre-sales-sync/       ← Redirect to /disposition-sync-v2
├── components/               ← 8 shared React components
├── hooks/                    ← useAuth.ts
├── lib/                      ← 12 TypeScript utility files
├── public/
│   ├── config.js             ← Gryd settings (gitignored!)
│   ├── fonts/                ← Self-hosted Inter, Manrope, IBM Plex Mono
│   ├── images/               ← Brand logos
│   └── legacy/               ← Original HTML app (preserved for reference)
├── .github/workflows/deploy.yml  ← CI/CD to GitHub Pages
├── next.config.ts            ← Static export + basePath /Mastersheetupdater
├── proxy.ts                  ← Edge function (security headers + redirect)
└── worker/worker.js          ← Cloudflare Worker (legacy, not used)
```

### Current Architecture Summary

| Aspect | Detail |
|--------|--------|
| **Pattern** | Next.js App Router — static export |
| **Framework** | Next.js 16 + React 19 (Client Components) |
| **Build system** | `next build` — TypeScript, bundling, static export |
| **State management** | In-memory React state + localStorage |
| **AI model** | Gryd AI (`gcp-gemini-3.1-flash-lite-preview`) — direct client calls |
| **Auth** | Gryd JWT tokens (sessionStorage + localStorage) |
| **Data format** | Excel I/O via npm `xlsx` (SheetJS) |
| **Hosting** | GitHub Pages (gh-pages branch) |
| **CI/CD** | GitHub Actions — auto-deploy on push to main |
| **Tests** | **0** — no test files exist |

---

## 🧩 Component Inventory

### Pages (10 routes)

| Route | Page | Lines | AI? | Key Files |
|---|---|---|---|---|
| `/` | Landing | ~90 | No | `app/page.tsx`, `app/index.css` |
| `/login` | Login | ~100 | No | `app/login/page.tsx`, `app/login/login.css` |
| `/disposition-sync-v2` | Pre-Sales Sync | ~1360 | Yes | `page.tsx`, `disposition-utils.ts`, `pre-sales-prompt-builder.ts` |
| `/post-sales-sync` | Post-Sales Sync | ~1800 | Yes | `page.tsx`, `classify-utils.ts`, `quality-utils.ts`, `prompt-builder.ts` |
| `/dashboard` | Dashboard | ~1240 | Yes | `page.tsx`, `dashboard.css` |
| `/recording-renamer` | Recording Renamer | ~765 | No | `page.tsx` |
| `/formatter` | Formatter | ~850 | No | `page.tsx`, `templates.ts` |
| `/call-analysis` | Call Summary | ~850 | No | `page.tsx` |
| `/reattempt-filter` | Re-Attempt Filter | ~725 | No | `page.tsx` |
| `/campaign-generator` | Campaign Gen | ~700 | No | `page.tsx`, `campaign-families.ts` |
| `/pre-sales-sync` | Redirect | 3 | No | `page.tsx` (redirects to `/disposition-sync-v2`) |

### Shared Components (8)

- `Nav.tsx` — 8-tool navigation bar
- `ThemeProvider.tsx` — Theme context + toggle
- `ThemeToggle.tsx` — Moon/sun toggle button
- `BrandLogo.tsx` — Theme-aware AN logo
- `DragDropFileUpload.tsx` — File upload with drag & drop
- `ProcessingOverlay.tsx` — Modal spinner with progress bar
- `StatusBar.tsx` — AI validation progress bar
- `Toast.tsx` — Toast notifications (provider + consumer)

### Shared Libraries (12 files)

- `lib/logger.ts` — `$log`, `$warn`, `$error`
- `lib/theme.ts` — `getStoredTheme`, `applyTheme`, `toggleTheme`
- `lib/data-pipeline.ts` — `parseSheet`, `normalizePhone`, `cellToString`
- `lib/date-utils.ts` — `parseDate`, `detectDateFormat`
- `lib/excel-safe.ts` — `excelSafe`, `excelSafeCsvCell`
- `lib/batch-export.ts` — `BatchExporter` class
- `lib/client-config.ts` — Public-safe config defaults
- `lib/server-config.ts` — Server-only env config (unused in static export)
- `lib/ai/ai-config.ts` — AI config helpers
- `lib/ai/llm-batch-runner.ts` — `runLlmBatches` (batch engine)
- `lib/ai/history-helpers.ts` — `detectHistory`, `formatHistoryForPrompt`
- `lib/ai/dashboard-analysis.ts` — Dashboard AI analysis

### Hooks

- `hooks/useAuth.ts` — `login()`, `logout()`, `checkSession()`, `isAuthenticated`, `loading`

---

## 🔐 Auth Flow

```
1. useAuth() hook on mount → checkSession()
   → reads gryd_token + gryd_expiry from sessionStorage/localStorage
   → sets isAuthenticated = Boolean(token) && expiry > now

2. Login page: handleSubmit() → POST {grydEndpoint}/gryd/login
   → On success: stores token, session_id, enterprise_id, user_id, expiry
     to BOTH sessionStorage and localStorage (for multi-tab sync)
   → Redirects to /

3. Landing page: if (!isAuthenticated) router.push('/login')

4. All tool pages: useAuth() → if (!isAuthenticated) redirect to /login

5. Logout: clears all gryd keys from storage
```

**No cookies, no middleware, no API routes.** Auth is purely client-side.

---

## ⚙️ AI Pipeline (llm-batch-runner.ts)

The heart of AI validation. Key behavior:

- **Batches items** into configurable groups
- **Runs concurrent workers** (up to `maxConcurrent`)
- **Adaptive throttling**: starts with `minGapMs` gap, backs off on 429s, recovers after 5 successes
- **Retries with split**: if a batch fails all retries, splits it in half and retries halves
- **Returns ordered results** as `Map<rowIndex, result>`
- **Gryd-only**: Direct calls to Gryd endpoint (no proxy). Uses `JEJO_CONFIG.grydEndpoint` + `JEJO_CONFIG.grydModel`.

### AI Endpoint Resolution

```typescript
// From lib/ai/ai-config.ts
getApiEndpoint() → JEJO_CONFIG.grydEndpoint + '/gryd/v1/chat/completions'
getLlmModel() → JEJO_CONFIG.grydModel || 'gcp-gemini-3.1-flash-lite-preview'
```

Auth headers: `X-GRYD-TOKEN`, `X-GRYD-SESSION-ID`, `X-GRYD-ENTERPRISE-ID` from storage.

### Pages Using AI

1. **Pre-Sales Sync** — Validates dispositions with LLM
2. **Post-Sales Sync** — Validates dispositions with LLM
3. **Dashboard** — Classifies dispositions, generates voice insights

---

## 🚀 Deployment

### GitHub Actions (Automatic)

```yaml
Push to main → npm ci → npm run build → peaceiris/actions-gh-pages → gh-pages branch
```

Deployed at: `https://jennyjoseph7.github.io/Mastersheetupdater/`

### next.config.ts

```typescript
output: 'export',                              // Static export
basePath: '/Mastersheetupdater',               // GitHub Pages repo path
assetPrefix: '/Mastersheetupdater/',           // Asset URLs
trailingSlash: true,                           // Directory-style URLs
images: { unoptimized: true },                 // No Next.js image optimization
```

### Key Config Files

- `public/config.js` — Gryd settings (gitignored!). Copied template from `public/legacy/config.example.js`.
- `next.config.ts` — Build config, basePath, assetPrefix
- `.github/workflows/deploy.yml` — CI/CD pipeline

---

## 🔧 Bug Fix Log (Chronological)

### June 2026

| # | Issue | Fix |
|---|-------|-----|
| 1–22 | Original HTML app fixes | See previous log in legacy docs |
| 23 | Next.js migration: landing page | Migrated `index.html` → `app/page.tsx` |
| 24 | Next.js migration: login page | Migrated `login.html` → `app/login/page.tsx` |
| 25 | Next.js migration: shared libs | Migrated 12 JS libs → `lib/*.ts` (typed) |
| 26 | Next.js migration: components | Created 8 React components |
| 27 | Next.js migration: Campaign Generator | Migrated first tool (~700 lines) |
| 28 | Next.js migration: Formatter | Migrated with 9 templates (~850 lines) |
| 29 | Next.js migration: Re-Attempt Filter | Migrated (~725 lines) |
| 30 | Next.js migration: Call Analysis | Migrated (~850 lines) |
| 31 | Next.js migration: Recording Renamer | Migrated (~765 lines) |
| 32 | Next.js migration: Dashboard | Migrated (~1240 lines) |
| 33 | Next.js migration: Pre-Sales Sync | Migrated (~1360 lines) |
| 34 | Next.js migration: Post-Sales Sync | Migrated (~1800 lines) |
| 35 | API routes deleted | Removed all `app/api/*` — static export doesn't support them |
| 36 | Auth refactored to client-side | Removed cookie/middleware auth — using sessionStorage only |
| 37 | GitHub Actions CI/CD | Created `.github/workflows/deploy.yml` |
| 38 | Drag-drop bug in Recording Renamer | `if (!f)` → `if (f)` — drops silently did nothing |
| 39 | State setters wired in Recording Renamer | `processBatch()` now calls React state setters |
| 40 | Wrong language maps in Post-Sales | Fixed to match dealer geography |
| 41 | 6 missing dispositions in Post-Sales | Added Service Postponed, Showroom Visit Planned, etc. |
| 42 | Pre-Sales redirect created | `/pre-sales-sync` → redirects to `/disposition-sync-v2` |
| 43 | Documentation updated | README, archi.md, freebuff.md rewritten for Next.js |

---

## 📝 Conventions I Must Follow

1. **Never assume libraries exist** — check imports in each file
2. **Client Components everywhere** — all pages use `'use client'`
3. **`public/config.js` is gitignored** — never commit API keys
4. **Static export** — no API routes, no server components with Node.js APIs
5. **`basePath: '/Mastersheetupdater'`** — all asset URLs must account for this
6. **Theme system** — `data-theme` attribute, `localStorage('jejo-theme')`
7. **Auth** — `useAuth()` hook, sessionStorage + localStorage. No cookies.
8. **Gryd-only LLM** — all AI calls go directly to Gryd endpoint
9. **No API routes** — all proxy/API code has been deleted
10. **CSS** — global tokens in `globals.css`, per-page styles in CSS files imported in each page
11. **File uploads** — use `DragDropFileUpload` component for consistency
12. **AI validation** — use `StatusBar` + `runLlmBatches` for consistent UX
13. **Path references** — use `/Mastersheetupdater/...` for static assets in `<script>` tags
14. **Build check** — always run `npm run build` before committing (static export is strict)

---

## 🔴 Remaining Issues

1. **No tests** — zero test files exist. TODO: add Vitest tests for pure functions in `lib/`
2. **No lint check in CI** — `github/workflows/deploy.yml` doesn't run `npm run lint`
3. **`config.js` at root** — old `config.js` at project root remains (gitignored). Clean up.
4. **`proxy.ts` unused** — edge function file exists but is not imported in static export
5. **`worker/worker.js`** — Cloudflare Worker preserved as legacy, no longer used
6. **`server/` directory** — old `server/proxy.js` and dependencies still exist. Should be removed.
7. **Old root files** — `index.html`, `login.html`, `nav.html` at project root could be cleaned up
8. **Legacy** `assets/` directory — old assets at root could be cleaned up (copies preserved in `public/legacy/`)
9. **`out/` directory** — build output tracked in git. Should be gitignored.
10. **Config path discrepancy** — `layout.tsx` loads `/Mastersheetupdater/config.js` but dev mode uses different path

---

## 🧩 Installed Agent Skills

| Skill | Source | Installs |
|-------|--------|----------|
| `@frontend-design` | `anthropics/skills` | 513.5K |
| `@xlsx` | `anthropics/skills` | 104.1K |
| `@improve-codebase-architecture` | `mattpocock/skills` | 223.3K |
| `@webapp-testing` | `anthropics/skills` | 90.5K |
| `@error-handling` | `affaan-m/everything-claude-code` | 1.2K |

---

*Last updated: 2026-06-29*
*Migration complete — Next.js static export on GitHub Pages.*
