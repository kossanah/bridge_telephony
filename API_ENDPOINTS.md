# Bridge Telephony API Endpoints

## Voice Actions
POST /api/method/bridge_telephony.api.voice_actions.voice_actions
Description: Webhook endpoint for Africa's Talking voice actions. Handles incoming call routing.

## Call Events
POST /api/method/bridge_telephony.api.voice_actions.call_events
Description: Webhook endpoint for Africa's Talking call events. Handles call status updates.

## Make Call
POST /api/method/bridge_telephony.api.voice_actions.make_call
Description: Initiate an outbound call via Africa's Talking.

## Get Call Details
POST /api/method/bridge_telephony.api.voice_actions.get_call_details
Description: Get details of a specific call.

## Retry Media Upload
POST /api/method/bridge_telephony.api.voice_actions.retry_media_upload
Description: Retry uploading a media file to Africa's Talking.

## Get Call History
POST /api/method/bridge_telephony.api.voice_actions.get_call_history
Description: Get call history for current user.

## Check Telephony Permission
POST /api/method/bridge_telephony.api.voice_actions.check_telephony_permission
Description: Check if user has telephony permissions.

## Test Connection
POST /api/method/bridge_telephony.api.voice_actions.test_connection
Description: Test Africa's Talking API connection.

## Test Africa's Talking Connection
POST /api/method/bridge_telephony.api.voice_actions.test_africastalking_connection
Description: Test Africa's Talking API connection with username.

## Is Call Integration Enabled
POST /api/method/bridge_telephony.api.voice_actions.is_call_integration_enabled
Description: Override CRM's is_call_integration_enabled to include Africa's Talking.

## Set Default Calling Medium
POST /api/method/bridge_telephony.api.voice_actions.set_default_calling_medium
Description: Set the user's default calling medium.
