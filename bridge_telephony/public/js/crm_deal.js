/**
 * CRM Deal Click-to-Call Integration
 * Adds telephony controls to CRM Deal forms
 */

frappe.ui.form.on('CRM Deal', {
    refresh: function(frm) {
        // Get contact phone number from linked contact
        get_contact_phone(frm, function(phone_number) {
            if (phone_number && !frm.is_new()) {
                // Add click-to-call button
                frm.add_custom_button(__('Make Call'), function() {
                    make_telephony_call(frm, phone_number, 'CRM Deal');
                }, __('Telephony'));
                
                // Add call icon in custom section
                add_call_section(frm, phone_number, 'CRM Deal');
            }
        });
        
        // Display call history if available
        if (!frm.is_new() && frm.doc.total_calls > 0) {
            display_call_stats(frm);
        }
        
        // Listen for realtime call updates
        setup_realtime_listeners(frm);
    }
});

function get_contact_phone(frm, callback) {
    // Try to get phone from deal's contact
    if (frm.doc.lead) {
        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'CRM Lead',
                filters: { name: frm.doc.lead },
                fieldname: 'mobile_no'
            },
            callback: function(r) {
                if (r.message && r.message.mobile_no) {
                    callback(r.message.mobile_no);
                } else {
                    callback(null);
                }
            }
        });
    } else {
        callback(null);
    }
}

function make_telephony_call(frm, phone_number, doctype) {
    // Check telephony permissions
    frappe.call({
        method: 'bridge_telephony.api.check_telephony_permission',
        callback: function(r) {
            if (!r.exc && r.message && r.message.has_permission) {
                initiate_call(frm, phone_number, doctype);
            } else {
                frappe.msgprint({
                    title: __('Permission Denied'),
                    indicator: 'red',
                    message: __('You do not have permission to make calls.')
                });
            }
        }
    });
}

function initiate_call(frm, phone_number, doctype) {
    frappe.call({
        method: 'bridge_telephony.api.make_call',
        args: {
            to_number: phone_number,
            from_number: null,
            reference_doctype: doctype,
            reference_name: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Initiating call...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('Call initiated successfully'),
                    indicator: 'green'
                }, 5);
                
                // Update call timestamp
                update_call_timestamp(frm);
                
                // Refresh to show updated call log
                setTimeout(() => frm.reload_doc(), 2000);
            } else {
                frappe.msgprint({
                    title: __('Call Failed'),
                    indicator: 'red',
                    message: r.message ? r.message.error : __('Failed to initiate call')
                });
            }
        },
        error: function(r) {
            frappe.msgprint({
                title: __('Error'),
                indicator: 'red',
                message: __('An error occurred while making the call')
            });
        }
    });
}

function add_call_section(frm, phone_number, doctype) {
    // Remove existing section if any
    $('.telephony-call-section').remove();
    
    // Create call section HTML
    const call_html = `
        <div class="telephony-call-section" style="margin: 15px 0; padding: 15px; background-color: #f8f9fa; border-radius: 4px; border-left: 3px solid #007bff;">
            <div class="row">
                <div class="col-sm-8">
                    <h6><i class="fa fa-phone"></i> Contact Phone</h6>
                    <p style="margin: 5px 0; font-size: 16px;">
                        <strong>${phone_number}</strong>
                        <button class="btn btn-xs btn-primary ml-2 call-button" style="margin-left: 10px;">
                            <i class="fa fa-phone"></i> Call Now
                        </button>
                    </p>
                </div>
            </div>
        </div>
    `;
    
    // Add section after deal details
    $(frm.fields_dict['deal_name'].$wrapper).after(call_html);
    
    // Attach click handler
    $('.call-button').on('click', function() {
        make_telephony_call(frm, phone_number, doctype);
    });
}

function display_call_stats(frm) {
    const stats_html = `
        <div class="telephony-stats" style="margin: 15px 0; padding: 10px; background-color: #e9ecef; border-radius: 4px;">
            <h6><i class="fa fa-bar-chart"></i> Call Statistics</h6>
            <div class="row">
                <div class="col-sm-6">
                    <strong>Total Calls:</strong> ${frm.doc.total_calls || 0}
                </div>
                <div class="col-sm-6">
                    <strong>Last Call:</strong> ${frm.doc.last_call_time ? frappe.datetime.str_to_user(frm.doc.last_call_time) : 'Never'}
                </div>
            </div>
        </div>
    `;
    
    // Add stats in the deal details section
    $('.telephony-call-section').after(stats_html);
}

function update_call_timestamp(frm) {
    if (!frm.is_new()) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'CRM Deal',
                name: frm.doc.name,
                fieldname: {
                    'last_call_time': frappe.datetime.now_datetime(),
                    'total_calls': (frm.doc.total_calls || 0) + 1
                }
            },
            callback: function() {
                frm.reload_doc();
            }
        });
    }
}

function setup_realtime_listeners(frm) {
    // Listen for call status updates
    frappe.realtime.on('call_status_update', function(data) {
        if (data && data.call_id) {
            frappe.show_alert({
                message: __('Call Status: {0}', [data.status]),
                indicator: data.status === 'Completed' ? 'green' : 'blue'
            }, 3);
            
            // Reload form to show updated information
            frm.reload_doc();
        }
    });
    
    // Listen for telephony settings changes
    frappe.realtime.on('bridge_telephony_settings_updated', function(data) {
        if (data && !data.enabled) {
            frappe.show_alert({
                message: __('Telephony has been disabled'),
                indicator: 'orange'
            }, 5);
        }
    });
}

// Add keyboard shortcut for quick call (Ctrl+Shift+C)
$(document).on('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.keyCode === 67) { // Ctrl+Shift+C
        const cur_frm = cur_dialog ? null : cur_frm;
        if (cur_frm && cur_frm.doctype === 'CRM Deal') {
            e.preventDefault();
            get_contact_phone(cur_frm, function(phone_number) {
                if (phone_number) {
                    make_telephony_call(cur_frm, phone_number, 'CRM Deal');
                } else {
                    frappe.msgprint(__('No contact phone number found'));
                }
            });
        }
    }
});
