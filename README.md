# AutoNage — Lead Operations Automation

A suite of browser-based tools for automotive lead operations. Each tool is a self-contained HTML file with no backend dependencies — everything runs locally in the browser. All external resources (fonts, JavaScript libraries) are self-hosted for offline use and security compliance.

---

## Project Structure

```
.
├── index.html                          # Landing page — tool catalog
├── config.js                           # API keys & proxy settings (gitignored)
├── config.example.js                   # Config template with instructions
├── opencode.json                       # Project metadata
├── .gitignore
├── README.md                           # This file
│
├── tools/                              # Tool HTML files
│   ├── disposition_sync_v2.html        # Pre-Sales Sync
│   ├── post_sales_disposition.html     # Post-Sales Sync
│   ├── recording_renamer.html          # Recording Renamer
│   ├── autongage_formatter.html        # AutoEngage Formatter
│   ├── call_analysis_summary.html      # Call Analysis Summary
│   ├── reattempt_filter.html           # Re-Attempt Filter
│   └── dashboard.html                  # Campaign Dashboard
│
├── assets/
│   ├── fonts/                          # Self-hosted web fonts
│   │   ├── fonts.css                   #   @font-face declarations
│   │   └── *.woff2                     #   Inter, Manrope, IBM Plex Mono
│   ├── lib/                            # Self-hosted JS libraries
│   │   ├── xlsx.full.min.js            #   SheetJS — Excel parsing
│   │   ├── jszip.min.js                #   JSZip — ZIP compression
│   │   ├── html2canvas.min.js          #   html2canvas — screenshot capture
│   │   └── jspdf.umd.min.js            #   jsPDF — PDF generation
│   └── images/
│       ├── AN.png                      #   Light mode logo
│       └── AN Dark.png                 #   Dark mode logo
│
└── docs/
    ├── AN_format.md                    # AutoNage format reference
    └── disposition.md                  # Disposition definitions
```

---

## Tools Overview

| Page | Purpose |
|---|---|
| **dashboard.html** | Campaign performance dashboard with KPIs, charts, and data overview |
| **call_analysis_summary.html** | Call analysis summary with connected/disconnected stats and KPIs |
| **disposition_sync_v2.html** | Pre-Sales Sync — merges AutoEngage exports into Zoho Master Sheet format |
| **post_sales_disposition.html** | Post-Sales Disposition — service campaign sync and validation |
| **recording_renamer.html** | Bulk rename call recording files with campaign metadata |
| **reattempt_filter.html** | Filter and manage re-attempt leads for call campaigns |
| **autongage_formatter.html** | Format and clean AutoEngage export data |

---

## Getting Started

### 1. Configuration

Copy `config.example.js` to `config.js` and fill in your API keys:

```js
window.JEJO_CONFIG = {
  apiEndpoint: '',                       // Custom API endpoint (optional)
  openRouterApiKey: 'sk-or-v1-...',     // Your OpenRouter API key
  openRouterModel: 'deepseek/deepseek-v4-flash',
  corsProxyUrl: '',                      // CORS proxy URL (if needed)
  proxyHandshakeToken: 'your-token-here',
};
```

**Note:** `config.js` is gitignored and should never be committed. Only `config.example.js` is tracked.

### 2. Open a Tool

Open any page directly in a browser — no server required:

- **Landing page:** `index.html`
- **Any tool:** `tools/dashboard.html` (or from the landing page)

> All tools work offline once assets are cached. No installation. No backend.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | HTML + CSS (no framework) |
| Logic | Vanilla JavaScript (ES6+) |
| File parsing | SheetJS (XLSX.js) — self-hosted |
| PDF generation | jsPDF + html2canvas — self-hosted |
| Fonts | Inter, Manrope, IBM Plex Mono — self-hosted |
| AI validation | OpenRouter API (configurable endpoint) |
| Hosting | Static file serving (CloudFront / S3 / any web server) |

---

## Deployment

The project is designed to be deployed as a static site to any web server or CDN.

### CloudFront (AWS)

1. Upload all files to an S3 bucket (keep the directory structure intact)
2. Point CloudFront distribution to the S3 bucket
3. Add a **Response Headers Policy** for security headers:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |

4. Set **Security Policy** to `TLSv1.2_2023` (disables TLS 1.0/1.1 and weak ciphers)

### Security

- All external scripts and fonts are self-hosted (zero CDN dependencies)
- Content Security Policy (CSP) enforced via `<meta>` tag
- `X-Frame-Options: DENY` and `X-Content-Type-Options: nosniff` set as meta tags and HTTP headers
- Inline scripts allowed (`'unsafe-inline'`) — necessary for self-contained HTML tools

---

## Development

All tools are single-file HTML documents in `tools/`. To modify:

1. Edit the relevant `tools/*.html` file
2. Open it directly in a browser to test
3. No build step, no bundler, no npm install needed

### Adding a New Tool

1. Create a new HTML file in `tools/`
2. Add a link in `index.html` with `href="tools/your-tool.html"`
3. Reference assets with `../assets/` prefix (e.g., `../assets/fonts/fonts.css`)

---

## License

Internal use — AutoNage Lead Operations Automation

*JEJO — Lead Operations Automation*
