<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex gap-1 items-center">
        <Button
          variant="ghost"
          icon-left="lucide-chevron-left"
          :label="__('Bridge Telephony Settings')"
          size="md"
          class="cursor-pointer -ml-4 hover:bg-transparent focus:bg-transparent focus:outline-none focus:ring-0 focus:ring-offset-0 focus-visible:none active:bg-transparent active:outline-none active:ring-0 active:ring-offset-0 active:text-ink-gray-5 text-2xl-semibold hover:opacity-70 !pr-0 !max-w-96 !justify-start"
          @click="emit('updateStep', 'telephony-settings')"
        />
        <Badge
          v-if="bridgeTelephony.doc?.enabled && isDirty"
          :label="__('Not Saved')"
          variant="subtle"
          theme="orange"
        />
      </div>
    </template>
    <template #header-actions>
      <div
        v-if="bridgeTelephony.doc?.enabled && !bridgeTelephony.get.loading"
        class="flex gap-2"
      >
        <Button
          v-if="isDirty"
          :label="__('Discard Changes')"
          variant="subtle"
          @click="bridgeTelephony.reload()"
        />
        <Button :label="__('Disable')" variant="subtle" @click="disable" />
        <Button
          variant="solid"
          :label="__('Update')"
          :loading="bridgeTelephony.save.loading"
          :disabled="!isDirty"
          @click="update"
        />
      </div>
    </template>
    <template #content>
      <div v-if="bridgeTelephony.doc" class="h-full">
        <div v-if="bridgeTelephony.doc.enabled" class="space-y-6">
          <!-- Provider Selection -->
          <div class="grid grid-cols-2 gap-4">
            <FormControl
              v-model="bridgeTelephony.doc.provider"
              :label="__('Telephony Provider')"
              type="select"
              :options="[
                { label: __('FreePBX (Asterisk AMI)'), value: 'FreePBX' },
                { label: __('Africa\'s Talking'), value: 'Africa\'s Talking' },
              ]"
              required
            />
          </div>

          <!-- FreePBX Configuration Section -->
          <div
            v-if="bridgeTelephony.doc.provider === 'FreePBX' || !bridgeTelephony.doc.provider"
            class="space-y-4"
          >
            <div class="flex items-center justify-between pb-2 border-b border-outline-elevation-2">
              <div class="flex flex-col">
                <span class="text-base-medium text-ink-gray-8">
                  {{ __('FreePBX Server & AMI Credentials') }}
                </span>
                <span class="text-p-sm text-ink-gray-5">
                  {{ __('Connect to FreePBX Asterisk Manager Interface for click-to-call and call logging') }}
                </span>
              </div>
              <Button
                :label="__('Test AMI Connection')"
                variant="subtle"
                theme="blue"
                icon-left="lucide-activity"
                :loading="testConnectionResource.loading"
                @click="testConnectionResource.submit()"
              />
            </div>

            <!-- AMI Test Result Banner -->
            <div
              v-if="testResult"
              class="p-3 rounded-lg flex items-center justify-between"
              :class="testResult.success ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'"
            >
              <div class="flex items-center gap-2 text-sm">
                <span class="font-semibold">{{ testResult.success ? '✓' : '✗' }}</span>
                <span>{{ testResult.message }}</span>
                <span v-if="testResult.banner" class="text-xs opacity-75">({{ testResult.banner }})</span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                icon="lucide-x"
                @click="testResult = null"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <FormControl
                v-model="bridgeTelephony.doc.freepbx_host"
                :label="__('Asterisk AMI Host')"
                type="text"
                placeholder="172.187.235.228"
                required
                :description="__('Server IP or hostname running Asterisk AMI (default port: 5038)')"
              />
              <FormControl
                v-model="bridgeTelephony.doc.freepbx_ami_port"
                :label="__('Asterisk AMI Port')"
                type="number"
                placeholder="5038"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <FormControl
                v-model="bridgeTelephony.doc.freepbx_ami_username"
                :label="__('AMI Username')"
                type="text"
                placeholder="frappe_crm"
                required
                autocomplete="off"
              />
              <Password
                v-model="bridgeTelephony.doc.freepbx_ami_secret"
                :label="__('AMI Secret / Password')"
                placeholder="••••••••••••"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <FormControl
                v-model="bridgeTelephony.doc.freepbx_context"
                :label="__('Dialplan Context')"
                type="text"
                placeholder="from-internal"
                :description="__('Dialplan context used for originating calls (default: from-internal)')"
              />
              <FormControl
                v-model="bridgeTelephony.doc.freepbx_recording_url"
                :label="__('Recording Audio Base URL')"
                type="text"
                placeholder="https://voice.bridge.ng"
                :description="__('URL where recordings are hosted or proxied')"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <FormControl
                v-model="bridgeTelephony.doc.freepbx_webhook_token"
                :label="__('FreePBX Webhook Secret Token')"
                type="text"
                placeholder="Secret token"
                :description="__('Optional verification token for FreePBX hangup webhooks')"
              />
            </div>
          </div>

          <!-- WebRTC & In-Browser Calling Section -->
          <div
            v-if="bridgeTelephony.doc.provider === 'FreePBX' || !bridgeTelephony.doc.provider"
            class="space-y-4 pt-2 border-t border-outline-elevation-2"
          >
            <div class="flex items-center justify-between pb-2 border-b border-outline-elevation-2">
              <div class="flex flex-col">
                <span class="text-base-medium text-ink-gray-8">
                  {{ __('WebRTC & In-Browser Phone (Cloud Contact Center)') }}
                </span>
                <span class="text-p-sm text-ink-gray-5">
                  {{ __('Enable agents to make and receive calls directly inside Frappe CRM and the PWA without MicroSIP') }}
                </span>
              </div>
            </div>

            <div class="space-y-2">
              <FormControl
                v-model="bridgeTelephony.doc.enable_webrtc"
                type="checkbox"
                :label="__('Enable WebRTC In-Browser Calling')"
                :description="__('Agents use browser microphone/speakers for calls based on their CRM Telephony Agent extension')"
              />
            </div>

            <div v-if="bridgeTelephony.doc.enable_webrtc" class="space-y-4 pt-2">
              <div class="grid grid-cols-2 gap-4">
                <FormControl
                  v-model="bridgeTelephony.doc.calling_mode"
                  :label="__('Default Calling Mode')"
                  type="select"
                  :options="[
                    { label: __('WebRTC (In-Browser Phone)'), value: 'WebRTC (In-Browser Phone)' },
                    { label: __('AMI Originate (MicroSIP Desktop)'), value: 'AMI Originate (MicroSIP Desktop)' },
                  ]"
                  :description="__('Select default behavior when clicking Make Call in CRM')"
                />
                <FormControl
                  v-model="bridgeTelephony.doc.webrtc_wss_url"
                  :label="__('Asterisk WSS URI')"
                  type="text"
                  placeholder="wss://webrtc.bridge.ng:8089/ws"
                  :description="__('WebSocket Secure URL for Asterisk WSS server')"
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <FormControl
                  v-model="bridgeTelephony.doc.webrtc_sip_domain"
                  :label="__('WebRTC SIP Domain')"
                  type="text"
                  placeholder="webrtc.bridge.ng"
                  :description="__('SIP realm domain configured in Asterisk PJSIP')"
                />
                <FormControl
                  v-model="bridgeTelephony.doc.webrtc_stun_server"
                  :label="__('STUN Server URI')"
                  type="text"
                  placeholder="stun:stun.l.google.com:19302"
                  :description="__('STUN server for ICE candidate NAT traversal')"
                />
              </div>
            </div>
          </div>

          <!-- Africa's Talking Configuration Section -->
          <div
            v-else-if="bridgeTelephony.doc.provider === 'Africa\'s Talking'"
            class="space-y-4"
          >
            <div class="pb-2 border-b border-outline-elevation-2">
              <span class="text-base-medium text-ink-gray-8">
                {{ __('Africa\'s Talking Credentials') }}
              </span>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <FormControl
                v-model="bridgeTelephony.doc.username"
                :label="__('Username')"
                type="text"
                placeholder="edubrigdeVoice"
                required
              />
              <Password
                v-model="bridgeTelephony.doc.api_key"
                :label="__('API Key')"
                placeholder="••••••••••••"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <FormControl
                v-model="bridgeTelephony.doc.phone_number"
                :label="__('Phone Number')"
                type="text"
                placeholder="+2342017001287"
              />
              <FormControl
                v-model="bridgeTelephony.doc.webhook_verify_token"
                :label="__('Webhook Verify Token')"
                type="text"
                placeholder="edubridge"
              />
            </div>
          </div>

          <!-- General Features Section -->
          <div class="space-y-3 pt-2 border-t border-outline-elevation-2">
            <span class="text-base-medium text-ink-gray-8">
              {{ __('General Telephony Options') }}
            </span>
            <div class="space-y-2">
              <FormControl
                v-model="bridgeTelephony.doc.enable_recording"
                type="checkbox"
                :label="__('Enable Call Recording')"
                :description="__('Record calls and link audio to CRM Call Log records')"
              />
              <FormControl
                v-model="bridgeTelephony.doc.auto_create_call_logs"
                type="checkbox"
                :label="__('Auto Create Call Logs')"
                :description="__('Automatically log incoming and outgoing calls in CRM Call Log')"
              />
            </div>
          </div>
        </div>

        <!-- Disabled State -->
        <div v-else class="h-full flex items-center justify-center">
          <div class="flex flex-col gap-3 text-center max-w-sm">
            <span class="text-lg-semibold text-ink-gray-8">
              {{ __('Bridge Telephony is disabled') }}
            </span>
            <span class="text-p-base text-ink-gray-6">
              {{
                __(
                  'Enable Bridge Telephony to connect FreePBX / Africa\'s Talking and make/receive calls directly from Frappe CRM.',
                )
              }}
            </span>
            <div class="flex justify-center mt-2">
              <Button
                :label="__('Enable')"
                variant="solid"
                theme="gray"
                @click="enable"
              />
            </div>
          </div>
        </div>
      </div>
      <div
        v-else-if="bridgeTelephony.get.loading"
        class="flex items-center justify-center mt-[35%]"
      >
        <LoadingIndicator class="size-6" />
      </div>
    </template>
  </SettingsLayoutBase>
</template>
<script setup>
import SettingsLayoutBase from '@/components/Layouts/SettingsLayoutBase.vue'
import { setEnabled } from '@/composables/telephony'
import { useDocument } from '@/data/document'
import {
  FormControl,
  Button,
  Badge,
  toast,
  Password,
  LoadingIndicator,
  createResource,
} from 'frappe-ui'
import { computed, ref } from 'vue'

const emit = defineEmits(['updateStep'])

const { document: bridgeTelephony } = useDocument(
  'Bridge Telephony Settings',
  'Bridge Telephony Settings',
)

const testResult = ref(null)

const testConnectionResource = createResource({
  url: 'bridge_telephony.api.freepbx.test_connection',
  onSuccess: (data) => {
    testResult.value = data
    if (data.success) {
      toast.success(data.message || __('FreePBX AMI Connected successfully!'))
    } else {
      toast.error(data.message || __('Failed to connect to FreePBX AMI'))
    }
  },
  onError: (err) => {
    testResult.value = {
      success: false,
      message: err.messages ? err.messages[0] : (err.message || __('Connection failed')),
    }
    toast.error(testResult.value.message)
  },
})

function enable() {
  bridgeTelephony.doc.enabled = true
}

function disable() {
  bridgeTelephony.doc.enabled = false
  update()
}

function update() {
  bridgeTelephony.save.submit(null, {
    onSuccess: () => {
      bridgeTelephony.reload()
      toast.success(__('Bridge Telephony settings saved successfully'))
    },
  })

  const isFreePBX =
    bridgeTelephony.doc.enabled &&
    (bridgeTelephony.doc.provider === 'FreePBX' ||
      Boolean(bridgeTelephony.doc.freepbx_enabled))

  setEnabled('freepbx', isFreePBX)
}

const isDirty = computed(() => {
  return (
    bridgeTelephony.doc &&
    bridgeTelephony.originalDoc &&
    JSON.stringify(bridgeTelephony.doc) !==
      JSON.stringify(bridgeTelephony.originalDoc)
  )
})
</script>
