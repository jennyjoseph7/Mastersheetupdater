"""
meta_webhook_config — Seed / Management Helper
================================================
Creates and manages the Meta page_id -> AutoNgage campaign mapping.

Storage priority (most reliable first):
  1. DB (meta_webhook_config table) — used in production / when GCP creds available
  2. Local JSON file (config/meta_webhook_config.json) — used locally without GCP creds

The webhook server (_get_webhook_config) reads from DB first, then JSON file,
then falls back to META_TEST_* env vars.

Usage:
    # From project root — seeds the JSON file locally:
    source crm_integration/local.sh
    export META_TEST_DEALERSHIP_ID=petromin-sa
    export META_TEST_CAMPAIGN_OBJECTIVE_ID=pre-sales-test-drive
    python3 seed/meta_webhook_config_seed.py

    # View what's stored:
    python3 seed/meta_webhook_config_seed.py --list

    # OR call functions directly from code:
    from seed.meta_webhook_config_seed import upsert_config, list_configs
    upsert_config(
        page_id               = '1774145496137418',
        dealership_id         = 'petromin-sa',
        campaign_id           = '120248254600500664',
        campaign_objective_id = 'pre-sales-test-drive',
        campaign_type         = 'pre-sales',
        dealership_name       = 'Petromin Saudi Arabia',
    )
    list_configs()
"""

import os
import sys
import time
import json
import uuid
import logging

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("meta_webhook_config_seed")

# Path to local JSON config file (used when DB is unavailable)
LOCAL_CONFIG_PATH = os.path.join(_ROOT, "config", "meta_webhook_config.json")


# ---------------------------------------------------------------------------
# JSON file storage (local dev, no GCP auth required)
# ---------------------------------------------------------------------------

def _load_json_store() -> list:
    """Load all configs from the local JSON file. Returns empty list if not found."""
    if not os.path.exists(LOCAL_CONFIG_PATH):
        return []
    try:
        with open(LOCAL_CONFIG_PATH, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Could not read %s: %s", LOCAL_CONFIG_PATH, exc)
        return []


def _save_json_store(rows: list):
    """Persist all configs to the local JSON file."""
    os.makedirs(os.path.dirname(LOCAL_CONFIG_PATH), exist_ok=True)
    with open(LOCAL_CONFIG_PATH, "w") as f:
        json.dump(rows, f, indent=2, default=str)
    logger.info("Saved %d config(s) to %s", len(rows), LOCAL_CONFIG_PATH)


def _upsert_json(config: dict) -> dict:
    """Insert or update a config row in the JSON file store."""
    rows = _load_json_store()
    existing_idx = next(
        (i for i, r in enumerate(rows) if r.get("page_id") == config["page_id"]),
        None,
    )
    if existing_idx is not None:
        old = rows[existing_idx]
        config["config_id"]  = old.get("config_id", config["config_id"])
        config["created_at"] = old.get("created_at", config["created_at"])
        rows[existing_idx] = config
        logger.info("Updated JSON config for page_id=%s", config["page_id"])
    else:
        rows.append(config)
        logger.info("Inserted JSON config for page_id=%s", config["page_id"])
    _save_json_store(rows)
    return config


# ---------------------------------------------------------------------------
# DB storage (production — requires GCP credentials)
# ---------------------------------------------------------------------------

def _try_db_upsert(config: dict) -> bool:
    """
    Try to upsert config into Postgres DB.
    Returns True on success, False if DB is unavailable (GCP auth fails locally).
    """
    try:
        from autocrm_db_helper import get_pg_connector
        with get_pg_connector() as pg:
            existing = list(pg.list("meta_webhook_config", {"page_id": config["page_id"]}))
            if existing:
                old = existing[0]
                config["config_id"]  = old.get("config_id", config["config_id"])
                config["created_at"] = old.get("created_at", config["created_at"])
                pg.update("meta_webhook_config", "config_id", old["config_id"], config)
                logger.info("DB: Updated config for page_id=%s", config["page_id"])
            else:
                pg.post("meta_webhook_config", config)
                logger.info("DB: Inserted config for page_id=%s", config["page_id"])
        return True
    except Exception as exc:
        logger.warning(
            "DB unavailable (likely no GCP creds locally): %s. "
            "Falling back to local JSON file.",
            type(exc).__name__,
        )
        return False


def _try_db_list(active_only: bool = False) -> list | None:
    """Try to list configs from DB. Returns None if DB unavailable."""
    try:
        from autocrm_db_helper import get_pg_connector
        with get_pg_connector() as pg:
            filters = {"is_active": True} if active_only else {}
            return list(pg.list("meta_webhook_config", filters))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def upsert_config(
    page_id: str,
    dealership_id: str,
    campaign_id: str,
    campaign_objective_id: str,
    campaign_type: str = "pre-sales",
    dealership_name: str = "",
    meta_app_id: str = "",
    notes: str = "",
    is_active: bool = True,
) -> dict:
    """
    Insert or update a Meta page -> AutoNgage campaign mapping.

    Tries DB first. If DB is unavailable (no GCP auth locally),
    falls back to writing a local JSON file at config/meta_webhook_config.json.
    The webhook server reads both the DB and this JSON file.

    Args:
        page_id               : Facebook Page ID (from Meta Page settings or webhook payload)
        dealership_id         : AutoNgage dealership_id
        campaign_id           : AutoNgage campaign_id (pre_sales_campaign.campaign_id)
        campaign_objective_id : AutoNgage campaign_objective_id
        campaign_type         : "pre-sales" or "post-sales" (default: "pre-sales")
        dealership_name       : Human-readable name (for logging)
        meta_app_id           : Meta App ID (from App Dashboard -> Settings -> Basic)
        notes                 : Free-text notes for ops team
        is_active             : If False, this config is ignored by the webhook handler

    Returns:
        The saved config dict.
    """
    config = {
        "config_id":             str(uuid.uuid4()),
        "page_id":               str(page_id),
        "meta_app_id":           str(meta_app_id) if meta_app_id else "",
        "dealership_id":         dealership_id,
        "dealership_name":       dealership_name,
        "campaign_id":           campaign_id,
        "campaign_type":         campaign_type,
        "campaign_objective_id": campaign_objective_id,
        "is_active":             is_active,
        "created_at":            time.time(),
        "notes":                 notes,
    }

    # Try DB first; fall back to JSON file
    db_ok = _try_db_upsert(config)
    if not db_ok:
        _upsert_json(config)

    return config


def list_configs(active_only: bool = False) -> list:
    """Print and return all webhook config rows (from DB or JSON file)."""
    # Try DB
    rows = _try_db_list(active_only)
    source = "DB"
    if rows is None:
        # Fall back to JSON file
        rows = _load_json_store()
        source = "local JSON file"
        if active_only:
            rows = [r for r in rows if r.get("is_active", True)]

    print(f"\n{'='*70}")
    print(f"  meta_webhook_config [{source}] — {len(rows)} row(s)")
    print(f"{'='*70}")
    for row in rows:
        print(f"  page_id    : {row.get('page_id')}")
        print(f"  dealership : {row.get('dealership_id')} ({row.get('dealership_name', '')})")
        print(f"  campaign   : {row.get('campaign_id')}  [{row.get('campaign_type')}]")
        print(f"  objective  : {row.get('campaign_objective_id')}")
        print(f"  active     : {row.get('is_active')}  notes: {row.get('notes', '')}")
        print()
    return rows


def deactivate_config(page_id: str):
    """Set is_active=False for a given page_id (soft delete)."""
    # Try DB
    db_ok = False
    try:
        from autocrm_db_helper import get_pg_connector
        with get_pg_connector() as pg:
            rows = list(pg.list("meta_webhook_config", {"page_id": page_id}))
            if not rows:
                logger.warning("No DB config found for page_id=%s", page_id)
            for row in rows:
                pg.update("meta_webhook_config", "config_id", row["config_id"], {"is_active": False})
                db_ok = True
    except Exception:
        pass

    if not db_ok:
        # Deactivate in JSON file
        rows = _load_json_store()
        updated = False
        for row in rows:
            if row.get("page_id") == str(page_id):
                row["is_active"] = False
                updated = True
        if updated:
            _save_json_store(rows)
            logger.info("Deactivated JSON config for page_id=%s", page_id)
        else:
            logger.warning("No config found for page_id=%s in JSON file either.", page_id)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        list_configs()
        sys.exit(0)

    print("=" * 60)
    print("  Meta Webhook Config Seed")
    print("=" * 60)
    print(f"  Local JSON path: {LOCAL_CONFIG_PATH}")
    print()

    # Read values from environment variables
    page_id      = os.environ.get("META_PAGE_ID",                    "1774145496137418")
    dealership   = os.environ.get("META_TEST_DEALERSHIP_ID",         "")
    campaign_id  = os.environ.get("META_TEST_CAMPAIGN_ID",           "120248254600500664")
    objective_id = os.environ.get("META_TEST_CAMPAIGN_OBJECTIVE_ID", "")
    camp_type    = os.environ.get("META_TEST_CAMPAIGN_TYPE",         "pre-sales")
    dealer_name  = os.environ.get("META_TEST_DEALERSHIP_NAME",       "Test Dealership")
    app_id       = os.environ.get("META_APP_ID",                     "")

    # Validate required fields
    missing = []
    if not dealership:
        missing.append("META_TEST_DEALERSHIP_ID")
    if not objective_id:
        missing.append("META_TEST_CAMPAIGN_OBJECTIVE_ID")

    if missing:
        print(f"ERROR: Required env vars not set: {', '.join(missing)}")
        print()
        print("Set them before running:")
        for m in missing:
            print(f"  export {m}=YOUR_VALUE_HERE")
        print()
        sys.exit(1)

    print(f"  page_id      : {page_id}")
    print(f"  dealership   : {dealership}")
    print(f"  campaign_id  : {campaign_id}")
    print(f"  objective_id : {objective_id}")
    print(f"  type         : {camp_type}")
    print()

    saved = upsert_config(
        page_id               = page_id,
        dealership_id         = dealership,
        campaign_id           = campaign_id,
        campaign_objective_id = objective_id,
        campaign_type         = camp_type,
        dealership_name       = dealer_name,
        meta_app_id           = app_id,
        notes                 = "Seeded by meta_webhook_config_seed.py",
    )

    print("\nSaved config:")
    print(json.dumps(saved, indent=2, default=str))
    print()
    list_configs()
