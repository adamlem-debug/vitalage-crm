#!/usr/bin/env python3
"""Pull Czech Translation records from the DEV Frappe REST API.

Requires DEV_FRAPPE_URL, DEV_FRAPPE_API_KEY and DEV_FRAPPE_API_SECRET.
The token owner needs read permission on Translation (e.g. Translator).
No write operations are performed against DEV.
"""

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DESTINATION = Path("crm/fcrm/vitalage_translations.json")
FIELDS = ["language", "source_text", "translated_text", "context"]


def export():
	base = os.environ["DEV_FRAPPE_URL"].rstrip("/")
	if not base.startswith("https://"):
		raise ValueError("DEV_FRAPPE_URL must be HTTPS")
	token = "token " + os.environ["DEV_FRAPPE_API_KEY"] + ":" + os.environ["DEV_FRAPPE_API_SECRET"]
	all_rows = []
	offset = 0
	while True:
		query = urlencode(
			{
				"fields": json.dumps(FIELDS),
				"filters": json.dumps([["language", "=", "cs"]]),
				"limit_start": offset,
				"limit_page_length": 200,
				"order_by": "name asc",
			}
		)
		request = Request(
			base + "/api/resource/Translation?" + query,
			headers={"Authorization": token, "Accept": "application/json"},
		)
		with urlopen(request, timeout=30) as response:
			chunk = json.load(response)["data"]
		if not isinstance(chunk, list):
			raise ValueError("Unexpected Frappe Translation API response")
		all_rows.extend(chunk)
		if len(chunk) < 200:
			break
		offset += 200

	if not all_rows:
		raise ValueError("DEV returned zero translations; refusing to replace versioned data")

	translations = []
	keys = set()
	for item in all_rows:
		row = {field: item.get(field) for field in FIELDS}
		if row["language"] != "cs" or not row["source_text"] or not row["translated_text"]:
			raise ValueError("Incomplete translation record from DEV")
		key = (row["source_text"], row["context"] or "")
		if key in keys:
			raise ValueError("Duplicate translation source/context in DEV")
		keys.add(key)
		translations.append(row)
	translations.sort(key=lambda row: (row["source_text"].casefold(), row["context"] or ""))

	old = json.loads(DESTINATION.read_text(encoding="utf-8"))
	old_by_key = {(row["source_text"], row.get("context") or ""): row for row in old}
	# Preserve records already versioned but missing from DEV, to avoid accidental deletion.
	current_by_key = {(row["source_text"], row["context"] or ""): row for row in translations}
	current_by_key.update({key: row for key, row in old_by_key.items() if key not in current_by_key})
	combined = sorted(
		current_by_key.values(), key=lambda row: (row["source_text"].casefold(), row.get("context") or "")
	)
	DESTINATION.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	print(f"Fetched {len(translations)} Czech translations; versioned {len(combined)} records.")


if __name__ == "__main__":
	export()
