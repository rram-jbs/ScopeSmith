<template>
  <div class="agent-stream-viewer">
    <!-- Main Live Activity Container -->
    <div class="live-activity-container">
      
      <!-- 8-Step Progress Timeline -->
      <div class="progress-timeline">
        <div 
          v-for="(step, index) in workflowSteps" 
          :key="index"
          class="timeline-step"
          :class="getStepClass(index)"
        >
          <div class="step-checkpoint">
            <div class="checkpoint-circle">
              <svg v-if="step.status === 'completed'" class="checkmark" width="16" height="16" viewBox="0 0 16 16">
                <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
              </svg>
              <div v-else-if="step.status === 'active'" class="spinner-dot"></div>
            </div>
          </div>
          <div class="step-label">{{ step.label }}</div>
          <div v-if="index < workflowSteps.length - 1" class="step-connector"></div>
        </div>
      </div>

      <!-- Agent Reasoning Panel (ReAct Pattern) -->
      <div class="reasoning-panel">
        <div class="panel-header">
          <div class="header-icon">🤖</div>
          <h3>Agent Orchestration</h3>
          <span class="status-badge" :class="statusBadgeClass">{{ formattedStatus }}</span>
        </div>
        
        <div class="reasoning-content" ref="reasoningContent">
          <div v-if="events.length === 0" class="loading-state">
            <div class="loading-spinner"></div>
            <p class="loading-text">Initializing Bedrock Agent session...</p>
            <p class="loading-subtext">Estimated time: &lt; 3 minutes</p>
          </div>

          <!-- Agent Events Stream -->
          <div v-for="(event, index) in events" :key="index" class="event-item" :class="`event-type-${event.type}`">
            
            <!-- Reasoning Event -->
            <div v-if="event.type === 'reasoning'" class="reasoning-event">
              <div class="event-header-small">
                <span class="event-icon">💭</span>
                <span class="event-label">Agent Thinking</span>
                <span class="event-time">{{ formatTime(event.timestamp) }}</span>
              </div>
              <div class="reasoning-text">{{ event.content }}</div>
            </div>

            <!-- Tool Call Event (Action Group Invocation) -->
            <div v-if="event.type === 'tool_call'" class="tool-call-event">
              <div class="action-group-card">
                <div class="card-header">
                  <div class="action-group-badge">
                    <span class="badge-icon">⚡</span>
                    <span class="badge-text">{{ event.action_group || 'Action Group' }}</span>
                  </div>
                  <div class="execution-status executing">
                    <div class="status-dot"></div>
                    <span>Invoking</span>
                  </div>
                </div>
                <div class="card-body">
                  <div class="lambda-info">
                    <span class="info-label">Function:</span>
                    <code class="info-value">{{ event.function || 'Unknown' }}</code>
                  </div>
                  <div v-if="event.parameters && event.parameters.length > 0" class="parameters-section">
                    <button 
                      @click="toggleParameters(index)" 
                      class="disclosure-button"
                      :class="{ expanded: expandedParams.has(index) }"
                    >
                      <svg class="chevron" width="12" height="12" viewBox="0 0 12 12">
                        <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                      </svg>
                      <span>Parameters ({{ event.parameters.length }})</span>
                    </button>
                    <div v-if="expandedParams.has(index)" class="parameters-content">
                      <div v-for="param in event.parameters" :key="param.name" class="parameter-item">
                        <span class="param-name">{{ param.name }}:</span>
                        <span class="param-value">{{ formatParamValue(param.value) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tool Response Event -->
            <div v-if="event.type === 'tool_response'" class="tool-response-event">
              <div class="response-card">
                <div class="card-header">
                  <div class="execution-status success">
                    <svg class="check-icon" width="14" height="14" viewBox="0 0 14 14">
                      <path d="M11.5 3.5L5.5 9.5L2.5 6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    </svg>
                    <span>Completed</span>
                  </div>
                  <button 
                    @click="toggleResponse(index)" 
                    class="disclosure-button small"
                    :class="{ expanded: expandedResponses.has(index) }"
                  >
                    <svg class="chevron" width="10" height="10" viewBox="0 0 12 12">
                      <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    </svg>
                    <span>View Response</span>
                  </button>
                </div>
                <div v-if="expandedResponses.has(index)" class="response-content">
                  <pre class="response-json">{{ formatResponseContent(event.content) }}</pre>
                </div>
              </div>
            </div>

            <!-- Agent Chunk (Streaming Response) -->
            <div v-if="event.type === 'chunk'" class="chunk-event">
              <div class="chunk-content">{{ event.content }}</div>
            </div>

            <!-- Warning Event -->
            <div v-if="event.type === 'warning'" class="warning-event">
              <div class="warning-banner">
                <span class="warning-icon">⚠️</span>
                <span>{{ event.content }}</span>
              </div>
            </div>

            <!-- Final Response Event (from Bedrock Agent) -->
            <div v-if="event.type === 'final_response'" class="final-response-event">
              <div class="final-response-card">
                <div class="card-header">
                  <div class="execution-status success">
                    <svg class="check-icon" width="14" height="14" viewBox="0 0 14 14">
                      <path d="M11.5 3.5L5.5 9.5L2.5 6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    </svg>
                    <span>Agent Complete</span>
                  </div>
                </div>
                <div class="response-content">
                  <pre class="response-json">{{ formatResponseContent(event.content) }}</pre>
                </div>
              </div>
            </div>

          </div>

          <!-- Completion State -->
          <div v-if="status === 'COMPLETED'" class="completion-state">
            <div class="completion-icon">
              <svg class="checkmark-large" width="48" height="48" viewBox="0 0 48 48">
                <circle cx="24" cy="24" r="22" fill="var(--color-green)" opacity="0.1"/>
                <path d="M14 24L20 30L34 16" stroke="var(--color-green)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
              </svg>
            </div>
            <h3 class="completion-title">Proposal Ready</h3>
            <p class="completion-subtitle">{{ orchestrationSummary }}</p>
            <div class="completion-logo">
              <img src="/logo.png" alt="ScopeSmith" />
            </div>
          </div>

          <!-- Error State -->
          <div v-if="error" class="error-state">
            <div class="error-icon">❌</div>
            <h3 class="error-title">Action Group Failed</h3>
            <p class="error-message">{{ error }}</p>
            <button @click="$emit('retry')" class="retry-button">Try Again</button>
          </div>

        </div>
      </div>

      <!-- Session State Sidebar (Collapsible) -->
      <div class="session-sidebar" :class="{ collapsed: sidebarCollapsed }">
        <button @click="sidebarCollapsed = !sidebarCollapsed" class="sidebar-toggle">
          <svg class="chevron" :class="{ rotated: !sidebarCollapsed }" width="12" height="12" viewBox="0 0 12 12">
            <path d="M4.5 3L7.5 6L4.5 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          <span v-if="!sidebarCollapsed">Session Context</span>
        </button>
        
        <div v-if="!sidebarCollapsed" class="sidebar-content">
          <div class="context-item">
            <div class="context-label">Session ID</div>
            <div class="context-value mono">{{ sessionId.slice(0, 8) }}...</div>
          </div>
          <div v-if="sessionData.client_name" class="context-item">
            <div class="context-label">Client</div>
            <div class="context-value">{{ sessionData.client_name }}</div>
          </div>
          <div v-if="sessionData.project_name" class="context-item">
            <div class="context-label">Project</div>
            <div class="context-value">{{ sessionData.project_name }}</div>
          </div>
          <div v-if="currentStage" class="context-item">
            <div class="context-label">Current Stage</div>
            <div class="context-value">{{ currentStage }}</div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useApi } from '../composables/useApi'

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['complete', 'error', 'retry'])

const { get } = useApi()

// Workflow Steps (8-step process) - aligned with backend Lambda functions
const workflowSteps = ref([
  { label: 'Initiate', status: 'pending' },           // Session created
  { label: 'Analyze', status: 'pending' },            // RequirementsAnalyzer
  { label: 'Calculate', status: 'pending' },          // CostCalculator
  { label: 'Templates', status: 'pending' },          // TemplateRetriever
  { label: 'PowerPoint', status: 'pending' },         // PowerPointGenerator
  { label: 'SOW', status: 'pending' },                // SOWGenerator
  { label: 'Finalize', status: 'pending' },           // Final processing
  { label: 'Complete', status: 'pending' }            // Completion
])

const events = ref([])
const status = ref('INITIATED')
const error = ref(null)
const reasoningContent = ref(null)
const sessionData = ref({})
const currentStage = ref('')

const expandedParams = ref(new Set())
const expandedResponses = ref(new Set())
const sidebarCollapsed = ref(false)

let pollInterval = null
let currentStepIndex = 0

const formattedStatus = computed(() => {
  const statusMap = {
    'INITIATED': 'Starting',
    'AGENT_PROCESSING': 'Processing',
    'COMPLETED': 'Completed',
    'ERROR': 'Failed',
    'CONFIGURATION_ERROR': 'Configuration Error'
  }
  return statusMap[status.value] || status.value
})

const statusBadgeClass = computed(() => {
  const classMap = {
    'INITIATED': 'badge-processing',
    'AGENT_PROCESSING': 'badge-processing',
    'COMPLETED': 'badge-success',
    'ERROR': 'badge-error',
    'CONFIGURATION_ERROR': 'badge-error'
  }
  return classMap[status.value] || 'badge-processing'
})

const orchestrationSummary = computed(() => {
  const actionGroupCount = events.value.filter(e => e.type === 'tool_call').length
  const stepsCompleted = workflowSteps.value.filter(s => s.status === 'completed').length
  return `${actionGroupCount} action groups invoked, ${stepsCompleted} steps completed`
})

const getStepClass = (index) => {
  const step = workflowSteps.value[index]
  return {
    'step-completed': step.status === 'completed',
    'step-active': step.status === 'active',
    'step-pending': step.status === 'pending'
  }
}

const updateWorkflowProgress = () => {
  // Map action group names to workflow steps - synchronized with Lambda function names
  const stageToStepMap = {
    'RequirementsAnalyzer': 1,  // Match actual Lambda function name
    'CostCalculator': 2,         // Match actual Lambda function name
    'TemplateRetriever': 3,      // Match actual Lambda function name
    'PowerPointGenerator': 4,    // Match actual Lambda function name
    'SOWGenerator': 5            // Match actual Lambda function name
  }

  // Mark initiate as completed when first event arrives
  if (events.value.length > 0 && workflowSteps.value[0].status === 'pending') {
    workflowSteps.value[0].status = 'completed'
    currentStepIndex = 0
  }

  // Update based on tool calls - match with actual action group names from Lambda
  events.value.forEach(event => {
    if (event.type === 'tool_call' && event.action_group) {
      const stepIndex = stageToStepMap[event.action_group]
      if (stepIndex !== undefined) {
        // Mark this step as active
        if (workflowSteps.value[stepIndex].status === 'pending') {
          workflowSteps.value[stepIndex].status = 'active'
          currentStepIndex = stepIndex
        }
      }
    }
    
    // Mark step as completed when we receive the response
    if (event.type === 'tool_response') {
      // Find the most recent tool_call to determine which step completed
      const recentToolCalls = events.value.filter(e => e.type === 'tool_call').reverse()
      if (recentToolCalls.length > 0) {
        const lastCall = recentToolCalls[0]
        const stepIndex = stageToStepMap[lastCall.action_group]
        if (stepIndex !== undefined && workflowSteps.value[stepIndex].status === 'active') {
          workflowSteps.value[stepIndex].status = 'completed'
          // Mark next step as active if available
          if (stepIndex + 1 < workflowSteps.value.length - 1) {
            workflowSteps.value[stepIndex + 1].status = 'pending'
          }
        }
      }
    }
  })

  // Handle completion - mark all remaining steps as completed
  if (status.value === 'COMPLETED') {
    workflowSteps.value.forEach((step, index) => {
      if (index < workflowSteps.value.length) {
        step.status = 'completed'
      }
    })
  }

  // Handle error states
  if (status.value === 'ERROR' || status.value === 'CONFIGURATION_ERROR') {
    // Mark current active step as pending (failed state)
    workflowSteps.value.forEach((step, index) => {
      if (step.status === 'active') {
        step.status = 'pending'
      }
    })
  }
}

const toggleParameters = (index) => {
  if (expandedParams.value.has(index)) {
    expandedParams.value.delete(index)
  } else {
    expandedParams.value.add(index)
  }
}

const toggleResponse = (index) => {
  if (expandedResponses.value.has(index)) {
    expandedResponses.value.delete(index)
  } else {
    expandedResponses.value.add(index)
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatParamValue = (value) => {
  if (typeof value === 'string' && value.length > 100) {
    return value.slice(0, 100) + '...'
  }
  return value
}

const formatResponseContent = (content) => {
  try {
    const parsed = JSON.parse(content)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return content
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (reasoningContent.value) {
    reasoningContent.value.scrollTo({
      top: reasoningContent.value.scrollHeight,
      behavior: 'smooth'
    })
  }
}

const fetchAgentStatus = async () => {
  try {
    const data = await get(`/api/agent-status/${props.sessionId}`)
    
    // Update status - sync with backend status values from session_manager/app.py
    status.value = data.status || 'AGENT_PROCESSING'
    
    // Update session data
    sessionData.value = {
      client_name: data.client_name,
      project_name: data.project_name,
      industry: data.industry
    }
    
    currentStage.value = data.current_stage || ''
    
    // Parse and update agent events - handle JSON string from DynamoDB
    if (data.agent_events) {
      try {
        const parsedEvents = typeof data.agent_events === 'string' 
          ? JSON.parse(data.agent_events) 
          : data.agent_events
        
        // Only update if we have new events
        if (Array.isArray(parsedEvents) && parsedEvents.length > events.value.length) {
          events.value = parsedEvents
          updateWorkflowProgress()
          scrollToBottom()
        }
      } catch (e) {
        console.error('Error parsing agent events:', e)
        // Fallback: if parsing fails, keep existing events
      }
    }
    
    // Check for completion or error states
    if (status.value === 'COMPLETED') {
      clearInterval(pollInterval)
      updateWorkflowProgress() // Final update
      emit('complete', data)
    } else if (status.value === 'ERROR' || status.value === 'CONFIGURATION_ERROR') {
      clearInterval(pollInterval)
      error.value = data.error_message || 'An error occurred during agent execution'
      emit('error', error.value)
    }
    
  } catch (err) {
    console.error('Error fetching agent status:', err)
    // Don't stop polling on network errors - agent might still be working
    // Only stop if we get a 404 (session not found)
    if (err.response?.status === 404) {
      clearInterval(pollInterval)
      error.value = 'Session not found'
      emit('error', error.value)
    }
  }
}

watch(events, () => {
  updateWorkflowProgress()
}, { deep: true })

onMounted(() => {
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
/* Main Container */
.agent-stream-viewer {
  width: 100%;
  min-height: calc(100vh - 52px);
  padding: var(--spacing-lg);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.live-activity-container {
  width: 100%;
  max-width: 1000px;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  position: relative;
}

/* 8-Step Progress Timeline */
.progress-timeline {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--spacing-xl) var(--spacing-lg);
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: var(--radius-lg);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  position: relative;
  overflow-x: auto;
}

.timeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
  min-width: 80px;
  position: relative;
}

.step-checkpoint {
  z-index: 2;
}

.checkpoint-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-separator);
  background: var(--color-background);
  transition: all var(--transition-base);
}

.step-pending .checkpoint-circle {
  border-color: var(--color-separator);
  background: var(--color-background);
}

.step-active .checkpoint-circle {
  border-color: var(--color-blue);
  background: var(--color-blue);
  animation: pulse-ring 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.step-completed .checkpoint-circle {
  border-color: var(--color-blue);
  background: var(--color-blue);
  color: white;
}

.checkmark {
  color: white;
}

.spinner-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  animation: pulse-scale 1.5s ease-in-out infinite;
}

@keyframes pulse-ring {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(0, 122, 255, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(0, 122, 255, 0);
  }
}

@keyframes pulse-scale {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(0.8);
    opacity: 0.7;
  }
}

.step-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-secondary-label);
  text-align: center;
  white-space: nowrap;
}

.step-active .step-label {
  color: var(--color-blue);
  font-weight: 600;
}

.step-completed .step-label {
  color: var(--color-label);
}

.step-connector {
  position: absolute;
  top: 20px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: var(--color-separator);
  z-index: 1;
}

.step-completed .step-connector {
  background: var(--color-blue);
}

/* Reasoning Panel */
.reasoning-panel {
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: var(--radius-lg);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-bottom: 0.5px solid var(--color-separator);
}

.header-icon {
  font-size: 24px;
}

.panel-header h3 {
  flex: 1;
  font-size: 20px;
  font-weight: 600;
  color: var(--color-label);
  letter-spacing: -0.4px;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-processing {
  background: rgba(0, 122, 255, 0.1);
  color: var(--color-blue);
}

.badge-success {
  background: rgba(52, 199, 89, 0.1);
  color: var(--color-green);
}

.badge-error {
  background: rgba(255, 59, 48, 0.1);
  color: var(--color-red);
}

.reasoning-content {
  max-height: 600px;
  overflow-y: auto;
  padding: var(--spacing-lg);
  scroll-behavior: smooth;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  text-align: center;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 3px solid var(--color-separator);
  border-top-color: var(--color-blue);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-lg);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 17px;
  font-weight: 500;
  color: var(--color-label);
  margin-bottom: var(--spacing-xs);
}

.loading-subtext {
  font-size: 14px;
  color: var(--color-secondary-label);
}

/* Event Items */
.event-item {
  margin-bottom: var(--spacing-md);
  animation: slideIn var(--transition-base);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.event-header-small {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
  font-size: 13px;
  color: var(--color-secondary-label);
}

.event-icon {
  font-size: 16px;
}

.event-label {
  flex: 1;
  font-weight: 500;
}

.event-time {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--color-tertiary-label);
}

/* Reasoning Event */
.reasoning-event {
  padding: var(--spacing-md);
  background: rgba(0, 122, 255, 0.05);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-blue);
}

.reasoning-text {
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-label);
  font-style: italic;
}

/* Action Group Card (Tool Call) */
.tool-call-event {
  padding: var(--spacing-md);
  background: rgba(52, 199, 89, 0.05);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-green);
}

.action-group-card {
  background: var(--color-background);
  border-radius: var(--radius-sm);
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--color-tertiary-background);
  border-bottom: 0.5px solid var(--color-separator);
}

.action-group-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: 4px 10px;
  background: var(--color-green);
  color: white;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.badge-icon {
  font-size: 14px;
}

.execution-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
}

.execution-status.executing {
  color: var(--color-blue);
}

.execution-status.success {
  color: var(--color-green);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.check-icon {
  color: currentColor;
}

.card-body {
  padding: var(--spacing-md);
}

.lambda-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.info-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-secondary-label);
}

.info-value {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 4px 8px;
  background: var(--color-secondary-background);
  border-radius: 4px;
  color: var(--color-label);
}

.disclosure-button {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: transparent;
  border: 1px solid var(--color-separator);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-label);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.disclosure-button:hover {
  background: var(--color-separator);
}

.disclosure-button.small {
  padding: 4px 8px;
  font-size: 12px;
}

.chevron {
  transition: transform var(--transition-fast);
}

.disclosure-button.expanded .chevron {
  transform: rotate(180deg);
}

.parameters-content {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-md);
  background: var(--color-secondary-background);
  border-radius: var(--radius-sm);
}

.parameter-item {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) 0;
  font-size: 13px;
}

.param-name {
  font-weight: 600;
  color: var(--color-label);
}

.param-value {
  color: var(--color-secondary-label);
  font-family: var(--font-mono);
}

/* Tool Response */
.tool-response-event {
  padding: var(--spacing-md);
  background: rgba(255, 204, 0, 0.05);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-yellow);
}

.response-card {
  background: var(--color-background);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.response-content {
  padding: var(--spacing-md);
  background: var(--color-secondary-background);
}

.response-json {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-label);
  overflow-x: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Chunk Event */
.chunk-event {
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(175, 82, 222, 0.05);
  border-radius: var(--radius-sm);
  border-left: 2px solid var(--color-purple);
}

.chunk-content {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-label);
}

/* Warning Event */
.warning-event {
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.warning-banner {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background: rgba(255, 149, 0, 0.1);
  border: 1px solid var(--color-orange);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--color-label);
}

.warning-icon {
  font-size: 18px;
}

/* Completion State */
.completion-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--spacing-2xl);
  margin-top: var(--spacing-xl);
  animation: slideIn var(--transition-slow);
}

.completion-icon {
  margin-bottom: var(--spacing-lg);
  animation: scaleIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes scaleIn {
  from {
    transform: scale(0);
  }
  to {
    transform: scale(1);
  }
}

.checkmark-large {
  filter: drop-shadow(0 4px 12px rgba(52, 199, 89, 0.2));
}

.completion-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-label);
  margin-bottom: var(--spacing-xs);
  letter-spacing: -0.5px;
}

.completion-subtitle {
  font-size: 15px;
  color: var(--color-secondary-label);
  margin-bottom: var (--spacing-lg);
}

.completion-logo {
  margin-top: var(--spacing-md);
  opacity: 0.6;
}

.completion-logo img {
  height: 32px;
  width: auto;
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--spacing-2xl);
  background: rgba(255, 59, 48, 0.05);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-red);
}

.error-icon {
  font-size: 48px;
  margin-bottom: var(--spacing-md);
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-red);
  margin-bottom: var(--spacing-sm);
}

.error-message {
  font-size: 14px;
  color: var(--color-secondary-label);
  margin-bottom: var(--spacing-lg);
  max-width: 400px;
}

.retry-button {
  padding: 10px 20px;
  background: var(--color-red);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.retry-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 59, 48, 0.3);
}

.retry-button:active {
  transform: translateY(0);
}

/* Session Sidebar */
.session-sidebar {
  position: fixed;
  right: 0;
  top: 52px;
  height: calc(100vh - 52px);
  width: 280px;
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-left: 0.5px solid var(--glass-border);
  box-shadow: -4px 0 16px rgba(0, 0, 0, 0.08);
  transition: transform var(--transition-base);
  z-index: 100;
}

.session-sidebar.collapsed {
  transform: translateX(calc(100% - 40px));
}

.sidebar-toggle {
  position: absolute;
  left: -40px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 0.5px solid var(--glass-border);
  border-right: none;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.sidebar-toggle:hover {
  background: var(--color-separator);
}

.sidebar-toggle .chevron {
  transition: transform var(--transition-base);
}

.sidebar-toggle .chevron.rotated {
  transform: rotate(180deg);
}

.sidebar-toggle span {
  writing-mode: vertical-rl;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-secondary-label);
}

.sidebar-content {
  padding: var(--spacing-lg);
  overflow-y: auto;
  height: 100%;
}

.context-item {
  margin-bottom: var(--spacing-lg);
}

.context-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-tertiary-label);
  margin-bottom: var(--spacing-xs);
}

.context-value {
  font-size: 14px;
  color: var(--color-label);
  word-break: break-word;
}

.context-value.mono {
  font-family: var(--font-mono);
  font-size: 13px;
}

/* Responsive Design */
@media (max-width: 1280px) {
  .session-sidebar {
    transform: translateX(100%);
  }
  
  .session-sidebar.collapsed {
    transform: translateX(100%);
  }
  
  .sidebar-toggle {
    display: none;
  }
}

@media (max-width: 768px) {
  .agent-stream-viewer {
    padding: var(--spacing-md);
  }
  
  .progress-timeline {
    padding: var(--spacing-lg) var(--spacing-sm);
  }
  
  .timeline-step {
    min-width: 60px;
  }
  
  .checkpoint-circle {
    width: 32px;
    height: 32px;
  }
  
  .step-label {
    font-size: 10px;
  }
  
  .reasoning-content {
    max-height: 500px;
  }
}
</style>
