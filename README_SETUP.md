# Bridge Telephony - Africa's Talking Integration for Frappe CRM

## Overview

Bridge Telephony adds Africa's Talking as a third telephony provider option alongside Twilio and Exotel in Frappe CRM. It follows the same integration patterns used by the existing CRM telephony providers.

## ✅ Architecture

### Integration Approach

- **Custom Fields**: Extends `CRM Telephony Agent` with Africa's Talking fields
- **Property Setter**: Adds "Africa's Talking" to the `default_medium` dropdown
- **API Override**: Overrides `is_call_integration_enabled` to include Africa's Talking
- **Frontend Override**: Extends CRM's TelephonySettings.vue with Africa's Talking section

### Key Files

```
bridge_telephony/
├── bridge_telephony/
│   ├── fixtures/
│   │   ├── custom_field.json      # Africa's Talking fields for CRM Telephony Agent
│   │   └── property_setter.json   # Adds Africa's Talking to default_medium options
│   │
│   ├── integrations/africastalking/
│   │   ├── handler.py             # Webhook handler (follows CRM Exotel pattern)
│   │   ├── voice_actions.py       # Voice XML builder
│   │   ├── media_manager.py       # Media file management
│   │   └── queue_manager.py       # Call queue management
│   │
│   ├── doctype/
│   │   └── bridge_telephony_settings/  # Settings DocType
│   │
│   ├── public/js/
│   │   ├── crm_lead.js            # Click-to-call for Leads
│   │   ├── crm_deal.js            # Click-to-call for Deals
│   │   └── telephony_patch.js     # JavaScript patches
│   │
│   ├── api.py                     # Whitelisted API methods
│   ├── hooks.py                   # App configuration
│   └── install.py                 # Installation scripts
│
└── frontend/
    ├── src_override/
    │   ├── composables/
    │   │   └── settings.js        # Adds africastalkingEnabled to callEnabled
    │   └── components/Settings/
    │       └── TelephonySettings.vue  # Africa's Talking settings UI
    ├── custom-build.cjs           # Build script
    └── package.json               # Frontend dependencies
```

## 📦 Installation

### 1. Install the App

```bash
cd /path/to/bench
bench --site your-site.local install-app bridge_telephony
bench --site your-site.local migrate
```

### 2. Build Frontend (Required for TelephonySettings UI customization)

The frontend build process copies CRM's frontend, applies our overrides (Africa's Talking option), and builds the final bundle.

**Automated Deployment (Recommended):**
We have provided a script to automate the build and deployment process.

```bash
cd apps/bridge_telephony
./deploy_frontend.sh
```

**Manual Deployment:**

```bash
cd apps/bridge_telephony/frontend

# Step 1: Run custom build script to merge CRM source with our overrides
node custom-build.cjs

# Step 2: Install dependencies (if not already done)
yarn install

# Step 3: Build the frontend
# Note: Increased memory limit is often required
NODE_OPTIONS="--max-old-space-size=8192" yarn build

# Step 4: Copy built entry point to CRM
# This is CRITICAL: We replace CRM's entry point to serve our custom frontend
cp ../bridge_telephony/public/frontend/index.html ../../crm/crm/www/crm.html

# Step 5: Clear cache
cd ../../../
bench --site all clear-cache
```

**Important Notes:**

- The `custom-build.cjs` script copies CRM's `src/` folder and then applies files from `src_override/`
- The Africa's Talking dropdown option is added via `src_override/components/Settings/TelephonySettings.vue`
- The build artifacts are served from `bridge_telephony` app, but accessed via the CRM route because we replaced `crm.html`
- After deployment, clear browser cache (Ctrl+Shift+R) to see changes

### 3. Import Fixtures

The fixtures are automatically imported during migration, but you can manually import them:

```bash
bench --site your-site.local import-fixtures bridge_telephony
```

## ⚙️ Configuration

### 1. Configure Bridge Telephony Settings

1. Go to **Frappe Desk** → Search for "Bridge Telephony Settings"
2. Enable the integration
3. Enter your Africa's Talking credentials:
   - **Username**: Your AT username
   - **API Key**: Your AT API key
   - **Caller ID**: Your AT virtual number
4. Generate and save the webhook token

### 2. Set Up Webhooks in Africa's Talking Dashboard

Configure these webhook URLs in your AT Voice settings:

| Event | URL |
|-------|-----|
| Voice Callback | `https://your-site.com/api/method/bridge_telephony.integrations.africastalking.handler.handle_webhook?token=YOUR_TOKEN` |

### 3. Configure Telephony Agents

1. Go to **CRM** → **Settings** → **CRM Telephony Agent**
2. Create or edit agent records
3. Enable "Africa's Talking" checkbox
4. Enter the Africa's Talking Number for the agent

### 4. Set Default Calling Medium

In CRM Telephony Settings, users can select "Africa's Talking" as their default calling medium.

## 🔧 How It Works

### Custom Fields Added to CRM Telephony Agent

- **Section Break**: Africa's Talking section
- **africastalking**: Check field to enable
- **africastalking_number**: The agent's Africa's Talking number

### API Override

The `is_call_integration_enabled` API is overridden to return:

```python
{
    "twilio_enabled": True/False,
    "exotel_enabled": True/False,
    "africastalking_enabled": True/False,  # NEW
    "default_calling_medium": "Africa's Talking"
}
```

### Frontend Integration

The settings.js composable is extended to:

1. Add `africastalkingEnabled` ref
2. Update `callEnabled` to include Africa's Talking:

   ```javascript
   callEnabled.value = twilioEnabled.value || exotelEnabled.value || africastalkingEnabled.value
   ```

### Call Log Integration

Calls are logged to `CRM Call Log` with:

- `telephony_medium`: "Africa's Talking"
- Links to Lead/Deal/Contact
- Recording URLs (if enabled)

## 📋 Development

### Making Changes to Backend

```bash
# After Python changes
bench restart

# After DocType schema changes
bench --site your-site.local migrate
```

### Making Changes to Frontend

```bash
cd apps/bridge_telephony/frontend

# Edit files in src_override/
# Then rebuild
yarn build

# Clear cache
cd /path/to/bench
bench --site your-site.local clear-cache
```

### Testing the Integration

```bash
# Check if API override is working
bench --site your-site.local console
>>> import frappe
>>> frappe.call("bridge_telephony.api.is_call_integration_enabled")
```

## 🧪 Verification

### Check Custom Fields

```bash
bench --site your-site.local console
>>> import frappe
>>> frappe.get_all("Custom Field", filters={"dt": "CRM Telephony Agent"}, fields=["name", "fieldname"])
```

### Check Property Setters

```bash
bench --site your-site.local console
>>> import frappe
>>> frappe.get_all("Property Setter", filters={"doc_type": "CRM Telephony Agent"}, fields=["name", "property", "value"])
```

### Test Webhook

```bash
curl -X POST "https://your-site.com/api/method/bridge_telephony.integrations.africastalking.handler.handle_webhook?token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test123", "direction": "Inbound", "callerNumber": "+254711000000"}'
```

## 📚 References

- [Africa's Talking Voice API](https://developers.africastalking.com/docs/voice/overview)
- [Frappe CRM Telephony Architecture](./EXOTEL_TELEPHONY_ARCHITECTURE.md)
- [Custom App Developer Guide](./FRAPPE_CRM_CUSTOM_APP_DEVELOPER_GUIDE.md)
- [Implementation Guide](./BRIDGE_TELEPHONY_AFRICASTALKING_IMPLEMENTATION_GUIDE.md)

## 🆘 Troubleshooting

### "Africa's Talking" not appearing in Default Medium dropdown

1. **Verify frontend build was deployed:**

   ```bash
   # Check if the override was applied
   grep -r "Africa's Talking" apps/bridge_telephony/frontend/src/components/Settings/TelephonySettings.vue
   ```

2. **Re-run deployment script:**

   ```bash
   cd apps/bridge_telephony
   ./deploy_frontend.sh
   ```

3. **Clear all caches:**

   ```bash
   bench --site your-site.local clear-cache
   # Also clear browser cache (Ctrl+Shift+R)
   ```

4. **Check Property Setter exists:**

   ```bash
   bench --site your-site.local console
   >>> frappe.get_all("Property Setter", filters={"doc_type": "CRM Telephony Agent", "field_name": "default_medium"})
   ```

### Test Connection button not showing in Bridge Telephony Settings

- Ensure bench migrate was run: `bench --site your-site.local migrate`
- Check that `bridge_telephony_settings.js` exists in the doctype folder
- Clear cache: `bench --site your-site.local clear-cache`

### Media files not uploading to Africa's Talking

- Verify Bridge Telephony Settings is enabled and credentials are correct
- Check the Error Log for "AT Media Upload" errors
- Ensure your file's public URL is accessible from the internet
- Use "Retry Upload" on failed media files

### callEnabled is false even though Africa's Talking is enabled

- Check that the API override is registered in hooks.py
- Verify `is_call_integration_enabled` returns correct data

### Frontend changes not reflected

1. Clear browser cache (Ctrl+Shift+R or Chrome DevTools → Disable cache)
2. Run `bench --site your-site clear-cache`
3. Re-run deployment script:

   ```bash
   cd apps/bridge_telephony
   ./deploy_frontend.sh
   ```

### callEnabled is false even though Africa's Talking is enabled

- Check that the API override is registered in hooks.py
- Verify `is_call_integration_enabled` returns correct data:

  ```bash
  bench --site your-site.local console
  >>> frappe.call("bridge_telephony.api.is_call_integration_enabled")
  ```

---

## 🚀 Quick Deployment Checklist

After making changes, follow these steps:

```bash
# 1. Apply database changes
bench --site your-site.local migrate

# 2. Rebuild frontend (if UI changes)
cd apps/bridge_telephony
./deploy_frontend.sh

# 3. Build bench assets (optional, handled by script)
# cd /path/to/bench
# bench build --app bridge_telephony

# 4. Clear cache (handled by script)
# bench --site your-site.local clear-cache
```

# 5. Restart services

bench restart

# 6. Clear browser cache and refresh

```

---

**App Version**: 1.0.0
**Updated**: 2025-12-07
