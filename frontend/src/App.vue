<script setup>
import { ref } from 'vue'
import AssessmentForm from '@/components/AssessmentForm.vue'
import AgentStatus from '@/components/AgentStatus.vue'
import ResultsDisplay from '@/components/ResultsDisplay.vue'

const currentView = ref('form') // 'form', 'status', 'results'
const sessionId = ref(null)

const handleSubmit = (id) => {
  sessionId.value = id
  currentView.value = 'status'
}

const handleComplete = () => {
  currentView.value = 'results'
}

const resetToForm = () => {
  currentView.value = 'form'
  sessionId.value = null
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
    <header class="bg-white shadow-sm">
      <div class="max-w-7xl mx-auto py-4 px-6">
        <h1 class="text-2xl font-bold text-gray-900">ScopeSmith</h1>
        <p class="text-sm text-gray-600">AI-Powered Proposal Generation</p>
      </div>
    </header>

    <main class="max-w-7xl mx-auto py-8 px-6">
      <transition
        mode="out-in"
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 translate-y-1"
      >
        <AssessmentForm
          v-if="currentView === 'form'"
          @submit="handleSubmit"
          class="transition-all"
        />
        <AgentStatus
          v-else-if="currentView === 'status'"
          :session-id="sessionId"
          @complete="handleComplete"
          class="transition-all"
        />
        <ResultsDisplay
          v-else-if="currentView === 'results'"
          :session-id="sessionId"
          @reset="resetToForm"
          class="transition-all"
        />
      </transition>
    </main>

    <footer class="mt-auto py-6">
      <div class="max-w-7xl mx-auto px-6">
        <p class="text-center text-sm text-gray-500">
          Built for AWS AI Agent Hackathon 2025
        </p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
</style>
