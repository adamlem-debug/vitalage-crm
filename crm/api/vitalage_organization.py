"""Atomic Organization + ARES address creation for the quick-entry modal."""

import frappe
from frappe import _

from crm.api.vitalage_ares import valid_ico


@frappe.whitelist()
def create_organization(
	organization: dict | str, address_text: str | None = None, address_details: dict | str | None = None
):
	if not frappe.has_permission("CRM Organization", "create"):
		frappe.throw(_("Not permitted to create Organization"), frappe.PermissionError)

	organization = frappe.parse_json(organization)
	if not isinstance(organization, dict):
		frappe.throw(_("Invalid Organization data"))

	ico = str(organization.get("custom_ico") or "").strip()
	if ico:
		if not valid_ico(ico):
			frappe.throw(_("Neplatné IČO. Zkontrolujte prosím zadané číslo."))
		if frappe.db.exists("CRM Organization", {"custom_ico": ico}):
			frappe.throw(_("Organizace s tímto IČO již existuje."))

	# Only allow explicitly supported quick-entry fields; never trust client-supplied
	# document metadata, ownership, permissions, or privileged field names.
	allowed_fields = {
		"organization_name",
		"custom_ico",
		"custom_dic",
		"no_of_employees",
		"currency",
		"exchange_rate",
		"annual_revenue",
		"website",
		"territory",
		"industry",
		"address",
		"organization_logo",
	}
	invalid_fields = set(organization) - allowed_fields
	if invalid_fields:
		frappe.throw(_("Unsupported Organization fields: {0}").format(", ".join(sorted(invalid_fields))))
	doc = frappe.get_doc({"doctype": "CRM Organization", **organization})
	doc.insert()

	if address_text and not doc.address:
		if not frappe.has_permission("Address", "create"):
			frappe.throw(_("Not permitted to create Address"), frappe.PermissionError)
		details = frappe.parse_json(address_details or {}) or {}
		if not isinstance(details, dict):
			frappe.throw(_("Invalid address details"))
		address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": doc.organization_name,
				"address_type": "Billing",
				"address_line1": str(address_text)[:140],
				"city": details.get("city") or "—",
				"pincode": details.get("pincode") or "",
				"country": "Czech Republic",
				"links": [{"link_doctype": "CRM Organization", "link_name": doc.name}],
			}
		)
		address.insert()
		doc.address = address.name
		doc.save()

	return doc.as_dict()
