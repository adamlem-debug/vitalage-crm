"""Update the VitalAge Deal title automation and reconcile existing titles."""

import frappe

SCRIPT_NAME = "Populate custom_client_full_name"
SCRIPT_BODY = """doc.custom_client_full_name = ""

for row in doc.contacts:
	if row.is_primary and row.contact:
		doc.custom_client_full_name = frappe.db.get_value("Contact", row.contact, "full_name") or ""
		break"""


def execute():
	if not frappe.db.has_column("CRM Deal", "custom_client_full_name"):
		return

	if frappe.db.exists("Server Script", SCRIPT_NAME):
		script = frappe.get_doc("Server Script", SCRIPT_NAME)
		script.script = SCRIPT_BODY
		script.save(ignore_permissions=True)

	# Use the actual primary Contact, rather than the fetched child-row full_name.
	# Only update mismatches; don't trigger Deal save hooks or quota calculations.
	deals = frappe.get_all("CRM Deal", pluck="name", limit_page_length=0)
	for deal_name in deals:
		primary = frappe.db.get_value(
			"CRM Contacts",
			{"parenttype": "CRM Deal", "parent": deal_name, "is_primary": 1},
			"contact",
		)
		title = frappe.db.get_value("Contact", primary, "full_name") if primary else ""
		previous = frappe.db.get_value("CRM Deal", deal_name, "custom_client_full_name")
		if (previous or "") != (title or ""):
			frappe.db.set_value(
				"CRM Deal",
				deal_name,
				"custom_client_full_name",
				title or "",
				update_modified=False,
			)
