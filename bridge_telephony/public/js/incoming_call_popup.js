/**
 * Global Real-Time Incoming Call Popup for Frappe CRM
 * Listens for 'crm_incoming_call' events and shows an interactive screen-pop modal.
 */

(function () {
    if (typeof frappe === "undefined") return;

    // Active popup instance tracker
    let activeCallDialog = null;
    let callTimer = null;

    function initCallListener() {
        if (!frappe.realtime) return;

        frappe.realtime.on("crm_incoming_call", function (data) {
            if (!data || !data.caller) return;
            showIncomingCallDialog(data);
        });

        frappe.realtime.on("call_status_update", function (data) {
            if (activeCallDialog && (data.status === "Completed" || data.status === "Failed" || data.status === "No Answer")) {
                if (activeCallDialog.$wrapper) {
                    activeCallDialog.hide();
                    activeCallDialog = null;
                }
            }
        });
    }

    function showIncomingCallDialog(data) {
        // Close previous popup if any
        if (activeCallDialog) {
            try {
                activeCallDialog.hide();
            } catch (e) {}
            activeCallDialog = null;
        }

        const callerNumber = data.caller || "Unknown Number";
        const extension = data.extension || "";
        const lead = data.lead || null;

        let leadDisplayHtml = "";
        if (lead) {
            leadDisplayHtml = `
                <div style="margin-top: 10px; padding: 10px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px;">
                    <div style="font-weight: 600; font-size: 15px; color: #166534;">
                        <i class="fa fa-user" style="margin-right: 6px;"></i> ${frappe.utils.escape_html(lead.title || lead.name)}
                    </div>
                    ${lead.company ? `<div style="font-size: 13px; color: #15803d; margin-top: 2px;"><i class="fa fa-building" style="margin-right: 6px;"></i> ${frappe.utils.escape_html(lead.company)}</div>` : ""}
                    <div style="margin-top: 6px;">
                        <span class="badge badge-success" style="font-size: 11px;">Matched CRM Lead</span>
                    </div>
                </div>
            `;
        } else {
            leadDisplayHtml = `
                <div style="margin-top: 10px; padding: 10px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;">
                    <div style="color: #64748b; font-size: 13px;">
                        <i class="fa fa-question-circle" style="margin-right: 6px;"></i> Unrecognized phone number
                    </div>
                </div>
            `;
        }

        const contentHtml = `
            <div style="text-align: center; padding: 10px 0;">
                <div style="display: inline-block; width: 64px; height: 64px; line-height: 64px; border-radius: 50%; background: #e0f2fe; color: #0284c7; font-size: 28px; animation: pulse 1.5s infinite;">
                    <i class="fa fa-phone"></i>
                </div>
                <h3 style="margin-top: 14px; margin-bottom: 4px; font-weight: 700; color: #0f172a;">
                    ${frappe.utils.escape_html(callerNumber)}
                </h3>
                <p style="color: #64748b; margin-bottom: 12px; font-size: 13px;">
                    Incoming Call on Extension <strong>${frappe.utils.escape_html(extension || "Agent")}</strong>
                </p>
                <div style="text-align: left;">
                    ${leadDisplayHtml}
                </div>
            </div>
            <style>
                @keyframes pulse {
                    0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(2, 132, 199, 0.4); }
                    70% { transform: scale(1.06); box-shadow: 0 0 0 10px rgba(2, 132, 199, 0); }
                    100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(2, 132, 199, 0); }
                }
            </style>
        `;

        const dialog = new frappe.ui.Dialog({
            title: __("Incoming Phone Call"),
            indicator: "blue",
            fields: [
                {
                    fieldtype: "HTML",
                    fieldname: "call_details_html",
                    options: contentHtml
                }
            ],
            primary_action_label: lead ? __("Open Lead") : __("Create Lead"),
            primary_action: function () {
                dialog.hide();
                if (lead) {
                    frappe.set_route("Form", "CRM Lead", lead.name);
                } else {
                    frappe.new_doc("CRM Lead", {
                        mobile_no: callerNumber
                    });
                }
            },
            secondary_action_label: __("Dismiss"),
            secondary_action: function () {
                dialog.hide();
            }
        });

        dialog.show();
        activeCallDialog = dialog;

        // Auto-dismiss dialog after 60 seconds
        if (callTimer) clearTimeout(callTimer);
        callTimer = setTimeout(function () {
            if (activeCallDialog === dialog) {
                dialog.hide();
                activeCallDialog = null;
            }
        }, 60000);
    }

    // Initialize when desk is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () {
            frappe.after_ajax ? frappe.after_ajax(initCallListener) : initCallListener();
        });
    } else {
        frappe.after_ajax ? frappe.after_ajax(initCallListener) : initCallListener();
    }
})();
