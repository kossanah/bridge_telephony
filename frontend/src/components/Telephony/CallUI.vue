<template>
  <TwilioCallUI ref="twilio" />
  <ExotelCallUI ref="exotel" />
  <FreePBXCallUI ref="freepbx" />

  <!-- Quick Make Call icon button displayed in header bar when calling is enabled -->
  <Button
    v-if="callEnabled"
    variant="ghost"
    class="size-7 flex items-center justify-center text-ink-gray-7 hover:text-ink-gray-9 cursor-pointer rounded"
    :tooltip="__('Make a Call')"
    @click="openCallDialog"
  >
    <PhoneIcon class="size-4" />
  </Button>

  <Dialog
    v-model:open="show"
    :title="__('Make Call')"
    :actions="[
      {
        label: __('Call using {0}', [callMedium]),
        variant: 'solid',
        onClick: makeCallUsing,
      },
    ]"
  >
    <template #default>
      <div class="flex flex-col gap-4">
        <FormControl
          v-model="mobileNumber"
          type="text"
          :label="__('Mobile Number')"
          :placeholder="__('Enter phone number or extension (e.g. 08031234567, 1002)')"
        />
        <FormControl
          v-model="callMedium"
          type="select"
          :label="__('Calling Medium')"
          :options="callingMediumOptions"
        />
        <div class="flex flex-col gap-1">
          <FormControl
            v-model="isDefaultMedium"
            type="checkbox"
            :label="__('Make {0} as default calling medium', [callMedium])"
          />

          <div v-if="isDefaultMedium" class="text-sm text-ink-gray-4">
            {{
              __('You can change the default calling medium from the settings')
            }}
          </div>
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import PhoneIcon from '@/components/Icons/PhoneIcon.vue'
import TwilioCallUI from '@/components/Telephony/TwilioCallUI.vue'
import ExotelCallUI from '@/components/Telephony/ExotelCallUI.vue'
import FreePBXCallUI from '@/components/Telephony/FreePBXCallUI.vue'
import { callEnabled, defaultCallingMedium, useTelephony } from '@/composables/telephony'
import { globalStore } from '@/stores/global'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const { setMakeCall } = globalStore()
const { isEnabled, isAnyEnabled } = useTelephony()

const twilio = ref(null)
const exotel = ref(null)
const freepbx = ref(null)

const callMedium = ref('FreePBX')
const isDefaultMedium = ref(false)

const show = ref(false)
const mobileNumber = ref('')

const enabledIntegrations = computed(() =>
  [
    { key: 'freepbx', label: 'FreePBX', ref: freepbx },
    { key: 'twilio', label: 'Twilio', ref: twilio },
    { key: 'exotel', label: 'Exotel', ref: exotel },
  ].filter(({ key }) => isEnabled(key)),
)

const callingMediumOptions = computed(() => {
  if (enabledIntegrations.value.length > 0) {
    return enabledIntegrations.value.map(({ label }) => label)
  }
  return ['FreePBX', 'Twilio', 'Exotel']
})

function openCallDialog() {
  mobileNumber.value = ''
  callMedium.value =
    defaultCallingMedium.value ||
    enabledIntegrations.value[0]?.label ||
    'FreePBX'
  show.value = true
}

function makeCall(number) {
  if (
    !number ||
    (enabledIntegrations.value.length > 1 && !defaultCallingMedium.value)
  ) {
    mobileNumber.value = number || ''
    callMedium.value =
      defaultCallingMedium.value ||
      enabledIntegrations.value[0]?.label ||
      'FreePBX'
    show.value = true
    return
  }

  callMedium.value =
    defaultCallingMedium.value ||
    enabledIntegrations.value[0]?.label ||
    'FreePBX'
  mobileNumber.value = number
  makeCallUsing()
}

function makeCallUsing() {
  if (!mobileNumber.value) {
    toast.error(__('Please enter a mobile number'))
    return
  }

  if (isDefaultMedium.value && callMedium.value) {
    setDefaultCallingMedium()
  }

  if (callMedium.value === 'FreePBX' || callMedium.value === 'Bridge Telephony') {
    freepbx.value?.makeOutgoingCall(mobileNumber.value)
  } else if (callMedium.value === 'Twilio') {
    twilio.value?.makeOutgoingCall(mobileNumber.value)
  } else if (callMedium.value === 'Exotel') {
    exotel.value?.makeOutgoingCall(mobileNumber.value)
  }
  show.value = false
}

async function setDefaultCallingMedium() {
  await call('crm.integrations.api.set_default_calling_medium', {
    medium: callMedium.value,
  })

  defaultCallingMedium.value = callMedium.value
  toast.success(
    __('Default calling medium set successfully to {0}', [callMedium.value]),
  )
}

onMounted(() => {
  setMakeCall(makeCall)
})

watch(
  [isAnyEnabled, defaultCallingMedium],
  () =>
    nextTick(() => {
      for (const {
        key,
        label,
        ref: integrationRef,
      } of enabledIntegrations.value) {
        if (integrationRef.value && integrationRef.value.setup) {
          integrationRef.value.setup()
        }
      }

      if (isAnyEnabled.value) {
        callMedium.value =
          defaultCallingMedium.value ||
          enabledIntegrations.value[0]?.label ||
          'FreePBX'
        setMakeCall(makeCall)
      }
    }),
  { immediate: true },
)
</script>
