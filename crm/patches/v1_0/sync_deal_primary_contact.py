import json
from collections import defaultdict

import frappe

OLD_DEFAULT_DEAL_COLUMNS = [
	"organization",
	"annual_revenue",
	"status",
	"email",
	"mobile_no",
	"_assign",
	"modified",
]


def execute():
	sync_primary_contact_field()
	migrate_old_default_deal_views()


def sync_primary_contact_field():
	"""Mirror the CRM Deal contacts table primary contact into CRM Deal.contact.

	Existing relationships remain untouched. A single linked contact is promoted
	to primary automatically, matching CRM Deal validation behavior. For multiple
	contacts without an explicit primary, an existing CRM Deal.contact value is
	used only when it already points to one of the linked contacts.
	"""
	contacts_by_deal = defaultdict(list)
	for row in frappe.get_all(
		"CRM Contacts",
		filters={"parenttype": "CRM Deal"},
		fields=["name", "parent", "contact", "is_primary", "idx"],
		order_by="parent asc, idx asc",
		limit_page_length=0,
	):
		if row.contact:
			contacts_by_deal[row.parent].append(row)

	for deal in frappe.get_all(
		"CRM Deal",
		fields=["name", "contact"],
		limit_page_length=0,
	):
		rows = contacts_by_deal.get(deal.name, [])
		selected = None

		if rows:
			primary_rows = [row for row in rows if row.is_primary]

			if len(primary_rows) == 1:
				selected = primary_rows[0]
			elif len(primary_rows) > 1:
				selected = next(
					(row for row in primary_rows if row.contact == deal.contact),
					primary_rows[0],
				)
			elif len(rows) == 1:
				selected = rows[0]
			elif deal.contact:
				selected = next(
					(row for row in rows if row.contact == deal.contact),
					None,
				)

		if selected:
			# Reconcile only the primary flags; linked contacts themselves are
			# never removed or recreated by this migration.
			for row in rows:
				expected = 1 if row.name == selected.name else 0
				if row.is_primary != expected:
					frappe.db.set_value(
						"CRM Contacts",
						row.name,
						"is_primary",
						expected,
						update_modified=False,
					)
			primary_contact = selected.contact
		else:
			primary_contact = None

		if deal.contact != primary_contact:
			frappe.db.set_value(
				"CRM Deal",
				deal.name,
				"contact",
				primary_contact,
				update_modified=False,
			)


def migrate_old_default_deal_views():
	"""Replace Organization with Contact in saved views using the old defaults."""
	for view in frappe.get_all(
		"CRM View Settings",
		filters={"dt": "CRM Deal"},
		fields=["name", "columns", "rows"],
		limit_page_length=0,
	):
		try:
			columns = json.loads(view.columns or "[]")
			rows = json.loads(view.rows or "[]")
		except (TypeError, json.JSONDecodeError):
			continue

		if [column.get("key") for column in columns] != OLD_DEFAULT_DEAL_COLUMNS:
			continue

		organization_column = columns[0]
		organization_column.update(
			{
				"label": "Contact",
				"type": "Link",
				"key": "contact",
				"options": "Contact",
			}
		)

		rows = ["contact" if row == "organization" else row for row in rows]
		rows = list(dict.fromkeys(rows))

		frappe.db.set_value(
			"CRM View Settings",
			view.name,
			{
				"columns": json.dumps(columns),
				"rows": json.dumps(rows),
			},
			update_modified=False,
		)
