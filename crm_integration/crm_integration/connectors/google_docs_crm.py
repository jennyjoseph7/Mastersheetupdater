try:
    import gspread
except ImportError:
    gspread = None
from google.oauth2.service_account import Credentials
from crm_integration.crm_integration.base_crm import BaseCRMClass


STANDARD_FIELDS = [
    "workshop_city",
    "dealership_id",
    "VIN",
    "next_service_due",
    "person_name",
    "vehicle_model",
    "reg_number",
    "phone_number",
    "alt_phone_number_2",
    "odometer_reading",
    "last_service_date",
    "customer_score",
    "purpose_of_visit",
    "status",
    "disposition_detail",
    "summary",
    "call_date",
    "sentiment",
    "campaign_id"
]


HEADER_MAPPING = {
    # ── Sheet columns → internal field names ──────────────────────────────────
    "Location":         "workshop_city",
    "Dealer Code":      "dealership_id",
    "VIN":              "VIN",
    "Due Date":         "next_service_due",
    "Cust. Name":       "person_name",
    "Model Name":       "vehicle_model",
    "Registration Num": "reg_number",
    "Mobile Number":    "phone_number",
    "Status":           "status",

    # ── Written back by post-processing task ──────────────────────────
    "Disposition":      "disposition",
    "Sentiment":        "sentiment",
    "Call Duration":    "call_duration",
    "Lead Summary":     "lead_summary",
}


class GoogleDocsCRM(BaseCRMClass):

    def __init__(self, sheet_name=None, credentials=None, sheet_url=None):
        """
        Args:
            credentials (dict): Service account credentials dict (from DB crm_source_details.api_key).
                                 If None, falls back to reading credentials.json from disk.
            sheet_url (str):    Full Google Sheet URL or just the spreadsheet ID.
                                 Takes priority over sheet_name.
            sheet_name (str):   Sheet title (legacy fallback — used only when sheet_url is not given).
        """
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # ── Build credentials ─────────────────────────────────────────────────
        if credentials and isinstance(credentials, dict):
            # NEW: credentials passed directly as dict from DB
            creds = Credentials.from_service_account_info(credentials, scopes=scope)
        else:
            # LEGACY fallback: read from credentials.json file on disk
            import os
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(BASE_DIR, "credentials.json")
            creds = Credentials.from_service_account_file(cred_path, scopes=scope)

        client = gspread.authorize(creds)

        # ── Open the sheet ────────────────────────────────────────────────────
        if sheet_url:
            # Extract spreadsheet ID from full URL if needed
            # URL format: https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit...
            if "/spreadsheets/d/" in sheet_url:
                spreadsheet_id = sheet_url.split("/spreadsheets/d/")[1].split("/")[0]
            else:
                # Assume it's already just the spreadsheet ID
                spreadsheet_id = sheet_url
            self.sheet = client.open_by_key(spreadsheet_id).sheet1
        elif sheet_name:
            # Legacy: open by sheet title
            self.sheet = client.open(sheet_name).sheet1
        else:
            raise ValueError("Either sheet_url or sheet_name must be provided to GoogleDocsCRM")


  
    # CORE UTIL METHODS
    

    def get_sheet_headers(self):
        return self.sheet.row_values(1)


    def normalize_row(self, row_dict):
        normalized = {}
        for sheet_key, value in row_dict.items():
            # Strip whitespace before lookup so headers with trailing spaces match
            internal_key = HEADER_MAPPING.get(sheet_key.strip(), sheet_key.strip().lower())
            normalized[internal_key] = value
        return normalized


    def append_dynamic_row(self, data):

        headers = self.get_sheet_headers()
        row = []

        for header in headers:

            internal_key = HEADER_MAPPING.get(header, header.lower())

            row.append(data.get(internal_key, ""))

        self.sheet.append_row(row)

    def get_column_index(self, column_name):
        headers = self.get_sheet_headers()
        return headers.index(column_name)    


    
    # PRE SALES
    

    def post_pre_sales_lead(self, data):

        self.append_dynamic_row(data)

        return {"status": "success"}


    def list_pre_sales_leads(self, batch_size=None, last_updated=None, status_filter=None, **kwargs):
        """
        Read leads from the Google Sheet.

        Filtering rules:
        - By default, return only leads that have NOT been processed yet:
            → Status is empty ("") or "NEW"
            → Skips: QUEUED, CONTACTED, engaged, not_interested, completed, done
        - status_filter: explicit override — pass a specific status string to
          filter for (e.g. "CONTACTED" for Phase 2 disposition updates).
        - batch_size: max rows to return. If None, returns all matching rows.
        - last_updated: kept for API compatibility, not used (Due Date is a
          business date, not an insertion timestamp).
        """
        headers = self.get_sheet_headers()
        rows    = self.sheet.get_all_values()[1:]

        results = []
        for row in rows:
            if not any(cell.strip() for cell in row):
                continue  # skip fully empty rows
            row_dict   = dict(zip(headers, row))
            normalized = self.normalize_row(row_dict)
            results.append(normalized)

        # ── Status filtering ──────────────────────────────────────────────────
        if status_filter is not None:
            # Explicit override — caller wants a specific status
            results = [
                r for r in results
                if r.get("status", "").strip().upper() == status_filter.strip().upper()
            ]
        else:
            # Default: only NEW / empty leads (not yet triggered)
            # Skip anything that has already been queued or dispositioned
            DONE_STATUSES = {
                "queued", "contacted",
                "engaged", "not_interested", "interested",
                "completed", "done", "callback",
            }
            results = [
                r for r in results
                if r.get("status", "").strip().lower() not in DONE_STATUSES
            ]

        # ── Batch size limit ──────────────────────────────────────────────────
        if batch_size:
            results = results[:batch_size]

        return results


    def get_pre_sales_lead(self, search_data):

        records = self.list_pre_sales_leads()

        for row in records:

            if row.get("phone_number") == search_data.get("phone_number"):
                return row

        return {"error": "Not found"}
    def update_row_by_phone(self, phone_number: str, data: dict) -> dict:
        """
        Find row(s) where 'Mobile Number' == phone_number and write all
        non-empty key-value pairs from `data` back to the sheet.

        Rules :
        - Skip keys where the value is None or empty string — don't update, don't create column
        - If the column header already exists → update the cell for that row
        - If the column header does NOT exist  → create it in row 1, then update the cell

        Args:
            phone_number (str): Phone number to identify the row.
            data (dict):        Key-value pairs to write.
                                e.g. {"disposition": "engaged", "lead_summary": ""}
                                     ↑ disposition gets written, lead_summary is skipped

        Returns:
            dict: {"updated": bool, "rows_updated": int, "columns_added": list}
        """
        # ── Drop empty values up front ─────────────────────────────────────────
        # If value is None, empty string, or the literal string "None" → skip it
        data = {
            k: v for k, v in data.items()
            if v is not None and str(v).strip() not in ("", "None", "none")
        }

        if not data:
            return {"updated": False, "rows_updated": 0, "columns_added": [], "note": "all values were empty"}

        # Reload live headers + all rows from the sheet
        headers  = self.sheet.row_values(1)
        all_rows = self.sheet.get_all_values()

        # Find the "Mobile Number" column index
        phone_idx = next(
            (i for i, h in enumerate(headers) if h.strip().lower() == "mobile number"),
            None
        )
        if phone_idx is None:
            return {"updated": False, "error": "Mobile Number column not found in sheet"}

        # ── Ensure every key in data has a column in the sheet ────────────────
        # If a key doesn't match any existing header → create it at the end
        columns_added  = []
        key_to_col_idx = {}   # key → 0-based column index

        for key in data:
            found_idx = next(
                (i for i, h in enumerate(headers) if h.strip().lower() == key.strip().lower()),
                None
            )
            if found_idx is not None:
                # Column already exists — just map to its index
                key_to_col_idx[key] = found_idx
            else:
                # Column doesn't exist — create it at the end of row 1
                new_col_idx = len(headers)
                self.sheet.update_cell(1, new_col_idx + 1, key)   # gspread is 1-indexed
                headers.append(key)
                key_to_col_idx[key] = new_col_idx
                columns_added.append(key)

        # ── Find matching rows and update each cell ────────────────────────────
        updated_count = 0
        for row_idx, row in enumerate(all_rows):
            if row_idx == 0:
                continue   # skip header row

            row_phone = row[phone_idx].strip() if phone_idx < len(row) else ""
            if row_phone == str(phone_number).strip():
                for key, value in data.items():
                    col_idx = key_to_col_idx[key]
                    self.sheet.update_cell(row_idx + 1, col_idx + 1, str(value))
                updated_count += 1

        return {
            "updated":       updated_count > 0,
            "rows_updated":  updated_count,
            "columns_added": columns_added,
        }



    def patch_pre_sales_lead(self, search_data, updated_status):
        """
        Update status for all rows matching VIN or phone that are not already CONTACTED.
        Iterates ALL rows (not just first match) to handle duplicate entries.
        """
        headers = self.get_sheet_headers()
        rows = self.sheet.get_all_values()

        vin_idx   = headers.index("VIN") if "VIN" in headers else None
        phone_idx = headers.index("Mobile Number") if "Mobile Number" in headers else None
        status_idx = headers.index("Status")

        updated_count = 0

        for i, row in enumerate(rows):

            if i == 0:
                continue

            vin_match   = vin_idx   is not None and row[vin_idx]   == search_data.get("VIN")
            phone_match = phone_idx is not None and row[phone_idx] == search_data.get("phone_number")

            # Only update rows not already CONTACTED — avoids double-patching
            current_status = row[status_idx].strip().upper() if status_idx < len(row) else ""

            if (vin_match or phone_match) and current_status != "CONTACTED":
                self.sheet.update_cell(i + 1, status_idx + 1, updated_status)
                updated_count += 1

        return {"updated": updated_count > 0, "rows_updated": updated_count}
    
    # POST SALES
    
    def post_post_sales_lead(self, data):

        headers = self.get_sheet_headers()
        row = []

        for header in headers:

            internal_key = HEADER_MAPPING.get(header, header.lower())

            value = data.get(internal_key, "")

            row.append(value)

        self.sheet.append_row(row)

        return {
                "status": "success",
                "inserted": data
        }

    def list_post_sales_leads(self):
        return self.list_pre_sales_leads()


   
    # CUSTOMER
    

    def list_customers(self):
        return self.list_pre_sales_leads()
    
   


   #logger
    def get_post_sales_lead(self, id):
        return {"message": "Not implemented yet"}


    def patch_post_sales_lead(self, search_data, data):

        headers = self.get_sheet_headers()
        rows = self.sheet.get_all_values()

        phone_idx = headers.index("Mobile Number")
        status_idx = headers.index("Status")

        for i, row in enumerate(rows):

            if i == 0:
                continue

            if row[phone_idx] == search_data.get("phone_number"):

                self.sheet.update_cell(i+1, status_idx+1, data.get("status"))

                return {"updated": True}

        return {"updated": False}


    def get_customer(self, id):
        return {"message": "Not implemented yet"}


    def post_customer(self, data):
        return {"message": "Not implemented yet"}


    def patch_customer(self, id, data):
        return {"message": "Not implemented yet"}
