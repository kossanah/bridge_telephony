<template>
  <TelephonySettings
    v-if="step === 'telephony-settings'"
    @updateStep="updateStep"
  />
  <TwilioSettings
    v-else-if="step === 'twilio-settings'"
    @updateStep="updateStep"
  />
  <ExotelSettings
    v-else-if="step === 'exotel-settings'"
    @updateStep="updateStep"
  />
  <BridgeTelephonySettings
    v-else-if="step === 'bridge-telephony-settings'"
    @updateStep="updateStep"
  />
</template>
<script setup>
import TelephonySettings from './TelephonySettings.vue'
import ExotelSettings from './ExotelSettings.vue'
import TwilioSettings from './TwilioSettings.vue'
import BridgeTelephonySettings from './BridgeTelephonySettings.vue'
import { ref } from 'vue'

const step = ref('telephony-settings')

function updateStep(newStep) {
  step.value = newStep
}
</script>
