#!/usr/bin/env python3
"""Snapshot DEV-authored CRM Custom Fields and Property Setters (read-only API)."""

import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

PAYLOAD = Path(__file__).resolve().parents[1] / "crm/fcrm/vitalage_config_payload.json"
TARGETS = ("CRM Lead", "CRM Deal", "CRM Organization", "CRM Task", "CRM Contact", "Contact", "FCRM Note")
GROUPS = {
	"custom_fields": ("Custom Field", "dt"),
	"property_setters": ("Property Setter", "doc_type"),
}


def fetch_rows(doctype, fields, filter_field):
	base = os.environ["DEV_FRAPPE_URL"].rstrip("/")
	parts = urlsplit(base)
	if (
		parts.scheme != "https"
		or parts.hostname != "vitalageclinic.frappe.cloud"
		or parts.path
		or parts.query
		or parts.fragment
	):
		raise ValueError("DEV_FRAPPE_URL must be the VitalAge DEV HTTPS origin")
	token = f'token {os.environ["DEV_FRAPPE_API_KEY"]}:{os.environ["DEV_FRAPPE_API_SECRET"]}'
	rows = []
	start = 0
	while True:
		query = urlencode(
			{
				"fields": json.dumps(fields),
				"filters": json.dumps([[filter_field, "in", list(TARGETS)]]),
				"limit_start": start,
				"limit_page_length": 100,
				"order_by": "name asc",
			}
		)
		request = Request(
			f"{base}/api/resource/{doctype.replace(' ', '%20')}?{query}",
			headers={"Authorization": token, "Accept": "application/json"},
		)
		with urlopen(request, timeout=30) as response:
			page = json.load(response)["data"]
		if not isinstance(page, list):
			raise ValueError(f"Invalid {doctype} response")
		rows.extend(page)
		if len(page) < 100:
			break
		start += len(page)
	return rows


def main():
	payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
	for group, (doctype, filter_field) in GROUPS.items():
		existing = payload.get(group, [])
		if not existing:
			raise ValueError(f"Missing baseline for {group}")
		fields = sorted(({key for row in existing for key in row} | {"name", filter_field}) - {"doctype"})
		# Frappe's property setter schema has no guaranteed is_system_generated on older sites.
		if group == "property_setters":
			fields.remove("is_system_generated") if "is_system_generated" not in existing[0] else None
		rows = fetch_rows(doctype, fields, filter_field)
		if not rows:
			raise ValueError(f"No {doctype} records from DEV; refusing empty snapshot")
		seen = set()
		for row in rows:
			name = row.get("name")
			if not name or name in seen or row.get(filter_field) not in TARGETS:
				raise ValueError(f"Invalid or duplicate {doctype} record")
			seen.add(name)
			row["doctype"] = doctype
		# Preserve unrelated configuration; preserve system-generated fields in the baseline.
		by_name = {row["name"]: row for row in existing}
		for row in rows:
			if row.get("is_system_generated") and group == "custom_fields":
				continue
			by_name[row["name"]] = row
		payload[group] = sorted(by_name.values(), key=lambda row: row["name"])
		print(f"Fetched {len(rows)} {doctype} records; snapshot has {len(by_name)}")
	PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
	main()
