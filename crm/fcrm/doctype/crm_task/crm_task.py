# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.desk.form.assign_to import add as assign
from frappe.desk.form.assign_to import remove as unassign
from frappe.model.document import Document


class CRMTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from crm.fcrm.doctype.crm_task_participant.crm_task_participant import CRMTaskParticipant

		assigned_to: DF.Link | None
		description: DF.TextEditor | None
		due_date: DF.Datetime | None
		name: DF.Int | None
		participants: DF.Table[CRMTaskParticipant]
		priority: DF.Literal["Low", "Medium", "High"]
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		start_date: DF.Date | None
		status: DF.Literal["Backlog", "Todo", "In Progress", "Done", "Canceled"]
		title: DF.Data
	# end: auto-generated types

	def after_insert(self):
		self.sync_assignments()

	def on_update(self):
		self.sync_assignments()

	def get_assignment_users(self):
		users = {row.user for row in (self.get("participants") or []) if row.user}
		if self.assigned_to:
			users.add(self.assigned_to)
		return users

	def sync_assignments(self):
		desired_users = self.get_assignment_users()
		current_users = set(self.get_assigned_users())

		for user in current_users - desired_users:
			unassign(self.doctype, self.name, user)

		for user in desired_users - current_users:
			assign(
				{
					"assign_to": [user],
					"doctype": self.doctype,
					"name": self.name,
					"description": self.title or self.description,
				}
			)

		# Frappe's assignment helpers update/clear a physical assigned_to
		# field while adding or removing ToDos. For CRM Task that field is
		# our primary assignee, so always restore it after syncing the
		# additional participant assignments.
		frappe.db.set_value(
			self.doctype,
			self.name,
			"assigned_to",
			self.assigned_to,
			update_modified=False,
		)

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Title",
				"type": "Data",
				"key": "title",
				"width": "16rem",
			},
			{
				"label": "Status",
				"type": "Select",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "Priority",
				"type": "Select",
				"key": "priority",
				"width": "8rem",
			},
			{
				"label": "Due Date",
				"type": "Date",
				"key": "due_date",
				"width": "8rem",
			},
			{
				"label": "Assigned To",
				"type": "Link",
				"key": "assigned_to",
				"width": "10rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]

		rows = [
			"name",
			"title",
			"description",
			"assigned_to",
			"due_date",
			"status",
			"priority",
			"reference_doctype",
			"reference_docname",
			"modified",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "title",
			"kanban_fields": '["description", "priority", "creation"]',
		}
