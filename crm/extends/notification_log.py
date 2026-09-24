import frappe

CRM_ROUTES = {
	"CRM Lead": "leads",
	"CRM Deal": "deals",
}


def before_insert(doc, method=None):
	if doc.link:
		return

	route = get_crm_route(doc.document_type, doc.document_name)
	if route:
		doc.link = frappe.utils.get_url(route)


def get_crm_route(doctype, name):
	if not name:
		return None

	suffix = ""
	if doctype == "CRM Task":
		parent = frappe.db.get_value(
			"CRM Task", name, ["reference_doctype", "reference_docname"], as_dict=True
		)
		if not parent or not parent.reference_docname:
			return None
		doctype, name = parent.reference_doctype, parent.reference_docname
		suffix = "#tasks"

	list_route = CRM_ROUTES.get(doctype)
	if not list_route:
		return None

	return f"/crm/{list_route}/{name}{suffix}"
