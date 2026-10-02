// Telemetry stub - provides capture function for event tracking
// This integrates with frappe-ui's telemetry plugin when available

export function capture(eventName, properties = {}) {
  // The telemetryPlugin from frappe-ui handles the actual tracking
  // This is a convenience wrapper for components to use
  if (window.posthog && typeof window.posthog.capture === 'function') {
    window.posthog.capture(eventName, properties)
  }
  // Optionally log in dev mode
  if (import.meta.env.DEV) {
    console.debug('[Telemetry]', eventName, properties)
  }
}

export default { capture }
