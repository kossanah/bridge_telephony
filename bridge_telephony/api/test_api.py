import frappe


@frappe.whitelist()
def simple_test():
    """Simple test function"""
    return {"success": True, "message": "Simple test works"}


@frappe.whitelist()
def test_with_param(username=None):
    """Test function with parameter"""
    return {"success": True, "message": f"Test works with {username}"}


@frappe.whitelist()
def test_with_settings():
    """Test function that loads settings"""
    try:
        settings = frappe.get_single("Bridge Telephony Settings")
        return {"success": True, "message": f"Settings loaded: {settings.username}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def test_with_password():
    """Test function that loads password"""
    try:
        settings = frappe.get_single("Bridge Telephony Settings")
        api_key = settings.get_password("api_key")
        return {"success": True, "message": f"Password retrieved, type={type(api_key).__name__}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
