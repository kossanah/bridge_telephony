"""
Bridge Telephony API
Public API endpoints for telephony operations
"""

import frappe


@frappe.whitelist(allow_guest=True)
def is_call_integration_enabled():
    """
    Override CRM's is_call_integration_enabled to include FreePBX & Africa's Talking

    Returns:
        dict: Status of all telephony integrations
    """
    twilio_enabled = frappe.db.get_single_value("CRM Twilio Settings", "enabled")
    exotel_enabled = frappe.db.get_single_value("CRM Exotel Settings", "enabled")
    
    settings = frappe.get_cached_doc("Bridge Telephony Settings")
    provider = getattr(settings, "provider", "FreePBX")
    
    africastalking_enabled = bool(settings.enabled and provider == "Africa's Talking")
    freepbx_enabled = bool(getattr(settings, "freepbx_enabled", 0) or (settings.enabled and provider == "FreePBX"))

    return {
        "integrations": {
            "twilio": bool(twilio_enabled),
            "exotel": bool(exotel_enabled),
            "africastalking": bool(africastalking_enabled),
            "freepbx": bool(freepbx_enabled),
        },
        "twilio_enabled": bool(twilio_enabled),
        "exotel_enabled": bool(exotel_enabled),
        "africastalking_enabled": bool(africastalking_enabled),
        "freepbx_enabled": bool(freepbx_enabled),
        "default_calling_medium": get_user_default_calling_medium(),
    }


def get_user_default_calling_medium():
    """Get the user's default calling medium from CRM Telephony Agent"""
    if not frappe.db.exists("CRM Telephony Agent", frappe.session.user):
        return "FreePBX"

    default_medium = frappe.db.get_value(
        "CRM Telephony Agent", frappe.session.user, "default_medium"
    )

    if not default_medium:
        settings = frappe.get_cached_doc("Bridge Telephony Settings")
        if getattr(settings, "freepbx_enabled", 0) or getattr(settings, "provider", "FreePBX") == "FreePBX":
            return "FreePBX"
        return None

    return default_medium


@frappe.whitelist()
def set_default_calling_medium(medium):
    """
    Set the user's default calling medium

    Args:
        medium: The calling medium (FreePBX, Twilio, Exotel, or Africa's Talking)

    Returns:
        str: The updated default medium
    """
    if not frappe.db.exists("CRM Telephony Agent", frappe.session.user):
        frappe.get_doc({
            "doctype": "CRM Telephony Agent",
            "user": frappe.session.user,
            "default_medium": medium,
        }).insert(ignore_permissions=True)
    else:
        frappe.db.set_value(
            "CRM Telephony Agent", frappe.session.user, "default_medium", medium
        )

    return get_user_default_calling_medium()


@frappe.whitelist()
def make_call(to_number, from_number=None, reference_doctype=None, reference_name=None):
    """
    Initiate an outbound call via configured provider (FreePBX or Africa's Talking)

    Args:
        to_number: Recipient phone number
        from_number: Caller extension/number (optional)
        reference_doctype: Reference DocType (e.g., 'CRM Lead', 'CRM Deal')
        reference_name: Reference document name

    Returns:
        dict: Call details
    """
    try:
        settings = frappe.get_cached_doc("Bridge Telephony Settings")
        provider = getattr(settings, "provider", "FreePBX")

        if provider == "FreePBX" or getattr(settings, "freepbx_enabled", 0):
            from bridge_telephony.integrations.freepbx.handler import FreePBXHandler
            handler = FreePBXHandler()
            return handler.make_call(
                to_number=to_number,
                from_number=from_number,
                call_from=reference_doctype or "CRM",
                reference_doctype=reference_doctype,
                reference_name=reference_name
            )
        else:
            from bridge_telephony.integrations.africastalking.handler import AfricasTalkingHandler
            handler = AfricasTalkingHandler()
            return handler.make_call(
                to_number=to_number,
                from_number=from_number,
                call_from=reference_doctype or "CRM"
            )

    except Exception as e:
        frappe.log_error(title="Make Call API Error", message=f"Error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def retry_media_upload(media_name):
    """
    Retry uploading a media file to Africa's Talking

    Args:
        media_name: Name of Call Queue Media document

    Returns:
        dict: Upload result
    """
    try:
        from bridge_telephony.integrations.africastalking.media_manager import MediaManager

        manager = MediaManager()
        result = manager.retry_at_upload(media_name)

        return result

    except Exception as e:
        frappe.log_error(
            title="Retry Media Upload API Error",
            message=f"Error: {str(e)}"
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_call_history(limit=50):
    """
    Get call history for current user

    Args:
        limit: Number of records to fetch

    Returns:
        dict: Call logs
    """
    try:
        call_logs = frappe.get_all(
            "CRM Call Log",
            filters={"owner": frappe.session.user},
            fields=["name", "from", "to", "type", "status",
                    "duration", "creation", "telephony_medium"],
            order_by="creation desc",
            limit=limit
        )

        return {
            "success": True,
            "data": call_logs
        }

    except Exception as e:
        frappe.log_error(
            title="Get Call History Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def check_telephony_permission():
    """
    Check if user has telephony permissions

    Returns:
        dict: Permission status
    """
    try:
        # System Managers always have permission
        if "System Manager" in frappe.get_roles():
            return {
                "has_permission": True,
                "role": "System Manager"
            }

        # Check if user is a CRM Telephony Agent
        agent = frappe.db.exists("CRM Telephony Agent", {
                                 "user": frappe.session.user})

        if agent:
            return {
                "has_permission": True,
                "role": "Telephony Agent"
            }

        # Check general CRM Call Log create permission
        has_permission = frappe.has_permission("CRM Call Log", "create")

        return {
            "has_permission": has_permission,
            "role": "User"
        }

    except Exception as e:
        frappe.log_error(
            title="Check Permission Error",
            message=str(e)
        )
        return {
            "has_permission": False,
            "error": str(e)
        }


@frappe.whitelist()
def get_call_details(call_id):
    """
    Get details of a specific call

    Args:
        call_id: Call session ID

    Returns:
        dict: Call details
    """
    try:
        from bridge_telephony.integrations.africastalking.handler import AfricasTalkingHandler

        handler = AfricasTalkingHandler()
        result = handler.get_call_details(call_id)

        return result

    except Exception as e:
        frappe.log_error(
            title="Get Call Details Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def voice_actions():
    """
    Webhook endpoint for Africa's Talking voice actions
    This handles incoming call routing
    """
    try:
        from bridge_telephony.integrations.africastalking.handler import incoming_call_webhook
        return incoming_call_webhook()

    except Exception as e:
        frappe.log_error(
            title="Voice Actions Webhook Error",
            message=str(e)
        )
        return {
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def call_events():
    """
    Webhook endpoint for Africa's Talking call events
    This handles call status updates
    """
    try:
        from bridge_telephony.integrations.africastalking.handler import call_events_webhook
        return call_events_webhook()

    except Exception as e:
        frappe.log_error(
            title="Call Events Webhook Error",
            message=str(e)
        )
        return {
            "error": str(e)
        }


@frappe.whitelist()
def test_connection():
    """
    Test Africa's Talking API connection

    Returns:
        dict: Connection test result
    """
    try:
        settings = frappe.get_single("Bridge Telephony Settings")

        if not settings.enabled:
            return {
                "success": False,
                "error": "Bridge Telephony is not enabled"
            }

        # Use get_password() for Password fields
        api_key = settings.get_password("api_key")

        if not api_key or not settings.username:
            return {
                "success": False,
                "error": "API credentials not configured"
            }

        # Test API connection (simple check)
        import requests

        headers = {
            "apiKey": str(api_key),
            "Accept": "application/json"
        }

        # Note: Africa's Talking doesn't have a direct test endpoint
        # We just validate credentials are present
        return {
            "success": True,
            "message": "Credentials configured. Make a test call to verify.",
            "username": settings.username,
            "phone_number": settings.phone_number
        }

    except Exception as e:
        frappe.log_error(
            title="Test Connection Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist()
def test_africastalking_connection(username=None):
    """Test Africa's Talking API connection

    Args:
        username: AT username (optional, uses from settings if not provided)

    Returns:
        dict: Connection test result with success status and balance
    """
    try:
        settings = frappe.get_doc(
            "Bridge Telephony Settings", "Bridge Telephony Settings")

        if not username:
            username = settings.username

        api_key = settings.get_password("api_key")

        if not username or not api_key:
            return {
                "success": False,
                "error": "Username and API key are not configured"
            }

        # Test AT API connection by checking user account
        import requests
        headers = {
            "apiKey": str(api_key),
            "Accept": "application/json"
        }
        url = f"https://api.africastalking.com/version1/user?username={username}"
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            resp_data = response.json()
            balance = resp_data.get("UserData", {}).get("balance", "Unknown")
            return {
                "success": True,
                "message": "Connection successful",
                "balance": balance
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code}"
            }

    except Exception as e:
        frappe.log_error(
            title="Test Connection Error",
            message=str(e)
        )
        return {
            "success": False,
            "error": str(e)
        }
