"""Tests for synchronizing Contact names to the Deal display title."""

from types import SimpleNamespace
from unittest.mock import patch

from crm.api.contact import on_update
from crm.tests import CRMTestCase


class TestDealClientNameSync(CRMTestCase):
	@patch("crm.api.contact.frappe")
	def test_updates_only_stale_primary_contact_deals(self, mock_frappe):
		mock_frappe.get_all.return_value = [
			SimpleNamespace(parent="DEAL-1"),
			SimpleNamespace(parent="DEAL-2"),
		]
		mock_frappe.db.get_value.side_effect = ["Old Name", "New Name"]

		on_update(SimpleNamespace(name="CONTACT-1", full_name="New Name"), None)

		mock_frappe.get_all.assert_called_once_with(
			"CRM Contacts",
			filters={"contact": "CONTACT-1", "is_primary": 1, "parenttype": "CRM Deal"},
			fields=["parent"],
			distinct=True,
		)
		mock_frappe.db.set_value.assert_called_once_with(
			"CRM Deal",
			"DEAL-1",
			"custom_client_full_name",
			"New Name",
		)

	@patch("crm.api.contact.frappe")
	def test_unlinked_contact_does_not_update_deals(self, mock_frappe):
		mock_frappe.get_all.return_value = []
		on_update(SimpleNamespace(name="CONTACT-2", full_name="Another Name"), None)
		mock_frappe.db.set_value.assert_not_called()
