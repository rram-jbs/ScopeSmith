<template>
  <div class="assessment-view">
    <!-- ...existing header and form sections... -->

    <!-- Show AgentStreamViewer when processing -->
    <div v-if="sessionId && currentStep === 'processing'" class="processing-section">
      <AgentStreamViewer 
        :session-id="sessionId" 
        @complete="handleAgentComplete"
        @error="handleAgentError"
      />
    </div>

    <!-- Show results after completion -->
    <div v-if="currentStep === 'results'" class="results-section">
      <div class="results-card">
        <h2>✅ Proposal Generated Successfully!</h2>
        <p>Your project proposal documents are ready for download.</p>
        
        <div class="download-buttons">
          <a v-if="powerpointUrl" :href="powerpointUrl" class="download-btn" download>
            📊 Download PowerPoint Presentation
          </a>
          <a v-if="sowUrl" :href="sowUrl" class="download-btn" download>
            📄 Download Statement of Work
          </a>
        </div>

        <button @click="startNew" class="btn-secondary">Create Another Proposal</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AgentStreamViewer from '../components/AgentStreamViewer.vue'

// ...existing reactive variables...
const sessionId = ref(null)
const currentStep = ref('form') // 'form', 'processing', 'results'
const powerpointUrl = ref(null)
const sowUrl = ref(null)

const handleAgentComplete = async (data) => {
  console.log('Agent completed:', data)
  
  // Fetch final results
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/results/${sessionId.value}`)
    const results = await response.json()
    
    powerpointUrl.value = results.powerpoint_url
    sowUrl.value = results.sow_url
    currentStep.value = 'results'
  } catch (error) {
    console.error('Error fetching results:', error)
  }
}

const handleAgentError = (errorMessage) => {
  console.error('Agent error:', errorMessage)
  alert(`Error: ${errorMessage}`)
  currentStep.value = 'form'
}

const startNew = () => {
  sessionId.value = null
  powerpointUrl.value = null
  sowUrl.value = null
  currentStep.value = 'form'
  // Reset form fields if needed
}

const submitAssessment = async () => {
  // ...existing submission code...
  
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/submit-assessment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  })
  
  const data = await response.json()
  sessionId.value = data.session_id
  currentStep.value = 'processing' // Switch to processing view with agent stream
}
</script>

<style scoped>
.processing-section {
  margin-top: 2rem;
}

.results-section {
  margin-top: 2rem;
}

.results-card {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.results-card h2 {
  color: #10b981;
  margin-bottom: 1rem;
}

.download-buttons {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 2rem 0;
}

.download-btn {
  display: inline-block;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: transform 0.2s;
}

.download-btn:hover {
  transform: translateY(-2px);
}

.btn-secondary {
  margin-top: 1rem;
  padding: 0.75rem 1.5rem;
  background: #6b7280;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
</style>