"""Manage VitalAge's site-specific Czech Translation records as code.

Run on DEV with:
  bench --site SITE execute crm.fcrm.vitalage_translations.export_translations_json
Then transfer the output into crm/fcrm/vitalage_translations.json
before promoting the code to production.
"""

import json
from importlib import resources

import frappe


def export_translations_json():
	"""Print Czech translations only; callable in a Frappe bench site context."""
	rows = frappe.get_all(
		"Translation",
		filters={"language": "cs"},
		fields=["source_text", "translated_text", "language", "context"],
		order_by="source_text asc",
		limit_page_length=0,
	)
	payload = [
		{key: row.get(key) for key in ("language", "source_text", "translated_text", "context")}
		for row in rows
		if row.get("source_text") and row.get("translated_text")
	]
	output = json.dumps(payload, ensure_ascii=False, indent=2)
	print(output)
	return output


def sync_translations():
	"""Upsert versioned translations without removing unrelated site records.

	On the source DEV site, set vitalage_preserve_local_translations=1 in
	site_config.json so a deployment never overwrites translations awaiting export.
	"""
	raw = resources.files("crm.fcrm").joinpath("vitalage_translations.json").read_text(encoding="utf-8")
	data = json.loads(raw)
	preserve_local = frappe.conf.get("vitalage_preserve_local_translations", False)
	for row in data:
		if row.get("language") != "cs" or not row.get("source_text"):
			continue
		filters = {
			"language": "cs",
			"source_text": row["source_text"],
			"context": row.get("context") or "",
		}
		existing = frappe.db.get_value("Translation", filters, "name")
		if existing:
			doc = frappe.get_doc("Translation", existing)
			if not preserve_local and doc.translated_text != row["translated_text"]:
				doc.translated_text = row["translated_text"]
				doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(
				{"doctype": "Translation", **filters, "translated_text": row["translated_text"]}
			).insert(ignore_permissions=True)
	frappe.clear_cache()
