# Mastersheetupdater — AutoNage Lead Operations Automation

A **Next.js** application for automotive lead operations. Processes AutoEngage exports into Zoho Master Sheet-ready data — entirely client-side, statically exported to GitHub Pages.

---

## Project Structure

```
.
├── app/                                # Next.js App Router pages
│   ├── layout.tsx                      #   Root layout — theme, fonts, config
│   ├── page.tsx                        #   Landing page — tool catalog + auth gate
│   ├── globals.css                     #   Design system + shared component styles
│   ├── index.css                       #   Landing page styles
│   ├── login/
│   │   ├── page.tsx                    #   Login page (client component)
│   │   └── login.css                   #   Login page styles
│   ├── disposition-sync-v2/            #   Pre-Sales Sync
│   ├── post-sales-sync/                #   Post-Sales Sync
│   ├── dashboard/                      #   Campaign Dashboard
│   ├── formatter/                      #   AutoEngage Formatter
│   ├── recording-renamer/              #   Recording Renamer
│   ├── call-analysis/                  #   Call Analysis Summary
│   ├── reattempt-filter/               #   Re-Attempt Filter
│   ├── campaign-generator/             #   Campaign Objective Generator
│   └── pre-sales-sync/                 #   Redirect → /disposition-sync-v2
├── components/                         # Shared React components
│   ├── BrandLogo.tsx                   #   Theme-aware brand mark
│   ├── DragDropFileUpload.tsx          #   Reusable file upload zone
│   ├── Nav.tsx                         #   Shared navigation bar
│   ├── ProcessingOverlay.tsx           #   Loading spinner overlay
│   ├── StatusBar.tsx                   #   AI validation progress bar
│   ├── ThemeProvider.tsx               #   Theme context + toggle logic
│   ├── ThemeToggle.tsx                 #   Dark/light toggle button
│   └── Toast.tsx                       #   Toast notification provider
├── hooks/
│   └── useAuth.ts                      #   Auth state management (client-side)
├── lib/                                # TypeScript utility libraries
│   ├── client-config.ts                #   Public-safe default config
│   ├── server-config.ts                #   Server-only env config (unused in static export)
│   ├── logger.ts                       #   Structured logging
│   ├── theme.ts                        #   Theme get/set/toggle utilities
│   ├── data-pipeline.ts                #   Excel parsing, phone normalization
│   ├── date-utils.ts                   #   Multi-format date parsing
│   ├── excel-safe.ts                   #   Formula injection protection
│   ├── batch-export.ts                 #   localStorage batch export
│   └── ai/
│       ├── ai-config.ts               #   AI config helpers
│       ├── llm-batch-runner.ts         #   Adaptive LLM batch engine
│       └── history-helpers.ts          #   Session history parsing
├── public/
│   ├── config.js                       #   Gryd settings & API keys (gitignored!)
│   ├── fonts/                          #   Self-hosted web fonts
│   │   ├── fonts.css                   #     @font-face declarations
│   │   └── *.woff2                     #     Inter, Manrope, IBM Plex Mono
│   ├── images/
│   │   ├── AN.png                      #     Light mode logo
│   │   └── AN Dark.png                 #     Dark mode logo
│   └── legacy/                         # Original HTML app (preserved for reference)
├── .github/workflows/deploy.yml        # GitHub Actions → GitHub Pages
├── next.config.ts                      # Static export + basePath config
├── tsconfig.json                       # TypeScript config
├── proxy.ts                            # Security headers + redirect (edge)
└── worker/worker.js                    # Cloudflare Worker (legacy production proxy)
```

---

## Tools Overview

| Route | Tool | Purpose |
|---|---|---|
| **`/`** | Landing Page | Tool catalog + auth gate |
| **`/login`** | Login | Gryd session-based authentication |
| **`/disposition-sync-v2`** | Pre-Sales Sync | Merge AutoEngage exports into Zoho Master Sheet format |
| **`/post-sales-sync`** | Post-Sales Sync | Service campaign sync and AI validation |
| **`/dashboard`** | Dashboard | Campaign KPIs, charts, AI analysis |
| **`/recording-renamer`** | Recording Renamer | Bulk rename call recordings with metadata |
| **`/formatter`** | AutoEngage Formatter | Map client columns → AutoEngage upload format |
| **`/call-analysis`** | Call Summary | Daily call analysis KPI tables |
| **`/reattempt-filter`** | Re-Attempt Filter | Filter and batch export re-attempt leads |
| **`/campaign-generator`** | Campaign Gen | Generate 20-field structured campaign JSONs |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | Next.js 16 (App Router) — statically exported |
| **UI** | React 19 — Client Components |
| **Styling** | CSS custom properties + per-page CSS files |
| **TypeScript** | Full type safety across all source files |
| **File parsing** | SheetJS (`xlsx`) via npm |
| **PDF generation** | `jspdf` + `html2canvas` via npm |
| **ZIP** | `jszip` via npm |
| **Charts** | CSS-based bar charts (no chart library) |
| **Fonts** | Inter, Manrope, IBM Plex Mono — self-hosted |
| **AI backend** | Gryd AI (Gemini-based, direct from client) |
| **Auth** | Gryd session-based (sessionStorage + localStorage) |
| **Hosting** | GitHub Pages (static export via GitHub Actions) |

---

## Getting Started

### Prerequisites

- Node.js >= 18
- npm

### Setup

```bash
# 1. Install dependencies
npm install

# 2. Configure secrets
cp public/legacy/config.example.js public/config.js
# Edit public/config.js with your gryd signup token

# 3. Start the dev server
npm run dev
# → http://localhost:3000
```

### Configuration

Copy `public/legacy/config.example.js` to `public/config.js` and fill in:

| Setting | Default | Required |
|---|---|---|
| `grydEndpoint` | `http://localhost:3456` | Yes |
| `grydModel` | `gcp-gemini-3.1-flash-lite-preview` | Yes |
| `grydSignupToken` | `""` | Yes |
| `llmBatchSize` | `30` | No |
| `llmMaxConcurrent` | `5` | No |
| `llmMaxRetries` | `1` | No |
| `llmRequestTimeoutMs` | `45000` | No |
| `llmPromptCharLimit` | `1200` | No |
| `llmMaxOutputTokens` | `1600` | No |
| `llmDispositionBatchSize` | `25` | No |
| `llmDispositionMaxConcurrent` | `5` | No |
| `llmDispositionTimeoutMs` | `60000` | No |
| `llmDispositionPromptCharLimit` | `2500` | No |
| `llmDispositionMaxOutputTokens` | `1800` | No |
| `corsProxyUrl` | `""` | No |

**Note:** `public/config.js` is gitignored. Only the example template is tracked.

---

## Development

```bash
# Dev server with hot reload
npm run dev

# Type-check + build
npm run build   # Build also runs type-checking

# Lint
npm run lint
```

All tool pages are under `app/*/page.tsx`. Each page is a Client Component with local state management. Shared libraries live in `lib/`, shared UI in `components/`.

---

## Deployment

The project is automatically deployed to **GitHub Pages** via GitHub Actions on every push to `main`.

### How it works

1. Push to `main` → triggers `.github/workflows/deploy.yml`
2. `next build` creates a static export in `./out`
3. `peaceiris/actions-gh-pages` publishes `./out` to the `gh-pages` branch

### Manual Build

```bash
npm run build
# Output: ./out/
# Serve locally: npx serve out
```

### Key Config

`next.config.ts`:
- `output: 'export'` — static HTML export (no Node.js server)
- `basePath: '/Mastersheetupdater'` — matches the GitHub Pages repo path
- `trailingSlash: true` — ensures directory-style URLs

---

## Architecture

- **Static Export**: `next build` generates pure HTML/CSS/JS — no server required
- **Client-Side Auth**: Auth tokens stored in `sessionStorage` + `localStorage`, validated on each page mount
- **Client-Side AI**: Calls Gryd AI directly from the browser (config endpoint + JWT token)
- **No API Routes**: All proxy/API routes were removed; the app is fully client-side
- **No Build Step**: Next.js handles TypeScript compilation and bundling
- **Self-Hosted Assets**: All fonts and third-party libs are served from `/public/`

### Auth Flow

1. User visits any page → `useAuth()` hook checks `sessionStorage` for `gryd_token`
2. No token → redirect to `/login`
3. User submits credentials → login POSTs directly to Gryd endpoint
4. On success → token stored in `sessionStorage` + `localStorage` → redirect to `/`
5. `pageshow` + `visibilitychange` listeners re-check auth on tab restore

---

## License

Internal use — AutoNage Lead Operations Automation

*JEJO — Lead Operations Automation*
