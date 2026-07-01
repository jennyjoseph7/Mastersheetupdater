# Google Sheet CRM Integration — README

## Overview

This integration connects a Google Sheet (customer data source) with the AutoNgage AI voice calling system. When a campaign runs, leads are read from the sheet, voice calls are triggered, and results (disposition, summary, sentiment) are written back to the same sheet automatically.

---

## Architecture

```
Google Sheet (customer rows)
  ↓ read_leads_from_sheet()
cron/cron.py → process_crm_campaigns()
  ↓ _trigger_audience_task()
AI Voice Call (Airtel/AutoNgage)
  ↓ contact_status table (DB)
_poll_and_post_process_session()
  ↓ session.history (DB)
post_session_process()   → LLM disposition + summary
  ↓ update_lead_in_sheet() [async task]
GoogleDocsCRM.update_row_by_phone_number()
  ↓
Google Sheet row updated
```

---

## Files & Functions

### `crm_integration/crm_integration/connectors/google_docs_crm.py`

| Function | Purpose |
|---|---|
| `__init__(sheet_name)` | Authenticates via service account, opens spreadsheet by title, selects first tab (`.sheet1`) |
| `get_sheet_headers()` | Returns row 1 of the sheet as a list |
| `read_leads_from_sheet(batch_size, status_filter)` | Reads all rows, filters already-processed leads (Status = QUEUED/CONTACTED/etc.) |
| `update_row_by_phone_number(phone_number, data)` | Finds row(s) by "Mobile Number", writes each key in `data`. Auto-creates column if missing |
| `update_status_for_matching_rows(search_data, status)` | Updates only the "Status" column |
| `normalize_row(row_dict)` | Maps sheet column names → internal field names using `HEADER_MAPPING` |

### `crm_integration/crm_integration/load_crm.py`

```python
load_crm("googledocs", sheet_name="My Sheet Name")
# → returns GoogleDocsCRM("My Sheet Name")
# Fallback if sheet_name=None: "Ambal Sanganur Post-sales"
```

### `crm_integration/autoengage_crm_worker.py`

| Task | Purpose |
|---|---|
| `fetch_crm_leads(campaign_id, crm_name, sheet_name)` | Pulls new leads from the sheet |
| `update_lead_in_crm(crm_name, sheet_name, phone_number, status)` | Updates Status column after lead is triggered |
| `update_lead_in_sheet(sheet_name, phone_number, **kwargs)` | Main write-back task. Writes disposition, summary, sentiment etc. |

### `cron/cron.py`

| Function | Purpose |
|---|---|
| `process_crm_campaigns(batch_size)` | Top-level cron. Finds active campaigns, fetches leads, triggers calls |
| `_trigger_audience_task(lead, campaign)` | Queues an AI voice call, returns `lead_id` |
| `_poll_and_post_process_session(lead_id, logger)` | Polls `contact_status` every 5s, reads `session.history`, triggers `post_session_process` |

### `conversation/lead_post_processing.py`

| Function | Purpose |
|---|---|
| `post_session_process(session_id)` | Runs LLM → disposition, lead_summary, sentiment. Dispatches `update_lead_in_sheet` async task |

---

## Authentication

- **Library:** `gspread` + `google.oauth2.service_account`
- **Credentials file:** `crm_integration/crm_integration/credentials.json`
- **Scopes:** `spreadsheets` + `drive`

The spreadsheet **must be shared** with the `client_email` inside `credentials.json` as **Editor**.

```python
# google_docs_crm.py
creds  = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(creds)
self.sheet = client.open(sheet_name).sheet1   # opens by title, always uses first tab
```

---

## Configuration

Sheet name is stored in the campaign DB record:

```json
{
  "crm_source_details": {
    "crm_name": "googledocs",
    "sheet_url": "Ambal Sanganur Post-sales"
  }
}
```

`sheet_url` must match the **exact Google Spreadsheet title** (case-sensitive, not a tab name, not a URL).

---

## Column Mapping

| Sheet Column | Internal Field | Direction |
|---|---|---|
| `Mobile Number` | `phone_number` | Read + Match |
| `Cust. Name` | `person_name` | Read |
| `Model Name` | `vehicle_model` | Read |
| `Status` | `status` | Read + Write |
| `Disposition` | `disposition` | Write |
| `Sentiment` | `sentiment` | Write |
| `Lead Summary` | `lead_summary` | Write |
| `Call Duration` | `call_duration` | Write |

Unknown keys auto-create new columns in row 1.

---

## Environment Variables

```bash
source crm_integration/local.sh

export GCP_SECRET="autocrm"               # DB pointer
export META_PIXEL_ID="..."                 # for Meta CAPI only
export META_CAPI_ACCESS_TOKEN="..."        # for Meta CAPI only
export META_PAGE_ACCESS_TOKEN="..."        # for webhook flow only
export META_WEBHOOK_VERIFY_TOKEN="..."     # for webhook verification only
```

---

## How to Run

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents
source crm_integration/local.sh

python3 -c "
from cron.cron import process_crm_campaigns
import logging
logging.basicConfig(level=logging.INFO)
result = process_crm_campaigns(batch_size=1, logger=logging.getLogger('test'))
print('Result:', result)
"
```

---

## Testing

### TEST 1 — Sheet: Read leads

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents && source crm_integration/local.sh && python3 -c "
import sys; sys.path.insert(0, 'crm_integration')
from crm_integration.crm_integration.connectors.google_docs_crm import GoogleDocsCRM

crm = GoogleDocsCRM('Ambal Sanganur Post-sales')
headers = crm.get_sheet_headers()
print('Headers:', headers)
for h in ['Mobile Number', 'Status', 'Cust. Name']:
    assert h in headers, f'FAIL: missing header: {h}'
print('✅ Required headers present')

leads = crm.read_leads_from_sheet(batch_size=3)
print(f'Fetched {len(leads)} new leads:')
for l in leads:
    print(f'  phone={l.get(\"phone_number\")}  name={l.get(\"person_name\")}  status={l.get(\"status\")}')
"
```

### TEST 2 — Sheet: Write-back a test row

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents && source crm_integration/local.sh && python3 -c "
import sys; sys.path.insert(0, 'crm_integration')
from crm_integration.crm_integration.connectors.google_docs_crm import GoogleDocsCRM

crm = GoogleDocsCRM('Ambal Sanganur Post-sales')
result = crm.update_row_by_phone_number(
    phone_number='7696770402',
    data={'Disposition': 'test_staging_run', 'Lead Summary': 'Automated test — ignore', 'Sentiment': 'neutral'}
)
print('Result:', result)
assert result.get('updated') == True
print('✅ Write-back successful')
"
```

### TEST 3 — DB: contact_status table reachable

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents && source crm_integration/local.sh && python3 -c "
from autocrm_db_helper import get_pg_connector

with get_pg_connector() as pg:
    rows = pg.fetch_all('SELECT lead_id, provider_status, created FROM contact_status ORDER BY created DESC LIMIT 5')
    for r in rows: print(r)
print('✅ contact_status reachable')
"
```

### TEST 4 — DB: session history transcript

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents && source crm_integration/local.sh && python3 -c "
from autocrm_db_helper import get_pg_connector

SESSION_ID = 'REPLACE-WITH-REAL-SESSION-ID'

with get_pg_connector() as pg:
    session = pg.get('session', 'session_id', SESSION_ID)
    history = session.get('history', []) if session else []
    valid   = [m for m in history if m.get('message', '').strip()]
    print(f'Total messages: {len(history)}  Valid: {len(valid)}')
    print('✅ Ready' if len(valid) >= 3 else '⚠️  Less than 3 messages')
"
```

### TEST 5 — post_session_process: Manual trigger

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents && source crm_integration/local.sh && python3 -c "
from conversation.lead_post_processing import post_session_process
import logging; logging.basicConfig(level=logging.INFO)

SESSION_ID = 'REPLACE-WITH-REAL-SESSION-ID'

result = list(post_session_process(session_id=SESSION_ID))
print('Result:', result)
print('✅ Check Google Sheet — Disposition/Summary/Sentiment should be filled')
"
```

### TEST 6 — Meta CAPI: Push test event

```bash
cd /Users/priyanshulkumar/DaveAi/autobot_agents && source crm_integration/local.sh && python3 -c "
import sys, logging; sys.path.insert(0, 'crm_integration')
from crm_integration.crm_integration.meta_capi.tasks import push_capi_lead_event
logging.basicConfig(level=logging.INFO)

result = list(push_capi_lead_event(
    phone_number='+917696770402', disposition='engaged', email='',
    name='Staging Test', facebook_lead_id=None,
    lead_event_source='DaveAI Staging Test',
    logger=logging.getLogger('test_capi')
))
print('Result:', result)
print('✅ Check Meta Events Manager → Test Events tab')
"
```

### Run all tests at once:

```bash
bash crm_integration/run_tests.sh
```

---

## Edge Cases

### 🔴 Critical

| # | Scenario | Behaviour | Action |
|---|---|---|---|
| 1 | Same phone+campaign triggered multiple times (deterministic `lead_id`) | `list_order_by(order_by="created") + cs[0]` picks latest row | **Verify sort is DESC** — `cs[0]` must be newest, not oldest |
| 2 | Call ends as `busy`/`attempted` (unanswered) | Poll loops until 600s timeout, exits, no sheet update | Lead stays NEW in sheet. Retry logic needed |
| 3 | Wrong `GCP_SECRET` (wrong DB) | Fast-fail at top of poll function exits in <5s | Check `GCP_SECRET` env var |
| 4 | `post_session_process` throws exception | Error logged, `return` called, sheet NOT updated | Check worker logs for full traceback |
| 5 | Phone format mismatch (sheet: `9876543210`, system: `+91...`) | No normalization — comparison fails silently | Ensure phone in sheet exactly matches what system passes |
| 6 | Spreadsheet title mismatch | `SpreadsheetNotFound` in async task | Title in `crm_source_details.sheet_url` must match exactly |

### 🟡 Medium

| # | Scenario | Risk |
|---|---|---|
| 7 | Transcript < 3 valid messages (call dropped immediately) | Poll retries until timeout. No disposition written |
| 8 | Service account not given Editor access on sheet | `APIError 403` in async worker. No sheet update |
| 9 | `batch_size > 1` (multiple simultaneous leads) | Each call blocks cron up to 600s. Total wait = 600s × batch_size |
| 10 | Sheets API rate limit (100 read+write / 100s) | `APIError 429`. Add exponential backoff |
| 11 | Duplicate phone numbers in sheet | All matching rows get updated with same disposition |
| 12 | Two async `update_lead_in_sheet` tasks race on same session | Both may try to create the same new column → duplicate headers |
| 13 | `crm_source_details` missing or `sheet_url` empty | Guard `if crm_sheet and crm_phone:` skips update silently |

### 🟢 Low

| # | Scenario | Notes |
|---|---|---|
| 14 | Lead already QUEUED/CONTACTED | Filtered out by `read_leads_from_sheet`. No duplicate call |
| 15 | Sheet has zero new leads | Exits cleanly with 0 leads processed |
| 16 | Meta lead with no `facebook_lead_id` | CAPI fires but Meta can't attribute to specific ad |
| 17 | `post_session_process` runs twice (cron restart mid-poll) | Row updated twice (idempotent). LLM called twice (extra cost) |

---

## Staging Checklist

```
□ 1.  TEST 1 passes        — sheet auth and headers OK
□ 2.  TEST 2 passes        — write-back works
□ 3.  TEST 3 passes        — contact_status reachable on staging DB
□ 4.  TEST 4 passes        — session.history has >= 3 valid messages
□ 5.  TEST 5 passes        — post_session_process completes without error
□ 6.  Full E2E call placed — phone rings with AI voice
□ 7.  Poll waits correctly — "No contact_status found, waiting..." while ringing
□ 8.  Session detected     — "Session completed — status=contacted" in logs
□ 9.  Sheet updated        — Disposition + Lead Summary + Sentiment columns filled
□ 10. Status updated       — Status column shows CONTACTED
□ 11. No re-trigger        — Running cron again skips the contacted lead
□ 12. Unanswered call      — Timeout exits cleanly after 600s, no crash
□ 13. Wrong DB fast-fail   — Set wrong GCP_SECRET, confirm exit in < 5s
```

---

## How to Switch to a Different Sheet

1. Update `crm_source_details.sheet_url` on the campaign DB record → new spreadsheet title
2. Share the new spreadsheet with the `client_email` in `credentials.json` as **Editor**
3. Ensure customer data is on the **first tab** (system always uses `.sheet1`)
4. Verify required headers exist: `Mobile Number`, `Status`, `Cust. Name`

**No code changes required** if the data is on the first tab.

---

## Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `SpreadsheetNotFound` | Title typo in `crm_source_details.sheet_url` | Match exact spreadsheet title |
| `APIError 403` | Service account not shared on sheet | Add `client_email` as Editor |
| `Column 'Mobile Number' not found` | Header missing or spelled differently | Check row 1 of the sheet |
| `Timed out after 600s` | Call went unanswered (busy/attempted) | Check Airtel/voice logs |
| `DB table missing` | Wrong `GCP_SECRET` | Set `GCP_SECRET=autocrm` |
| `post_session_process failed` | LLM or DB error | Check worker logs for traceback |
