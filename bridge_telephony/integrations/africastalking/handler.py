"""
Africa's Talking API Integration Handler
Handles voice call operations, webhooks, and API communication
Following the CRM Exotel integration pattern
"""

import frappe
import requests
import json
from frappe import _
from frappe.utils import now_datetime, get_datetime, cint, flt
from frappe.integrations.utils import create_request_log

from crm.integrations.api import get_contact_by_phone_number

# Endpoints for webhook
# Incoming Call:
# <site>/api/method/bridge_telephony.api.voice_actions.voice_actions?key=<webhook-verify-token>
# Call Events:
# <site>/api/method/bridge_telephony.api.voice_actions.call_events?key=<webhook-verify-token>


class AfricasTalkingHandler:
    """Main handler for Africa's Talking Voice API integration"""

    def __init__(self):
        self.settings = self.get_settings()
        self.base_url = "https://voice.africastalking.com"
        # Use get_password() for Password fields to get the actual value
        api_key = self.settings.get_password("api_key")
        self.headers = {
            "apiKey": str(api_key),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

    @staticmethod
    def get_settings():
        """Get cached Bridge Telephony Settings"""
        return frappe.get_single("Bridge Telephony Settings")

    def make_call(self, to_number, from_number=None, call_from="CRM"):
        """
        Initiate an outbound call through Africa's Talking

        Args:
            to_number: Recipient phone number (E.164 format)
            from_number: Your AT registered number (optional)
            call_from: Source context (CRM Lead, CRM Deal, etc.)

        Returns:
            dict: Call details or error
        """
        try:
            if not from_number:
                from_number = frappe.get_value(
                    "CRM Telephony Agent", {
                        "user": frappe.session.user}, "mobile_no"
                )

            caller_id = frappe.get_value(
                "CRM Telephony Agent", {
                    "user": frappe.session.user}, "africastalking_number"
            )

            if not caller_id:
                caller_id = self.settings.phone_number

            if not caller_id:
                frappe.throw(
                    _("You do not have Africa's Talking Number set in your Telephony Agent"),
                    title=_("Africa's Talking Number Missing")
                )

            if not from_number:
                frappe.throw(
                    _("You do not have mobile number set in your Telephony Agent"),
                    title=_("Mobile Number Missing")
                )

            # Format phone numbers
            to_number = self._format_phone_number(to_number)
            from_number = self._format_phone_number(from_number)

            # Generate callback URL for voice actions
            callback_url = get_status_updater_url()

            # Make API call
            url = f"{self.base_url}/call"
            data = {
                "username": self.settings.username,
                "to": to_number,
                "from": caller_id,
                "callbackUrl": callback_url
            }

            response = requests.post(
                url, headers=self.headers, data=data, timeout=30)
            response_data = response.json()

            if response.status_code == 200 or response.status_code == 201:
                entries = response_data.get("entries", [])
                call_id = entries[0].get("sessionId") if entries else None

                # Create CRM Call Log
                create_call_log(
                    call_id=call_id,
                    from_number=from_number,
                    to_number=to_number,
                    medium=caller_id,
                    call_type="Outgoing",
                    agent=frappe.session.user,
                )

                return {
                    "success": True,
                    "CallSid": call_id,
                    "data": response_data,
                    "message": "Call initiated successfully"
                }
            else:
                frappe.log_error(
                    title="Africa's Talking Call Failed",
                    message=f"Response: {response.text}"
                )
                return {
                    "success": False,
                    "error": response_data.get("errorMessage", "Failed to initiate call")
                }

        except Exception as e:
            frappe.log_error(
                title="Africa's Talking API Error",
                message=f"Error making call: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e)
            }

    def _format_phone_number(self, number):
        """Format phone number to E.164 format"""
        if not number:
            return None

        # Remove all non-digit characters except +
        cleaned = ''.join(c for c in str(number) if c.isdigit() or c == '+')

        # Add + if not present and starts with a country code
        if cleaned and not cleaned.startswith('+'):
            cleaned = '+' + cleaned

        return cleaned

    def get_call_details(self, call_id):
        """
        Retrieve call details from local CRM Call Log

        Args:
            call_id: The session ID from AT

        Returns:
            dict: Call details
        """
        try:
            if frappe.db.exists("CRM Call Log", call_id):
                call_log = frappe.get_doc("CRM Call Log", call_id)
                return {
                    "success": True,
                    "data": call_log.as_dict()
                }
            else:
                return {
                    "success": False,
                    "error": "Call log not found"
                }

        except Exception as e:
            frappe.log_error(
                title="Get Call Details Error",
                message=f"Error: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e)
            }


# Outgoing Call
@frappe.whitelist()
def make_a_call(to_number, from_number=None, caller_id=None):
    """Make an outgoing call via Africa's Talking"""
    if not is_integration_enabled():
        frappe.throw(_("Please setup Africa's Talking integration"),
                     title=_("Integration Not Enabled"))

    handler = AfricasTalkingHandler()
    return handler.make_call(to_number=to_number, from_number=from_number)


def get_africastalking_settings():
    """Get Bridge Telephony Settings"""
    return frappe.get_single("Bridge Telephony Settings")


def get_status_updater_url():
    """Generate callback URL for webhooks"""
    from frappe.utils.data import get_url

    webhook_verify_token = frappe.db.get_single_value(
        "Bridge Telephony Settings", "webhook_verify_token")
    return get_url(f"api/method/bridge_telephony.api.voice_actions.call_events?key={webhook_verify_token}")


def validate_request():
    """Validate incoming webhook request"""
    webhook_verify_token = frappe.db.get_single_value(
        "Bridge Telephony Settings", "webhook_verify_token")
    key = frappe.request.args.get("key")
    is_valid = key and key == webhook_verify_token

    if not is_valid:
        frappe.throw(_("Unauthorized request"), exc=frappe.PermissionError)


@frappe.whitelist()
def is_integration_enabled():
    """Check if Africa's Talking integration is enabled"""
    return frappe.db.get_single_value("Bridge Telephony Settings", "enabled", True)


# Incoming Call
@frappe.whitelist(allow_guest=True)
def handle_request(**kwargs):
    """Handle incoming call webhook from Africa's Talking"""
    validate_request()
    if not is_integration_enabled():
        return

    request_log = create_request_log(
        kwargs,
        request_description="Africa's Talking Call",
        service_name="Africa's Talking",
        request_headers=frappe.request.headers,
        is_remote_request=1,
    )

    try:
        request_log.status = "Completed"
        settings = get_africastalking_settings()
        if not settings.enabled:
            return

        call_payload = kwargs

        frappe.publish_realtime("africastalking_call", call_payload)

        session_id = call_payload.get("sessionId")
        is_active = call_payload.get("isActive", "1")
        status = call_payload.get("callSessionState", "")

        if status == "free" or is_active == "0":
            # Call ended - update call log
            if call_log := get_call_log(call_payload):
                update_call_log(call_payload, call_log=call_log)
            return

        if call_log := get_call_log(call_payload):
            update_call_log(call_payload, call_log=call_log)
        else:
            create_call_log(
                call_id=session_id,
                from_number=call_payload.get("callerNumber"),
                to_number=call_payload.get("destinationNumber"),
                medium=call_payload.get("callerNumber"),
                status=get_call_log_status(call_payload),
                agent=call_payload.get("AgentEmail"),
            )

        # Return Voice Actions XML for incoming calls
        return build_voice_response(call_payload, settings)

    except Exception:
        request_log.status = "Failed"
        request_log.error = frappe.get_traceback()
        frappe.db.rollback()
        frappe.log_error(title="Error while handling AT call request")
        frappe.db.commit()
    finally:
        request_log.save(ignore_permissions=True)
        frappe.db.commit()


def build_voice_response(call_payload, settings):
    """Build Voice Actions XML response for incoming call"""
    from .voice_actions import VoiceActionsBuilder

    session_id = call_payload.get("sessionId")
    caller_number = call_payload.get("callerNumber")

    # Check if call queue is enabled
    if settings.enable_call_queue:
        from .queue_manager import QueueManager
        queue_manager = QueueManager()
        queue_response = queue_manager.add_to_queue(
            caller_number=caller_number,
            session_id=session_id
        )

        if queue_response.get("queued"):
            builder = VoiceActionsBuilder()
            builder.say(
                "Thank you for calling. You are being placed in the queue.")

            if settings.default_queue_music:
                media = frappe.get_doc(
                    "Call Queue Media", settings.default_queue_music)
                if media.public_url:
                    builder.play(media.public_url)

            return builder.build()

    # Find available agent
    agent = find_available_agent()

    if agent:
        builder = VoiceActionsBuilder()
        builder.say("Connecting you to an agent. Please wait.")
        builder.dial([agent.mobile_no], record=settings.enable_recording)
        return builder.build()
    else:
        builder = VoiceActionsBuilder()
        builder.say(
            "Sorry, all our agents are currently busy. Please try again later.")
        builder.reject()
        return builder.build()


def find_available_agent():
    """Find an available CRM Telephony Agent with Africa's Talking enabled"""
    try:
        agents = frappe.get_all(
            "CRM Telephony Agent",
            filters={"africastalking": 1},
            fields=["name", "user", "mobile_no", "africastalking_number"],
            limit=1
        )

        if agents:
            return frappe._dict(agents[0])

        return None

    except Exception as e:
        frappe.log_error(
            title="Agent Lookup Error",
            message=f"Error: {str(e)}"
        )
        return None


# Call Log Functions
def create_call_log(
    call_id,
    from_number,
    to_number,
    medium,
    agent,
    status="Ringing",
    call_type="Incoming",
):
    """Create a CRM Call Log record"""
    call_log = frappe.new_doc("CRM Call Log")
    call_log.id = call_id
    call_log.to = to_number
    call_log.medium = medium
    call_log.type = call_type
    call_log.status = status
    call_log.telephony_medium = "Africa's Talking"
    setattr(call_log, "from", from_number)

    if call_type == "Incoming":
        call_log.receiver = agent
    else:
        call_log.caller = agent

    # Link call log with lead/deal
    contact_number = from_number if call_type == "Incoming" else to_number
    link(contact_number, call_log)

    call_log.save(ignore_permissions=True)
    frappe.db.commit()
    return call_log


def link(contact_number, call_log):
    """Link call log with contact/lead/deal"""
    contact = get_contact_by_phone_number(contact_number)
    if contact.get("name"):
        doctype = "Contact"
        docname = contact.get("name")
        if contact.get("lead"):
            doctype = "CRM Lead"
            docname = contact.get("lead")
        elif contact.get("deal"):
            doctype = "CRM Deal"
            docname = contact.get("deal")
        call_log.link_with_reference_doc(doctype, docname)


def get_call_log(call_payload):
    """Get existing CRM Call Log by session ID"""
    call_log_id = call_payload.get("sessionId")
    if frappe.db.exists("CRM Call Log", call_log_id):
        return frappe.get_doc("CRM Call Log", call_log_id)
    return None


def get_call_log_status(call_payload, direction="incoming"):
    """Map Africa's Talking call status to CRM status"""
    status = call_payload.get("callSessionState", "")
    dial_status = call_payload.get("dialCallStatus", "")

    status_map = {
        "Completed": "Completed",
        "Answered": "Completed",
        "Busy": "Busy",
        "NoAnswer": "No Answer",
        "Rejected": "No Answer",
        "NotReachable": "No Answer",
        "Cancelled": "Canceled",
        "Failed": "Failed",
        "Ringing": "Ringing",
        "Queued": "Ringing",
    }

    mapped_status = status_map.get(
        dial_status) or status_map.get(status, "Ringing")
    return mapped_status


def update_call_log(call_payload, status="Ringing", call_log=None):
    """Update existing CRM Call Log with new status"""
    call_log = call_log or get_call_log(call_payload)
    status = get_call_log_status(call_payload)

    try:
        if call_log:
            call_log.status = status
            call_log.to = call_payload.get("destinationNumber") or call_log.to
            call_log.duration = call_payload.get("durationInSeconds", 0) or 0

            recording_url = call_payload.get("recordingUrl", "")
            if recording_url:
                call_log.recording_url = recording_url

            call_log.start_time = call_payload.get("callStartTime")
            call_log.end_time = call_payload.get("callEndTime")

            if call_payload.get("AgentEmail"):
                call_log.receiver = call_payload.get("AgentEmail")

            call_log.save(ignore_permissions=True)
            frappe.db.commit()
            return call_log
    except Exception:
        frappe.log_error(title="Error while updating AT call record")
        frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def incoming_call_webhook():
    """
    Webhook endpoint for incoming calls from Africa's Talking
    Returns Voice Actions XML
    """
    return handle_request(**frappe.form_dict)


@frappe.whitelist(allow_guest=True)
def call_events_webhook():
    """
    Webhook endpoint for call status events from Africa's Talking
    """
    return handle_request(**frappe.form_dict)
