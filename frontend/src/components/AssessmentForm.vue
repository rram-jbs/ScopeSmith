<script setup>
import { ref, computed } from 'vue'
import { INDUSTRIES, PROJECT_DURATIONS } from '@/utils/constants'
import { useApi } from '@/composables/useApi'
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorMessage from './ErrorMessage.vue'

const emit = defineEmits(['submit'])
const { submitAssessment, loading, error } = useApi()

const form = ref({
  clientName: '',
  projectName: '',
  meetingNotes: '',
  industry: '',
  projectDuration: '',
  teamSize: 1
})

const validationErrors = computed(() => {
  const errors = {}
  if (!form.value.clientName) errors.clientName = 'Client name is required'
  else if (form.value.clientName.length > 100) errors.clientName = 'Client name must be less than 100 characters'

  if (!form.value.projectName) errors.projectName = 'Project name is required'
  else if (form.value.projectName.length > 150) errors.projectName = 'Project name must be less than 150 characters'

  if (!form.value.meetingNotes) errors.meetingNotes = 'Meeting notes are required'
  else if (form.value.meetingNotes.length < 200) errors.meetingNotes = 'Please provide at least 200 characters of meeting notes'

  if (!form.value.industry) errors.industry = 'Please select an industry'
  if (!form.value.projectDuration) errors.projectDuration = 'Please select a project duration'
  if (form.value.teamSize < 1 || form.value.teamSize > 50) errors.teamSize = 'Team size must be between 1 and 50'

  return errors
})

const isValid = computed(() => Object.keys(validationErrors.value).length === 0)

const handleSubmit = async () => {
  if (!isValid.value) return

  try {
    const response = await submitAssessment(form.value)
    emit('submit', response.session_id)
  } catch (err) {
    // Error handling is managed by useApi composable
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto bg-white shadow-lg rounded-lg overflow-hidden">
    <div class="px-6 py-4 bg-gradient-to-r from-primary to-secondary">
      <h2 class="text-2xl font-bold text-white">New Proposal Assessment</h2>
      <p class="text-white/80">Enter client meeting details to generate proposal</p>
    </div>

    <form @submit.prevent="handleSubmit" class="p-6 space-y-6">
      <ErrorMessage
        v-if="error"
        :message="error"
        :retry-action="handleSubmit"
      />

      <!-- Client Name -->
      <div>
        <label for="clientName" class="block text-sm font-medium text-gray-700">
          Client Name
        </label>
        <input
          id="clientName"
          v-model="form.clientName"
          type="text"
          maxlength="100"
          required
          class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
          :class="{ 'border-red-500': validationErrors.clientName }"
        />
        <p v-if="validationErrors.clientName" class="mt-1 text-sm text-red-600">
          {{ validationErrors.clientName }}
        </p>
      </div>

      <!-- Project Name -->
      <div>
        <label for="projectName" class="block text-sm font-medium text-gray-700">
          Project Name
        </label>
        <input
          id="projectName"
          v-model="form.projectName"
          type="text"
          maxlength="150"
          required
          class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
          :class="{ 'border-red-500': validationErrors.projectName }"
        />
        <p v-if="validationErrors.projectName" class="mt-1 text-sm text-red-600">
          {{ validationErrors.projectName }}
        </p>
      </div>

      <!-- Meeting Notes -->
      <div>
        <label for="meetingNotes" class="block text-sm font-medium text-gray-700">
          Meeting Notes
        </label>
        <textarea
          id="meetingNotes"
          v-model="form.meetingNotes"
          rows="6"
          required
          placeholder="Paste client meeting notes here..."
          class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary resize-none"
          :class="{ 'border-red-500': validationErrors.meetingNotes }"
        ></textarea>
        <p v-if="validationErrors.meetingNotes" class="mt-1 text-sm text-red-600">
          {{ validationErrors.meetingNotes }}
        </p>
      </div>

      <!-- Industry -->
      <div>
        <label for="industry" class="block text-sm font-medium text-gray-700">
          Industry
        </label>
        <select
          id="industry"
          v-model="form.industry"
          required
          class="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary focus:border-primary rounded-md"
          :class="{ 'border-red-500': validationErrors.industry }"
        >
          <option value="">Select an industry</option>
          <option v-for="industry in INDUSTRIES" :key="industry" :value="industry">
            {{ industry }}
          </option>
        </select>
        <p v-if="validationErrors.industry" class="mt-1 text-sm text-red-600">
          {{ validationErrors.industry }}
        </p>
      </div>

      <!-- Project Duration -->
      <div>
        <label for="projectDuration" class="block text-sm font-medium text-gray-700">
          Estimated Project Duration
        </label>
        <select
          id="projectDuration"
          v-model="form.projectDuration"
          required
          class="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-primary focus:border-primary rounded-md"
          :class="{ 'border-red-500': validationErrors.projectDuration }"
        >
          <option value="">Select duration</option>
          <option v-for="duration in PROJECT_DURATIONS" :key="duration" :value="duration">
            {{ duration }}
          </option>
        </select>
        <p v-if="validationErrors.projectDuration" class="mt-1 text-sm text-red-600">
          {{ validationErrors.projectDuration }}
        </p>
      </div>

      <!-- Team Size -->
      <div>
        <label for="teamSize" class="block text-sm font-medium text-gray-700">
          Estimated Team Size
        </label>
        <input
          id="teamSize"
          v-model.number="form.teamSize"
          type="number"
          min="1"
          max="50"
          required
          class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
          :class="{ 'border-red-500': validationErrors.teamSize }"
        />
        <p v-if="validationErrors.teamSize" class="mt-1 text-sm text-red-600">
          {{ validationErrors.teamSize }}
        </p>
      </div>

      <!-- Submit Button -->
      <div class="pt-4">
        <button
          type="submit"
          :disabled="!isValid || loading"
          class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-white bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <LoadingSpinner v-if="loading" size="sm" class="mr-2" />
          {{ loading ? 'Generating Proposal...' : 'Generate Proposal' }}
        </button>
      </div>
    </form>
  </div>
</template>