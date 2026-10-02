import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def before_install():
	"""Run before app installation"""
	# Check dependencies
	if "crm" not in frappe.get_installed_apps():
		frappe.throw(_("Frappe CRM must be installed first"))


def after_install():
	"""Run after app installation"""
	print("Setting up Bridge Telephony...")
	
	# Add custom fields to CRM doctypes
	add_custom_fields()
	
	# Create default settings
	create_default_settings()
	
	print("Bridge Telephony installed successfully!")


def add_custom_fields():
	"""Add custom fields to CRM Lead and Deal"""
	custom_fields = {
		"CRM Lead": [
			{
				"fieldname": "telephony_status",
				"fieldtype": "Select",
				"label": "Telephony Status",
				"options": "\nNot Called\nCalled - No Answer\nCalled - Busy\nCalled - Connected\nDo Not Call",
				"insert_after": "mobile_no",
			},
			{
				"fieldname": "last_call_time",
				"fieldtype": "Datetime",
				"label": "Last Call Time",
				"insert_after": "telephony_status",
				"read_only": 1,
			},
			{
				"fieldname": "total_calls",
				"fieldtype": "Int",
				"label": "Total Calls",
				"insert_after": "last_call_time",
				"read_only": 1,
				"default": 0,
			},
		],
		"CRM Deal": [
			{
				"fieldname": "last_call_time",
				"fieldtype": "Datetime",
				"label": "Last Call Time",
				"insert_after": "status",
				"read_only": 1,
			},
			{
				"fieldname": "total_calls",
				"fieldtype": "Int",
				"label": "Total Calls",
				"insert_after": "last_call_time",
				"read_only": 1,
				"default": 0,
			},
		],
	}
	
	create_custom_fields(custom_fields, ignore_validate=True)


def create_default_settings():
	"""Create Bridge Telephony Settings with defaults"""
	if not frappe.db.exists("Bridge Telephony Settings", "Bridge Telephony Settings"):
		settings = frappe.get_doc({
			"doctype": "Bridge Telephony Settings",
			"enabled": 0,
			"enable_recording": 1,
			"auto_create_call_logs": 1,
			"enable_call_queue": 1,
			"webhook_verify_token": frappe.generate_hash(length=32),
		})
		settings.insert(ignore_permissions=True)
		frappe.db.commit()
