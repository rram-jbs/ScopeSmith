<template>
  <div class="assessment-view">
    <!-- Header -->
    <div class="header">
      <h1>🚀 ScopeSmith Proposal Generator</h1>
      <p class="subtitle">Powered by Amazon Nova Pro AI</p>
    </div>

    <!-- Form View -->
    <div v-if="currentView === 'form'" class="form-container">
      <div class="form-card">
        <h2>📝 Project Assessment</h2>
        <p class="form-description">
          Paste your client meeting notes below. Our AI will analyze requirements, 
          calculate costs, and generate a complete proposal with PowerPoint and SOW documents.
        </p>

        <form @submit.prevent="submitAssessment">
          <div class="form-group">
            <label for="requirements">Client Meeting Notes</label>
            <textarea
              id="requirements"
              v-model="formData.requirements"
              placeholder="Example:&#10;&#10;Client: TechCorp Inc&#10;Project: Modernize inventory system&#10;&#10;Requirements:&#10;- Migrate to microservices architecture&#10;- Real-time inventory tracking&#10;- Mobile app for warehouse staff&#10;- Integration with existing ERP&#10;- Support 10,000+ concurrent users&#10;&#10;Timeline: 9-12 months&#10;Budget: Flexible"
              rows="15"
              required
            ></textarea>
          </div>

          <div class="form-group">
            <label for="clientName">Client Name (Optional)</label>
            <input
              type="text"
              id="clientName"
              v-model="formData.clientName"
              placeholder="e.g., TechCorp Inc"
            />
          </div>

          <div class="form-group">
            <label for="projectType">Project Type (Optional)</label>
            <select id="projectType" v-model="formData.projectType">
              <option value="">Auto-detect</option>
              <option value="web-application">Web Application</option>
              <option value="mobile-app">Mobile App</option>
              <option value="enterprise-software">Enterprise Software</option>
              <option value="cloud-migration">Cloud Migration</option>
              <option value="data-analytics">Data Analytics</option>
            </select>
          </div>

          <button 
            type="submit" 
            class="submit-button"
            :disabled="isSubmitting"
          >
            <span v-if="!isSubmitting">Generate Proposal 🎯</span>
            <span v-else>Creating Session...</span>
          </button>
        </form>

        <div v-if="submitError" class="error-message">
          {{ submitError }}
        </div>
      </div>
    </div>

    <!-- Processing View with Agent Stream -->
    <div v-if="currentView === 'processing'" class="processing-container">
      <AgentStreamViewer 
        :sessionId="sessionId"
        @complete="handleAgentComplete"
        @error="handleAgentError"
      />
    </div>

    <!-- Results View -->
    <div v-if="currentView === 'results'" class="results-container">
      <div class="results-card">
        <div class="results-header">
          <h2>✅ Proposal Ready!</h2>
          <p>Your proposal documents have been generated successfully.</p>
        </div>

        <div class="documents-grid">
          <div v-if="documents.powerpoint" class="document-card">
            <div class="document-icon">📊</div>
            <h3>PowerPoint Presentation</h3>
            <p>Professional presentation with project overview, costs, and timeline</p>
            <a :href="documents.powerpoint" class="download-button" download>
              Download Presentation
            </a>
          </div>

          <div v-if="documents.sow" class="document-card">
            <div class="document-icon">📄</div>
            <h3>Statement of Work</h3>
            <p>Detailed SOW document with deliverables, milestones, and terms</p>
            <a :href="documents.sow" class="download-button" download>
              Download SOW
            </a>
          </div>
        </div>

        <button @click="startNew" class="new-assessment-button">
          Create New Proposal
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AgentStreamViewer from '../components/AgentStreamViewer.vue'

const currentView = ref('form') // 'form', 'processing', 'results'
const sessionId = ref(null)
const isSubmitting = ref(false)
const submitError = ref(null)

const formData = ref({
  requirements: '',
  clientName: '',
  projectType: ''
})

const documents = ref({
  powerpoint: null,
  sow: null
})

const submitAssessment = async () => {
  isSubmitting.value = true
  submitError.value = null

  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3000'
    
    console.log('Submitting to:', `${apiUrl}/api/assessments`)
    
    const response = await fetch(`${apiUrl}/api/assessments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        requirements: formData.value.requirements,
        client_name: formData.value.clientName,
        project_type: formData.value.projectType
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}`)
    }

    const data = await response.json()
    console.log('Assessment created:', data)

    sessionId.value = data.session_id

    // Switch to processing view
    currentView.value = 'processing'

  } catch (error) {
    console.error('Submission error:', error)
    submitError.value = `Failed to submit: ${error.message}`
  } finally {
    isSubmitting.value = false
  }
}

const handleAgentComplete = async (data) => {
  console.log('Agent completed:', data)
  
  // Fetch document URLs
  try {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:3000'
    const response = await fetch(`${apiUrl}/api/results/${sessionId.value}`)
    
    if (response.ok) {
      const results = await response.json()
      documents.value = {
        powerpoint: results.powerpoint_url,
        sow: results.sow_url
      }
    }
  } catch (error) {
    console.error('Error fetching documents:', error)
  }
  
  // Switch to results view
  currentView.value = 'results'
}

const handleAgentError = (error) => {
  console.error('Agent error:', error)
  submitError.value = error
  currentView.value = 'form'
}

const startNew = () => {
  currentView.value = 'form'
  sessionId.value = null
  formData.value = {
    requirements: '',
    clientName: '',
    projectType: ''
  }
  documents.value = {
    powerpoint: null,
    sow: null
  }
}
</script>

<style scoped>
.assessment-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.header {
  text-align: center;
  color: white;
  margin-bottom: 3rem;
}

.header h1 {
  font-size: 3rem;
  margin-bottom: 0.5rem;
  font-weight: 700;
}

.subtitle {
  font-size: 1.2rem;
  opacity: 0.9;
}

.form-container, .processing-container, .results-container {
  max-width: 800px;
  margin: 0 auto;
}

.form-card, .results-card {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.form-card h2 {
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.form-description {
  color: #6b7280;
  margin-bottom: 2rem;
  line-height: 1.6;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #374151;
  font-weight: 600;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  transition: border-color 0.2s;
}

.form-group textarea {
  resize: vertical;
  font-family: 'Courier New', monospace;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.submit-button {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.submit-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  margin-top: 1rem;
  padding: 1rem;
  background: #fee2e2;
  border: 1px solid #ef4444;
  border-radius: 8px;
  color: #991b1b;
}

.results-header {
  text-align: center;
  margin-bottom: 2rem;
}

.results-header h2 {
  color: #059669;
  margin-bottom: 0.5rem;
}

.results-header p {
  color: #6b7280;
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.document-card {
  padding: 2rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  text-align: center;
  transition: all 0.3s;
}

.document-card:hover {
  border-color: #667eea;
  box-shadow: 0 10px 20px rgba(102, 126, 234, 0.2);
  transform: translateY(-5px);
}

.document-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.document-card h3 {
  color: #1f2937;
  margin-bottom: 0.5rem;
}

.document-card p {
  color: #6b7280;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.download-button {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background: #667eea;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s;
}

.download-button:hover {
  background: #5a67d8;
  transform: scale(1.05);
}

.new-assessment-button {
  width: 100%;
  padding: 1rem;
  background: #f3f4f6;
  color: #374151;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.new-assessment-button:hover {
  background: #e5e7eb;
  border-color: #d1d5db;
}
</style>