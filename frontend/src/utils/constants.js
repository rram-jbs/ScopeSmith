export const POLLING_INTERVAL = 2000 // 2 seconds
export const MAX_POLLING_TIME = 300000 // 5 minutes timeout

export const WORKFLOW_STAGES = [
  { id: 1, name: 'Session Created', key: 'session_created', icon: '✓' },
  { id: 2, name: 'Analyzing Requirements', key: 'RequirementsAnalyzer', icon: '⏳' },
  { id: 3, name: 'Calculating Costs', key: 'CostCalculator', icon: '⏳' },
  { id: 4, name: 'Selecting Templates', key: 'TemplateRetriever', icon: '⏳' },
  { id: 5, name: 'Generating PowerPoint', key: 'PowerPointGenerator', icon: '⏳' },
  { id: 6, name: 'Generating SOW', key: 'SOWGenerator', icon: '⏳' },
  { id: 7, name: 'Complete', key: 'completed', icon: '✅' }
]

// Status constants - synchronized with backend Lambda status values
export const STATUS = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  ERROR: 'ERROR',
  CONFIGURATION_ERROR: 'CONFIGURATION_ERROR'
}

export const INDUSTRIES = [
  'Technology',
  'Healthcare',
  'Finance',
  'Retail',
  'Manufacturing',
  'Other'
]

export const PROJECT_DURATIONS = [
  '1-3 months',
  '3-6 months',
  '6-12 months',
  '12+ months'
]

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'

export const ENDPOINTS = {
  SUBMIT_ASSESSMENT: '/api/submit-assessment',
  AGENT_STATUS: (sessionId) => `/api/agent-status/${sessionId}`,
  RESULTS: (sessionId) => `/api/results/${sessionId}`,
  UPLOAD_TEMPLATE: '/api/upload-template'
}