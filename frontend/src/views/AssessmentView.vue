<template>
  <div class="assessment-view">
    <div class="container">
      <header class="header">
        <h1>ScopeSmith</h1>
        <p class="subtitle">AI-Powered Proposal Generator</p>
      </header>

      <!-- Step 1: Form -->
      <div v-if="currentStep === 'form'" class="form-section">
        <div class="card">
          <h2>Project Information</h2>
          <form @submit.prevent="submitAssessment">
            <div class="form-group">
              <label>Client Name *</label>
              <input v-model="formData.client_name" type="text" required placeholder="Enter client name" />
            </div>

            <div class="form-group">
              <label>Project Name</label>
              <input v-model="formData.project_name" type="text" placeholder="Enter project name" />
            </div>

            <div class="form-group">
              <label>Industry</label>
              <input v-model="formData.industry" type="text" placeholder="e.g., Retail, Healthcare, Finance" />
            </div>

            <div class="form-group">
              <label>Project Duration</label>
              <input v-model="formData.duration" type="text" placeholder="e.g., 6 months, 12+ months" />
            </div>

            <div class="form-group">
              <label>Team Size</label>
              <input v-model="formData.team_size" type="number" min="1" placeholder="Number of team members" />
            </div>

            <div class="form-group">
              <label>Requirements / Meeting Notes *</label>
              <textarea 
                v-model="formData.requirements" 
                rows="10" 
                required 
                placeholder="Paste your client meeting notes or project requirements here..."
              ></textarea>
            </div>

            <button type="submit" class="btn-primary" :disabled="isSubmitting">
              {{ isSubmitting ? 'Processing...' : 'Generate Proposal' }}
            </button>
          </form>
        </div>
      </div>

      <!-- Step 2: Processing with Agent Stream -->
      <div v-if="currentStep === 'processing'" class="processing-section">
        <AgentStreamViewer 
          :session-id="sessionId" 
          @complete="handleAgentComplete"
          @error="handleAgentError"
        />
      </div>

      <!-- Step 3: Results -->
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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AgentStreamViewer from '../components/AgentStreamViewer.vue'

const currentStep = ref('form') // 'form', 'processing', 'results'
const sessionId = ref(null)
const powerpointUrl = ref(null)
const sowUrl = ref(null)
const isSubmitting = ref(false)

const formData = ref({
  client_name: '',
  project_name: '',
  industry: '',
  duration: '',
  team_size: 1,
  requirements: ''
})

const submitAssessment = async () => {
  isSubmitting.value = true
  
  try {
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/submit-assessment`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData.value)
    })
    
    if (!response.ok) {
      throw new Error('Failed to submit assessment')
    }
    
    const data = await response.json()
    sessionId.value = data.session_id
    currentStep.value = 'processing' // Switch to processing view
  } catch (error) {
    console.error('Error submitting assessment:', error)
    alert('Failed to submit assessment. Please try again.')
  } finally {
    isSubmitting.value = false
  }
}

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
    alert('Failed to fetch results. Please check the logs.')
  }
}

const handleAgentError = (errorMessage) => {
  console.error('Agent error:', errorMessage)
  alert(`Error: ${errorMessage}`)
  currentStep.value = 'form'
  isSubmitting.value = false
}

const startNew = () => {
  sessionId.value = null
  powerpointUrl.value = null
  sowUrl.value = null
  currentStep.value = 'form'
  isSubmitting.value = false
  
  // Reset form
  formData.value = {
    client_name: '',
    project_name: '',
    industry: '',
    duration: '',
    team_size: 1,
    requirements: ''
  }
}
</script>

<style scoped>
.assessment-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem 1rem;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
}

.header {
  text-align: center;
  color: white;
  margin-bottom: 2rem;
}

.header h1 {
  font-size: 3rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.subtitle {
  font-size: 1.25rem;
  opacity: 0.9;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.card h2 {
  margin-bottom: 1.5rem;
  color: #333;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #555;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.btn-primary {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.processing-section {
  margin-top: 2rem;
}

.results-section {
  margin-top: 2rem;
}

.results-card {
  background: white;
  padding: 3rem;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
  text-align: center;
}

.results-card h2 {
  color: #10b981;
  margin-bottom: 1rem;
  font-size: 2rem;
}

.results-card p {
  color: #6b7280;
  margin-bottom: 2rem;
  font-size: 1.1rem;
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
  font-size: 1.1rem;
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
  font-size: 1rem;
  transition: background 0.3s;
}

.btn-secondary:hover {
  background: #4b5563;
}
</style>