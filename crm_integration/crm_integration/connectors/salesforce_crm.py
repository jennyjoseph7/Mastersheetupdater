import requests
from crm_integration.crm_integration.base_crm import BaseCRMClass

# Token endpoints — production vs sandbox
SF_LOGIN_URL_PROD    = "https://login.salesforce.com/services/oauth2/token"
SF_LOGIN_URL_SANDBOX = "https://test.salesforce.com/services/oauth2/token"


# ---------------------------------------------------------------------------
# Field mapping: internal field name → Salesforce Lead field name
# ---------------------------------------------------------------------------
SALESFORCE_FIELD_MAP = {
    "person_name":      "LastName",
    "phone_number":     "Phone",
    "alt_phone_number_2": "MobilePhone",
    "vehicle_model":    "Description",          # No standard SF field; map to Description
    "reg_number":       "Reg_Number__c",        # Custom field — confirm name in your SF org
    "VIN":              "VIN__c",               # Custom field — confirm name in your SF org
    "next_service_due": "Next_Service_Due__c",  # Custom field — confirm name in your SF org
    "workshop_city":    "City",
    "dealership_id":    "LeadSource",           # Or a custom field
    "status":           "Status",
    "company":          "Company",              # Required by Salesforce
}

# Reverse map: Salesforce field → internal field
INTERNAL_FIELD_MAP = {v: k for k, v in SALESFORCE_FIELD_MAP.items()}

# Salesforce API version
SF_API_VERSION = "v60.0"


class SalesforceCRM(BaseCRMClass):
    """
    Salesforce CRM connector.

    Authenticates via OAuth 2.0 Username-Password flow (Connected App).
    All CRUD operations use the Salesforce REST API on the Lead object.

    Credentials required (pass as dict):
        {
            "client_id":      "<Consumer Key>",
            "client_secret":  "<Consumer Secret>",
            "username":       "<SF Username>",
            "password":       "<SF Password + Security Token concatenated>",
            "instance_url":   "https://<your-org>.my.salesforce.com"  # optional override
        }
    """

    def __init__(self, credentials: dict):
        super().__init__(crm_name="salesforce")

        self.credentials  = credentials
        self.access_token = None
        self.instance_url = credentials.get("instance_url", "")

        # Use sandbox token URL if specified in credentials
        self._is_sandbox = credentials.get("sandbox", False)

        # Authenticate on init
        self._authenticate()


    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _authenticate(self):
        """
        OAuth 2.0 Username-Password flow.
        Fetches access_token and instance_url from Salesforce.
        Supports both production and sandbox orgs.
        """
        token_url = SF_LOGIN_URL_SANDBOX if self._is_sandbox else SF_LOGIN_URL_PROD

        payload = {
            "grant_type":    "password",
            "client_id":     self.credentials["client_id"],
            "client_secret": self.credentials["client_secret"],
            "username":      self.credentials["username"],
            # password must include Security Token if IP not whitelisted
            "password":      self.credentials["password"],
        }

        response = requests.post(token_url, data=payload)
        response.raise_for_status()

        data = response.json()

        self.access_token = data["access_token"]
        self.instance_url = data.get("instance_url", self.instance_url)
        self.connected    = True


    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type":  "application/json",
        }


    def _base_url(self):
        return f"{self.instance_url}/services/data/{SF_API_VERSION}"


    # ------------------------------------------------------------------
    # Field mapping helpers
    # ------------------------------------------------------------------

    def _to_sf_payload(self, data: dict) -> dict:
        """Map internal field names → Salesforce field names."""
        payload = {}
        for internal_key, value in data.items():
            sf_key = SALESFORCE_FIELD_MAP.get(internal_key)
            if sf_key and value:
                payload[sf_key] = value

        # Salesforce requires Company — default to dealership_id or "Unknown"
        if "Company" not in payload:
            payload["Company"] = data.get("dealership_id", "Unknown Dealership")

        return payload


    def _from_sf_record(self, record: dict) -> dict:
        """Map Salesforce field names → internal field names."""
        normalized = {}
        for sf_key, value in record.items():
            if sf_key == "attributes":
                continue
            internal_key = INTERNAL_FIELD_MAP.get(sf_key, sf_key.lower())
            normalized[internal_key] = value
        return normalized


    # ------------------------------------------------------------------
    # SOQL query helper
    # ------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Wrapper around requests that auto-retries once on 401 (token expired).
        Salesforce returns 401 with errorCode INVALID_SESSION_ID when the token expires.
        """
        response = getattr(requests, method)(url, headers=self._headers(), **kwargs)

        if response.status_code == 401:
            # Token expired — re-authenticate and retry once
            self._authenticate()
            response = getattr(requests, method)(url, headers=self._headers(), **kwargs)

        response.raise_for_status()
        return response


    def _soql_query(self, soql: str) -> list:
        """
        Run a SOQL query and return ALL records, following pagination.
        Salesforce paginates results (max 2000 per page) via nextRecordsUrl.
        """
        url      = f"{self._base_url()}/query/"
        response = self._request("get", url, params={"q": soql})
        data     = response.json()

        records = data.get("records", [])

        # Follow pagination until done=True
        while not data.get("done", True):
            next_url  = f"{self.instance_url}{data['nextRecordsUrl']}"
            response  = self._request("get", next_url)
            data      = response.json()
            records  += data.get("records", [])

        return records


    def _find_lead_id(self, search_data: dict) -> "str | None":
        """
        Find a Lead's Salesforce Id using phone_number or VIN.
        Returns Id string or None if not found.
        """
        phone = search_data.get("phone_number")
        vin   = search_data.get("VIN")

        if phone:
            soql = f"SELECT Id FROM Lead WHERE Phone = '{phone}' LIMIT 1"
        elif vin:
            soql = f"SELECT Id FROM Lead WHERE VIN__c = '{vin}' LIMIT 1"
        else:
            return None

        records = self._soql_query(soql)
        if records:
            return records[0]["Id"]
        return None


    # ------------------------------------------------------------------
    # PRE-SALES LEADS
    # ------------------------------------------------------------------

    def post_pre_sales_lead(self, data: dict) -> dict:
        """Create a new Lead in Salesforce. Required SF fields: LastName, Company, Status."""
        url     = f"{self._base_url()}/sobjects/Lead/"
        payload = self._to_sf_payload(data)

        response = self._request("post", url, json=payload)
        result   = response.json()

        return {
            "status":   "success",
            "sf_id":    result.get("id"),
            "inserted": data,
        }


    def read_leads_from_sheet(self, last_updated=None, **kwargs) -> list:
        """
        List Leads from Salesforce.
        Optionally filter by last_updated (ISO 8601 datetime string).
        """
        fields = "Id, FirstName, LastName, Phone, MobilePhone, Status, City, Description"

        if last_updated:
            soql = (
                f"SELECT {fields} FROM Lead "
                f"WHERE LastModifiedDate >= {last_updated} "
                f"ORDER BY LastModifiedDate DESC"
            )
        else:
            soql = f"SELECT {fields} FROM Lead ORDER BY CreatedDate DESC LIMIT 200"

        records = self._soql_query(soql)
        return [self._from_sf_record(r) for r in records]


    def find_lead_by_phone_number(self, search_data: dict) -> dict:
        """Get a single Lead by phone_number or VIN."""
        phone = search_data.get("phone_number")
        vin   = search_data.get("VIN")

        if phone:
            soql = (
                f"SELECT Id, FirstName, LastName, Phone, MobilePhone, Status, City, Description "
                f"FROM Lead WHERE Phone = '{phone}' LIMIT 1"
            )
        elif vin:
            soql = (
                f"SELECT Id, FirstName, LastName, Phone, MobilePhone, Status, City, Description "
                f"FROM Lead WHERE VIN__c = '{vin}' LIMIT 1"
            )
        else:
            return {"error": "phone_number or VIN required"}

        records = self._soql_query(soql)
        if not records:
            return {"error": "Not found"}

        return self._from_sf_record(records[0])


    def update_status_for_matching_rows(self, search_data: dict, updated_status: str) -> dict:
        """Update the Status of a Lead identified by phone_number or VIN."""
        lead_id = self._find_lead_id(search_data)

        if not lead_id:
            return {"updated": False, "error": "Lead not found"}

        url     = f"{self._base_url()}/sobjects/Lead/{lead_id}"
        payload = {"Status": updated_status}

        # PATCH returns 204 No Content on success — no response body
        self._request("patch", url, json=payload)

        return {"updated": True, "sf_id": lead_id}


    # ------------------------------------------------------------------
    # POST-SALES LEADS
    # ------------------------------------------------------------------

    def post_post_sales_lead(self, data: dict) -> dict:
        """Same as post_pre_sales_lead — Salesforce uses one Lead object."""
        return self.post_pre_sales_lead(data)


    def list_post_sales_leads(self, **kwargs) -> list:
        return self.read_leads_from_sheet(**kwargs)


    def get_post_sales_lead(self, lead_id: str) -> dict:
        """Get a Lead directly by Salesforce Id."""
        url      = f"{self._base_url()}/sobjects/Lead/{lead_id}"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return self._from_sf_record(response.json())


    def patch_post_sales_lead(self, search_data: dict, data: dict) -> dict:
        """Update a post-sales Lead. Accepts full data dict (uses 'status' key)."""
        lead_id = self._find_lead_id(search_data)

        if not lead_id:
            return {"updated": False, "error": "Lead not found"}

        url     = f"{self._base_url()}/sobjects/Lead/{lead_id}"
        payload = self._to_sf_payload(data)

        # PATCH returns 204 No Content on success — no response body
        self._request("patch", url, json=payload)

        return {"updated": True, "sf_id": lead_id}


    def patch_post_sales_leads_bulk(self, phone_numbers: list, status: str) -> dict:
        """Bulk update status for a list of phone numbers."""
        updated = []
        failed  = []

        for phone in phone_numbers:
            result = self.update_status_for_matching_rows({"phone_number": phone}, status)
            if result.get("updated"):
                updated.append(phone)
            else:
                failed.append(phone)

        return {
            "updated_count": len(updated),
            "failed_count":  len(failed),
            "updated":       updated,
            "failed":        failed,
        }


    # ------------------------------------------------------------------
    # CUSTOMER
    # ------------------------------------------------------------------

    def list_customers(self, **kwargs) -> list:
        return self.read_leads_from_sheet(**kwargs)


    def get_customer(self, customer_id: str) -> dict:
        return self.get_post_sales_lead(customer_id)


    def post_customer(self, data: dict) -> dict:
        return self.post_pre_sales_lead(data)


    def patch_customer(self, customer_id: str, data: dict) -> dict:
        url     = f"{self._base_url()}/sobjects/Lead/{customer_id}"
        payload = self._to_sf_payload(data)

        self._request("patch", url, json=payload)

        return {"updated": True, "sf_id": customer_id}
