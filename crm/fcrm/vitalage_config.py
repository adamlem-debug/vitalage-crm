import base64
import json
import zlib
from importlib import resources

import frappe

from crm.fcrm.doctype.crm_view_settings.crm_view_settings import (
	get_route_name,
	remove_duplicates,
	sync_default_columns,
	sync_default_rows,
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


STOCK_CRM_MASTER_RECORDS = {
	"CRM Deal Status": (
		"Demo/Making",
		"Negotiation",
		"Proposal/Quotation",
		"Qualification",
		"Ready to Close",
		"Won",
	),
	"CRM Lead Source": (
		"Advertisement",
		"Campaign",
		"Cold Calling",
		"Customer's Vendor",
		"Email",
		"Exhibition",
		"Existing Customer",
		"Facebook",
		"Mass Mailing",
		"Reference",
		"Supplier Reference",
		"Walk In",
		"Web Form",
	),
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
	"""Bootstrap VitalAge database configuration without business data or secrets."""
	payload = _load_payload()
	_install_missing_records(payload)
	_apply_crm_fields_layouts(payload)
	_apply_vitalage_custom_field_overrides()
	_remove_stock_crm_master_records()
	_apply_additional_property_setters()
	_apply_custom_docperms()
	_apply_vitalage_crm_settings(payload)
	_apply_safe_fcrm_settings()
	_apply_safe_crm_settings()
	_apply_safe_erpnext_crm_settings()
	_apply_notifications()
	_ensure_global_default_views()
	frappe.clear_cache()


def _load_payload():
	payload = resources.files("crm.fcrm").joinpath("vitalage_config_payload.json").read_text(encoding="utf-8")
	return json.loads(payload)


def _install_missing_records(payload):
	ordered_groups = (
		"custom_doctypes",
		"custom_fields",
		"property_setters",
		"crm_fields_layout",
		"crm_form_scripts",
		"server_scripts",
	)

	for group in ordered_groups:
		for data in payload.get(group, []):
			doctype = data.get("doctype")
			name = data.get("name")
			if not doctype or not name:
				continue
			if frappe.db.exists(doctype, name):
				continue
			frappe.get_doc(data).insert(ignore_permissions=True)


def _apply_crm_fields_layouts(payload):
	"""Reconcile VitalAge CRM layouts even when stock records already exist."""
	for source in payload.get("crm_fields_layout", []):
		name = source.get("name")
		if not name:
			continue

		if frappe.db.exists("CRM Fields Layout", name):
			doc = frappe.get_doc("CRM Fields Layout", name)
		else:
			doc = frappe.new_doc("CRM Fields Layout")
			doc.name = name

		doc.dt = source.get("dt")
		doc.type = source.get("type")
		doc.layout = source.get("layout")

		if doc.is_new():
			doc.insert(ignore_permissions=True)
		else:
			doc.save(ignore_permissions=True)


def _apply_vitalage_custom_field_overrides():
	"""Reconcile targeted Custom Field values that must also update existing sites."""
	name = "CRM Lead-custom_country"
	if not frappe.db.exists("Custom Field", name):
		return

	if not frappe.db.exists("Country", "Czech Republic"):
		frappe.throw('Required Country master "Czech Republic" is missing')

	if frappe.db.get_value("Custom Field", name, "default") != "Czech Republic":
		frappe.db.set_value("Custom Field", name, "default", "Czech Republic", update_modified=False)


def _remove_stock_crm_master_records():
	"""Remove only the stock CRM masters replaced by the VitalAge configuration."""
	for doctype, names in STOCK_CRM_MASTER_RECORDS.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		for name in names:
			if not frappe.db.exists(doctype, name):
				continue

			# Do not force deletion. If a supposedly clean target site already links
			# business data to a stock master, migration should stop for review rather
			# than silently rewriting or deleting that business data.
			frappe.delete_doc(doctype, name, ignore_permissions=True)


def _apply_vitalage_crm_settings(payload):
	if not frappe.db.exists("DocType", "VitalAge CRM Settings"):
		return

	data = (payload.get("vitalage_crm_settings") or [{}])[0]
	settings = frappe.get_single("VitalAge CRM Settings")
	settings.external_calendar_removal_status = data.get("external_calendar_removal_status")

	settings.set("calendar_task_types", [])
	for row in data.get("calendar_task_types", []):
		settings.append("calendar_task_types", {"task_type": row.get("task_type")})

	settings.set("calendar_cancellation_statuses", [])
	for row in data.get("calendar_cancellation_statuses", []):
		settings.append(
			"calendar_cancellation_statuses",
			{"task_status": row.get("task_status")},
		)

	settings.save(ignore_permissions=True)


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


CUSTOM_DOCPERM_B64 = "eNrtmlFv0zAQx79Klec+xHvsW8XEE4FqG7wghI7k1lpz7Mp2GQXx3XGSKrAuW5fUmewcb5bjuP71f7672Pf5V7IFjdImi+TNVTa7RBDJPNFKoOu5BoFmloGENWrXzW+/qnvpmot0nmxRlwK/o0gWbJ4YFJjb+oFGKOq+e80t1q3c9VVN97RwAw9Ns/tW8uadHGRezeSaUKIs6lYJ5u4w41bpZiD+aJpuUl62vWbjIJpVaS4PI0vgzYxuIGqjZLOE3/MXMH80zwJfPAucBg78Qa9B8p9guZI9wdOXKs3+grMB4OwEOGvBWQvOzgI/beWU2ePe4U+w743FcvLCD3PpF9EKfuVAZyutbrkD7i/2a1m6f7G7wT9xC2K5xtqz9zN29kqhLQ1C+Hh3+dtqm79XFinFtC5oklK3G3y12Ruec5CDd3eURj7ZjPUANtCPx52xvavWO7KJ+wvgJwJYnwAehzdL/WUsFDOVGvBmv8WxtnfQJxBKWnDrbtFXO51vwOBIpp4GYepPU48Qv0JHzsC5Nj1p1/YIPgP3PspqObQMfbQsLVTeOL5CmH+NSZn1v/uZjnEv81ztpDUUXRjFqNXqTcfEPX5sRpWGL4V4AMqCtGlfx8J0vrcyVez+/wNErwZ8iR/vWcvj00QChQ5HwDQuurtUnjLzeaenLOoSpmFax3sn0nFivCxKLrmxGqwKLDX3eAF2BO3flaURUNOK1sMKlqZUpEXkvrNDbLoleUTKGC7R3PVgbS06jeZiN+Caw7GBz4hTo6YmwQgd8ZWPc1s31c8QC8xHzDTiU5fQkz4veQgcekXlGenXlz8oddQ/"


NOTIFICATION_TEMPLATES_B64 = "eNq9VcFqGzEQ/ZVhIZCAGze0EDCOIY17TClJmktsFlka20q00iJpHRzjDyk55QPyCT05/a+O1rv2Ol6nh4YaFtaamTczb/Rmb2aRZglGrehMSdQetPFyKDnz0uioEfEx0xoV2b8mTKpwYrSQubUV7fdsTwP9hOGHI/T7vcjiEC1qjjGd+WmKvegATk6gF51dnEMXmepFZRTTohLJM+dNEvO8jhhDOop909czdxeXSaSGm9I7/Cij0S5TPu+lFzU2jd8yb/M+gL/ldsmSVCH5KIW81uNqjJal08p5v75oRykyF0olkuvKZUSbQrGVoWs0voY/qI4i54Dm8X3qx/nYBPMYh9mNUNC5yGgcdJRbpi6WOmZiEtJFrc90ZniWBNILmDCpK6KW3FGzgQoYR/Q+IR8ydwkCvuDQ2ACYoHNsFMLaaadrBnbxCwTqRruZdkKh4SGLXTwJCYMpH5sErhdPCaS/f8rUJPrlUUnQTPDx4ukBbxfPfPEMHm2yeNZwZ/RDmA1HaIIRg5dHm9GbD5RLbL1KsmSo7bw1etSZzXLyvfQ0wPm83SzO2wNbeHZpIEkLyHFIeCkeZl4qd0idJcznjHmZ4H5AKSk8IKQ822bmS0jNg7BsgkkJfy09U6cjBFKWljwErOkqqT5n9k6Y+zAzh1rEbuo8JvGGClsfC6M3MVMqZs7JkUZ0S0s2uKWbSVh5QlhnhAtMpBZo8w6rVFA2i1ymQWmEcjMLf1FO0MaDaby6DkOJKlyfGmUuEVYh1ijqRmdKbSyI4oCXb4Pydd5ftoS2ru5TQXVH88Z6N1UUuuoKPsAxhLv41zUVWn+9MTb0t3NV7F4TwaO/EvhS2lu6rtV0qecc4b1UfPx+Kh5/6vxIuSGSRxs9gy2IbzfJpXL3aQHCkPajud8KCXSDdEClB2KOIRS+qdpMlbJVslNKN9TdWgkWtpRMrjVB1Pd20Nbgd8Z3qcjA7zZGyfzu2OLryZmrCd/4JoYrvRvndKltAd5s4xTCD4ugitBuFhyGZ7YHcrgsGh23Ms3nsDcvZrXqdW1c5ynnUnZdAVguPQIn0RL+3vzdV9lRdZWd1d27f11jFfr+x/rq/wFiHkXT"


CUSTOM_PERMISSION_FIELDS = (
	"select",
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"mask",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"impersonate",
)


def _pad_base64(encoded):
	return encoded + ("=" * (-len(encoded) % 4))


def _decode_bundle(encoded):
	return json.loads(zlib.decompress(base64.b64decode(_pad_base64(encoded))).decode("utf-8"))


def _apply_additional_property_setters():
	name = "CRM Organization-annual_revenue-permlevel"
	values = {
		"doctype_or_field": "DocField",
		"doc_type": "CRM Organization",
		"field_name": "annual_revenue",
		"property": "permlevel",
		"property_type": "Int",
		"value": "1",
		"is_system_generated": 0,
	}

	if frappe.db.exists("Property Setter", name):
		frappe.db.set_value("Property Setter", name, values, update_modified=False)
		return

	frappe.get_doc({"doctype": "Property Setter", "name": name, **values}).insert(ignore_permissions=True)


def _apply_custom_docperms():
	for source in _decode_bundle(CUSTOM_DOCPERM_B64):
		filters = {
			"parent": source["parent"],
			"role": source["role"],
			"permlevel": source["permlevel"],
		}
		name = frappe.db.exists("Custom DocPerm", filters)
		values = {
			"if_owner": source.get("if_owner", 0),
			**{field: source.get(field, 0) for field in CUSTOM_PERMISSION_FIELDS},
		}

		if name:
			frappe.db.set_value("Custom DocPerm", name, values, update_modified=False)
			continue

		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				**filters,
				**values,
			}
		).insert(ignore_permissions=True)


def _apply_safe_crm_settings():
	if not frappe.db.exists("DocType", "CRM Settings"):
		return

	settings = frappe.get_single("CRM Settings")
	if settings.get("enable_frappe_crm_data_synchronization") != 1:
		settings.enable_frappe_crm_data_synchronization = 1
		settings.save(ignore_permissions=True)


def _apply_safe_erpnext_crm_settings():
	if "erpnext" not in frappe.get_installed_apps():
		return

	if not frappe.db.exists("DocType", "ERPNext CRM Settings"):
		return

	settings = frappe.get_single("ERPNext CRM Settings")
	targets = {
		"enabled": 1,
		"erpnext_company": "Vital Age Clinic",
		"create_customer_on_status_change": 1,
		"deal_status": "Monitoring",
	}
	changed = False

	for fieldname, value in targets.items():
		if settings.get(fieldname) != value:
			settings.set(fieldname, value)
			changed = True

	# Saving intentionally invokes the CRM integration's own validation so its
	# system-generated fields, quotation filter and Item permissions are created.
	# API credentials and remote-site secrets are never populated here.
	if changed:
		settings.save(ignore_permissions=True)


def _apply_notifications():
	sender = "Vital Age Clinic Admin"
	if not frappe.db.exists("Email Account", sender):
		# Email Account credentials are environment-specific. Re-run migrate after
		# configuring this account on a fresh site to install the notifications.
		return

	for template in _decode_bundle(NOTIFICATION_TEMPLATES_B64):
		name = template["name"]
		if frappe.db.exists("Notification", name):
			continue

		doc = frappe.new_doc("Notification")
		for fieldname, value in template.items():
			if fieldname in {"name", "recipients", "sender"}:
				continue
			doc.set(fieldname, value)

		doc.name = name
		doc.sender = sender
		for recipient in template.get("recipients", []):
			doc.append("recipients", recipient)
		doc.insert(ignore_permissions=True)


def _ensure_global_default_views():
	if not frappe.db.exists("DocType", "CRM View Settings"):
		return

	for source in DEFAULT_VIEWS:
		view = frappe._dict(source)
		rows = remove_duplicates(sync_default_rows(view.doctype, view.type) or [])
		columns = sync_default_columns(view) or []

		name = frappe.db.exists(
			"CRM View Settings",
			{
				"dt": view.doctype,
				"type": view.type or "list",
				"is_standard": 1,
				"user": "",
			},
		)

		doc = frappe.get_doc("CRM View Settings", name) if name else frappe.new_doc("CRM View Settings")
		doc.label = view.label
		doc.type = view.type or "list"
		doc.dt = view.doctype
		doc.user = ""
		doc.public = 1
		doc.route_name = view.route_name or get_route_name(view.doctype)
		doc.load_default_columns = view.load_default_columns or False
		doc.filters = json.dumps(view.filters or {})
		doc.order_by = view.order_by or "modified desc"
		doc.group_by_field = view.group_by_field or "owner"
		doc.column_field = view.column_field or "status"
		doc.title_field = view.title_field
		doc.kanban_columns = "[]"
		doc.kanban_fields = "[]"
		doc.columns = json.dumps(columns)
		doc.rows = json.dumps(rows)
		doc.is_standard = 1
		doc.is_default = 1

		if name:
			doc.save(ignore_permissions=True)
		else:
			doc.insert(ignore_permissions=True)

		# Keep only one global default per DocType.
		frappe.db.set_value(
			"CRM View Settings",
			{
				"name": ("!=", doc.name),
				"user": "",
				"dt": view.doctype,
				"is_default": 1,
			},
			"is_default",
			0,
			update_modified=False,
		)

		# Earlier versions of the VitalAge bootstrap created these defaults for
		# Administrator only. They are invisible to normal CRM users, so make sure
		# they no longer compete as defaults after the global view is installed.
		frappe.db.set_value(
			"CRM View Settings",
			{
				"user": "Administrator",
				"dt": view.doctype,
				"is_standard": 1,
				"is_default": 1,
			},
			"is_default",
			0,
			update_modified=False,
		)
