# 🧠 AutoNage — Architecture Reference (Next.js)

> **Purpose**: Complete architecture map for the Next.js application.
> This migration is **complete** — all 10 pages have been migrated from static HTML to Next.js App Router.
> Read this before making any change.

---

## ✅ Migration Status: COMPLETE

| Page | Route | Status | Notes |
|------|-------|--------|-------|
| Landing | `/` | ✅ | Client component, auth gate, 8 tool cards |
| Login | `/login` | ✅ | Gryd session auth, theme toggle |
| Pre-Sales Sync | `/disposition-sync-v2` | ✅ | ~1360 lines, AI validation |
| Post-Sales Sync | `/post-sales-sync` | ✅ | ~1800 lines, auto-classify, AI |
| Dashboard | `/dashboard` | ✅ | ~1240 lines, KPIs, charts, AI, PDF |
| Recording Renamer | `/recording-renamer` | ✅ | ~765 lines, ZIP download |
| Formatter | `/formatter` | ✅ | ~850 lines, 9 templates |
| Call Analysis | `/call-analysis` | ✅ | ~850 lines, KPI tables |
| Re-Attempt Filter | `/reattempt-filter` | ✅ | ~725 lines, batch export |
| Campaign Generator | `/campaign-generator` | ✅ | ~700 lines, JSON preview |
| Pre-Sales redirect | `/pre-sales-sync` | ✅ | 3-line redirect → `/disposition-sync-v2` |

---

## 🏗️ Current Architecture

### Routing — App Router (`app/`)

```
app/
├── layout.tsx                    # Root layout — fonts, theme provider, config.js
├── page.tsx                      # Landing page — tool catalog + auth gate
├── index.css                     # Landing page styles
├── globals.css                   # Design system + shared component styles
│
├── login/
│   ├── page.tsx                  # Login form (client component)
│   └── login.css                 # Login-specific styles
│
├── disposition-sync-v2/          # Pre-Sales Sync
│   ├── page.tsx                  # Main tool
│   ├── disposition-utils.ts      # Merge & quality logic
│   ├── pre-sales-prompt-builder.ts # AI prompt builder
│   └── disposition-sync-v2.css   # Tool styles
│
├── post-sales-sync/              # Post-Sales Sync
│   ├── page.tsx                  # Main tool
│   ├── classify-utils.ts         # Keyword classification
│   ├── quality-utils.ts          # Quality scoring
│   ├── prompt-builder.ts         # AI prompt builder
│   ├── post-sales-dispositions.ts# Disposition definitions
│   └── post-sales-sync.css       # Tool styles
│
├── dashboard/
│   ├── page.tsx                  # Main tool
│   └── dashboard.css             # Tool styles
│
├── recording-renamer/
│   ├── page.tsx                  # Main tool
│   └── recording-renamer.css     # Tool styles
│
├── formatter/
│   ├── page.tsx                  # Main tool
│   ├── templates.ts              # 9 dealership templates
│   └── formatter.css             # Tool styles
│
├── call-analysis/
│   ├── page.tsx                  # Main tool
│   └── call-analysis.css         # Tool styles
│
├── reattempt-filter/
│   ├── page.tsx                  # Main tool
│   └── reattempt-filter.css      # Tool styles
│
├── campaign-generator/
│   ├── page.tsx                  # Main tool
│   ├── campaign-families.ts      # Campaign family definitions
│   └── campaign-generator.css    # Tool styles
│
└── pre-sales-sync/
    └── page.tsx                  # Redirect → /disposition-sync-v2
```

### Shared Components (`components/`)

| Component | Purpose |
|---|---|
| `Nav.tsx` | 8-tool navigation bar with active state |
| `ThemeProvider.tsx` | React context for dark/light theme |
| `ThemeToggle.tsx` | Theme toggle button (moon/sun icons) |
| `BrandLogo.tsx` | Theme-aware brand logo image |
| `DragDropFileUpload.tsx` | Reusable file upload zone (drag & drop + click) |
| `ProcessingOverlay.tsx` | Modal spinner overlay with progress bar |
| `StatusBar.tsx` | AI validation progress bar with actions |
| `Toast.tsx` | Toast notification provider + consumer |

### Shared Libraries (`lib/`)

| Module | Key Exports | Purpose |
|---|---|---|
| `logger.ts` | `$log`, `$warn`, `$error` | Structured console logging |
| `theme.ts` | `getStoredTheme`, `applyTheme`, `toggleTheme` | Dark/light theme |
| `data-pipeline.ts` | `parseSheet`, `normalizePhone`, `cellToString` | Excel parsing & data normalization |
| `date-utils.ts` | `parseDate`, `detectDateFormat`, `formatDateDisplay` | Multi-format date parsing |
| `excel-safe.ts` | `excelSafe`, `excelSafeCsvCell` | Formula injection protection |
| `batch-export.ts` | `BatchExporter` class | localStorage batch export |
| `client-config.ts` | `clientConfig` | Public-safe default config values |
| `server-config.ts` | `serverConfig` | Server-only env config (unused in static export) |
| `ai/ai-config.ts` | `getApiEndpoint`, `getLlmModel`, `sanitizeForPrompt` | AI configuration helpers |
| `ai/llm-batch-runner.ts` | `runLlmBatches` | Adaptive LLM batch engine |
| `ai/history-helpers.ts` | `detectHistory`, `formatHistoryForPrompt` | Session transcript parsing |

### Hooks

| Hook | Purpose |
|---|---|
| `useAuth.ts` | Auth state: `login`, `logout`, `checkSession`, `isAuthenticated` |

---

## 🔐 Authentication

**Client-side only** — no cookies, no middleware, no API routes.

```
useAuth() hook:
  ├── checkSession() → reads gryd_token from sessionStorage + localStorage
  ├── login(userId, password) → POSTs to grydEndpoint/gryd/login
  │   └── On success → stores token in sessionStorage + localStorage
  ├── logout() → clears all gryd keys from storage
  └── isAuthenticated → Boolean(token) && expiry > now
```

### Storage Schema

| Key | Storage | Purpose |
|---|---|---|
| `gryd_token` | sessionStorage + localStorage | JWT auth token |
| `gryd_session_id` | sessionStorage + localStorage | Gryd session ID |
| `gryd_enterprise_id` | sessionStorage + localStorage | Enterprise ID |
| `gryd_user_id` | sessionStorage + localStorage | User identifier |
| `gryd_expiry` | sessionStorage + localStorage | Token expiry (epoch seconds) |
| `jejo-theme` | localStorage | Dark/light theme preference |

---

## 🎨 CSS Architecture

### Design System — Centralized

All theme tokens defined once in `app/globals.css`:

- **Dark theme**: `:root, [data-theme="dark"]` — 30+ CSS custom properties
- **Light theme**: `[data-theme="light"]` — overrides for light mode
- **8 accent color pairs** — one per tool (red, orange, yellow, green, teal, blue, purple, pink)
- **Shared component styles** — header, nav, drop zone, toast, overlay, status bar, buttons

### Per-Page CSS

Each tool page has its own CSS file loaded via import:
- `import './dashboard.css'` in each `page.tsx`
- Per-tool accent colors via `--accent-p` / `--accent-soft-p` overrides

---

## 📦 Static Export (GitHub Pages)

### Build Pipeline

```yaml
# .github/workflows/deploy.yml
Push to main → npm ci → npm run build → publish out/ to gh-pages
```

### next.config.ts

```typescript
output: 'export',           // Static HTML export (no server)
basePath: '/Mastersheetupdater', // GitHub Pages repo path
assetPrefix: '/Mastersheetupdater/', // Asset URLs
trailingSlash: true,        // Directory-style URLs
```

### Key implications

- **No API routes** — all routes deleted (no `app/api/` directory)
- **No middleware** — `proxy.ts` is preserved but not used in static export
- **No SSR** — all pages are pre-rendered as static HTML
- **Client-side config** — `public/config.js` loaded via `<script>` in layout.tsx

---

## 🔗 Dependency Graph

```
app/layout.tsx
├── app/globals.css (design system)
├── components/ThemeProvider.tsx
│   └── lib/theme.ts
└── components/Toast.tsx

app/page.tsx (landing)
├── app/index.css
├── hooks/useAuth.ts
│   └── lib/client-config.ts (via grydEndpoint())
├── components/BrandLogo.tsx
│   └── components/ThemeProvider.tsx
└── components/ThemeToggle.tsx

app/login/page.tsx
├── app/login/login.css
├── hooks/useAuth.ts
└── components/ThemeProvider.tsx

app/disposition-sync-v2/page.tsx (all tools follow same pattern)
├── hooks/useAuth.ts
├── components/Nav.tsx
├── components/BrandLogo.tsx
├── components/ThemeToggle.tsx
├── components/DragDropFileUpload.tsx
├── components/ProcessingOverlay.tsx
├── components/StatusBar.tsx
├── lib/data-pipeline.ts
├── lib/date-utils.ts
├── lib/excel-safe.ts
├── lib/ai/llm-batch-runner.ts
├── lib/ai/history-helpers.ts
├── lib/ai/ai-config.ts
└── lib/client-config.ts
```

---

## 🧩 Function Inventory — Per Page

| Page | Lines | Key Functions | AI |
|------|-------|---------------|----|
| Landing (`/`) | ~90 | `logout`, auth gate | No |
| Login (`/login`) | ~100 | `handleSubmit`, auth state | No |
| Pre-Sales Sync | ~1360 | `mergeData`, `buildQualityReport`, `validateDispositionsWithLLM` | Yes |
| Post-Sales Sync | ~1800 | `classifyDisposition`, `buildQualityReport`, `validateDispositionsWithLLM` | Yes |
| Dashboard | ~1240 | `computeKpis`, `generateDashboard`, `classifyWithLlm` | Yes |
| Recording Renamer | ~765 | `processBatch`, `fetchRecordingWithRetry`, `downloadZip` | No |
| Formatter | ~850 | Column mapping, 9 templates, batch export | No |
| Call Analysis | ~850 | KPI computation, date detection | No |
| Re-Attempt Filter | ~725 | Phone grouping, terminal disposition filter | No |
| Campaign Generator | ~700 | Tab navigation, form state, JSON preview | No |

---

## ⚠️ Migration Rules

### What Changed

| Old Pattern | New Pattern |
|---|---|
| Static HTML pages in `pages/` | Next.js App Router (`app/*/page.tsx`) |
| Inline `<script>` blocks | React Client Components |
| `window.*` globals | ES module imports |
| `document.getElementById` | React state + refs |
| `onclick=` attributes | React `onClick` handlers |
| `innerHTML` string rendering | JSX |
| `assets/fonts/` | `public/fonts/` |
| `assets/images/` | `public/images/` |
| `assets/js/vendor/*` | npm packages (`xlsx`, `jszip`, etc.) |
| `server/proxy.js` | Deleted (no API routes needed) |
| `worker/worker.js` | Preserved as legacy |
| 10 duplicated CSS files | 1 `globals.css` + per-page CSS files |

### What Stayed the Same

- **Auth model**: sessionStorage + localStorage (client-side, no cookies)
- **AI backend**: Gryd AI only (direct from client, no proxy)
- **File parsing**: SheetJS (`xlsx`)
- **Theme system**: `data-theme` attribute + `localStorage('jejo-theme')`
- **Feature logic**: All business logic preserved in React components + utility functions
- **Deployment**: Static hosting (now GitHub Pages via GitHub Actions)

---

## 🚀 Deployment

### GitHub Actions (Automatic)

```yaml
Push to main → npm ci → npm run build → peaceiris/actions-gh-pages → gh-pages branch
```

### Manual

```bash
npm run build
# Output: ./out/
# Deploy out/ to any static host (S3, Cloudflare Pages, etc.)
```

### Legacy Files

Original HTML files preserved in `public/legacy/` for reference:
- `public/legacy/index.html`, `login.html`, `nav.html`
- `public/legacy/pages/*.html` — all 8 tool pages
- `public/legacy/assets/` — styles, scripts, fonts, images
- Accessible at `https://jennyjoseph7.github.io/Mastersheetupdater/legacy/`

---

## 📋 File Count

| Directory | Files | Description |
|---|---|---|
| `app/` | 10 pages + 1 layout + 1 globals.css | Next.js routes |
| `components/` | 8 TSX files | Shared React components |
| `lib/` | 12 TS files | Shared TypeScript utilities |
| `hooks/` | 1 TS file | useAuth hook |
| `public/fonts/` | 12 woff2 + 1 css | Self-hosted fonts |
| `public/images/` | 2 PNG | Brand logos |
| `public/legacy/` | ~60 files | Original HTML app |
| **Total** | **~45 active source files** | |

---

*Last updated: 2026-06-29*
*Migration complete. See `PROGRESS.md` for remaining cleanup tasks.*
