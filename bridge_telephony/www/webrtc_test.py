import frappe

def get_context(context):
    context.no_cache = 1
    context.title = "FreePBX WebRTC Test Dialer"
    context.show_sidebar = False
