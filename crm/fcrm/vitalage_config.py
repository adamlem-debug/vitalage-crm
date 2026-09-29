import frappe

from crm.fcrm.doctype.crm_view_settings.crm_view_settings import (
	create_or_update_standard_view,
)

SAFE_FCRM_SETTINGS = {
	"enable_forecasting": 0,
	"enable_sales_hierarchy": 0,
	"auto_update_expected_deal_value": 1,
	"update_timestamp_on_new_communication": 1,
	"auto_mark_replied_on_response": 0,
	"auto_reopen_on_new_communication": 0,
	"currency": "CZK",
	"service_provider": "frankfurter.app",
	"brand_name": "Vital Age Clinic",
}

DEFAULT_VIEWS = (
	{
		"doctype": "CRM Lead",
		"type": "group_by",
		"label": "Group By",
		"route_name": "Leads",
		"filters": {},
		"group_by_field": "status",
		"column_field": "status",
		"load_default_columns": 1,
		"is_default": 1,
	},
	{
		"doctype": "CRM Deal",
		"type": "group_by",
		"label": "Group By",
		"route_name": "Deals",
		"filters": {},
		"group_by_field": "owner",
		"column_field": "status",
		"load_default_columns": 1,
		"is_default": 1,
	},
	{
		"doctype": "CRM Task",
		"type": "calendar",
		"label": "Calendar",
		"route_name": "Tasks",
		"filters": {},
		"group_by_field": "owner",
		"column_field": "status",
		"load_default_columns": 1,
		"is_default": 1,
	},
)


def apply_vitalage_site_config():
	"""Apply non-secret, environment-independent VitalAge settings after migrate."""
	_apply_safe_fcrm_settings()
	_ensure_administrator_default_views()


def _apply_safe_fcrm_settings():
	if not frappe.db.exists("DocType", "FCRM Settings"):
		return

	settings = frappe.get_single("FCRM Settings")
	changed = False

	for fieldname, value in SAFE_FCRM_SETTINGS.items():
		if not settings.meta.has_field(fieldname):
			continue
		if settings.get(fieldname) != value:
			settings.set(fieldname, value)
			changed = True

	# Intentionally do not touch access_key or any other credential-bearing field.
	if changed:
		settings.save(ignore_permissions=True)


def _ensure_administrator_default_views():
	if not frappe.db.exists("DocType", "CRM View Settings"):
		return

	previous_user = getattr(frappe.session, "user", "Administrator") or "Administrator"

	try:
		frappe.set_user("Administrator")

		for view in DEFAULT_VIEWS:
			doc = create_or_update_standard_view(view)

			frappe.db.set_value(
				"CRM View Settings",
				{
					"name": ("!=", doc.name),
					"user": "Administrator",
					"dt": view["doctype"],
					"is_default": 1,
				},
				"is_default",
				0,
				update_modified=False,
			)
	finally:
		frappe.set_user(previous_user)
