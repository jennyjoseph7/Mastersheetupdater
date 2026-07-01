"""
check_disposition.py
====================
Finds the session_id for a lead (by phone + campaign_id) and runs
post_session_process to get/trigger disposition.

Usage:
    python3 crm_integration/crm_integration/meta_capi/check_disposition.py
    python3 crm_integration/crm_integration/meta_capi/check_disposition.py --phone 7696770402
"""

import os
import sys
import time
import json
import argparse
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── Config from environment ────────────────────────────────────────────────────
BASE_URL    = os.environ.get("AUTOCRM_BASE_URL",
              "https://autobot-webapp-dev-unstable.gryd.in:60133")
TOKEN       = os.environ.get("AUTOCRM_TOKEN", "")
SESSION_ID  = os.environ.get("AUTOCRM_SESSION_ID", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Session-Id":  SESSION_ID,
    "Content-Type":  "application/json",
}


# ── Step 1: Find session_id for a lead via Gryd task ──────────────────────────

def submit_and_poll(service: str, task_name: str, payload: dict,
                    max_retries=30, interval=2.0) -> dict:
    """Generic Gryd task submit → poll → result."""

    # Submit
    r = requests.post(
        f"{BASE_URL}/gryd/task/{service}/{task_name}",
        json=payload, headers=HEADERS, verify=False, timeout=15,
    )
    r.raise_for_status()
    task_res = r.json()
    task_id  = task_res.get("job", {}).get("task_id") or task_res.get("task_id")
    if not task_id:
        raise RuntimeError(f"No task_id in response: {task_res}")
    logger.info("  Task submitted: task_id=%s", task_id)

    # Poll
    for attempt in range(max_retries):
        time.sleep(interval)
        sr = requests.get(
            f"{BASE_URL}/gryd/status/{task_id}",
            headers=HEADERS, verify=False, timeout=10,
        ).json()
        status = (sr.get("status") or "").lower()
        logger.info("  Attempt %d — status: %s", attempt + 1, status)
        if status in ("success", "completed"):
            break
        if status in ("failed", "error"):
            raise RuntimeError(f"Task failed: {sr}")
    else:
        raise RuntimeError(f"Task {task_id} timed out after {max_retries} retries")

    # Result
    rr = requests.get(
        f"{BASE_URL}/gryd/result/{task_id}",
        headers=HEADERS, verify=False, timeout=10,
    ).json()
    return rr.get("result", rr)


# ── Step 2: Get session via get_lead_session Gryd task ────────────────────────

def get_session_id_for_lead(lead_id: str) -> str | None:
    """
    Calls the server to fetch contact_status rows for a lead_id.
    Returns the session_id (message_id) of the most recent completed session.
    """
    logger.info("Step 1 — Looking up session for lead_id=%s", lead_id)
    try:
        result = submit_and_poll(
            service="autocrm-cron",
            task_name="get_lead_session",
            payload={
                "args": [lead_id],
                "kwargs": {},
                "runtime_limit": 15000,
            }
        )
        logger.info("  get_lead_session result: %s", json.dumps(result, indent=2))
        if isinstance(result, dict):
            return result.get("session_id") or result.get("message_id")
        if isinstance(result, list) and result:
            return result[0].get("session_id") or result[0].get("message_id")
    except Exception as e:
        logger.warning("  get_lead_session task failed (%s) — will try direct model query.", e)

    # Fallback: try direct model list (may or may not be exposed)
    try:
        r = requests.get(
            f"{BASE_URL}/gryd/model/autocrm-campaign/contact_status",
            params={"lead_id": lead_id, "limit": 5},
            headers=HEADERS, verify=False, timeout=10,
        )
        if r.status_code == 200:
            rows = r.json()
            rows = rows if isinstance(rows, list) else rows.get("results", [])
            for row in rows:
                if row.get("provider_status") == "contacted":
                    sid = row.get("message_id") or row.get("session_id")
                    logger.info("  Found completed session_id=%s via model API", sid)
                    return sid
    except Exception as e2:
        logger.warning("  Direct model query also failed: %s", e2)

    return None


# ── Step 3: Call post_session_process via Gryd task ───────────────────────────

def run_post_session_process(session_id: str) -> dict:
    """
    Triggers post_session_process on the server for the given session_id.
    Returns the disposition and summary.
    """
    logger.info("Step 2 — Running post_session_process for session_id=%s", session_id)
    result = submit_and_poll(
        service="autocrm-conversation-post-process",
        task_name="post_session_process",
        payload={
            "args": [],
            "kwargs": {"session_id": session_id},
            "runtime_limit": 60000,
            "cancellable": True,
        },
        max_retries=60,
        interval=3.0,
    )
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Check/trigger disposition for a lead.")
    parser.add_argument("--phone",       default="7696770402",
                        help="Phone number used in the test lead")
    parser.add_argument("--campaign-id", default="54f3b91c-c8ac-3d2b-900e-5629102c7d3f",
                        help="Campaign ID")
    parser.add_argument("--dealership",  default="dave-ai-india",
                        help="Dealership ID")
    parser.add_argument("--name",        default="priyanshul",
                        help="Lead name (lowercase, no spaces in lead_id)")
    parser.add_argument("--session-id",  default=None,
                        help="Provide session_id directly to skip Step 1")
    args = parser.parse_args()

    # Construct lead_id (same pattern as the server)
    phone_clean = args.phone.lstrip("+").replace(" ", "")
    name_clean  = args.name.lower().replace(" ", "-")
    lead_id     = f"{name_clean}-{phone_clean}--{args.dealership}-{args.campaign_id}"

    print("\n" + "="*65)
    print("  AutoNgage — Disposition Checker")
    print("="*65)
    print(f"  lead_id     : {lead_id}")
    print(f"  session_id  : {args.session_id or '(will look up)'}")
    print("="*65 + "\n")

    if not TOKEN or not SESSION_ID:
        logger.error("AUTOCRM_TOKEN and AUTOCRM_SESSION_ID must be set in env (source crm_integration/local.sh)")
        sys.exit(1)

    # Step 1 — Get session_id
    session_id = args.session_id
    if not session_id:
        session_id = get_session_id_for_lead(lead_id)

    if not session_id:
        print("\n❌ Could not find a completed session for this lead.")
        print("   Possible reasons:")
        print("   - Call has not been made yet (check campaign calling hours)")
        print("   - Call was made but marked 'busy' or 'no-answer' — no transcript to process")
        print("   - The session_id task endpoint is not exposed on this server")
        print("\n   ➡ Ask Ananth to run:")
        print(f"     SELECT message_id, provider_status FROM contact_status WHERE lead_id='{lead_id}';")
        print("     Then re-run: python3 check_disposition.py --session-id <message_id>")
        sys.exit(0)

    logger.info("Using session_id=%s", session_id)

    # Step 2 — Run post_session_process
    try:
        result = run_post_session_process(session_id)
        print("\n" + "="*65)
        print("  post_session_process Result")
        print("="*65)
        print(f"  Disposition  : {result.get('disposition') or result.get('new_disposition') or 'see full result'}")
        print(f"  Summary      : {result.get('summary') or result.get('lead_summary') or 'N/A'}")
        print(f"  Full result  :")
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(f"\n❌ post_session_process failed: {e}")
        print("\n   The session may not have a valid transcript yet.")
        print("   If the call was 'busy', there's no transcript → no disposition to process.")


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings()
    main()
