# Design System: AutoNage Lead Operations
**Project ID:** AutoNage-LeadOps-Web

## 1. Visual Theme & Atmosphere
The AutoNage interface is precision-engineered for automotive dealership operations and lead engineering workflows. The atmosphere is **technical, high-contrast, and focused**, eliminating extraneous decoration to maximize information density, caller audit clarity, and operational throughput.

* **Dark Theme (Default):** Deep obsidian background (`#080b10`) with elevated midnight-slate cards (`#10151d`), subtle border strokes (`rgba(218, 230, 242, 0.09)`), and high-vibrancy chromatic accents.
* **Light Theme:** Crisp alabaster canvas (`#f3f5f8`) with pure white elevated panels (`#ffffff`) and deep slate typography (`#1a1e26`).
* **Visual Hierarchy:** Chromatic color coding identifies distinct operational workflows instantly across the landing hub, top navigation, status chips, dropzones, and action buttons.

---

## 2. Color Palette & Roles

### Global Core Tokens
* **Dark Background Canvas:** Pitch Obsidian (`#080b10`) — Primary viewport background.
* **Dark Surface (Cards/Panels):** Midnight Slate (`#10151d`) — Primary container and modal background.
* **Dark Elevated Surface:** Deep Navy Charcoal (`#151c27`) — Secondary containers, tables, dropzones, and button backgrounds.
* **Dark Surface Border:** Faint Luminescent Stroke (`rgba(218, 230, 242, 0.09)`) — Crisp component delineation without visual clutter.
* **Primary Text:** Warm Off-White (`#f4f0e8`) — Primary headings, high-priority labels, and active states.
* **Text Dim:** Neutral Silver-Ash (`#aeb8c3`) — Secondary descriptions, captions, and table cell details (9.1:1 contrast).
* **Text Muted:** WCAG AA Accessible Slate (`#7e8a97`) — Form helper labels, step tags, and tertiary metadata (≥ 4.5:1 contrast).
* **Functional Success:** Mint Emerald (`#63d6a3` dark / `#1a9960` light) — Validated files, completed matches, ready states.
* **Functional Warning:** Solar Amber (`#ffc857` dark / `#c89520` light) — Partial matches, format warnings, template updates.
* **Functional Danger:** Crimson Coral (`#ff6b6b` dark / `#d63636` light) — Parse failures, missing columns, error states.

### Tool-Specific Chromatic Architecture (11 Unique Accents)
Each operational tool commands a dedicated accent hue maintained identically across its hub card, top header nav indicator, active badges, dropzone borders, and primary CTA.
> **Status Note**: Currently 8 tools are actively exposed in frontend navigation. 3 tools (*Dashboard*, *Campaign Generator*, and *Master Matcher*) are disabled from frontend navigation and guarded with root redirects.

1. **Pre-Sales Sync — Crimson Blaze** *(Active)*
   * Dark Accent: `#ef4444` | Soft Tint: `rgba(239, 68, 68, 0.13)` | Light Accent: `#dc2626`
   * *Role:* Pre-sales AutoEngage audience and session batch consolidation.
2. **Post-Sales Sync — Safety Orange** *(Active)*
   * Dark Accent: `#f97316` | Soft Tint: `rgba(249, 115, 22, 0.13)` | Light Accent: `#ea580c`
   * *Role:* Dealership service reminder and post-service feedback row generation.
3. **Master Matcher — Electric Indigo** *(Disabled from frontend)*
   * Dark Accent: `#7679f5` | Soft Tint: `rgba(118, 121, 245, 0.14)` | Light Accent: `#4f46e5`
   * *Role:* Clubbing raw client spreadsheets with processed master sheets via registration/phone keys.
4. **Re-Attempt Filter — Hot Flamingo Pink** *(Active)*
   * Dark Accent: `#ec4899` | Soft Tint: `rgba(236, 72, 153, 0.13)` | Light Accent: `#db2777`
   * *Role:* Filtering multi-day connected leads to isolate pristine re-attempt batches.
5. **Formatter — Sunburst Amber** *(Active)*
   * Dark Accent: `#eab308` | Soft Tint: `rgba(234, 179, 8, 0.13)` | Light Accent: `#8a6d05`
   * *Role:* Mapping client columns into dealership-wise AutoEngage templates.
6. **Campaign Generator — Mint Teal** *(Disabled from frontend)*
   * Dark Accent: `#5eead4` | Soft Tint: `rgba(94, 234, 212, 0.12)` | Light Accent: `#0d9488`
   * *Role:* 20-field structured campaign objectives for voice AI and WhatsApp outbound flows.
7. **Recording Renamer — Vivid Emerald** *(Active)*
   * Dark Accent: `#22c55e` | Soft Tint: `rgba(34, 197, 94, 0.13)` | Light Accent: `#16a34a`
   * *Role:* Fetching call recording audio URLs and batch exporting renamed audio archives.
8. **Call Summary — Royal Amethyst** *(Active)*
   * Dark Accent: `#a855f7` | Soft Tint: `rgba(168, 85, 247, 0.12)` | Light Accent: `#7c3aed`
   * *Role:* Daily disposition telemetry, connectivity stats, and KPI reporting.
9. **Dashboard — Cobalt Blue** *(Disabled from frontend)*
   * Dark Accent: `#3b82f6` | Soft Tint: `rgba(59, 130, 246, 0.13)` | Light Accent: `#2563eb`
   * *Role:* Holistic campaign visualization, chart generation, and follow-up analytics.
10. **Session Report — Cerulean Sky** *(Active)*
    * Dark Accent: `#0ea5e9` | Soft Tint: `rgba(14, 165, 233, 0.14)` | Light Accent: `#0284c7`
    * *Role:* Caller audio performance audits, connection duration tracking, and agent telemetry.
11. **Credit Report — Radiant Lime** *(Active)*
    * Dark Accent: `#84cc16` | Soft Tint: `rgba(132, 204, 22, 0.14)` | Light Accent: `#65a30d`
    * *Role:* Bot billing CSV processing, objective-level voice/WhatsApp expense reconciliation.

---

## 3. Typography Rules
* **Display & Headings:** `Manrope`, `Inter`, sans-serif. Tight tracking (`-0.03em` to `-0.05em`), extra-bold weight (700 to 800) for authoritative hierarchy.
* **Body & Forms:** `Inter`, sans-serif. Normal tracking, regular (400) to medium (500) weights for extended readability on dense data grids.
* **Monospace Data:** `IBM Plex Mono`, monospace. Used strictly for numeric KPI stat values, phone numbers, vehicle registration codes, JSON keys, and file schemas.

---

## 4. Component Stylings
* **Buttons:**
  * Primary Action: Radiused pill (`border-radius: 8px` to `12px`), gradient fill using the tool's chromatic accent, crisp white text (`#ffffff`), subtle elevation shadow.
  * Primary Disabled: Tool accent background retained, high-contrast dark text (`#1a1e26`), lowered opacity (`0.55`).
  * Secondary / Utility: Surface-backed with thin border stroke (`1px solid var(--border)`), hover elevation with tool accent border color.
* **Cards / Containers:**
  * Hub Cards: Subtly rounded corners (`border-radius: 22px`), dark surface fill, gentle hover translation (`translateY(-2px)`), chromatically tinted border and shadow glow matching the tool's accent hue.
  * Panels: Generously rounded (`border-radius: 16px` to `18px`), glass-sheen borders, padding `1.25rem` to `1.5rem`.
* **Inputs & Dropzones:**
  * Inputs: Inset dark background (`var(--surface2)` or `var(--bg)`), rounded (`8px` to `10px`), accented focus ring.
  * Dropzones: Distinctive dashed border (`2px dashed var(--border)`), generous padding, hover and drag-over transitions illuminating the tool's chromatic accent tint. Hidden native file inputs explicitly labeled with `aria-label` for full screen-reader compliance.

---

## 5. Layout Principles
* **Mobile-Responsive Clamping:** Full viewport containment via `overflow-x: clip;` on root containers.
* **Header & Navigation:** Sticky top header with brand logo, 11-tool scrollable pill navigation, and theme toggle. Header inner layout wraps to vertical stack with touch-scrolling links below `640px` breakpoint.
* **Data Grids:** Responsive desktop multi-column layouts collapsing gracefully to single-column streams on mobile screens (`≤ 640px`).
* **Hub Grid System:** Desktop layout utilizing `grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))` ensuring completely aligned, uniform card heights and 1-sentence descriptions without ragged rows.

