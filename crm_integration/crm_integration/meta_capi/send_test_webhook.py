"""
Test Webhook Sender — sends a properly signed POST to the local webhook server.

Usage (from project root, Terminal 2):
    source crm_integration/local.sh
    python3 crm_integration/crm_integration/meta_capi/send_test_webhook.py

Optional overrides:
    META_TEST_LEADGEN_ID=967008122915003 python3 send_test_webhook.py
    META_TEST_PAGE_ID=1774145496137418   python3 send_test_webhook.py
"""

import os, sys, json, hmac, hashlib, urllib.request, urllib.error

# --------------------------------------------------------------------------
# Config — reads from env vars set by local.sh
# --------------------------------------------------------------------------
APP_SECRET  = os.environ.get("META_APP_SECRET", "")
PAGE_ID     = os.environ.get("META_TEST_PAGE_ID",    "1774145496137418")
LEADGEN_ID  = int(os.environ.get("META_TEST_LEADGEN_ID",  "967008122915003"))
FORM_ID     = os.environ.get("META_TEST_FORM_ID",         "1617631612642314")
AD_ID       = os.environ.get("META_TEST_AD_ID",           "120248472991380664")
WEBHOOK_URL = f"http://localhost:{os.environ.get('META_WEBHOOK_PORT', '5055')}/meta/webhook"

# --------------------------------------------------------------------------
# Build payload (same format Meta actually sends)
# --------------------------------------------------------------------------
payload = {
    "object": "page",
    "entry": [{
        "id": PAGE_ID,
        "changes": [{
            "field": "leadgen",
            "value": {
                "leadgen_id": LEADGEN_ID,
                "form_id":    FORM_ID,
                "ad_id":      AD_ID,
                "page_id":    PAGE_ID,
            }
        }]
    }]
}

body = json.dumps(payload, separators=(",", ":"))

# --------------------------------------------------------------------------
# Sign with HMAC-SHA256 (same as Meta signs real webhooks)
# --------------------------------------------------------------------------
if not APP_SECRET:
    print("WARNING: META_APP_SECRET not set — sending without signature (server may reject)")
    signature = "sha256=unsigned"
else:
    signature = "sha256=" + hmac.new(
        APP_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

# --------------------------------------------------------------------------
# Send the request
# --------------------------------------------------------------------------
print("=" * 55)
print("  Meta Webhook Test Sender")
print("=" * 55)
print(f"  URL         : {WEBHOOK_URL}")
print(f"  page_id     : {PAGE_ID}")
print(f"  leadgen_id  : {LEADGEN_ID}")
print(f"  form_id     : {FORM_ID}")
print(f"  Signature   : {signature[:35]}...")
print()

req = urllib.request.Request(
    WEBHOOK_URL,
    data=body.encode("utf-8"),
    headers={
        "Content-Type":        "application/json",
        "X-Hub-Signature-256": signature,
    },
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
        print(f"Response {resp.status}: {json.dumps(result, indent=2)}")
        if result.get("status") == "ok" and result.get("leads_queued", 0) > 0:
            print()
            print("SUCCESS! Lead queued for processing.")
            print("Watch Terminal 1 (where the server runs) for processing logs.")
        else:
            print()
            print("WARNING: Server responded OK but no leads were queued.")
            print("Check the payload — 'field' must be 'leadgen'.")

except urllib.error.HTTPError as e:
    body_text = e.read().decode()
    print(f"HTTP Error {e.code}: {body_text}")
    if e.code == 403:
        print()
        print("HINT: 403 = signature mismatch.")
        print("  Make sure META_APP_SECRET is set:  source crm_integration/local.sh")
    elif e.code == 401:
        print()
        print("HINT: 401 = wrong verify token.")

except ConnectionRefusedError:
    print("ERROR: Cannot connect to http://localhost:5055")
    print("  The webhook server is not running.")
    print("  Start it first:")
    print("    source crm_integration/local.sh")
    print("    lsof -ti:5055 | xargs kill -9 2>/dev/null")
    print("    python3 crm_integration/crm_integration/meta_capi/webhook_server.py")

except Exception as e:
    print(f"ERROR: {e}")
