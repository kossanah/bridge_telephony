import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    # 1. Update CRM Call Log telephony_medium options
    doctype = "CRM Call Log"
    fieldname = "telephony_medium"
    property_name = "options"
    new_options = "\nManual\nTwilio\nExotel\nAfrica's Talking\nFreePBX"

    ps_name = frappe.db.get_value("Property Setter", {
        "doc_type": doctype,
        "field_name": fieldname,
        "property": property_name
    })

    if ps_name:
        ps = frappe.get_doc("Property Setter", ps_name)
        ps.value = new_options
        ps.module = "Bridge Telephony"
        ps.save()
        frappe.db.commit()
        print(f"Updated Property Setter: {ps.name}")
    else:
        make_property_setter(doctype, fieldname, property_name, new_options, "Select", for_doctype=False)
        ps_name = frappe.db.get_value("Property Setter", {
            "doc_type": doctype,
            "field_name": fieldname,
            "property": property_name
        })
        if ps_name:
            ps = frappe.get_doc("Property Setter", ps_name)
            ps.module = "Bridge Telephony"
            ps.save()
            frappe.db.commit()
            print(f"Created Property Setter: {ps.name}")

    # 2. Add FreePBX Custom Fields to CRM Telephony Agent
    custom_fields = {
        "CRM Telephony Agent": [
            {
                "fieldname": "section_break_freepbx",
                "label": "FreePBX",
                "fieldtype": "Section Break",
                "insert_after": "africastalking_number",
                "module": "Bridge Telephony"
            },
            {
                "fieldname": "freepbx",
                "label": "FreePBX Enabled",
                "fieldtype": "Check",
                "default": "1",
                "insert_after": "section_break_freepbx",
                "module": "Bridge Telephony"
            },
            {
                "fieldname": "freepbx_extension",
                "label": "FreePBX Extension",
                "fieldtype": "Data",
                "insert_after": "freepbx",
                "depends_on": "freepbx",
                "mandatory_depends_on": "freepbx",
                "description": "Agent internal extension number on FreePBX (e.g., 1001)",
                "module": "Bridge Telephony"
            }
        ]
    }
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    print("Created/Updated FreePBX Custom Fields on CRM Telephony Agent")

def configure_freepbx_settings(
    host="172.187.235.228",
    port=5038,
    username="frappe_crm",
    secret="FrappeCrm_Voice2026_SecureKey",
    context="from-internal",
    recording_url="https://voice.bridge.ng"
):
    settings = frappe.get_doc("Bridge Telephony Settings")
    settings.provider = "FreePBX"
    settings.freepbx_enabled = 1
    settings.freepbx_host = host
    settings.freepbx_ami_port = int(port)
    settings.freepbx_ami_username = username
    settings.freepbx_context = context
    settings.freepbx_recording_url = recording_url
    settings.save(ignore_permissions=True)
    if secret:
        from frappe.utils.password import set_encrypted_password
        set_encrypted_password("Bridge Telephony Settings", "Bridge Telephony Settings", secret, "freepbx_ami_secret")
    frappe.db.commit()
    print("Bridge Telephony Settings configured for FreePBX!")

def update_agents():
    for user in ["Administrator", "kanaekwe@gmail.com"]:
        if frappe.db.exists("CRM Telephony Agent", user):
            frappe.db.set_value("CRM Telephony Agent", user, {
                "freepbx_extension": "1001",
                "default_medium": "FreePBX",
                "freepbx": 1
            })
    frappe.db.commit()
    print("Agents updated with extension 1001 and default_medium FreePBX")

if __name__ == "__main__":
    execute()


