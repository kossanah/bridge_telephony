"""
FreePBX API Endpoints for Frappe CRM
Provides whitelisted methods for Click-to-Call, Webhooks, Incoming Screen-Pop, and Audio Streaming
"""

import os
import re
import frappe
from frappe import _
from werkzeug.wrappers import Response
from werkzeug.wsgi import wrap_file
from bridge_telephony.integrations.freepbx.handler import FreePBXHandler, clean_phone_number, get_agent_extension


@frappe.whitelist()
def test_connection():
    """
    Test connection to FreePBX AMI using saved or default settings
    """
    handler = FreePBXHandler()
    return handler.test_connection()


@frappe.whitelist()
def make_call(to_number, from_number=None, reference_doctype=None, reference_name=None):
    """
    Whitelisted endpoint for Click-to-Call from CRM Lead / Deal / Contact
    """
    handler = FreePBXHandler()
    return handler.make_call(
        to_number=to_number,
        from_number=from_number,
        call_from="CRM",
        reference_doctype=reference_doctype,
        reference_name=reference_name
    )


@frappe.whitelist()
def get_my_telephony_profile():
    """
    Returns the WebRTC telephony profile for the currently logged in user:
    - Central FreePBX / WebRTC settings
    - Agent's extension and SIP password
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"enabled": False, "error": "Not authenticated"}

    settings = frappe.get_single("Bridge Telephony Settings")
    enabled = bool(settings.get("enabled", 1) and settings.get("freepbx_enabled", 1))
    enable_webrtc = bool(settings.get("enable_webrtc", 1))
    calling_mode = settings.get("calling_mode") or "WebRTC (In-Browser Phone)"
    wss_url = settings.get("webrtc_wss_url") or "wss://webrtc.bridge.ng:8089/ws"
    sip_domain = settings.get("webrtc_sip_domain") or "webrtc.bridge.ng"
    stun_server = settings.get("webrtc_stun_server") or "stun:stun.l.google.com:19302"

    agent = None
    extension = None
    secret = None

    if frappe.db.exists("CRM Telephony Agent", user):
        agent = frappe.get_doc("CRM Telephony Agent", user)
    else:
        agents = frappe.get_all("CRM Telephony Agent", filters={"user": user}, limit=1)
        if agents:
            agent = frappe.get_doc("CRM Telephony Agent", agents[0].name)

    if agent:
        extension = str(agent.get("freepbx_extension") or "").strip()
        try:
            from frappe.utils.password import get_decrypted_password
            secret = get_decrypted_password("CRM Telephony Agent", agent.name, "freepbx_secret", raise_exception=False)
        except Exception:
            secret = None

    # Safe defaults if secret is not yet explicitly set on the agent profile
    if extension == "2001" and not secret:
        secret = "BridgeVoice2026!WebRTC"
    elif extension == "1001" and not secret:
        secret = "*556#MTN"

    return {
        "enabled": enabled,
        "enable_webrtc": enable_webrtc,
        "calling_mode": calling_mode,
        "wss_url": wss_url,
        "sip_domain": sip_domain,
        "stun_server": stun_server,
        "user": user,
        "extension": extension,
        "secret": secret,
        "agent_name": agent.user_name if agent else user,
    }


@frappe.whitelist()
def create_webrtc_call_log(to_number, reference_doctype=None, reference_name=None):
    """
    Creates an initial CRM Call Log record when a WebRTC call is initiated in the browser.
    """
    user = frappe.session.user
    agent_ext = get_agent_extension(user) or "2001"
    dial_number = clean_phone_number(to_number)

    ref_dt = reference_doctype
    ref_dn = reference_name
    if not ref_dn and dial_number:
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
        "caller": user,
        "reference_doctype": ref_dt,
        "reference_docname": ref_dn,
        "start_time": frappe.utils.now_datetime(),
        "owner": user,
    })
    if ref_dt and ref_dn:
        try:
            call_log.link_with_reference_doc(ref_dt, ref_dn)
        except Exception:
            pass
    call_log.insert(ignore_permissions=True)
    frappe.db.commit()

    frappe.publish_realtime(
        "crm_call_log_updated",
        {
            "call_id": call_log.name,
            "status": "Initiated",
            "reference_doctype": ref_dt,
            "reference_docname": ref_dn,
        }
    )

    return {
        "success": True,
        "call_log": call_log.name,
        "agent_extension": agent_ext,
        "dial_number": dial_number,
        "reference_doctype": ref_dt,
        "reference_docname": ref_dn,
    }


@frappe.whitelist()
def update_webrtc_call_status(call_log, status="Completed", duration=0):
    """
    Updates CRM Call Log when WebRTC call finishes in browser.
    """
    if not call_log or not frappe.db.exists("CRM Call Log", call_log):
        return {"success": False, "message": "Call Log not found"}

    doc = frappe.get_doc("CRM Call Log", call_log)
    if status:
        doc.status = status
    try:
        doc.duration = int(float(duration or 0))
    except (ValueError, TypeError):
        pass
    doc.end_time = frappe.utils.now_datetime()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    payload = {
        "call_id": doc.name,
        "status": doc.status,
        "duration": doc.duration,
        "reference_doctype": getattr(doc, "reference_doctype", None),
        "reference_docname": getattr(doc, "reference_docname", None),
    }

    frappe.publish_realtime("crm_call_log_updated", payload, after_commit=True)

    return {"success": True, "call_log": doc.name, "status": doc.status}


@frappe.whitelist(allow_guest=True)
def webhook(**kwargs):
    """
    Webhook called by FreePBX post-call hangup macro (macro-hangupcall-custom).
    Updates CRM Call Log with final disposition, duration, and recording file.
    """
    data = frappe.form_dict if hasattr(frappe, "form_dict") and frappe.form_dict else kwargs
    if not data:
        data = kwargs

    uniqueid = data.get("uniqueid") or data.get("unique_id")
    src = clean_phone_number(data.get("src", ""))
    dst = clean_phone_number(data.get("dst", ""))
    try:
        duration = int(float(data.get("duration") or 0))
    except (ValueError, TypeError):
        duration = 0

    try:
        billsec = int(float(data.get("billsec") or 0))
    except (ValueError, TypeError):
        billsec = 0

    disposition = (data.get("disposition", "") or "").upper()
    recording = data.get("recording", "") or data.get("recordingfile", "")
    call_log_id = data.get("call_log") or data.get("CRM_CALL_LOG")

    call_log = None

    # 1. Attempt to find existing Call Log by ID
    if call_log_id and frappe.db.exists("CRM Call Log", call_log_id):
        call_log = frappe.get_doc("CRM Call Log", call_log_id)

    # 2. Or search recent Call Log with matching numbers created within last 20 minutes
    if not call_log and (src or dst):
        recent_logs = frappe.get_all(
            "CRM Call Log",
            filters=[
                ["creation", ">=", frappe.utils.add_to_date(frappe.utils.now(), minutes=-20)],
                ["telephony_medium", "=", "FreePBX"],
            ],
            fields=["name", "from", "to", "status"],
            order_by="creation desc",
            limit=10
        )
        # First preference: match log not yet finalized
        for log in recent_logs:
            if (log.get("to") in [dst, src] or log.get("from") in [src, dst]) and log.get("status") not in ["Completed", "Failed", "Busy", "No Answer"]:
                call_log = frappe.get_doc("CRM Call Log", log["name"])
                break
        # Second preference: any recent log with matching numbers
        if not call_log:
            for log in recent_logs:
                if log.get("to") in [dst, src] or log.get("from") in [src, dst]:
                    call_log = frappe.get_doc("CRM Call Log", log["name"])
                    break

    # 3. If still no Call Log found (e.g. Inbound call from customer), create one
    if not call_log and (src or dst):
        matched_lead = find_matching_lead(src or dst)
        is_incoming = len(src) > 5 and len(dst) <= 5
        call_type = "Incoming" if is_incoming else "Outgoing"
        target_ext = dst if is_incoming else src
        agent_user = None
        if target_ext:
            agents = frappe.db.get_all("CRM Telephony Agent", filters={"freepbx_extension": str(target_ext).strip()}, pluck="user")
            if agents:
                agent_user = agents[0]

        call_log = frappe.get_doc({
            "doctype": "CRM Call Log",
            "from": src,
            "to": dst,
            "type": call_type,
            "status": "Initiated",
            "telephony_medium": "FreePBX",
            "reference_doctype": "CRM Lead" if matched_lead else None,
            "reference_docname": matched_lead if matched_lead else None,
            "receiver": agent_user if is_incoming else None,
            "caller": agent_user if not is_incoming else None,
            "start_time": frappe.utils.now_datetime(),
        })
        if matched_lead:
            call_log.link_with_reference_doc("CRM Lead", matched_lead)
        call_log.insert(ignore_permissions=True)

    if not call_log:
        return {"success": False, "message": "No matching CRM Call Log found"}

    # Ensure reference_docname and links are populated if missing
    if not getattr(call_log, "reference_docname", None):
        matched_lead = find_matching_lead(call_log.get("from") or call_log.get("to"))
        if matched_lead:
            call_log.reference_doctype = "CRM Lead"
            call_log.reference_docname = matched_lead
            call_log.link_with_reference_doc("CRM Lead", matched_lead)

    # 4. Map Asterisk disposition to CRM status
    if disposition == "ANSWERED":
        call_log.status = "Completed"
    elif disposition == "BUSY":
        call_log.status = "Busy"
    elif disposition == "NO ANSWER":
        call_log.status = "No Answer"
    elif disposition in ["FAILED", "CONGESTION"]:
        call_log.status = "Failed"
    else:
        call_log.status = "Completed" if billsec > 0 else "Failed"

    # 5. Set duration and recording URL
    call_log.duration = billsec if billsec > 0 else duration
    call_log.end_time = frappe.utils.now_datetime()

    if recording and recording != "none":
        rec_filename = os.path.basename(recording)
        proxy_url = f"/api/method/bridge_telephony.api.freepbx.get_recording_audio?call_log={call_log.name}&file={rec_filename}"
        call_log.recording_url = proxy_url
    elif not getattr(call_log, "recording_url", None):
        # Auto-discover if not provided in webhook parameters
        rec_found = _find_recording_for_call_log(call_log, uniqueid=uniqueid)
        if rec_found:
            call_log.recording_url = f"/api/method/bridge_telephony.api.freepbx.get_recording_audio?call_log={call_log.name}&file={rec_found}"

    call_log.save(ignore_permissions=True)
    frappe.db.commit()

    # 6. Publish realtime update to refresh desk view and CRM SPA
    payload = {
        "call_id": call_log.name,
        "status": call_log.status,
        "duration": call_log.duration,
        "recording_url": getattr(call_log, "recording_url", None),
        "reference_doctype": getattr(call_log, "reference_doctype", None),
        "reference_docname": getattr(call_log, "reference_docname", None),
    }
    frappe.publish_realtime("call_status_update", payload)
    frappe.publish_realtime("crm_call_log_updated", payload)

    return {"success": True, "call_log": call_log.name, "status": call_log.status}


@frappe.whitelist(allow_guest=True)
def incoming_call(caller=None, destination=None, did=None, **kwargs):
    """
    Webhook triggered by FreePBX dialplan when an incoming call arrives.
    Publishes a real-time screen-pop notification to CRM agents.
    """
    caller_num = clean_phone_number(caller or frappe.form_dict.get("caller", ""))
    target_ext = destination or frappe.form_dict.get("destination", "")

    if not caller_num:
        return {"success": False, "error": "Caller number is required"}

    # Match caller with Lead or Contact
    lead_info = None
    digits = re.sub(r"\D", "", str(caller_num))
    search_suffix = digits[-10:] if len(digits) >= 10 else digits

    matched_lead = frappe.db.get_value(
        "CRM Lead",
        {"mobile_no": ["like", f"%{search_suffix}%"]},
        ["name", "lead_name", "organization", "mobile_no"],
        as_dict=True
    )
    if not matched_lead:
        # Check phone field
        matched_lead = frappe.db.get_value(
            "CRM Lead",
            {"phone": ["like", f"%{search_suffix}%"]},
            ["name", "lead_name", "organization", "phone"],
            as_dict=True
        )

    if matched_lead:
        lead_info = {
            "name": matched_lead.name,
            "title": matched_lead.lead_name or matched_lead.name,
            "company": matched_lead.get("organization", "") or "",
            "doctype": "CRM Lead"
        }

    # If no Lead matched, check Contact
    if not lead_info:
        try:
            matched_contact = frappe.db.get_value(
                "Contact",
                {"mobile_no": ["like", f"%{caller_num[-10:]}%"]},
                ["name", "first_name", "last_name", "company_name"],
                as_dict=True
            )
            if not matched_contact:
                matched_contact = frappe.db.get_value(
                    "Contact",
                    {"phone": ["like", f"%{caller_num[-10:]}%"]},
                    ["name", "first_name", "last_name", "company_name"],
                    as_dict=True
                )
            if matched_contact:
                full_name = f"{matched_contact.get('first_name') or ''} {matched_contact.get('last_name') or ''}".strip()
                lead_info = {
                    "name": matched_contact.name,
                    "title": full_name or matched_contact.name,
                    "company": matched_contact.get("company_name", "") or "",
                    "doctype": "Contact"
                }
        except Exception:
            pass

    # Find agents to notify based on destination extension
    target_users = []
    if target_ext:
        try:
            target_users = frappe.db.get_all(
                "CRM Telephony Agent",
                filters={"freepbx_extension": str(target_ext).strip()},
                pluck="user"
            )
        except Exception:
            pass

    # Create initial CRM Call Log for the incoming call
    call_log = None
    if frappe.db.exists("DocType", "CRM Call Log"):
        try:
            receiver_user = target_users[0] if target_users else None
            call_log = frappe.get_doc({
                "doctype": "CRM Call Log",
                "from": caller_num,
                "to": str(target_ext or "1001"),
                "type": "Incoming",
                "status": "Ringing",
                "telephony_medium": "FreePBX",
                "reference_doctype": lead_info.get("doctype") if lead_info else None,
                "reference_docname": lead_info.get("name") if lead_info else None,
                "receiver": receiver_user,
                "start_time": frappe.utils.now_datetime(),
            })
            if lead_info and lead_info.get("doctype") and lead_info.get("name"):
                call_log.link_with_reference_doc(lead_info.get("doctype"), lead_info.get("name"))
            call_log.insert(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(title="Failed to create incoming CRM Call Log", message=str(e))

    notification_payload = {
        "caller": caller_num,
        "extension": target_ext,
        "lead": lead_info,
        "call_id": call_log.name if call_log else None,
        "call_log": call_log.name if call_log else None,
        "timestamp": frappe.utils.now(),
    }

    # Notify specific agent rooms if mapped
    for u in set(target_users):
        frappe.publish_realtime("crm_incoming_call", notification_payload, user=u)
        frappe.publish_realtime("incoming_call", notification_payload, user=u)

    # Also broadcast globally to ensure all active CRM tabs receive the screen-pop
    frappe.publish_realtime("crm_incoming_call", notification_payload, room="all")
    frappe.publish_realtime("incoming_call", notification_payload, room="all")

    return {
        "success": True,
        "notified": True,
        "lead": lead_info,
        "call_id": call_log.name if call_log else None,
        "call_log": call_log.name if call_log else None,
    }


@frappe.whitelist()
def check_active_call():
    """
    Check if there is an active ringing or in-progress incoming call for the current agent/session.
    Acts as a fail-safe poll so the incoming call pop appears reliably even if websocket dropped.
    """
    cutoff = frappe.utils.add_to_date(frappe.utils.now(), seconds=-45)
    
    agent_ext = None
    try:
        agent_ext = frappe.db.get_value("CRM Telephony Agent", {"user": frappe.session.user}, "freepbx_extension")
    except Exception:
        pass

    filters = [
        ["creation", ">=", cutoff],
        ["telephony_medium", "=", "FreePBX"],
        ["status", "in", ["Ringing", "Initiated"]],
        ["type", "=", "Incoming"],
    ]

    logs = frappe.get_all(
        "CRM Call Log",
        filters=filters,
        fields=["name", "from", "to", "type", "status", "reference_doctype", "reference_docname", "creation"],
        order_by="creation desc",
        limit=1,
    )
    if not logs:
        return None

    log = logs[0]
    lead_info = None
    if log.get("reference_doctype") and log.get("reference_docname"):
        lead_info = {
            "name": log["reference_docname"],
            "title": log["reference_docname"],
            "doctype": log["reference_doctype"],
        }
    return {
        "call_id": log["name"],
        "caller": log["from"],
        "destination": log["to"],
        "status": log["status"],
        "call_type": log["type"],
        "lead": lead_info,
    }


@frappe.whitelist()
def get_or_create_call_log(caller=None, destination=None, call_type="Incoming", reference_doctype=None, reference_name=None):
    """
    Get existing active call log for a caller/destination or create a new one.
    Guarantees note/task saving can always link to a valid CRM Call Log record.
    """
    caller_clean = clean_phone_number(caller or "")
    dest_clean = clean_phone_number(destination or "")

    # 1. Search for recent Call Log created within last 20 minutes
    if caller_clean or dest_clean:
        recent_logs = frappe.get_all(
            "CRM Call Log",
            filters=[
                ["creation", ">=", frappe.utils.add_to_date(frappe.utils.now(), minutes=-20)],
                ["telephony_medium", "=", "FreePBX"],
            ],
            fields=["name", "from", "to", "status"],
            order_by="creation desc",
            limit=5
        )
        for log in recent_logs:
            if log.get("to") in [caller_clean, dest_clean] or log.get("from") in [caller_clean, dest_clean]:
                return {"success": True, "call_log": log["name"], "call_id": log["name"]}

    # 2. Match Lead/Contact if not provided
    if not reference_name and caller_clean:
        matched_lead = find_matching_lead(caller_clean)
        if matched_lead:
            reference_doctype = "CRM Lead"
            reference_name = matched_lead

    # 3. Create a new CRM Call Log
    call_log = frappe.get_doc({
        "doctype": "CRM Call Log",
        "from": caller_clean or "Unknown",
        "to": dest_clean or "1001",
        "type": call_type or "Incoming",
        "status": "In Progress",
        "telephony_medium": "FreePBX",
        "reference_doctype": reference_doctype,
        "reference_docname": reference_name,
        "caller": frappe.session.user if call_type == "Outgoing" else None,
        "receiver": frappe.session.user if call_type == "Incoming" else None,
        "start_time": frappe.utils.now_datetime(),
        "owner": frappe.session.user,
    })
    if reference_doctype and reference_name:
        call_log.link_with_reference_doc(reference_doctype, reference_name)
    call_log.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "call_log": call_log.name, "call_id": call_log.name}


@frappe.whitelist(allow_guest=True)
def get_recording_audio(call_log=None, file=None):
    """
    Audio streaming endpoint with HTTP Range header support.
    Fetches the recording from FreePBX if not already locally cached,
    and streams to the browser HTML5 audio player.
    """
    rec_filename = file
    log_doc = None
    if call_log and frappe.db.exists("CRM Call Log", call_log):
        log_doc = frappe.get_doc("CRM Call Log", call_log)
        rec_url = getattr(log_doc, "recording_url", "") or ""
        if rec_url:
            match = re.search(r"file=([^&]+)", rec_url)
            if match:
                rec_filename = match.group(1)
            else:
                rec_filename = os.path.basename(rec_url)

    # Auto-discovery fallback if recording_url was not populated
    if not rec_filename and log_doc:
        rec_filename = _find_recording_for_call_log(log_doc)
        if rec_filename:
            log_doc.recording_url = f"/api/method/bridge_telephony.api.freepbx.get_recording_audio?call_log={log_doc.name}&file={rec_filename}"
            log_doc.save(ignore_permissions=True)
            frappe.db.commit()

    if not rec_filename:
        frappe.throw(_("No recording file specified or found for this call"), frappe.DoesNotExistError)

    # Sanitize filename
    rec_filename = os.path.basename(rec_filename)

    # Local cache directory
    cache_dir = os.path.join(frappe.get_site_path(), "private", "files", "recordings")
    os.makedirs(cache_dir, exist_ok=True)
    local_file_path = os.path.join(cache_dir, rec_filename)

    # If file not in local cache, fetch from FreePBX
    if not os.path.exists(local_file_path):
        fetch_success = _fetch_recording_from_freepbx(rec_filename, local_file_path)
        if not fetch_success or not os.path.exists(local_file_path):
            frappe.throw(_("Recording file could not be retrieved from FreePBX"), frappe.DoesNotExistError)

    # Stream the file with Range header support
    return _stream_audio_file(local_file_path)


def _find_recording_for_call_log(log_doc, uniqueid=None):
    """
    Search FreePBX monitor directory for recordings matching uniqueid or call log numbers
    """
    import subprocess
    ssh_key = os.path.expanduser("~/.ssh/dokploy_ed25519")
    remote_host = "bridge@172.187.235.228"

    # 1. Search by uniqueid if provided
    if uniqueid:
        find_cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
            "-i", ssh_key, remote_host,
            f"sudo find /var/spool/asterisk/monitor/ -name '*{uniqueid}*' -type f 2>/dev/null | head -n 1"
        ]
        try:
            res = subprocess.check_output(find_cmd, timeout=8).decode().strip()
            if res:
                return os.path.basename(res)
        except Exception:
            pass

    # 2. Search by phone numbers
    targets = [t for t in [log_doc.get("to"), log_doc.get("from")] if t and len(str(t)) >= 4]
    for target in targets:
        find_cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
            "-i", ssh_key, remote_host,
            f"sudo find /var/spool/asterisk/monitor/ -name '*{target}*' -type f 2>/dev/null | tail -n 1"
        ]
        try:
            res = subprocess.check_output(find_cmd, timeout=8).decode().strip()
            if res:
                return os.path.basename(res)
        except Exception:
            pass
    return None


def _fetch_recording_from_freepbx(filename, dest_path):
    """
    Fetch recording from FreePBX /var/spool/asterisk/monitor/
    Searches standard FreePBX YYYY/MM/DD subdirectories.
    """
    import subprocess

    ssh_key = os.path.expanduser("~/.ssh/dokploy_ed25519")
    remote_host = "bridge@172.187.235.228"

    find_cmd = [
        "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
        "-i", ssh_key, remote_host,
        f"sudo find /var/spool/asterisk/monitor/ -name '{filename}*' -type f | head -n 1"
    ]

    try:
        remote_path = subprocess.check_output(find_cmd, timeout=10).decode().strip()
        if not remote_path:
            return False

        cat_cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
            "-i", ssh_key, remote_host,
            f"sudo cat '{remote_path}'"
        ]
        with open(dest_path, "wb") as f_out:
            subprocess.run(cat_cmd, stdout=f_out, check=True, timeout=30)

        return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0

    except Exception as e:
        frappe.log_error(title="Failed to fetch FreePBX recording", message=str(e))
        return False


def _stream_audio_file(filepath):
    """
    Stream audio file supporting HTTP Range requests for in-browser playback
    """
    file_size = os.path.getsize(filepath)
    content_type = "audio/wav"
    if filepath.endswith(".mp3"):
        content_type = "audio/mpeg"

    req = getattr(frappe.local, "request", None)
    range_header = None
    if req and hasattr(req, "headers"):
        range_header = req.headers.get("Range")

    if not range_header:
        f = open(filepath, "rb")

        def _stream():
            try:
                while chunk := f.read(64 * 1024):
                    yield chunk
            finally:
                f.close()

        response = Response(
            _stream(),
            status=200,
            content_type=content_type,
            direct_passthrough=True
        )
        response.headers["Content-Length"] = str(file_size)
        response.headers["Accept-Ranges"] = "bytes"
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response

    # Parse byte range header, e.g. 'bytes=0-1024'
    range_match = re.match(r"bytes=(\d+)-(\d+)?", range_header)
    if not range_match:
        f = open(filepath, "rb")

        def _stream():
            try:
                while chunk := f.read(64 * 1024):
                    yield chunk
            finally:
                f.close()

        resp = Response(_stream(), status=200, content_type=content_type)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp

    byte1 = int(range_match.group(1))
    byte2 = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    length = byte2 - byte1 + 1

    f = open(filepath, "rb")
    f.seek(byte1)

    def stream_chunk():
        try:
            remaining = length
            while remaining > 0:
                chunk_size = min(remaining, 64 * 1024)
                data = f.read(chunk_size)
                if not data:
                    break
                remaining -= len(data)
                yield data
        finally:
            f.close()

    response = Response(
        stream_chunk(),
        status=206,
        content_type=content_type,
        direct_passthrough=True
    )
    response.headers["Content-Range"] = f"bytes {byte1}-{byte2}/{file_size}"
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Content-Length"] = str(length)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def find_matching_lead(phone_number):
    """Helper to match a phone number against CRM Lead records"""
    if not phone_number:
        return None
    cleaned = clean_phone_number(phone_number)
    if len(cleaned) < 5:
        return None

    last_digits = cleaned[-8:]
    lead = frappe.db.sql(
        """
        SELECT name FROM `tabCRM Lead`
        WHERE mobile_no LIKE %s OR phone LIKE %s
        ORDER BY modified DESC LIMIT 1
        """,
        (f"%{last_digits}", f"%{last_digits}"),
        as_dict=True
    )
    return lead[0].name if lead else None
