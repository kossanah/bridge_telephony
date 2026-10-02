// Copyright (c) 2025, Edubridge Consultants Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bridge Telephony Settings", {
    refresh(frm) {
        // Test Connection button handler
        frm.add_custom_button(__("Test Connection"), function() {
            frm.trigger("test_connection");
        });
    },

    test_connection(frm) {
        // Get username from form
        var username = frm.doc.username;

        if (!username) {
            frappe.msgprint(__("Please enter your Africa's Talking Username first"));
            return;
        }

        // Don't send api_key as parameter - it's a Password field and causes issues
        // The backend will retrieve it securely from settings
        frappe.call({
            method: "bridge_telephony.api.test_africastalking_connection",
            args: {
                username: username
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
                        message: r.message.error || __("Failed to connect to Africa's Talking"),
                        indicator: "red"
                    });
                }
            },
            error: function(r) {
                frappe.msgprint({
                    title: __("Connection Error"),
                    message: __("An error occurred while testing the connection"),
                    indicator: "red"
                });
            }
        });
    }
});
