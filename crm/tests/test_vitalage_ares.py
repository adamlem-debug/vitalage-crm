"""Unit coverage for IČO validation and ARES response states."""

from unittest.mock import patch

from crm.api.vitalage_ares import lookup_organization, valid_ico
from crm.tests import CRMTestCase


class TestVitalAgeARES(CRMTestCase):
	def test_ico_checksum(self):
		self.assertTrue(valid_ico("00177041"))
		self.assertFalse(valid_ico("00177042"))
		self.assertFalse(valid_ico("123"))
		self.assertFalse(valid_ico("ABCDEFGH"))

	@patch("crm.api.vitalage_ares.frappe.db.get_value", return_value=None)
	@patch("crm.api.vitalage_ares.frappe.has_permission", return_value=True)
	def test_invalid_ico_does_not_call_ares(self, _permission, _db):
		with patch("crm.api.vitalage_ares.requests.get") as request:
			self.assertEqual(lookup_organization("00177042")["status"], "invalid_ico")
			request.assert_not_called()

	@patch("crm.api.vitalage_ares.frappe.db.get_value", return_value=None)
	@patch("crm.api.vitalage_ares.frappe.has_permission", return_value=True)
	@patch("crm.api.vitalage_ares.requests.get")
	def test_not_found(self, request, _permission, _db):
		request.return_value.status_code = 404
		self.assertEqual(lookup_organization("00177041")["status"], "not_found")

	@patch("crm.api.vitalage_ares.frappe.db.get_value", return_value=None)
	@patch("crm.api.vitalage_ares.frappe.has_permission", return_value=True)
	@patch("crm.api.vitalage_ares.requests.get")
	def test_lookup_result(self, request, _permission, _db):
		request.return_value.status_code = 200
		request.return_value.json.return_value = {
			"ico": "00177041",
			"obchodniJmeno": "Testovací společnost",
			"dic": "CZ00177041",
			"sidlo": {"textovaAdresa": "Ulice 1, Praha", "nazevObce": "Praha"},
		}
		result = lookup_organization("00177041")
		self.assertEqual(result["status"], "ok")
		self.assertEqual(result["data"]["custom_dic"], "CZ00177041")
		self.assertEqual(result["data"]["address"]["city"], "Praha")
