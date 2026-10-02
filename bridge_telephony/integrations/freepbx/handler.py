"""
FreePBX Telephony Integration Handler
Manages Asterisk AMI interactions and call lifecycle for Frappe CRM
"""

import re
import frappe
from frappe import _
from bridge_telephony.integrations.freepbx.ami_client import AMIClient, AMIException


def get_freepbx_config():
    """Retrieve FreePBX configuration from Bridge Telephony Settings"""
    settings = frappe.get_cached_doc("Bridge Telephony Settings")

    # If provider field is present, check provider; otherwise check freepbx_enabled
    provider = getattr(settings, "provider", "FreePBX")
    freepbx_enabled = getattr(settings, "freepbx_enabled", 0) or (settings.enabled and provider == "FreePBX")

    secret = None
    try:
        secret = settings.get_password("freepbx_ami_secret")
    except Exception:
        pass

    return {
        "enabled": bool(freepbx_enabled),
        "host": getattr(settings, "freepbx_host", None) or "172.187.235.228",
        "port": int(getattr(settings, "freepbx_ami_port", 5038) or 5038),
        "username": getattr(settings, "freepbx_ami_username", None) or "frappe_crm",
        "secret": secret,
        "context": getattr(settings, "freepbx_context", None) or "from-internal",
        "recording_url": getattr(settings, "freepbx_recording_url", None) or "https://voice.bridge.ng",
    }


def get_agent_extension(user=None):
    """
    Find the SIP extension mapped to the given Frappe user.
    Checks CRM Telephony Agent doctype.
    """
    if not user:
        user = frappe.session.user

    if not frappe.db.exists("CRM Telephony Agent", user):
        # Check if user has an agent record with a different name or email
        agent = frappe.db.get_value("CRM Telephony Agent", {"user": user}, ["name", "freepbx_extension"], as_dict=True)
        if agent and agent.get("freepbx_extension"):
            return str(agent.freepbx_extension).strip()
        return None

    ext = frappe.db.get_value("CRM Telephony Agent", user, "freepbx_extension")
    if ext:
        return str(ext).strip()

    # Fallback to africastalking_number if numeric extension
    alt_ext = frappe.db.get_value("CRM Telephony Agent", user, "africastalking_number")
    if alt_ext and str(alt_ext).isdigit():
        return str(alt_ext).strip()

    return None


def clean_phone_number(number):
    """
    Format phone number for Asterisk outbound dialing.
    Converts +234XXXXXXXXXX or +2340XXXXXXXXXX -> 0XXXXXXXXXX.
    """
    if not number:
        return ""

    cleaned = re.sub(r"[^\d+]", "", str(number))
    if cleaned.startswith("+2340"):
        cleaned = "0" + cleaned[5:]
    elif cleaned.startswith("+234"):
        cleaned = "0" + cleaned[4:]
    elif cleaned.startswith("2340") and len(cleaned) >= 12:
        cleaned = "0" + cleaned[4:]
    elif cleaned.startswith("234") and len(cleaned) >= 12:
        cleaned = "0" + cleaned[3:]

    # Remove extra leading zeros if any (e.g. 00803... -> 0803...)
    if cleaned.startswith("00") and len(cleaned) >= 12:
        cleaned = cleaned[1:]

    return cleaned


class FreePBXHandler:
    """Main FreePBX integration handler for making calls and verifying connectivity"""

    def __init__(self, config=None):
        self.config = config or get_freepbx_config()

    def get_client(self):
        """Instantiate an AMIClient from current configuration"""
        return AMIClient(
            host=self.config["host"],
            port=self.config["port"],
            username=self.config["username"],
            secret=self.config["secret"],
            timeout=10.0
        )

    def test_connection(self):
        """Test connection and authentication to FreePBX AMI"""
        if not self.config.get("enabled"):
            return {
                "success": False,
                "error": _("FreePBX integration is not enabled in Bridge Telephony Settings")
            }

        if not self.config.get("secret"):
            return {
                "success": False,
                "error": _("AMI Secret is not configured in Bridge Telephony Settings")
            }

        client = self.get_client()
        try:
            client.connect()
            login_resp = client.login()
            banner = client.banner

            # Ping to confirm session is responsive
            ping_ok = client.ping()
            client.logoff()

            return {
                "success": True,
                "message": _("Successfully connected to FreePBX Asterisk Manager Interface"),
                "banner": banner,
                "host": self.config["host"],
                "port": self.config["port"],
                "ping": ping_ok
            }
        except Exception as e:
            client.close()
            return {
                "success": False,
                "error": str(e),
                "host": self.config["host"],
                "port": self.config["port"]
            }

    def make_call(
        self,
        to_number,
        from_number=None,
        call_from="CRM",
        reference_doctype=None,
        reference_name=None
    ):
        """
        Initiate an outbound Click-to-Call:
        1. Identifies the CRM agent's SIP extension.
        2. Creates an initial CRM Call Log record.
        3. Sends AMI Originate command to FreePBX.
        4. FreePBX rings the agent's extension, and on pickup, dials the callee.
        """
        if not self.config.get("enabled"):
            frappe.throw(_("FreePBX telephony is not enabled. Please check Bridge Telephony Settings."))

        # 1. Resolve agent extension
        agent_ext = from_number or get_agent_extension()
        if not agent_ext:
            frappe.throw(
                _(
                    "No FreePBX extension configured for user '{0}'. "
                    "Please assign an extension in CRM Telephony Agent."
                ).format(frappe.session.user)
            )

        # 2. Format target destination
        dial_number = clean_phone_number(to_number)
        if not dial_number:
            frappe.throw(_("Invalid destination phone number."))

        # 3. Create CRM Call Log record
        call_log = None
        if frappe.db.exists("DocType", "CRM Call Log"):
            try:
                ref_dt = reference_doctype
                ref_dn = reference_name
                if not ref_dn:
                    from bridge_telephony.api.freepbx import find_matching_lead
                    matched_lead = find_matching_lead(dial_number)
                    if matched_lead:
                        ref_dt = "CRM Lead"
                        ref_dn = matched_lead

                call_log = frappe.get_doc({
                    "doctype": "CRM Call Log",
                    "from": agent_ext,
                    "to": dial_number,
                    "type": "Outgoing",
                    "status": "Initiated",
                    "telephony_medium": "FreePBX",
                    "caller": frappe.session.user,
                    "reference_doctype": ref_dt,
                    "reference_docname": ref_dn,
                    "start_time": frappe.utils.now_datetime(),
                    "owner": frappe.session.user,
                })
                if ref_dt and ref_dn:
                    call_log.link_with_reference_doc(ref_dt, ref_dn)
                call_log.insert(ignore_permissions=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Failed to create CRM Call Log", message=str(e))

        call_log_name = call_log.name if call_log else None

        # 4. Trigger AMI Originate
        client = self.get_client()
        try:
            client.connect()
            client.login()

            # Channel format: Local/<exten>@from-internal allows FreePBX dialplan
            # to handle device routing, follow-me, and ring strategies smoothly.
            channel = f"Local/{agent_ext}@{self.config['context']}"
            caller_id = f"CRM <{agent_ext}>"

            variables = {
                "CRM_CALL_LOG": call_log_name or "",
                "__CRM_CALL_LOG": call_log_name or "",
                "CHANNEL(hangup_handler_push)": "crm-hangup-handler,s,1",
                "CRM_USER": frappe.session.user,
                "CRM_REF_DT": reference_doctype or "",
                "CRM_REF_DN": reference_name or "",
            }

            resp = client.originate(
                channel=channel,
                exten=dial_number,
                context=self.config["context"],
                priority=1,
                caller_id=caller_id,
                timeout_ms=30000,
                async_call=True,
                variables=variables,
                account="FrappeCRM"
            )

            client.logoff()

            if resp.get("Response", "").lower() == "success":
                return {
                    "success": True,
                    "call_id": call_log_name,
                    "message": _("Calling extension {0}. Please pick up your phone to connect to {1}.").format(agent_ext, dial_number),
                    "agent_extension": agent_ext,
                    "destination": dial_number,
                    "call_log": call_log_name
                }
            else:
                err_msg = resp.get("Message", "Failed to originate call on Asterisk")
                if call_log:
                    call_log.status = "Failed"
                    call_log.save(ignore_permissions=True)
                    frappe.db.commit()
                return {
                    "success": False,
                    "error": err_msg,
                    "call_log": call_log_name
                }

        except Exception as e:
            client.close()
            frappe.log_error(title="FreePBX Originate Error", message=str(e))
            if call_log:
                call_log.status = "Failed"
                call_log.save(ignore_permissions=True)
                frappe.db.commit()
            return {
                "success": False,
                "error": str(e),
                "call_log": call_log_name
            }
