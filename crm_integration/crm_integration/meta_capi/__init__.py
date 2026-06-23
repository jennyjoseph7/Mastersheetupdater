"""
Meta Conversions API (CAPI) + Webhook Lead Ingestion — CRM Integration Package

Part 1 — Receive leads FROM Meta:
    MetaGraphAPIClient  : Fetches full lead data using a leadgen_id.
    webhook_server      : Flask app that receives Meta Webhook events.

Part 2 — Send outcomes BACK to Meta:
    MetaCAPIClient      : Sends CAPI conversion events.
    build_lead_event_payload : Builds spec-compliant event payloads.
    CRMLeadToCapiMapper : Maps internal lead dicts to CAPI events.
"""
# Part 2 — Conversions API (outbound)
from .client import MetaCAPIClient
from .payload import build_lead_event_payload, hash_pii
from .mapper import CRMLeadToCapiMapper

# Part 1 — Graph API (inbound)
from .graph_api_client import MetaGraphAPIClient, MetaGraphAPIError, normalize_field_data

__all__ = [
    # Part 2
    "MetaCAPIClient",
    "build_lead_event_payload",
    "hash_pii",
    "CRMLeadToCapiMapper",
    # Part 1
    "MetaGraphAPIClient",
    "MetaGraphAPIError",
    "normalize_field_data",
]
