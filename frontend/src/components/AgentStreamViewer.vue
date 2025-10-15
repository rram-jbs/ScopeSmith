<template>
  <div class="agent-stream-viewer">
    <div class="stream-container">
      <div class="stream-header">
        <h2>🤖 AI Agent Progress</h2>
        <span class="status-badge" :class="statusClass">{{ status }}</span>
      </div>

      <div class="events-container" ref="eventsContainer">
        <div v-if="events.length === 0" class="loading">
          <div class="spinner"></div>
          <p>Starting agent...</p>
        </div>

        <div v-for="(event, index) in events" :key="index" class="event-card" :class="`event-${event.type}`">
          <div class="event-header">
            <span class="event-icon">{{ getEventIcon(event.type) }}</span>
            <span class="event-type">{{ formatEventType(event.type) }}</span>
            <span class="event-time">{{ formatTime(event.timestamp) }}</span>
          </div>
          <div class="event-content">
            <pre v-if="event.type === 'tool_call'">{{ formatToolCall(event) }}</pre>
            <pre v-else-if="event.type === 'tool_response'">{{ formatToolResponse(event.content) }}</pre>
            <div v-else-if="event.type === 'reasoning'" class="reasoning-text">{{ event.content }}</div>
            <div v-else class="event-text">{{ event.content }}</div>
          </div>
        </div>

        <div v-if="status === 'COMPLETED'" class="completion-card">
          <h3>✅ Proposal Generation Complete!</h3>
          <p>Your documents are ready for download.</p>
        </div>

        <div v-if="error" class="error-card">
          <h3>❌ Error</h3>
          <p>{{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useApi } from '../composables/useApi'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['complete', 'error'])

const { get } = useApi()

const events = ref([])
const status = ref('STARTING')
const error = ref(null)
const eventsContainer = ref(null)
let pollInterval = null

const statusClass = ref('status-processing')

const getEventIcon = (type) => {
  const icons = {
    'reasoning': '🤔',
    'tool_call': '🔧',
    'tool_response': '✅',
    'chunk': '💬',
    'final_response': '🎉',
    'warning': '⚠️',
    'error': '❌'
  }
  return icons[type] || '📝'
}

const formatEventType = (type) => {
  const labels = {
    'reasoning': 'Agent Thinking',
    'tool_call': 'Calling Function',
    'tool_response': 'Function Response',
    'chunk': 'Agent Response',
    'final_response': 'Final Response',
    'warning': 'Warning',
    'error': 'Error'
  }
  return labels[type] || type
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

const formatToolCall = (event) => {
  const params = event.parameters?.map(p => `  ${p.name}: ${p.value}`).join('\n') || ''
  return `Function: ${event.function}\nAction Group: ${event.action_group}\nParameters:\n${params}`
}

const formatToolResponse = (content) => {
  try {
    const parsed = JSON.parse(content)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return content
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (eventsContainer.value) {
    eventsContainer.value.scrollTop = eventsContainer.value.scrollHeight
  }
}

const fetchAgentStatus = async () => {
  try {
    const data = await get(`/api/agent-status/${props.sessionId}`)
    console.log('Agent status:', data)
    
    status.value = data.status || 'PROCESSING'
    
    // Update status class
    if (status.value === 'COMPLETED') {
      statusClass.value = 'status-completed'
    } else if (status.value === 'ERROR') {
      statusClass.value = 'status-error'
    } else {
      statusClass.value = 'status-processing'
    }
    
    // Parse agent events
    if (data.agent_events) {
      try {
        const parsedEvents = typeof data.agent_events === 'string' 
          ? JSON.parse(data.agent_events) 
          : data.agent_events
        
        if (parsedEvents.length > events.value.length) {
          events.value = parsedEvents
          scrollToBottom()
        }
      } catch (e) {
        console.error('Error parsing agent events:', e)
      }
    }
    
    // Check for completion or error
    if (status.value === 'COMPLETED') {
      clearInterval(pollInterval)
      emit('complete', data)
    } else if (status.value === 'ERROR') {
      clearInterval(pollInterval)
      error.value = data.error_message || 'An error occurred'
      emit('error', error.value)
    }
    
  } catch (err) {
    console.error('Error fetching agent status:', err)
    error.value = `Failed to fetch status: ${err.message}`
  }
}

onMounted(() => {
  console.log('AgentStreamViewer mounted for session:', props.sessionId)
  
  // Start polling every 2 seconds
  fetchAgentStatus()
  pollInterval = setInterval(fetchAgentStatus, 2000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style scoped>
.agent-stream-viewer {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.stream-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  overflow: hidden;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stream-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-processing {
  background: #fbbf24;
  color: #78350f;
}

.status-completed {
  background: #10b981;
  color: white;
}

.status-error {
  background: #ef4444;
  color: white;
}

.events-container {
  max-height: 600px;
  overflow-y: auto;
  padding: 1.5rem;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: #6b7280;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e5e7eb;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.event-card {
  margin-bottom: 1rem;
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
  border-color: #3b82f6;
}

.event-tool_call {
  background: #f0fdf4;
  border-color: #10b981;
}

.event-tool_response {
  background: #fefce8;
  border-color: #eab308;
}

.event-chunk {
  background: #f5f3ff;
  border-color: #8b5cf6;
}

.event-warning {
  background: #fef3c7;
  border-color: #f59e0b;
}

.event-error {
  background: #fee2e2;
  border-color: #ef4444;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-weight: 600;
  font-size: 0.9rem;
}

.event-icon {
  font-size: 1.2rem;
}

.event-type {
  flex: 1;
  color: #374151;
}

.event-time {
  color: #6b7280;
  font-size: 0.8rem;
  font-weight: normal;
}

.event-content {
  color: #1f2937;
}

.event-content pre {
  background: rgba(0, 0, 0, 0.05);
  padding: 0.75rem;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 0.85rem;
  margin: 0;
}

.reasoning-text {
  font-style: italic;
  color: #1e40af;
  line-height: 1.6;
}

.event-text {
  line-height: 1.6;
}

.completion-card, .error-card {
  margin-top: 2rem;
  padding: 2rem;
  border-radius: 8px;
  text-align: center;
  animation: slideIn 0.3s ease-out;
}

.completion-card {
  background: #d1fae5;
  border: 2px solid #10b981;
}

.completion-card h3 {
  color: #065f46;
  margin-bottom: 0.5rem;
}

.completion-card p {
  color: #047857;
}

.error-card {
  background: #fee2e2;
  border: 2px solid #ef4444;
}

.error-card h3 {
  color: #991b1b;
  margin-bottom: 0.5rem;
}

.error-card p {
  color: #b91c1c;
}
</style>
