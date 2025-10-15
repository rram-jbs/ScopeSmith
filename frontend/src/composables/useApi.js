import axios from 'axios'
import { ref } from 'vue'
import { API_BASE_URL, ENDPOINTS } from '@/utils/constants'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  // Generic methods
  const post = async (endpoint, data) => {
    loading.value = true
    error.value = null
    try {
      const response = await api.post(endpoint, data)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to post data'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  const get = async (endpoint) => {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(endpoint)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch data'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  const submitAssessment = async (formData) => {
    loading.value = true
    error.value = null
    try {
      const formatted = {
        client_name: formData.clientName,
        project_name: formData.projectName,
        requirements: formData.meetingNotes,
        industry: formData.industry,
        duration: formData.projectDuration,
        team_size: formData.teamSize
      }
      const response = await api.post(ENDPOINTS.SUBMIT_ASSESSMENT, formatted)
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to submit assessment'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  const getAgentStatus = async (sessionId) => {
    error.value = null
    try {
      const response = await api.get(ENDPOINTS.AGENT_STATUS(sessionId))
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch status'
      throw error.value
    }
  }

  const getResults = async (sessionId) => {
    loading.value = true
    error.value = null
    try {
      const response = await api.get(ENDPOINTS.RESULTS(sessionId))
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch results'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  const uploadTemplate = async (file) => {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post(ENDPOINTS.UPLOAD_TEMPLATE, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      return response.data
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to upload template'
      throw error.value
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    post,
    get,
    submitAssessment,
    getAgentStatus,
    getResults,
    uploadTemplate
  }
}