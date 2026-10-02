// Bridge Telephony - Patch CRM to recognize Africa's Talking
// This script patches the call integration settings

(function() {
    // Wait for Frappe app to initialize
    const route = frappe && frappe.get_route ? frappe.get_route() : null;
    if (route && route[0] === 'app') {
        // We're in desk app - use frappe.boot event
        frappe.after_ajax(() => {
            patchCallIntegration();
        });
    } else {
        // For other pages, use DOMContentLoaded
        document.addEventListener('DOMContentLoaded', patchCallIntegration);
    }

    function patchCallIntegration() {
        // Patch the is_call_integration_enabled response handler
        const originalCall = frappe.call;

        frappe.call = function(opts) {
            if (opts.method === 'crm.integrations.api.is_call_integration_enabled') {
                // The API is already overridden via hooks, but let's ensure
                // the frontend processes africastalking_enabled
                const originalCallback = opts.callback;
                opts.callback = function(r) {
                    if (r && r.message) {
                        // Make africastalking count toward callEnabled
                        if (r.message.africastalking_enabled) {
                            console.log('Africa\'s Talking telephony is enabled');
                        }
                    }
                    if (originalCallback) {
                        originalCallback(r);
                    }
                };
            }
            return originalCall.call(this, opts);
        };
    }
})();

// Add makeCall function for Africa's Talking
window.makeAfricasTalkingCall = async function(toNumber) {
    try {
        const response = await frappe.call({
            method: 'bridge_telephony.api.make_call',
            args: {
                to_number: toNumber
            }
        });

        if (response.message && response.message.success) {
            frappe.show_alert({
                message: __('Call initiated successfully'),
                indicator: 'green'
            });
        } else {
            frappe.show_alert({
                message: response.message?.error || __('Failed to initiate call'),
                indicator: 'red'
            });
        }

        return response.message;
    } catch (error) {
        console.error('Error making call:', error);
        frappe.show_alert({
            message: __('Error making call: ') + error.message,
            indicator: 'red'
        });
    }
};
