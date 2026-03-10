# Disposition Sync — JEJO Lead Operations Automation

## What This Is

A single-file browser tool (`disposition_sync_v2.html`) that takes two AutoEngage export files, merges them by phone number, applies all business logic, and produces a fully populated table ready to copy-paste directly into the Zoho Master Sheet. No backend. No Python. No installation. Open in any browser.

---

## Files

| File | Purpose |
|---|---|
| `disposition_sync_v2.html` | The entire tool — UI + logic in one file |
| `README.md` | This file |

---

## Inputs

### File 1 — Audience & Leads Export
Downloaded from AutoEngage → Audience & Leads section.

Columns used:

| AutoEngage Column | Used For |
|---|---|
| `person_name` | Full_Name |
| `phone_number` | Phone (match key) |
| `city` | City |
| `campaign_id` | Campaign_ID |
| `lead_source` | Lead_Source |
| `disposition` | Disposition + Outcome + SUMMARY logic |
| `updated` | Call_Date |
| `interested_vehicle_name` | Model |
| `seating_capacity_preference` | Seating (primary source) |
| `lead_summary` | SUMMARY fallback if File 2 has none |

### File 2 — Sessions Export
Downloaded from AutoEngage → Sessions section.

Columns used:

| AutoEngage Column | Used For |
|---|---|
| `phone_number` | Match key to join with File 1 |
| `created` | Call Triggered (min and max time) |
| `start_time` | Call Triggered fallback |
| `summary` | SUMMARY |
| `call_recording` | Recordings |
| `sentiment_score` | SENTIMENT |

---

## Output Columns

Exact column order matching the Zoho Master Sheet:

| # | Column | Source | Logic |
|---|---|---|---|
| 1 | Lead_ID | — | Left blank. Filled manually in Zoho. |
| 2 | Full_Name | File 1 `person_name` | Direct copy |
| 3 | Phone | File 1 `phone_number` | Normalized to 10 digits |
| 4 | City | File 1 `city` | Direct copy |
| 5 | Pincode | — | Left blank. Not in either export file. |
| 6 | Lead_Source | File 1 `lead_source` | Direct copy |
| 7 | Campaign_ID | File 1 `campaign_id` | Direct copy |
| 8 | Call Triggered | File 2 `created` / `start_time` | See formula below |
| 9 | Outcome | File 1 `disposition` | See formula below |
| 10 | Disposition | File 1 `disposition` | Deduplicated by priority |
| 11 | SUMMARY | File 2 `summary` | See formula below |
| 12 | Call_Date | File 1 `updated` | Parsed as DD/MM/YYYY |
| 13 | Number of attempts | File 1 `phone_number` | See formula below |
| 14 | SENTIMENT | File 2 `sentiment_score` | Direct copy |
| 15 | Recordings | File 2 `call_recording` | Direct URL copy |
| 16 | Model | File 1 `interested_vehicle_name` | Direct copy |
| 17 | Seating | File 1 `seating_capacity_preference` | See formula below |
| 18 | Exclusion_Flag | Derived from Disposition priority | YES for terminal dispositions |

---

## Formulas and Business Logic

### Phone Normalization
Applied to both File 1 and File 2 before any matching.
```
1. Strip all non-digit characters (spaces, +, -, brackets)
2. If starts with "91" and total length is 12 → remove first 2 digits
3. If starts with "0" and total length is 11 → remove first digit
4. Result must be exactly 10 digits → valid phone
5. Anything else → null (excluded from output)
```
Example: `+91 98765 43210` → `9876543210`

---

### Call Triggered
Reads all `created` (or `start_time`) timestamps from the entire File 2.
Finds the minimum (earliest) and maximum (latest) timestamps across the full batch.
Formats as:
```
{ordinal day} {Month} Calls Triggered From {min time} - {max time}
```
Example: `9th March Calls Triggered From 7:19pm - 7:31pm`

Date parsing handles AutoEngage format `DD/MM/YYYY, H:MM:SS am/pm` explicitly.
JavaScript's native `new Date()` is NOT used for parsing because it assumes MM/DD/YYYY
which would misread `9/3/2026` as September 3rd instead of March 9th.

---

### Outcome
Equivalent Zoho formula:
```
=IF(OR(TRIM(LOWER(Disposition))="contacted", TRIM(LOWER(Disposition))="engaged",
       TRIM(LOWER(Disposition))="converted", TRIM(LOWER(Disposition))="attempted"),
   "Connected", "Not Connected")
```

---

### Disposition Deduplication
A lead may appear multiple times in File 1 (called on different dates).
One row per unique phone is kept. The row with the highest priority disposition wins.

Priority table:

| Priority | Disposition | Type |
|---|---|---|
| 10 | Test Drive Booked | Terminal |
| 10 | Converted | Terminal |
| 9 | Not Interested | Terminal |
| 9 | DND | Terminal |
| 9 | Wrong Number | Terminal |
| 8 | Interested | Interim |
| 6 | Callback Requested / Call Back | Interim |
| 4 | Busy | Interim |
| 3 | Not Connected / No Revert | Interim |
| 2 | User Did Not Speak | Interim |
| 1 | Any unlisted value | Interim |

Terminal dispositions (priority ≥ 9) set `Exclusion_Flag = YES`.

---

### SUMMARY
```
if disposition in ['busy', 'not connected', 'no revert', 'user did not speak']:
    SUMMARY = "No response"
else:
    SUMMARY = File 2 session summary
    if File 2 summary is empty:
        SUMMARY = File 1 lead_summary
    if both empty:
        SUMMARY = ""
```

---

### Number of Attempts
Count of how many rows in File 1 share the same normalized phone number.

---

### Seating
```
if File 1 seating_capacity_preference is not empty → use it directly
else derive from model name:
    basalt         → "5 Seater"
    aircross / c3  → "5 Seater & 7 Seater"
    meridian / jeep→ "5 Seater & 7 Seater"
    else           → ""
```

---

### File 2 Session Matching
Each phone in File 1 may have multiple session rows in File 2.
Selection priority:
```
1. Session with a non-empty call_recording URL
2. Session with a non-empty summary
3. Most recent session (last row)
```

---

### CSV Column Shift Bug Fix
File 2 contains a `history` column with JSON data inside it (quotes and commas).
XLSX.js misparses this when reading CSV, shifting all subsequent column positions.

Fix applied:
- Phone detection scans all values in the row for a 10-12 digit number pattern.
- Recording detection scans all values for any string containing `cloudphone` or `/recording`.
- Date detection scans all values for strings matching `DD/MM/YYYY` pattern.

---

## How to Use

1. Export **Audience & Leads** from AutoEngage — save as File 1
2. Export **Sessions** from AutoEngage — save as File 2
3. Open `disposition_sync_v2.html` in any browser (Chrome recommended)
4. Upload File 1 in the left zone, File 2 in the right zone
5. Click **Process Both Files**
6. Click **Copy All Data**
7. Open Zoho Master Sheet → click the first empty row → **Ctrl+V**

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | HTML + CSS (no framework) |
| Logic | Vanilla JavaScript (ES6+) |
| File parsing | XLSX.js v0.18.5 (via CDN) |
| Clipboard | `navigator.clipboard` with `execCommand` fallback for `file://` protocol |
| Fonts | Google Fonts — Sora + DM Mono |
| Hosting | None needed — runs entirely in browser |

---

## Known Limitations

- Pincode is not present in either AutoEngage export file. Must be filled manually in Zoho.
- Lead_ID is not generated. Must be assigned manually in Zoho.
- SENTIMENT and Recordings will be empty for sessions where AutoEngage did not capture them.
- Table preview is capped at 200 rows for performance. Full data is always in the copied TSV.
- Only tested with AutoEngage CSV exports. XLSX export from AutoEngage may behave differently.

---

## Phase Roadmap

| Phase | What | Status |
|---|---|---|
| 1 | Disposition sync browser tool (this file) | ✅ Done |
| 2 | LLM-based transcript intelligence — summary + intent detection from raw conversation text | Planned |
| 3 | Disposition accuracy evaluation — precision, recall, confusion matrix of LLM-suggested vs ground truth | Planned |

---

*JEJO — Lead Operations Automation*  
*AI/ML Intern: Kanniga (Jenny Joseph K.) | March 2026*
