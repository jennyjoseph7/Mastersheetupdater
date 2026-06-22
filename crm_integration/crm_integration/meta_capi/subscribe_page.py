"""
Meta Page Subscription Helper
===============================
Subscribes a Facebook Page to our webhook app so that Meta
starts sending leadgen notifications to our server.

This is a ONE-TIME setup step per dealership page.

Steps:
  1. Fill in META_PAGE_ID and META_PAGE_ACCESS_TOKEN in local.sh
  2. Run: source crm_integration/local.sh
  3. Run: python3 crm_integration/crm_integration/meta_capi/subscribe_page.py

What this does:
  POST https://graph.facebook.com/{PAGE_ID}/subscribed_apps
       ?subscribed_fields=leadgen
       &access_token={PAGE_ACCESS_TOKEN}

Required:
  - A Page Access Token with pages_manage_metadata permission
  - The Page must have the App Platform enabled in Page Settings

References:
  https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/#install-app
"""

import os
import sys
import requests

def subscribe_page_to_leadgen(page_id: str, page_access_token: str) -> dict:
    """
    Subscribe a Facebook Page to receive leadgen webhook notifications.

    Args:
        page_id            : Facebook Page ID.
        page_access_token  : Page Access Token with pages_manage_metadata permission.

    Returns:
        dict: {"success": True} on success.
    """
    api_version = os.environ.get("META_CAPI_API_VERSION", "v21.0")
    url = f"https://graph.facebook.com/{api_version}/{page_id}/subscribed_apps"

    print(f"\nSubscribing Page {page_id} to leadgen notifications...")
    print(f"URL: {url}")

    resp = requests.post(
        url,
        params={
            "subscribed_fields": "leadgen",
            "access_token":      page_access_token,
        },
        timeout=15,
    )

    data = resp.json()

    if resp.status_code == 200 and data.get("success"):
        print(f"\n✅ Page {page_id} successfully subscribed to leadgen webhook!")
        print("   Meta will now send real-time lead notifications to your webhook URL.")
    else:
        error = data.get("error", {})
        print(f"\n❌ Subscription failed (HTTP {resp.status_code})")
        print(f"   Error: {error.get('message', data)}")
        print("\n   Common fixes:")
        print("   • Ensure the Page Access Token has 'pages_manage_metadata' permission")
        print("   • Ensure the Meta App is configured with Webhooks product + 'leadgen' field")
        print("   • Ensure the Page has 'App Platform' enabled (Page Settings → Apps)")

    return data


def check_page_subscriptions(page_id: str, page_access_token: str) -> dict:
    """
    List all apps currently subscribed to the Page.
    Useful to verify the subscription was registered.
    """
    api_version = os.environ.get("META_CAPI_API_VERSION", "v21.0")
    url = f"https://graph.facebook.com/{api_version}/{page_id}/subscribed_apps"

    print(f"\nChecking existing subscriptions for Page {page_id}...")
    resp = requests.get(url, params={"access_token": page_access_token}, timeout=15)
    data = resp.json()

    apps = data.get("data", [])
    if apps:
        print(f"Found {len(apps)} subscribed app(s):")
        for app_info in apps:
            print(f"  • {app_info.get('name', '?')} (id={app_info.get('id')})")
    else:
        print("No apps subscribed to this page yet.")

    return data


if __name__ == "__main__":
    page_id     = os.environ.get("META_PAGE_ID", "")
    page_token  = os.environ.get("META_PAGE_ACCESS_TOKEN", "")

    if not page_id or page_id.startswith("YOUR_"):
        print("❌ META_PAGE_ID is not set. Add it to crm_integration/local.sh")
        sys.exit(1)

    if not page_token or page_token.startswith("YOUR_"):
        print("❌ META_PAGE_ACCESS_TOKEN is not set. Add it to crm_integration/local.sh")
        sys.exit(1)

    # Check existing subscriptions first
    check_page_subscriptions(page_id, page_token)

    # Subscribe
    subscribe_page_to_leadgen(page_id, page_token)

    # Verify
    print("\nVerifying subscription...")
    check_page_subscriptions(page_id, page_token)
