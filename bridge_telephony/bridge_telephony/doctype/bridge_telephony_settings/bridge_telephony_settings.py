# Copyright (c) 2025, Edubridge Consultants Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests


class BridgeTelephonySettings(Document):
    def validate(self):
        """Validate settings before saving"""
        if self.enabled:
            provider = getattr(self, "provider", "FreePBX")
            if provider == "FreePBX":
                self.validate_freepbx_settings()
            elif provider == "Africa's Talking":
                self.validate_credentials()

    def validate_freepbx_settings(self):
        """Validate FreePBX configuration"""
        if getattr(self, "freepbx_enabled", 0):
            if not self.freepbx_host:
                frappe.throw("FreePBX Host is required when FreePBX is enabled")
            if not self.freepbx_ami_port:
                frappe.throw("FreePBX AMI Port is required when FreePBX is enabled")
            if not self.freepbx_ami_username:
                frappe.throw("FreePBX AMI Username is required when FreePBX is enabled")

    def validate_credentials(self):
        """Verify API credentials with Africa's Talking"""
        if not self.username or not self.api_key:
            frappe.throw(
                "Africa's Talking username and API key are required when Africa's Talking is selected"
            )

    def on_update(self):
        """Called after document is saved"""
        frappe.cache().delete_value("bridge_telephony_settings")
        frappe.publish_realtime(
            "bridge_telephony_settings_updated",
            {
                "enabled": self.enabled,
                "provider": getattr(self, "provider", "FreePBX"),
                "freepbx_enabled": getattr(self, "freepbx_enabled", 0),
            },
            user=frappe.session.user
        )


@frappe.whitelist()
def get_telephony_settings():
    """Get cached telephony settings"""
    settings = frappe.cache().get_value("bridge_telephony_settings")

    if not settings:
        settings = frappe.get_cached_doc(
            "Bridge Telephony Settings", "Bridge Telephony Settings"
        )
        frappe.cache().set_value("bridge_telephony_settings", settings.as_dict())

    return settings


@frappe.whitelist()
def test_freepbx_connection():
    """Test FreePBX AMI connection"""
    from bridge_telephony.integrations.freepbx.handler import FreePBXHandler

    handler = FreePBXHandler()
    return handler.test_connection()


@frappe.whitelist()
def test_connection():
    """Test Africa's Talking connection"""
    settings = frappe.get_doc(
        "Bridge Telephony Settings", "Bridge Telephony Settings"
    )

    if not settings.enabled:
        return {"success": False, "message": "Telephony is not enabled"}

    provider = getattr(settings, "provider", "FreePBX")
    if provider == "FreePBX":
        return test_freepbx_connection()

    try:
        api_key = settings.get_password("api_key")
        url = "https://api.africastalking.com/version1/user"
        headers = {
            "apiKey": str(api_key),
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        balance = data.get("UserData", {}).get("balance", "Unknown")

        return {
            "success": True,
            "message": f"Connection successful. Balance: {balance}"
        }
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": str(e)}
