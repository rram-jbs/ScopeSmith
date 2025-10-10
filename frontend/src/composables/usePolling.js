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

    // Implement exponential backoff with a maximum interval
    const maxInterval = Math.min(POLLING_INTERVAL * 8, 10000) // Cap at 10 seconds
    currentInterval.value = Math.min(currentInterval.value * 1.5, maxInterval)

    pollInterval.value = setTimeout(fetchStatus, currentInterval.value)
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

      // Check if process is complete or has error
      if (response.status === 'completed' || response.status === 'error') {
        isComplete.value = true
        clearTimeout(pollInterval.value)
      } else {
        // Schedule next poll with backoff
        scheduleNextPoll()
      }
    } catch (err) {
      error.value = err
      // On error, wait a bit longer before retrying
      currentInterval.value = Math.min(currentInterval.value * 2, 15000) // Cap at 15 seconds on error
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