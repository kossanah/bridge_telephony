# Bridge Telephony Configuration Guide

## Overview
This guide will help you configure Bridge Telephony with your Africa's Talking account to enable click-to-call functionality in Frappe CRM.

## Prerequisites

1. **Africa's Talking Account**
   - Sign up at https://africastalking.com
   - Purchase a phone number from your dashboard
   - Get your API credentials (Username and API Key)

2. **Frappe CRM Installed**
   - Bridge Telephony is already installed on your site: `local.bridge.ng`
   - The migration has been completed successfully

## Step 1: Configure Bridge Telephony Settings

1. **Log into your Frappe site:**
   ```
   http://local.bridge.ng
   ```

2. **Navigate to Bridge Telephony Settings:**
   - Search for "Bridge Telephony Settings" in the awesome bar (Ctrl+K or Cmd+K)
   - Or go to: `http://local.bridge.ng/app/bridge-telephony-settings`

3. **Fill in the required fields:**

   ### API Credentials Section
   - **Enabled:** Check this box to enable telephony
   - **Africa's Talking Username:** Your AT username (usually 'sandbox' for testing or your account username)
   - **API Key:** Your AT API Key (found in your AT dashboard)
   - **Your AT Phone Number:** Your registered AT phone number (e.g., +234XXXXXXXXXX)
   - **Webhook Verification Token:** (Optional) A secret token to verify webhook requests

   ### Features Section
   - **Enable Call Recording:** Check to record calls (recommended)
   - **Enable WebRTC:** Check if you want browser-based calling
   - **Enable Call Queue:** Check to enable call queuing
   - **Default Queue Hold Music:** Select or upload hold music (optional)
   - **Auto Create Call Logs:** Check to automatically log all calls

   ### SIP Configuration (Optional)
   - Only fill this if you're using SIP integration
   - **Enable SIP Integration:** Check if using SIP
   - **SIP Domain:** Your SIP domain
   - **SIP Username:** Your SIP username
   - **SIP Password:** Your SIP password

4. **Save the settings**

## Step 2: Test the Connection

1. After saving settings, scroll to the bottom
2. Click the **"Test Connection"** button
3. You should see a success message if credentials are correct

## Step 3: Configure Africa's Talking Webhooks

You need to configure webhooks in your Africa's Talking dashboard to handle incoming calls and call events.

1. **Log into Africa's Talking Dashboard:**
   - Go to https://account.africastalking.com

2. **Navigate to Voice Settings:**
   - Click on "Voice" in the left sidebar
   - Click on "Settings"

3. **Configure Callback URLs:**

   ### Voice Callback URL (for incoming calls):
   ```
   https://local.bridge.ng/api/method/bridge_telephony.bridge_telephony.api.voice_actions
   ```
   
   Or with verification token (if you set one):
   ```
   https://local.bridge.ng/api/method/bridge_telephony.bridge_telephony.api.voice_actions?verify_token=YOUR_TOKEN
   ```

   ### Call Status Callback URL (for call events):
   ```
   https://local.bridge.ng/api/method/bridge_telephony.bridge_telephony.api.call_events
   ```
   
   Or with verification token:
   ```
   https://local.bridge.ng/api/method/bridge_telephony.bridge_telephony.api.call_events?verify_token=YOUR_TOKEN
   ```

   **Important:** Replace `local.bridge.ng` with your actual domain if you're in production.

4. **Save the webhook configurations**

## Step 4: Create Telephony Agents

To allow users to make and receive calls, you need to create Telephony Agent records.

1. **Navigate to Telephony Agent:**
   - Search for "Telephony Agent" in the awesome bar
   - Or go to: `http://local.bridge.ng/app/telephony-agent`

2. **Create a new Telephony Agent:**
   - Click "New"
   - **User:** Select a Frappe user
   - **Mobile Number:** Enter the agent's mobile number (E.164 format: +234XXXXXXXXXX)
   - **Status:** Set to "Available"
   - **Exotel Number:** (Optional) Leave blank for now
   - Save

3. **Repeat for all users who need telephony access**

## Step 5: Test Click-to-Call in CRM

### Testing with CRM Lead:

1. **Open or create a CRM Lead:**
   - Navigate to CRM > Lead
   - Open an existing lead or create a new one
   - Ensure the lead has a **Mobile Number** filled

2. **Make a call:**
   - You'll see a phone icon next to the mobile number field
   - You can also click the "Telephony" button dropdown and select "Make Call"
   - Or use keyboard shortcut: `Ctrl+Shift+C`

3. **Monitor the call:**
   - After initiating, you'll see a success notification
   - The call status will update in real-time
   - Call logs will be created automatically

### Testing with CRM Deal:

1. **Open a CRM Deal linked to a Lead:**
   - Navigate to CRM > Deal
   - Open a deal that's linked to a lead with a phone number

2. **Make a call:**
   - Click the "Call Now" button in the telephony section
   - Or use the "Telephony" dropdown menu
   - Or use keyboard shortcut: `Ctrl+Shift+C`

## Step 6: Upload Hold Music (Optional)

If you want custom hold music for queued calls:

1. **Navigate to Call Queue Media:**
   - Search for "Call Queue Media" in the awesome bar

2. **Create new media:**
   - Click "New"
   - **Title:** Give it a descriptive name
   - **Media Type:** Select "Hold Music"
   - **File URL:** Upload your audio file (MP3, WAV supported)
   - **Status:** Set to "Active"
   - Save

3. **Set as default:**
   - Go back to Bridge Telephony Settings
   - In the "Default Queue Hold Music" field, select your uploaded media
   - Save

## Troubleshooting

### Common Issues:

1. **"Bridge Telephony is not enabled" error:**
   - Make sure you checked the "Enabled" checkbox in settings
   - Restart bench: `cd /home/kanaekwe/bench/bridge && bench restart`

2. **"No phone number configured" error:**
   - Ensure you've entered your AT phone number in settings
   - Verify the number is in E.164 format (+234XXXXXXXXXX)

3. **"Permission Denied" when making calls:**
   - Create a Telephony Agent record for the user
   - Or ensure the user has "System Manager" role

4. **Calls not connecting:**
   - Verify your AT API credentials are correct
   - Check that you have sufficient balance in your AT account
   - Ensure webhooks are configured correctly in AT dashboard

5. **Click-to-call buttons not showing:**
   - Clear browser cache and restart bench
   - Run: `bench --site local.bridge.ng clear-cache`
   - Then: `bench restart`

6. **Import errors in console:**
   - These are normal Pylance warnings and will work at runtime
   - If you see actual errors when making calls, check the Error Log in Frappe

### Checking Error Logs:

1. Navigate to: Settings > Error Log
2. Filter by "Title" containing "Telephony" or "Africa's Talking"
3. Review error messages for specific issues

### Testing API Connectivity:

You can test the API directly in bench console:

```bash
cd /home/kanaekwe/bench/bridge
bench --site local.bridge.ng console
```

Then in Python console:
```python
# Test settings
settings = frappe.get_doc("Bridge Telephony Settings", "Bridge Telephony Settings")
print(settings.as_dict())

# Test API connection
from bridge_telephony.bridge_telephony.integrations.africastalking.handler import AfricasTalkingHandler
handler = AfricasTalkingHandler()
result = handler.make_call("+234XXXXXXXXXX")  # Replace with actual number
print(result)
```

## Next Steps

1. **Test thoroughly in sandbox mode first**
2. **Purchase production credits from Africa's Talking**
3. **Update webhook URLs if moving to production**
4. **Train your team on using the click-to-call features**
5. **Monitor call logs and recordings regularly**

## Support

If you encounter issues:
1. Check Error Logs in Frappe
2. Review Africa's Talking API documentation: https://developers.africastalking.com/docs/voice/overview
3. Check the implementation guide: `BRIDGE_TELEPHONY_AFRICASTALKING_IMPLEMENTATION_GUIDE.md`

## Features Summary

✅ **Implemented:**
- Click-to-call from CRM Lead
- Click-to-call from CRM Deal
- Call logging and tracking
- Real-time call status updates
- Call recording support
- Call queue management
- Hold music support
- WebRTC support (configurable)
- SIP integration (configurable)
- Webhook handlers for incoming calls
- Telephony agent management
- Permission controls

✅ **Custom Fields Added:**
- CRM Lead: `telephony_status`, `last_call_time`, `total_calls`
- CRM Deal: `last_call_time`, `total_calls`

✅ **Keyboard Shortcuts:**
- `Ctrl+Shift+C`: Quick call from Lead or Deal form

## Security Notes

- **Webhook Verification:** Always use a verification token in production
- **API Keys:** Never expose your AT API key in client-side code
- **Permissions:** Only grant telephony access to trusted users
- **Call Recordings:** Ensure compliance with local recording laws
