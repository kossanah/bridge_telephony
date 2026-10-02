/**
 * CRM Lead Click-to-Call Integration
 * Adds telephony controls to CRM Lead forms
 */

frappe.ui.form.on('CRM Lead', {
    refresh: function(frm) {
        // Add click-to-call button if mobile number exists
        if (frm.doc.mobile_no && !frm.is_new()) {
            frm.add_custom_button(__('Make Call'), function() {
                make_telephony_call(frm, frm.doc.mobile_no, 'CRM Lead');
            }, __('Telephony'));
            
            // Add call icon next to mobile number field
            add_call_icon(frm, 'mobile_no', frm.doc.mobile_no, 'CRM Lead');
        }
        
        // Display call history if available
        if (!frm.is_new() && frm.doc.telephony_status) {
            display_call_stats(frm);
        }
        
        // Listen for realtime call updates
        setup_realtime_listeners(frm);
    },
    
    mobile_no: function(frm) {
        // Update call icon when mobile number changes
        if (frm.doc.mobile_no) {
            add_call_icon(frm, 'mobile_no', frm.doc.mobile_no, 'CRM Lead');
        }
    }
});

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
                
                // Update telephony status
                update_telephony_status(frm, 'Calling');
                
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

function add_call_icon(frm, fieldname, phone_number, doctype) {
    // Remove existing icon if any
    frm.fields_dict[fieldname].$wrapper.find('.call-icon').remove();
    
    // Add call icon button
    const $call_icon = $('<span class="call-icon" style="margin-left: 10px; cursor: pointer;" title="Click to call">')
        .append('<i class="fa fa-phone text-primary"></i>')
        .on('click', function() {
            make_telephony_call(frm, phone_number, doctype);
        });
    
    frm.fields_dict[fieldname].$wrapper.find('.control-value').append($call_icon);
}

function display_call_stats(frm) {
    const stats_html = `
        <div class="telephony-stats" style="margin-top: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 4px;">
            <div class="row">
                <div class="col-sm-4">
                    <strong>Status:</strong> <span class="badge badge-${get_status_color(frm.doc.telephony_status)}">${frm.doc.telephony_status || 'N/A'}</span>
                </div>
                <div class="col-sm-4">
                    <strong>Total Calls:</strong> ${frm.doc.total_calls || 0}
                </div>
                <div class="col-sm-4">
                    <strong>Last Call:</strong> ${frm.doc.last_call_time ? frappe.datetime.str_to_user(frm.doc.last_call_time) : 'Never'}
                </div>
            </div>
        </div>
    `;
    
    // Add stats below mobile number field
    frm.fields_dict['mobile_no'].$wrapper.append(stats_html);
}

function get_status_color(status) {
    const color_map = {
        'Available': 'success',
        'Calling': 'warning',
        'In Call': 'info',
        'Busy': 'danger',
        'Offline': 'secondary'
    };
    return color_map[status] || 'secondary';
}

function update_telephony_status(frm, status) {
    if (!frm.is_new()) {
        frappe.call({
            method: 'frappe.client.set_value',
            args: {
                doctype: 'CRM Lead',
                name: frm.doc.name,
                fieldname: 'telephony_status',
                value: status
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
        if (cur_frm && cur_frm.doctype === 'CRM Lead' && cur_frm.doc.mobile_no) {
            e.preventDefault();
            make_telephony_call(cur_frm, cur_frm.doc.mobile_no, 'CRM Lead');
        }
    }
});
