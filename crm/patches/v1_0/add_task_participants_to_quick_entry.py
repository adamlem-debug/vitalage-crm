import json

import frappe


LAYOUT_NAME = "CRM Task-Quick Entry"


def execute():
	if not frappe.db.exists("CRM Fields Layout", LAYOUT_NAME):
		return

	layout_doc = frappe.get_doc("CRM Fields Layout", LAYOUT_NAME)

	try:
		layout = json.loads(layout_doc.layout or "[]")
	except (TypeError, ValueError):
		return

	if _insert_participants(layout):
		layout_doc.layout = json.dumps(layout)
		layout_doc.save(ignore_permissions=True)


def _insert_participants(node):
	changed = False

	if isinstance(node, list):
		for item in node:
			changed = _insert_participants(item) or changed
		return changed

	if not isinstance(node, dict):
		return False

	fields = node.get("fields")
	if isinstance(fields, list) and "assigned_to" in fields and "participants" not in fields:
		fields.insert(fields.index("assigned_to") + 1, "participants")
		changed = True

	for value in node.values():
		if value is fields:
			continue
		changed = _insert_participants(value) or changed

	return changed
