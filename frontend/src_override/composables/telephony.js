import { call } from 'frappe-ui'
import { computed, ref } from 'vue'

const integrations = ref({
  freepbx: true,
})
export const defaultCallingMedium = ref('FreePBX')
export const callEnabled = ref(true)

function handleData(data) {
  if (!data) return
  const res = data.message || data
  const ints = { ...(res.integrations || {}) }
  if (res.freepbx_enabled !== undefined) ints.freepbx = Boolean(res.freepbx_enabled)
  if (res.twilio_enabled !== undefined) ints.twilio = Boolean(res.twilio_enabled)
  if (res.exotel_enabled !== undefined) ints.exotel = Boolean(res.exotel_enabled)
  if (res.africastalking_enabled !== undefined) ints.africastalking = Boolean(res.africastalking_enabled)

  integrations.value = ints
  defaultCallingMedium.value = res.default_calling_medium || (ints.freepbx ? 'FreePBX' : '')
  callEnabled.value = Object.values(ints).some(Boolean)
}

// Fetch immediately via call() to bypass any stale IndexedDB cache
call('crm.integrations.api.is_call_integration_enabled')
  .then(handleData)
  .catch((err) => console.warn('Failed to fetch telephony status:', err))

export function setEnabled(name, value) {
  integrations.value[name] = value
  callEnabled.value = Object.values(integrations.value).some(Boolean)
}

export function useTelephony() {
  const allIntegrations = computed(() =>
    Object.entries(integrations.value).map(([name, enabled]) => ({
      name,
      enabled,
    })),
  )

  function isEnabled(name) {
    return Boolean(integrations.value[name])
  }

  const isAnyEnabled = computed(() =>
    Object.values(integrations.value).some(Boolean),
  )

  return { integrations: allIntegrations, isEnabled, isAnyEnabled }
}
