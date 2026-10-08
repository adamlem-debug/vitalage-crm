"""ARES business registry lookup used by the VitalAge Organization quick-entry form."""

import re

import frappe
import requests
from frappe import _

ARES_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/"


def valid_ico(ico):
	"""Validate a Czech eight-digit IČO including its check digit."""
	if not isinstance(ico, str) or not re.fullmatch(r"[0-9]{8}", ico):
		return False
	weighted = sum(int(digit) * weight for digit, weight in zip(ico[:7], range(8, 1, -1), strict=False))
	check = (11 - (weighted % 11)) % 10
	return check == int(ico[7])


@frappe.whitelist()
def lookup_organization(ico: str):
	"""Return normalized public registry data; never expose raw upstream errors."""
	if not frappe.has_permission("CRM Organization", "create"):
		frappe.throw(_("Not permitted to create Organization"), frappe.PermissionError)

	ico = (ico or "").strip()
	if not valid_ico(ico):
		return {"status": "invalid_ico"}

	existing = frappe.db.get_value("CRM Organization", {"custom_ico": ico}, "name")
	if existing:
		return {"status": "existing", "organization": existing}

	try:
		response = requests.get(
			ARES_URL + ico,
			headers={"Accept": "application/json"},
			timeout=8,
		)
	except requests.RequestException:
		return {"status": "unavailable"}

	if response.status_code == 404:
		return {"status": "not_found"}
	if response.status_code != 200:
		return {"status": "unavailable"}

	try:
		data = response.json()
	except ValueError:
		return {"status": "unavailable"}
	if not isinstance(data, dict) or str(data.get("ico") or "") != ico:
		return {"status": "incomplete"}

	address = data.get("sidlo") if isinstance(data.get("sidlo"), dict) else {}
	name = data.get("obchodniJmeno")
	normalized = {
		"organization_name": name if isinstance(name, str) else "",
		"custom_ico": ico,
		"custom_dic": data.get("dic") if isinstance(data.get("dic"), str) else "",
		"address_display": address.get("textovaAdresa") or "",
		"address": {
			"address_line1": address.get("nazevUlice") or address.get("textovaAdresa") or "",
			"city": address.get("nazevObce") or "",
			"pincode": str(address.get("psc") or ""),
			"country": "Czech Republic",
		},
	}
	return {
		"status": "ok" if normalized["organization_name"] and normalized["address_display"] else "incomplete",
		"data": normalized,
	}
