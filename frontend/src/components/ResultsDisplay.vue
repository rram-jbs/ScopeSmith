<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorMessage from './ErrorMessage.vue'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['reset'])

const { getResults, loading, error } = useApi()
const results = ref(null)
const showCostBreakdown = ref(false)

onMounted(async () => {
  try {
    results.value = await getResults(props.sessionId)
  } catch (err) {
    // Error handling managed by useApi
  }
})

const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount)
}

const formatFileSize = (bytes) => {
  if (!bytes) return 'N/A'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <LoadingSpinner size="lg" message="Loading results..." />
    </div>

    <!-- Error State -->
    <ErrorMessage
      v-else-if="error"
      :message="error"
      :retry-action="() => getResults(sessionId)"
    />

    <!-- Results Content -->
    <div v-else-if="results" class="space-y-6">
      <!-- Success Header -->
      <div class="bg-white p-6 rounded-lg shadow-lg text-center">
        <div class="w-16 h-16 mx-auto mb-4 bg-secondary rounded-full flex items-center justify-center">
          <span class="text-2xl text-white">✓</span>
        </div>
        <h2 class="text-2xl font-bold text-gray-900">Proposal Generated Successfully!</h2>
        <p class="mt-2 text-gray-600">
          Your documents are ready for download
        </p>
      </div>

      <!-- Download Cards -->
      <div class="grid md:grid-cols-2 gap-6">
        <!-- PowerPoint Card -->
        <div class="bg-white p-6 rounded-lg shadow-lg">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="text-lg font-medium text-gray-900">PowerPoint Presentation</h3>
              <p class="text-sm text-gray-500">Project proposal slides</p>
            </div>
            <svg class="h-8 w-8 text-primary" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 16l-4-4h8l-4 4zm0-12l4 4H8l4-4z"/>
            </svg>
          </div>
          <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt class="text-gray-500">Size</dt>
            <dd class="text-gray-900">{{ formatFileSize(results.powerpoint_size) }}</dd>
            <dt class="text-gray-500">Created</dt>
            <dd class="text-gray-900">{{ new Date(results.powerpoint_created).toLocaleString() }}</dd>
          </dl>
          <a
            :href="results.powerpoint_url"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-4 block w-full text-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
          >
            Download Presentation
          </a>
        </div>

        <!-- SOW Card -->
        <div class="bg-white p-6 rounded-lg shadow-lg">
          <div class="flex items-start justify-between">
            <div>
              <h3 class="text-lg font-medium text-gray-900">Statement of Work</h3>
              <p class="text-sm text-gray-500">Detailed project documentation</p>
            </div>
            <svg class="h-8 w-8 text-primary" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 1.5L18.5 9H13V3.5zM6 20V4h5v7h7v9H6z"/>
            </svg>
          </div>
          <dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt class="text-gray-500">Size</dt>
            <dd class="text-gray-900">{{ formatFileSize(results.sow_size) }}</dd>
            <dt class="text-gray-500">Created</dt>
            <dd class="text-gray-900">{{ new Date(results.sow_created).toLocaleString() }}</dd>
          </dl>
          <a
            :href="results.sow_url"
            target="_blank"
            rel="noopener noreferrer"
            class="mt-4 block w-full text-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
          >
            Download SOW
          </a>
        </div>
      </div>

      <!-- Cost Summary -->
      <div class="bg-white p-6 rounded-lg shadow-lg">
        <button
          class="w-full flex items-center justify-between text-left"
          @click="showCostBreakdown = !showCostBreakdown"
        >
          <div>
            <h3 class="text-lg font-medium text-gray-900">Cost Summary</h3>
            <p class="text-sm text-gray-500">Estimated project costs</p>
          </div>
          <div class="flex items-center">
            <span class="text-lg font-bold text-primary mr-2">
              {{ formatCurrency(results.cost_data.total_cost) }}
            </span>
            <svg
              class="h-5 w-5 text-gray-500 transform transition-transform"
              :class="{ 'rotate-180': showCostBreakdown }"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>

        <!-- Cost Breakdown Table -->
        <div v-show="showCostBreakdown" class="mt-4">
          <table class="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Hours</th>
                <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Rate</th>
                <th class="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Subtotal</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="(cost, role) in results.cost_data.breakdown" :key="role">
                <td class="px-4 py-2 text-sm text-gray-900">{{ role }}</td>
                <td class="px-4 py-2 text-sm text-gray-900 text-right">{{ cost.hours }}</td>
                <td class="px-4 py-2 text-sm text-gray-900 text-right">{{ formatCurrency(cost.rate) }}/hr</td>
                <td class="px-4 py-2 text-sm text-gray-900 text-right">{{ formatCurrency(cost.subtotal) }}</td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <td colspan="3" class="px-4 py-2 text-sm font-medium text-gray-900">Total</td>
                <td class="px-4 py-2 text-sm font-medium text-primary text-right">
                  {{ formatCurrency(results.cost_data.total_cost) }}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex justify-center space-x-4">
        <button
          @click="emit('reset')"
          class="px-6 py-3 border border-gray-300 rounded-md shadow-sm text-base font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
        >
          Generate Another Proposal
        </button>
      </div>
    </div>
  </div>
</template>