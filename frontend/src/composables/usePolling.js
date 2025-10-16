import { ref, onMounted, onUnmounted } from 'vue'
import { POLLING_INTERVAL, MAX_POLLING_TIME } from '@/utils/constants'
import { useApi } from './useApi'

export function usePolling(sessionId) {
  const status = ref(null)
  const isComplete = ref(false)
  const error = ref(null)
  const pollInterval = ref(null)
  const startTime = ref(Date.now())
  const elapsedTime = ref(0)
  const currentInterval = ref(POLLING_INTERVAL)
  const { getAgentStatus } = useApi()

  const updateElapsedTime = () => {
    elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
  }

  const scheduleNextPoll = () => {
    // Clear existing interval if any
    if (pollInterval.value) {
      clearTimeout(pollInterval.value)
    }

    // Keep polling at consistent 2-second intervals during active processing
    // No exponential backoff needed since backend handles this efficiently
    pollInterval.value = setTimeout(fetchStatus, POLLING_INTERVAL)
  }

  const fetchStatus = async () => {
    try {
      // Check if we've exceeded maximum polling time
      if (Date.now() - startTime.value > MAX_POLLING_TIME) {
        clearTimeout(pollInterval.value)
        error.value = 'Operation timed out. Please try again.'
        return
      }

      const response = await getAgentStatus(sessionId)
      status.value = response
      updateElapsedTime()

      // Check if process is complete or has error - sync with backend status values
      if (response.status === 'COMPLETED' || response.status === 'ERROR') {
        isComplete.value = true
        clearTimeout(pollInterval.value)
      } else {
        // Continue polling for PENDING or PROCESSING states
        scheduleNextPoll()
      }
    } catch (err) {
      error.value = err
      // On error, continue polling - agent might still be working
      scheduleNextPoll()
    }
  }

  onMounted(() => {
    fetchStatus() // Initial fetch
  })

  onUnmounted(() => {
    if (pollInterval.value) clearTimeout(pollInterval.value)
  })

  return {
    status,
    isComplete,
    error,
    elapsedTime
  }
}