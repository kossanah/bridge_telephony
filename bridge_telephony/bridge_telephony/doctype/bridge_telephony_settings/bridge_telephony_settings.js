// Copyright (c) 2025, Edubridge Consultants Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bridge Telephony Settings", {
    refresh(frm) {
        // Dynamic Test Connection button depending on selected provider
        const provider = frm.doc.provider || "FreePBX";
        
        frm.add_custom_button(__("Test Connection"), function() {
            if (frm.doc.provider === "FreePBX") {
                frm.trigger("test_freepbx_connection");
            } else {
                frm.trigger("test_at_connection");
            }
        });
    },

    test_freepbx_connection(frm) {
        if (!frm.doc.freepbx_host || !frm.doc.freepbx_ami_port || !frm.doc.freepbx_ami_username) {
            frappe.msgprint(__("Please enter FreePBX Host, Port, and AMI Username first."));
            return;
        }

        frappe.call({
            method: "bridge_telephony.api.freepbx.test_connection",
            freeze: true,
            freeze_message: __("Connecting to FreePBX Asterisk AMI..."),
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.msgprint({
                        title: __("Connection Successful"),
                        message: __("Successfully connected and authenticated with FreePBX AMI!<br><br><b>Banner:</b> ") + (r.message.banner || "Asterisk AMI"),
                        indicator: "green"
                    });
                } else {
                    frappe.msgprint({
                        title: __("Connection Failed"),
                        message: r.message?.error || __("Failed to connect to FreePBX AMI. Please verify host, port 5038, and credentials."),
                        indicator: "red"
                    });
                }
            }
        });
    },

    test_at_connection(frm) {
        if (!frm.doc.username || !frm.doc.api_key) {
            frappe.msgprint(__("Please enter your Africa's Talking Username and API Key first"));
            return;
        }

        frappe.call({
            method: "bridge_telephony.api.test_africastalking_connection",
            args: {
                username: frm.doc.username,
                api_key: frm.doc.api_key
            },
            freeze: true,
            freeze_message: __("Testing connection..."),
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.msgprint({
                        title: __("Connection Successful"),
                        message: __("Successfully connected to Africa's Talking. Account Balance: ") + r.message.balance,
                        indicator: "green"
                    });
                } else {
                    frappe.msgprint({
                        title: __("Connection Failed"),
                        message: r.message?.error || __("Failed to connect to Africa's Talking"),
                        indicator: "red"
                    });
                }
            }
        });
    }
});
