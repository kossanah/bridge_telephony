#!/usr/bin/env python3
"""
Quick setup script to create all necessary files for Bridge Telephony
Run this to quickly scaffold the entire app structure
"""

import os
import json

# Base directory
BASE_DIR = "/home/kanaekwe/bench/bridge/apps/bridge_telephony/bridge_telephony"

# Create Call Queue Media DocType
call_queue_media_dir = f"{BASE_DIR}/doctype/call_queue_media"
os.makedirs(call_queue_media_dir, exist_ok=True)

call_queue_media_json = {
    "actions": [],
    "creation": "2025-11-30 06:00:00",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": ["title", "media_type", "file_url", "public_url", "duration", "status"],
    "fields": [
        {"fieldname": "title", "fieldtype": "Data", "label": "Title", "reqd": 1},
        {"fieldname": "media_type", "fieldtype": "Select", "label": "Media Type", 
         "options": "Hold Music\nIVR Prompt\nGreeting", "reqd": 1},
        {"fieldname": "file_url", "fieldtype": "Attach", "label": "Audio File"},
        {"fieldname": "public_url", "fieldtype": "Data", "label": "Public URL", "read_only": 1},
        {"fieldname": "duration", "fieldtype": "Int", "label": "Duration (seconds)", "read_only": 1},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status",
         "options": "Pending\nUploaded\nFailed", "default": "Pending"}
    ],
    "modified": "2025-11-30 06:00:00",
    "module": "Bridge Telephony",
    "name": "Call Queue Media",
    "naming_rule": "By fieldname",
    "autoname": "field:title",
    "permissions": [
        {"create": 1, "delete": 1, "read": 1, "role": "System Manager", "write": 1}
    ],
    "sort_field": "modified",
    "sort_order": "DESC",
    "track_changes": 1
}

# Create Telephony Agent DocType
telephony_agent_dir = f"{BASE_DIR}/doctype/telephony_agent"
os.makedirs(telephony_agent_dir, exist_ok=True)

telephony_agent_json = {
    "actions": [],
    "creation": "2025-11-30 06:00:00",
    "doctype": "DocType",
    "engine": "InnoDB",
    "field_order": ["user", "mobile_no", "status", "exotel_number"],
    "fields": [
        {"fieldname": "user", "fieldtype": "Link", "label": "User", 
         "options": "User", "reqd": 1, "unique": 1},
        {"fieldname": "mobile_no", "fieldtype": "Data", "label": "Mobile Number", "reqd": 1},
        {"fieldname": "status", "fieldtype": "Select", "label": "Status",
         "options": "Available\nBusy\nOffline", "default": "Available"},
        {"fieldname": "exotel_number", "fieldtype": "Data", "label": "Assigned Phone Number"}
    ],
    "modified": "2025-11-30 06:00:00",
    "module": "Bridge Telephony",
    "name": "Telephony Agent",
    "naming_rule": "By fieldname",
    "autoname": "field:user",
    "permissions": [
        {"create": 1, "delete": 1, "read": 1, "role": "System Manager", "write": 1}
    ],
    "sort_field": "modified",
    "sort_order": "DESC"
}

# Write JSON files
with open(f"{call_queue_media_dir}/call_queue_media.json", "w") as f:
    json.dump(call_queue_media_json, f, indent=1)

with open(f"{telephony_agent_dir}/telephony_agent.json", "w") as f:
    json.dump(telephony_agent_json, f, indent=1)

# Create __init__.py files
open(f"{call_queue_media_dir}/__init__.py", "w").close()
open(f"{telephony_agent_dir}/__init__.py", "w").close()

# Create Python controllers
with open(f"{call_queue_media_dir}/call_queue_media.py", "w") as f:
    f.write("""# Copyright (c) 2025, Edubridge Consultants Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CallQueueMedia(Document):
\tpass
""")

with open(f"{telephony_agent_dir}/telephony_agent.py", "w") as f:
    f.write("""# Copyright (c) 2025, Edubridge Consultants Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TelephonyAgent(Document):
\tpass
""")

print("DocTypes created successfully!")
print("- Call Queue Media")
print("- Telephony Agent")
