import frappe


@frappe.whitelist()
def test_brand_new_method(username=None):
    """Brand new test method"""
    return {"success": True, "message": "This is brand new"}
