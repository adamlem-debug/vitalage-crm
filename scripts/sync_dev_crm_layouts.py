#!/usr/bin/env python3
"""Export DEV CRM field layouts into the versioned VitalAge configuration.

Requires DEV_FRAPPE_URL, DEV_FRAPPE_API_KEY and DEV_FRAPPE_API_SECRET.
Read-only against DEV; modifies only the local JSON payload.
"""
import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

PAYLOAD = Path(__file__).resolve().parents[1] / "crm/fcrm/vitalage_config_payload.json"
FIELDS = ["name", "dt", "type", "layout"]


def export_layouts():
    url = os.environ["DEV_FRAPPE_URL"].rstrip("/")
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.path or parts.query or parts.fragment:
        raise ValueError("DEV_FRAPPE_URL must be an HTTPS site origin")
    if parts.hostname != "vitalageclinic.frappe.cloud":
        raise ValueError("Refusing to export from a site other than VitalAge DEV")
    token = f'token {os.environ["DEV_FRAPPE_API_KEY"]}:{os.environ["DEV_FRAPPE_API_SECRET"]}'
    result = []
    start = 0
    while True:
        query = f'fields={quote(json.dumps(FIELDS))}&limit_start={start}&limit_page_length=100'
        req = Request(f'{url}/api/resource/CRM%20Fields%20Layout?{query}', headers={
            "Authorization": token,
            "Accept": "application/json",
        })
        with urlopen(req, timeout=30) as response:
            page = json.load(response)["data"]
        if not isinstance(page, list):
            raise ValueError("Unexpected CRM Fields Layout response")
        result.extend(page)
        if len(page) < 100:
            break
        start += len(page)
    if not result:
        raise ValueError("DEV returned no layouts; refusing to overwrite the snapshot")
    names = [row.get("name") for row in result]
    if len(names) != len(set(names)) or any(not name for name in names):
        raise ValueError("Duplicate or missing layout names")
    for row in result:
        if set(row) != set(FIELDS):
            raise ValueError(f'Unexpected layout fields in {row.get("name")}')
        if not isinstance(row["layout"], str):
            raise ValueError(f'Invalid layout for {row["name"]}')
        json.loads(row["layout"])
    return sorted(result, key=lambda row: row["name"])


def main():
    layouts = export_layouts()
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    payload["crm_fields_layout"] = [
        {"name": row["name"], "docstatus": 0, "idx": 0,
         "dt": row["dt"], "type": row["type"], "layout": row["layout"],
         "doctype": "CRM Fields Layout"}
        for row in layouts
    ]
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(layouts)} CRM field layouts from DEV")


if __name__ == "__main__":
    main()
