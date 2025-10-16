<template>
  <div class="assessment-view">
    
    <!-- Form View (Compact State) -->
    <div v-if="currentView === 'form'" class="form-view">
      <div class="welcome-section">
        <div class="logo-hero">
          <img src="/logo.png" alt="ScopeSmith" class="hero-logo" />
        </div>
        <h1 class="hero-title">Generate Professional Proposals</h1>
        <p class="hero-subtitle">AI-powered proposal generation using Amazon Bedrock Agents</p>
      </div>

      <div class="upload-card">
        <div class="card-header">
          <h2>Project Requirements</h2>
          <p class="card-subtitle">Paste your client meeting notes to begin</p>
        </div>

        <form @submit.prevent="submitAssessment" class="assessment-form">
          
          <!-- Drag-and-Drop Zone Style Textarea -->
          <div class="form-section">
            <label for="requirements" class="form-label">Meeting Notes</label>
            <div 
              class="textarea-container"
              :class="{ focused: requirementsFocused }"
            >
              <textarea
                id="requirements"
                v-model="formData.requirements"
                @focus="requirementsFocused = true"
                @blur="requirementsFocused = false"
                placeholder="Example:&#10;&#10;Client: TechCorp Inc&#10;Project: Modernize inventory system&#10;&#10;Requirements:&#10;• Microservices architecture&#10;• Real-time inventory tracking&#10;• Mobile app for warehouse staff&#10;• ERP system integration&#10;• Support 10,000+ concurrent users&#10;&#10;Timeline: 9-12 months&#10;Budget: Flexible"
                required
              ></textarea>
              <div class="textarea-hint">
                <span class="hint-icon">💡</span>
                <span>Include client name, project details, requirements, timeline, and budget</span>
              </div>
            </div>
          </div>

          <!-- Optional Fields -->
          <div class="form-row">
            <div class="form-section">
              <label for="clientName" class="form-label">Client Name <span class="optional">(Optional)</span></label>
              <input
                type="text"
                id="clientName"
                v-model="formData.client_name"
                class="form-input"
                placeholder="e.g., TechCorp Inc"
              />
            </div>

            <div class="form-section">
              <label for="projectName" class="form-label">Project Name <span class="optional">(Optional)</span></label>
              <input
                type="text"
                id="projectName"
                v-model="formData.project_name"
                class="form-input"
                placeholder="e.g., Inventory System Modernization"
              />
            </div>
          </div>

          <div class="form-row">
            <div class="form-section">
              <label for="industry" class="form-label">Industry <span class="optional">(Optional)</span></label>
              <select
                id="industry"
                v-model="formData.industry"
                class="form-select"
              >
                <option value="">Auto-detect from notes</option>
                <option value="retail">Retail</option>
                <option value="healthcare">Healthcare</option>
                <option value="finance">Finance</option>
                <option value="manufacturing">Manufacturing</option>
                <option value="technology">Technology</option>
                <option value="education">Education</option>
                <option value="government">Government</option>
              </select>
            </div>

            <div class="form-section">
              <label for="duration" class="form-label">Duration <span class="optional">(Optional)</span></label>
              <select
                id="duration"
                v-model="formData.duration"
                class="form-select"
              >
                <option value="">Auto-detect from notes</option>
                <option value="1-3 months">1-3 months</option>
                <option value="3-6 months">3-6 months</option>
                <option value="6-12 months">6-12 months</option>
                <option value="12+ months">12+ months</option>
              </select>
            </div>
          </div>

          <!-- Generate Button -->
          <button 
            type="submit" 
            class="generate-button"
            :class="{ loading: isSubmitting }"
            :disabled="isSubmitting || !formData.requirements"
          >
            <span v-if="!isSubmitting" class="button-content">
              <svg class="button-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M10 3v14M17 10H3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              Generate Proposal
            </span>
            <span v-else class="button-content">
              <div class="button-spinner"></div>
              Creating Session...
            </span>
          </button>

          <div class="time-estimate">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.5"/>
              <path d="M8 5v3l2 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
            <span>Estimated time: &lt; 3 minutes</span>
          </div>

        </form>

        <div v-if="submitError" class="error-alert">
          <div class="alert-icon">⚠️</div>
          <div class="alert-content">
            <div class="alert-title">Unable to Start Generation</div>
            <div class="alert-message">{{ submitError }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Processing View (Expanded State) -->
    <transition name="modal">
      <div v-if="currentView === 'processing'" class="processing-view">
        <div class="processing-backdrop" @click="handleBackdropClick"></div>
        <div class="processing-content">
          <AgentStreamViewer 
            :sessionId="sessionId"
            @complete="handleAgentComplete"
            @error="handleAgentError"
            @retry="handleRetry"
          />
        </div>
      </div>
    </transition>

    <!-- Results View (Completion Screen) -->
    <transition name="fade">
      <div v-if="currentView === 'results'" class="results-view">
        <div class="results-container">
          
          <div class="results-hero">
            <div class="success-animation">
              <svg class="success-checkmark" width="80" height="80" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="36" fill="var(--color-green)" opacity="0.1" class="circle-bg"/>
                <circle cx="40" cy="40" r="36" stroke="var(--color-green)" stroke-width="3" fill="none" class="circle-stroke"/>
                <path d="M25 40L35 50L55 30" stroke="var(--color-green)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" fill="none" class="checkmark-path"/>
              </svg>
            </div>
            <h1 class="results-title">Proposal Ready</h1>
            <p class="results-subtitle">Your documents have been generated successfully</p>
          </div>

          <div class="documents-grid">
            
            <!-- PowerPoint Card -->
            <div v-if="documents.powerpoint_url" class="document-card powerpoint">
              <div class="document-icon-container">
                <div class="document-icon">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <rect x="8" y="6" width="32" height="36" rx="4" fill="#D35230"/>
                    <path d="M18 18h12M18 24h12M18 30h8" stroke="white" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </div>
              </div>
              <div class="document-info">
                <h3 class="document-title">Presentation</h3>
                <p class="document-description">Professional PowerPoint with project overview, costs, timeline, and deliverables</p>
              </div>
              <a 
                :href="documents.powerpoint_url" 
                class="download-button primary"
                download
              >
                <svg class="download-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M9 3v8m0 0L6 8m3 3l3-3M3 13v1a2 2 0 002 2h8a2 2 0 002-2v-1" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                Download Presentation
              </a>
            </div>

            <!-- SOW Card -->
            <div v-if="documents.sow_url" class="document-card sow">
              <div class="document-icon-container">
                <div class="document-icon">
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                    <rect x="8" y="6" width="32" height="36" rx="4" fill="var(--color-blue)"/>
                    <path d="M16 14h16M16 20h16M16 26h12M16 32h8" stroke="white" stroke-width="2" stroke-linecap="round"/>
                  </svg>
                </div>
              </div>
              <div class="document-info">
                <h3 class="document-title">Statement of Work</h3>
                <p class="document-description">Detailed SOW document with scope, deliverables, milestones, and terms</p>
              </div>
              <a 
                :href="documents.sow_url" 
                class="download-button primary"
                download
              >
                <svg class="download-icon" width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M9 3v8m0 0L6 8m3 3l3-3M3 13v1a2 2 0 002 2h8a2 2 0 002-2v-1" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                Download SOW
              </a>
            </div>

          </div>

          <!-- Cost Summary (if available) -->
          <div v-if="documents.cost_data && Object.keys(documents.cost_data).length > 0" class="cost-summary">
            <h3 class="summary-title">Cost Summary</h3>
            <div class="summary-content">
              <pre class="cost-json">{{ JSON.stringify(documents.cost_data, null, 2) }}</pre>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="results-actions">
            <button @click="startNew" class="action-button primary">
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M9 3v12M3 9h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
              Create New Proposal
            </button>
          </div>

          <!-- Branding Footer -->
          <div class="results-footer">
            <img src="/logo.png" alt="ScopeSmith" class="footer-logo" />
            <p class="footer-text">Powered by Amazon Bedrock Agents</p>
          </div>

        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useApi } from '../composables/useApi'
import AgentStreamViewer from '../components/AgentStreamViewer.vue'

const { post, get } = useApi()

const currentView = ref('form') // 'form', 'processing', 'results'
const sessionId = ref(null)
const isSubmitting = ref(false)
const submitError = ref(null)
const requirementsFocused = ref(false)

const formData = ref({
  requirements: '',
  client_name: '',
  project_name: '',
  industry: '',
  duration: '',
  team_size: 5
})

const documents = ref({
  powerpoint_url: null,
  sow_url: null,
  cost_data: {}
})

const submitAssessment = async () => {
  isSubmitting.value = true
  submitError.value = null

  try {
    const response = await post('/api/submit-assessment', {
      requirements: formData.value.requirements,
      client_name: formData.value.client_name,
      project_name: formData.value.project_name,
      industry: formData.value.industry,
      duration: formData.value.duration,
      team_size: formData.value.team_size
    })

    sessionId.value = response.session_id
    currentView.value = 'processing'

  } catch (error) {
    console.error('Submission error:', error)
    submitError.value = error.message || 'Failed to start proposal generation'
  } finally {
    isSubmitting.value = false
  }
}

const handleAgentComplete = async (data) => {
  console.log('Agent completed:', data)
  
  // Validate that documents are actually available before showing success
  if (!data.document_urls || data.document_urls.length === 0) {
    console.error('Agent completed but no documents were generated')
    submitError.value = 'Workflow completed but no documents were generated. Please check the logs and try again.'
    currentView.value = 'form'
    return
  }
  
  // Fetch document URLs
  try {
    const results = await get(`/api/results/${sessionId.value}`)
    
    // Double-check that we have actual document URLs
    if (!results.powerpoint_url && !results.sow_url) {
      console.error('No document URLs available in results')
      submitError.value = 'Documents were not generated successfully. Please try again.'
      currentView.value = 'form'
      return
    }
    
    documents.value = {
      powerpoint_url: results.powerpoint_url,
      sow_url: results.sow_url,
      cost_data: results.cost_data || {}
    }
    
    console.log('Documents retrieved successfully:', documents.value)
    currentView.value = 'results'
  } catch (error) {
    console.error('Error fetching documents:', error)
    submitError.value = 'Failed to retrieve generated documents. Please try again.'
    currentView.value = 'form'
  }
}

const handleAgentError = (error) => {
  console.error('Agent error:', error)
  submitError.value = error
  currentView.value = 'form'
}

const handleRetry = () => {
  currentView.value = 'form'
  submitError.value = 'Previous generation failed. Please try again.'
}

const handleBackdropClick = () => {
  // Prevent dismissal during processing for now
  // Could add confirmation dialog here
}

const startNew = () => {
  currentView.value = 'form'
  sessionId.value = null
  submitError.value = null
  formData.value = {
    requirements: '',
    client_name: '',
    project_name: '',
    industry: '',
    duration: '',
    team_size: 5
  }
  documents.value = {
    powerpoint_url: null,
    sow_url: null,
    cost_data: {}
  }
}
</script>

<style scoped>
.assessment-view {
  min-height: calc(100vh - 52px);
  position: relative;
}

/* Form View (Compact State) */
.form-view {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.welcome-section {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.logo-hero {
  margin-bottom: var(--spacing-lg);
}

.hero-logo {
  height: 88px; /* Large logo for hero */
  width: auto;
  filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.1));
  animation: logoFloat 3s ease-in-out infinite;
}

@keyframes logoFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

.hero-title {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -1px;
  color: var(--color-label);
  margin-bottom: var(--spacing-xs);
  line-height: 1.1;
}

.hero-subtitle {
  font-size: 17px;
  color: var(--color-secondary-label);
  font-weight: 400;
}

.upload-card {
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: var(--radius-xl);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  padding: var(--spacing-xl);
  animation: slideUp 0.6s ease-out 0.2s both;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card-header {
  margin-bottom: var(--spacing-xl);
}

.card-header h2 {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.5px;
  color: var(--color-label);
  margin-bottom: var(--spacing-xs);
}

.card-subtitle {
  font-size: 15px;
  color: var(--color-secondary-label);
}

.assessment-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
}

.form-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-label);
  display: flex;
  align-items: center;
  gap: 6px;
}

.optional {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-tertiary-label);
}

.textarea-container {
  position: relative;
  border-radius: var(--radius-md);
  border: 2px solid var(--color-separator);
  background: var(--color-background);
  transition: all var(--transition-fast);
}

.textarea-container.focused {
  border-color: var(--color-blue);
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1);
}

.textarea-container textarea {
  width: 100%;
  min-height: 280px;
  padding: var(--spacing-md);
  border: none;
  background: transparent;
  font-family: var(--font-system);
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-label);
  resize: vertical;
  outline: none;
}

.textarea-container textarea::placeholder {
  color: var(--color-tertiary-label);
}

.textarea-hint {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-secondary-background);
  border-top: 0.5px solid var(--color-separator);
  font-size: 13px;
  color: var(--color-secondary-label);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.hint-icon {
  font-size: 16px;
}

.form-input,
.form-select {
  padding: 12px 16px;
  border: 2px solid var(--color-separator);
  border-radius: var(--radius-sm);
  background: var(--color-background);
  font-family: var(--font-system);
  font-size: 15px;
  color: var(--color-label);
  transition: all var(--transition-fast);
  outline: none;
}

.form-input:focus,
.form-select:focus {
  border-color: var(--color-blue);
  box-shadow: 0 0 0 4px rgba(0, 122, 255, 0.1);
}

.form-select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%23666' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 40px;
}

.generate-button {
  width: 100%;
  padding: 16px 24px;
  background: var(--color-blue);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-top: var(--spacing-md);
}

.generate-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 122, 255, 0.4);
}

.generate-button:active:not(:disabled) {
  transform: translateY(0);
}

.generate-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.button-icon {
  color: currentColor;
}

.button-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.time-estimate {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  font-size: 14px;
  color: var(--color-secondary-label);
  padding: var(--spacing-md);
  background: var(--color-secondary-background);
  border-radius: var(--radius-sm);
}

.error-alert {
  display: flex;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: rgba(255, 59, 48, 0.1);
  border: 1px solid var(--color-red);
  border-radius: var(--radius-md);
  margin-top: var(--spacing-lg);
  animation: shake 0.4s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-8px); }
  75% { transform: translateX(8px); }
}

.alert-icon {
  font-size: 24px;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-red);
  margin-bottom: 4px;
}

.alert-message {
  font-size: 14px;
  color: var(--color-secondary-label);
}

/* Processing View (Modal Overlay) */
.processing-view {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.processing-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.processing-content {
  position: relative;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding-top: 52px; /* Account for header */
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-base);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .processing-content,
.modal-leave-active .processing-content {
  transition: transform var(--transition-base);
}

.modal-enter-from .processing-content,
.modal-leave-to .processing-content {
  transform: scale(0.95);
}

/* Results View */
.results-view {
  min-height: calc(100vh - 52px);
  padding: var(--spacing-2xl) var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.results-container {
  max-width: 900px;
  width: 100%;
}

.results-hero {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.success-animation {
  margin-bottom: var(--spacing-lg);
  display: inline-block;
  animation: scaleIn 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.success-checkmark {
  filter: drop-shadow(0 8px 24px rgba(52, 199, 89, 0.3));
}

.circle-bg {
  animation: fadeIn 0.4s ease-out;
}

.circle-stroke {
  stroke-dasharray: 226;
  stroke-dashoffset: 226;
  animation: drawCircle 0.6s ease-out 0.2s forwards;
}

.checkmark-path {
  stroke-dasharray: 48;
  stroke-dashoffset: 48;
  animation: drawCheck 0.4s ease-out 0.6s forwards;
}

@keyframes drawCircle {
  to {
    stroke-dashoffset: 0;
  }
}

@keyframes drawCheck {
  to {
    stroke-dashoffset: 0;
  }
}

.results-title {
  font-size: 40px;
  font-weight: 700;
  letter-spacing: -1px;
  color: var(--color-label);
  margin-bottom: var(--spacing-xs);
}

.results-subtitle {
  font-size: 17px;
  color: var(--color-secondary-label);
}

.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.document-card {
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: var(--radius-lg);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  padding: var(--spacing-xl);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  transition: all var(--transition-base);
  animation: slideUp 0.6s ease-out both;
}

.document-card:nth-child(1) {
  animation-delay: 0.1s;
}

.document-card:nth-child(2) {
  animation-delay: 0.2s;
}

.document-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12);
}

.document-icon-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-sm);
}

.document-icon {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.document-info {
  flex: 1;
}

.document-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-label);
  margin-bottom: var(--spacing-xs);
}

.document-description {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-secondary-label);
}

.download-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: 12px 20px;
  background: var(--color-blue);
  color: white;
  text-decoration: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 600;
  transition: all var(--transition-fast);
  margin-top: var(--spacing-md);
}

.download-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.4);
}

.download-button:active {
  transform: translateY(0);
}

.download-icon {
  color: currentColor;
}

.cost-summary {
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: var(--radius-lg);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  animation: slideUp 0.6s ease-out 0.3s both;
}

.summary-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-label);
  margin-bottom: var(--spacing-md);
}

.summary-content {
  background: var(--color-secondary-background);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
  overflow-x: auto;
}

.cost-json {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--color-label);
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.results-actions {
  display: flex;
  justify-content: center;
  margin-bottom: var(--spacing-2xl);
}

.action-button {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 14px 28px;
  background: var(--color-blue);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 17px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.action-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 122, 255, 0.4);
}

.action-button:active {
  transform: translateY(0);
}

.results-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-xl);
  border-top: 0.5px solid var(--color-separator);
}

.footer-logo {
  height: 32px; /* Footer logo size */
  width: auto;
  opacity: 0.6;
  transition: opacity var(--transition-fast);
}

.footer-logo:hover {
  opacity: 0.8;
}

.footer-text {
  font-size: 13px;
  color: var(--color-tertiary-label);
}

/* Responsive Design */
@media (max-width: 768px) {
  .form-view {
    padding: var(--spacing-lg);
  }
  
  .hero-logo {
    height: 64px;
  }
  
  .hero-title {
    font-size: 32px;
  }
  
  .upload-card {
    padding: var(--spacing-lg);
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .documents-grid {
    grid-template-columns: 1fr;
  }
  
  .results-title {
    font-size: 32px;
  }
}
</style>