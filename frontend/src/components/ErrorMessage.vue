<script setup>
defineProps({
  message: {
    type: String,
    required: true
  },
  retryAction: {
    type: Function,
    default: null
  },
  dismissable: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['dismiss'])
</script>

<template>
  <div
    role="alert"
    class="rounded-md bg-red-50 p-4 border border-red-200 relative"
    aria-live="assertive"
  >
    <div class="flex">
      <div class="flex-shrink-0">
        <svg
          class="h-5 w-5 text-red-400"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
            clip-rule="evenodd"
          />
        </svg>
      </div>
      <div class="ml-3 flex-1">
        <p class="text-sm text-red-700">{{ message }}</p>
        <div v-if="retryAction" class="mt-2">
          <button
            type="button"
            class="text-sm font-medium text-red-600 hover:text-red-500"
            @click="retryAction"
          >
            Try again
          </button>
        </div>
      </div>
      <div v-if="dismissable" class="ml-auto pl-3">
        <button
          type="button"
          class="inline-flex rounded-md bg-red-50 p-1.5 text-red-500 hover:bg-red-100"
          @click="emit('dismiss')"
        >
          <span class="sr-only">Dismiss</span>
          <svg
            class="h-5 w-5"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
            />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>