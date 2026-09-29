import frappe
from frappe import _


def execute():
	"""Ensure the VitalAge Lead country default uses Frappe's standard Country master."""
	name = "CRM Lead-custom_country"
	if not frappe.db.exists("Custom Field", name):
		return

	if not frappe.db.exists("Country", "Czech Republic"):
		frappe.throw(_('Required Country master "Czech Republic" is missing'))

	frappe.db.set_value(
		"Custom Field",
		name,
		"default",
		"Czech Republic",
		update_modified=False,
	)
	frappe.clear_cache(doctype="CRM Lead")
