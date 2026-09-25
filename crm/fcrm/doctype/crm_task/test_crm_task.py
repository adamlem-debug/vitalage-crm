# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from crm.tests import CRMTestCase as FrappeTestCase


class TestCRMTask(FrappeTestCase):
	def tearDown(self) -> None:
		frappe.db.rollback()

	def test_task_creation(self):
		"""Test creating a basic task"""
		task = create_test_task(
			title="Test Task",
			description="Test task description",
			status="Todo",
			priority="Medium",
		)

		self.assertTrue(task.name)
		self.assertEqual(task.title, "Test Task")
		self.assertEqual(task.status, "Todo")
		self.assertEqual(task.priority, "Medium")

	def test_task_assignment_on_creation(self):
		"""Test that task is assigned to user on creation"""
		task = create_test_task(
			title="Assigned Task",
			assigned_to="Administrator",
		)

		# Verify task was assigned to exactly one user
		assignees = task.get_assigned_users()
		self.assertEqual(assignees, {"Administrator"})

	def test_update_assigned_user(self):
		"""Test updating assigned user unassigns previous and assigns new user"""
		# Create test user if not exists
		if not frappe.db.exists("User", "test@example.com"):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": "test@example.com",
					"first_name": "Test",
				}
			).insert()

		# Create task with initial assignment
		task = create_test_task(
			title="Reassign Task",
			assigned_to="Administrator",
		)

		# Verify initial assignment
		assignees = task.get_assigned_users()
		self.assertIn("Administrator", assignees)

		# Get fresh copy of the document to avoid timestamp mismatch
		task = frappe.get_doc("CRM Task", task.name)

		# Change assigned user
		task.assigned_to = "test@example.com"
		task.save()

		# Verify new assignment
		task.reload()
		self.assertEqual(task.assigned_to, "test@example.com")
		assignees_after = task.get_assigned_users()
		self.assertIn("test@example.com", assignees_after)
		self.assertNotIn("Administrator", assignees_after)

	def test_task_with_reference_doctype(self):
		"""Test creating task with reference to another document"""
		# Create a deal for reference
		org = frappe.get_doc(
			{
				"doctype": "CRM Organization",
				"organization_name": "Task Reference Org",
			}
		).insert()

		deal = frappe.get_doc(
			{
				"doctype": "CRM Deal",
				"organization": org.name,
			}
		).insert()

		# Create task with reference
		task = create_test_task(
			title="Deal Task",
			reference_doctype="CRM Deal",
			reference_docname=deal.name,
		)

		self.assertEqual(task.reference_doctype, "CRM Deal")
		self.assertEqual(task.reference_docname, deal.name)

	def test_task_due_date(self):
		"""Test task with due date"""
		task = create_test_task(
			title="Due Date Task",
			due_date="2026-12-31 23:59:59",
			start_date="2026-01-01",
		)

		self.assertTrue(task.due_date)
		self.assertTrue(task.start_date)

	def test_task_priority_ordering(self):
		"""Test that tasks can be ordered by priority for proper display"""
		# Create tasks with different priorities
		low_task = create_test_task(
			title="Low Priority Task",
			priority="Low",
			status="Todo",
		)
		medium_task = create_test_task(
			title="Medium Priority Task",
			priority="Medium",
			status="Todo",
		)
		high_task = create_test_task(
			title="High Priority Task",
			priority="High",
			status="Todo",
		)

		# Verify priorities are set
		self.assertEqual(low_task.priority, "Low")
		self.assertEqual(medium_task.priority, "Medium")
		self.assertEqual(high_task.priority, "High")

		# Test priority-based filtering
		high_priority_tasks = frappe.get_all(
			"CRM Task",
			filters={"priority": "High", "status": "Todo"},
			fields=["name", "priority"],
		)

		# Verify high priority task is in filtered results
		high_task_names = [t.name for t in high_priority_tasks]
		self.assertIn(high_task.name, high_task_names)
		self.assertNotIn(low_task.name, high_task_names)

	def test_task_status_workflow_and_filtering(self):
		"""Test task status transitions and filtering by status"""
		statuses = ["Backlog", "Todo", "In Progress", "Done", "Canceled"]

		task = create_test_task(title="Status Workflow Task", status="Backlog")
		initial_name = task.name

		# Test status transitions up to Done
		for status in statuses[1:4]:  # Backlog -> Todo -> In Progress -> Done
			task.status = status
			task.save()
			task.reload()
			self.assertEqual(task.status, status)

		# Test filtering by completed status (task should be Done now)
		done_tasks = frappe.get_all("CRM Task", filters={"status": "Done"}, fields=["name"])
		done_task_names = [str(t.name) for t in done_tasks]
		self.assertIn(str(initial_name), done_task_names)

		# Test filtering by active statuses (excluding Done and Canceled)
		task2 = create_test_task(title="Active Task", status="In Progress")
		active_tasks = frappe.get_all(
			"CRM Task",
			filters={"status": ["in", ["Backlog", "Todo", "In Progress"]]},
			fields=["name"],
		)
		active_task_names = [str(t.name) for t in active_tasks]
		self.assertIn(str(task2.name), active_task_names)
		self.assertNotIn(str(initial_name), active_task_names)  # task is Done, not active

		# Test Canceled status separately
		task3 = create_test_task(title="Canceled Task", status="Canceled")
		canceled_tasks = frappe.get_all("CRM Task", filters={"status": "Canceled"}, fields=["name"])
		canceled_task_names = [str(t.name) for t in canceled_tasks]
		self.assertIn(str(task3.name), canceled_task_names)

	def test_task_without_assigned_user(self):
		"""Test creating task without assigned user"""
		task = create_test_task(title="Unassigned Task")

		self.assertFalse(task.assigned_to)
		assignees = task.get_assigned_users()
		self.assertEqual(len(assignees), 0)

	def test_task_description(self):
		"""Test task with rich text description"""
		description = "<p>This is a <strong>rich text</strong> description</p>"
		task = create_test_task(
			title="Description Task",
			description=description,
		)

		self.assertEqual(task.description, description)

	def test_reassign_to_same_user(self):
		"""Test that reassigning to same user doesn't create duplicate assignments"""
		task = create_test_task(
			title="Same User Task",
			assigned_to="Administrator",
		)

		initial_assignees = task.get_assigned_users()
		initial_count = len(initial_assignees)

		# Get fresh copy of the document to avoid timestamp mismatch
		task = frappe.get_doc("CRM Task", task.name)

		# Save again without changing assigned_to
		task.save()

		# Verify no duplicate assignments
		task.reload()
		assignees_after = task.get_assigned_users()
		self.assertEqual(len(assignees_after), initial_count)
		self.assertIn("Administrator", assignees_after)

	def test_task_participants_are_additional_assignees(self):
		"""Primary assignee and Participants are all assigned to the Task."""
		for email, first_name in [
			("participant.one@example.com", "Participant One"),
			("participant.two@example.com", "Participant Two"),
		]:
			if not frappe.db.exists("User", email):
				frappe.get_doc(
					{
						"doctype": "User",
						"email": email,
						"first_name": first_name,
					}
				).insert()

		task = create_test_task(
			title="Multi-assignee Task",
			assigned_to="Administrator",
			participants=[
				{"user": "participant.one@example.com"},
				{"user": "participant.two@example.com"},
			],
		)

		self.assertEqual(
			task.get_assigned_users(),
			{
				"Administrator",
				"participant.one@example.com",
				"participant.two@example.com",
			},
		)

	def test_removed_task_participant_is_unassigned(self):
		"""Removing a Participant removes only that user's Task assignment."""
		for email, first_name in [
			("participant.keep@example.com", "Participant Keep"),
			("participant.remove@example.com", "Participant Remove"),
		]:
			if not frappe.db.exists("User", email):
				frappe.get_doc(
					{
						"doctype": "User",
						"email": email,
						"first_name": first_name,
					}
				).insert()

		task = create_test_task(
			title="Participant removal Task",
			assigned_to="Administrator",
			participants=[
				{"user": "participant.keep@example.com"},
				{"user": "participant.remove@example.com"},
			],
		)
		task.reload()

		task.set(
			"participants",
			[{"user": "participant.keep@example.com"}],
		)
		task.save()
		task.reload()

		self.assertEqual(
			task.get_assigned_users(),
			{
				"Administrator",
				"participant.keep@example.com",
			},
		)

	def test_task_participants_map_to_event_attendees(self):
		"""Event attendees use the User email, not the User document name."""
		from crm.fcrm.task_calendar_sync import set_event_participants

		frappe.db.set_value(
			"User",
			"Administrator",
			"email",
			"administrator@example.com",
			update_modified=False,
		)

		task = frappe.get_doc(
			{
				"doctype": "CRM Task",
				"title": "Calendar participants Task",
				"assigned_to": "owner@example.com",
				"participants": [
					{"user": "Administrator"},
				],
			}
		)
		event = frappe.new_doc("Event")

		set_event_participants(event, task)

		self.assertEqual(
			[
				(
					row.reference_doctype,
					row.reference_docname,
					row.email,
				)
				for row in event.event_participants
			],
			[
				("User", "Administrator", "administrator@example.com"),
			],
		)

	def test_calendar_cleanup_breaks_both_links_before_deferred_event_delete(self):
		"""Task deletion clears both directions and defers Event deletion."""
		from crm.fcrm.task_calendar_sync import cleanup_task_calendar_events

		task = frappe._dict(
			{
				"doctype": "CRM Task",
				"name": "TEST-TASK",
				"custom_calendar_event": "EV-TEST",
				"flags": frappe._dict(),
			}
		)

		with (
			patch(
				"crm.fcrm.task_calendar_sync.get_task_calendar_event_names",
				return_value={"EV-TEST", "EV-HISTORY"},
			),
			patch("crm.fcrm.task_calendar_sync.frappe.db.set_value") as set_value,
			patch("crm.fcrm.task_calendar_sync.frappe.db.exists", return_value=True),
			patch("crm.fcrm.task_calendar_sync.frappe.get_meta") as get_meta,
		):
			get_meta.return_value.has_field.return_value = True
			cleanup_task_calendar_events(task)

		self.assertIsNone(task.custom_calendar_event)
		self.assertCountEqual(
			task.flags.calendar_events_to_delete,
			["EV-TEST", "EV-HISTORY"],
		)
		set_value.assert_any_call(
			"CRM Task",
			"TEST-TASK",
			"custom_calendar_event",
			None,
			update_modified=False,
		)
		set_value.assert_any_call(
			"Event",
			"EV-TEST",
			"custom_crm_task_name",
			None,
			update_modified=False,
		)
		set_value.assert_any_call(
			"Event",
			"EV-HISTORY",
			"custom_crm_task_name",
			None,
			update_modified=False,
		)

	def test_task_delete_queues_captured_events(self):
		"""after_delete queues the Event names captured during on_trash."""
		from crm.fcrm.task_calendar_sync import queue_task_calendar_delete

		task = frappe._dict(
			{
				"doctype": "CRM Task",
				"name": "TEST-TASK",
				"flags": frappe._dict(
					{
						"calendar_events_to_delete": ["EV-TEST", "EV-HISTORY"],
					}
				),
			}
		)

		with patch("crm.fcrm.task_calendar_sync.frappe.enqueue") as enqueue:
			queue_task_calendar_delete(task)

		enqueue.assert_called_once_with(
			"crm.fcrm.task_calendar_sync.delete_task_calendar_history",
			queue="short",
			enqueue_after_commit=True,
			task_name="TEST-TASK",
			event_names=["EV-TEST", "EV-HISTORY"],
		)


def create_test_task(**kwargs):
	"""Helper function to create a CRM Task for testing"""
	data = {"doctype": "CRM Task"}
	data.update(kwargs)
	return frappe.get_doc(data).insert()
