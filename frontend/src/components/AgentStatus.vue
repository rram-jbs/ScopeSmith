<script setup>
import { computed } from 'vue'
import { WORKFLOW_STAGES } from '@/utils/constants'
import { usePolling } from '@/composables/usePolling'
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorMessage from './ErrorMessage.vue'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['complete'])

const { status, isComplete, error, elapsedTime } = usePolling(props.sessionId)

const formattedTime = computed(() => {
  const minutes = Math.floor(elapsedTime.value / 60)
  const seconds = elapsedTime.value % 60
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
})

const currentStageIndex = computed(() => {
  if (!status.value) return 0
  return WORKFLOW_STAGES.findIndex(stage => stage.key === status.value.current_stage) || 0
})

// Watch for completion and emit event
if (isComplete) {
  emit('complete')
}
</script>

<template>
  <div class="max-w-3xl mx-auto bg-white shadow-lg rounded-lg overflow-hidden">
    <div class="px-6 py-4 bg-gradient-to-r from-primary to-secondary flex justify-between items-center">
      <div>
        <h2 class="text-2xl font-bold text-white">Generating Proposal</h2>
        <p class="text-white/80">Please wait while we process your request</p>
      </div>
      <div class="text-right">
        <p class="text-sm text-white/80">Session ID</p>
        <code class="text-xs text-white font-mono">{{ sessionId }}</code>
      </div>
    </div>

    <div class="p-6">
      <ErrorMessage
        v-if="error"
        :message="error"
      />

      <!-- Progress Steps -->
      <div class="space-y-4">
        <div
          v-for="(stage, index) in WORKFLOW_STAGES"
          :key="stage.id"
          class="flex items-start"
        >
          <!-- Stage Icon -->
          <div
            class="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full"
            :class="{
              'bg-secondary text-white': index < currentStageIndex,
              'bg-primary text-white': index === currentStageIndex,
              'bg-gray-100': index > currentStageIndex
            }"
          >
            <span v-if="index < currentStageIndex">✓</span>
            <LoadingSpinner v-else-if="index === currentStageIndex" size="sm" color="white" />
            <span v-else>{{ stage.icon }}</span>
          </div>

          <!-- Stage Content -->
          <div class="ml-4 flex-1">
            <h3 class="text-lg font-medium"
              :class="{
                'text-gray-900': index <= currentStageIndex,
                'text-gray-500': index > currentStageIndex
              }"
            >
              {{ stage.name }}
            </h3>
            <p v-if="status?.stage_details?.[stage.key]" class="mt-1 text-sm text-gray-600">
              {{ status.stage_details[stage.key] }}
            </p>
          </div>

          <!-- Stage Timestamp -->
          <div v-if="status?.stage_timestamps?.[stage.key]" class="ml-4 flex-shrink-0">
            <span class="text-sm text-gray-500">
              {{ new Date(status.stage_timestamps[stage.key]).toLocaleTimeString() }}
            </span>
          </div>
        </div>
      </div>

      <!-- Elapsed Time -->
      <div class="mt-6 flex justify-between items-center text-sm text-gray-500">
        <span>Elapsed Time: {{ formattedTime }}</span>
        <span>Status: {{ status?.status || 'Initializing...' }}</span>
      </div>
    </div>
  </div>
</template>