export const POLLING_INTERVAL = 2000 // 2 seconds
export const MAX_POLLING_TIME = 300000 // 5 minutes timeout

export const WORKFLOW_STAGES = [
  { id: 1, name: 'Session Created', key: 'session_created', icon: '✓' },
  { id: 2, name: 'Analyzing Requirements', key: 'requirements_analysis', icon: '⏳' },
  { id: 3, name: 'Calculating Costs', key: 'cost_calculation', icon: '⏳' },
  { id: 4, name: 'Selecting Templates', key: 'template_selection', icon: '⏳' },
  { id: 5, name: 'Generating PowerPoint', key: 'powerpoint_generation', icon: '⏳' },
  { id: 6, name: 'Generating SOW', key: 'sow_generation', icon: '⏳' },
  { id: 7, name: 'Complete', key: 'completed', icon: '✅' }
]

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