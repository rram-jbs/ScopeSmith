<template>
  <div class="agent-stream-viewer">
    <div class="stream-header">
      <h3>AI Agent Activity</h3>
      <span class="status-badge" :class="statusClass">{{ statusText }}</span>
    </div>
    
    <div class="stream-content" ref="streamContent">
      <div v-for="(event, index) in events" :key="index" class="event-item" :class="`event-${event.type}`">
        <div class="event-header">
          <span class="event-icon">{{ getEventIcon(event.type) }}</span>
          <span class="event-type">{{ formatEventType(event.type) }}</span>
          <span class="event-time">{{ formatTime(event.timestamp) }}</span>
        </div>
        
        <div class="event-content">
          <div v-if="event.type === 'reasoning'" class="reasoning-content">
            <p>{{ event.content }}</p>
          </div>
          
          <div v-else-if="event.type === 'tool_call'" class="tool-call-content">
            <div class="tool-name">
              <strong>{{ event.action_group }}</strong>
            </div>
            <div v-if="event.parameters && event.parameters.length > 0" class="tool-params">
              <div v-for="param in event.parameters" :key="param.name" class="param">
                <span class="param-name">{{ param.name }}:</span>
                <span class="param-value">{{ truncate(param.value, 100) }}</span>
              </div>
            </div>
          </div>
          
          <div v-else-if="event.type === 'tool_response'" class="tool-response-content">
            <pre>{{ formatResponse(event.content) }}</pre>
          </div>
          
          <div v-else-if="event.type === 'chunk'" class="chunk-content">
            <p>{{ event.content }}</p>
          </div>
          
          <div v-else-if="event.type === 'final_response'" class="final-response-content">
            <div class="final-badge">✓ Complete</div>
            <p>{{ event.content }}</p>
          </div>
        </div>
      </div>
      
      <div v-if="isProcessing" class="loading-indicator">
        <div class="spinner"></div>
        <span>Agent is processing...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['complete', 'error'])

const events = ref([])
const isProcessing = ref(true)
const currentStatus = ref('INITIATED')
const streamContent = ref(null)
let pollInterval = null

const statusClass = computed(() => {
  if (currentStatus.value === 'ERROR') return 'status-error'
  if (currentStatus.value === 'COMPLETED') return 'status-success'
  return 'status-processing'
})

const statusText = computed(() => {
  const statusMap = {
    'INITIATED': 'Starting',
    'AGENT_PROCESSING': 'Processing',
    'COMPLETED': 'Completed',
    'ERROR': 'Error'
  }
  return statusMap[currentStatus.value] || 'Processing'
})

const getEventIcon = (type) => {
  const icons = {
    'reasoning': '🤔',
    'tool_call': '🔧',
    'tool_response': '✅',
    'chunk': '💬',
    'final_response': '🎉'
  }
  return icons[type] || '📝'
}

const formatEventType = (type) => {
  const labels = {
    'reasoning': 'Agent Thinking',
    'tool_call': 'Calling Tool',
    'tool_response': 'Tool Response',
    'chunk': 'Agent Response',
    'final_response': 'Final Result'
  }
  return labels[type] || type
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const truncate = (str, length) => {
  if (!str) return ''
  return str.length > length ? str.substring(0, length) + '...' : str
}

const formatResponse = (content) => {
  if (!content) return ''
  try {
    const parsed = JSON.parse(content)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return content
  }
}

const scrollToBottom = () => {
  if (streamContent.value) {
    streamContent.value.scrollTop = streamContent.value.scrollHeight
  }
}

const fetchAgentEvents = async () => {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/agent-status/${props.sessionId}`)
    const data = await response.json()
    
    if (data.agent_events) {
      const parsedEvents = typeof data.agent_events === 'string' 
        ? JSON.parse(data.agent_events) 
        : data.agent_events
      
      events.value = parsedEvents
      currentStatus.value = data.status
      
      // Auto-scroll to bottom when new events arrive
      setTimeout(scrollToBottom, 100)
      
      // Check if completed
      if (data.status === 'COMPLETED' || data.status === 'ERROR') {
        isProcessing.value = false
        stopPolling()
        
        if (data.status === 'COMPLETED') {
          emit('complete', data)
        } else {
          emit('error', data.error_message)
        }
      }
    }
  } catch (error) {
    console.error('Error fetching agent events:', error)
  }
}

const startPolling = () => {
  fetchAgentEvents() // Initial fetch
  pollInterval = setInterval(fetchAgentEvents, 2000) // Poll every 2 seconds
}

const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})

watch(() => events.value.length, () => {
  scrollToBottom()
})
</script>

<style scoped>
.agent-stream-viewer {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stream-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-processing {
  background: rgba(255, 255, 255, 0.2);
}

.status-success {
  background: #10b981;
}

.status-error {
  background: #ef4444;
}

.stream-content {
  max-height: 600px;
  overflow-y: auto;
  padding: 1.5rem;
}

.event-item {
  margin-bottom: 1.5rem;
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.event-reasoning {
  background: #eff6ff;
  border-left-color: #3b82f6;
}

.event-tool_call {
  background: #f0fdf4;
  border-left-color: #10b981;
}

.event-tool_response {
  background: #fef3c7;
  border-left-color: #f59e0b;
}

.event-chunk {
  background: #f3e8ff;
  border-left-color: #a855f7;
}

.event-final_response {
  background: #d1fae5;
  border-left-color: #059669;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.event-icon {
  font-size: 1.25rem;
}

.event-type {
  font-weight: 600;
  color: #374151;
}

.event-time {
  margin-left: auto;
  font-size: 0.75rem;
  color: #6b7280;
}

.event-content {
  color: #4b5563;
  line-height: 1.6;
}

.reasoning-content p {
  margin: 0;
  font-style: italic;
}

.tool-call-content {
  font-family: 'Monaco', 'Courier New', monospace;
}

.tool-name {
  margin-bottom: 0.5rem;
  color: #059669;
}

.tool-params {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.75rem;
  border-radius: 4px;
}

.param {
  margin-bottom: 0.25rem;
}

.param-name {
  font-weight: 600;
  color: #6b7280;
}

.param-value {
  margin-left: 0.5rem;
  color: #374151;
}

.tool-response-content pre {
  margin: 0;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.875rem;
}

.chunk-content p {
  margin: 0;
  white-space: pre-wrap;
}

.final-response-content {
  position: relative;
}

.final-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #059669;
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  color: #6b7280;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 3px solid #e5e7eb;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
