<template>
  <div id="app">
    <header class="app-header">
      <div class="header-content">
        <div class="logo-container">
          <img src="/logo.png" alt="ScopeSmith" class="logo" />
          <h1>ScopeSmith</h1>
        </div>
        <div class="session-status" v-if="sessionStatus">
          <div class="status-indicator" :class="statusClass"></div>
          <span class="status-text">{{ sessionStatus }}</span>
        </div>
        <div class="user-controls">
          <button class="icon-button" aria-label="Settings">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" stroke="currentColor" stroke-width="1.5"/>
              <path d="M16.5 10a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </button>
        </div>
      </div>
    </header>
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" @status-update="updateStatus" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const sessionStatus = ref(null)
const statusClass = ref('status-idle')

const updateStatus = (status) => {
  sessionStatus.value = status
  
  if (status?.includes('Completed') || status?.includes('Ready')) {
    statusClass.value = 'status-success'
  } else if (status?.includes('Error')) {
    statusClass.value = 'status-error'
  } else if (status) {
    statusClass.value = 'status-active'
  } else {
    statusClass.value = 'status-idle'
  }
}
</script>

<style>
/* Apple Design System - Global Styles */
:root {
  /* SF Pro Font Stack */
  --font-system: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', sans-serif;
  --font-mono: 'SF Mono', 'Monaco', 'Cascadia Code', 'Courier New', monospace;
  
  /* Apple System Colors */
  --color-blue: #007AFF;
  --color-green: #34C759;
  --color-red: #FF3B30;
  --color-orange: #FF9500;
  --color-yellow: #FFCC00;
  --color-purple: #AF52DE;
  
  /* Neutral Colors */
  --color-label: rgba(0, 0, 0, 0.85);
  --color-secondary-label: rgba(0, 0, 0, 0.55);
  --color-tertiary-label: rgba(0, 0, 0, 0.30);
  --color-separator: rgba(0, 0, 0, 0.10);
  
  /* Background Colors */
  --color-background: #FFFFFF;
  --color-secondary-background: #F2F2F7;
  --color-tertiary-background: #FFFFFF;
  
  /* Liquid Glass Material */
  --glass-background: rgba(255, 255, 255, 0.72);
  --glass-border: rgba(255, 255, 255, 0.18);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  
  /* Spacing Scale (Apple's 8pt grid) */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-2xl: 48px;
  
  /* Border Radius */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  
  /* Transitions */
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-label: rgba(255, 255, 255, 0.85);
    --color-secondary-label: rgba(255, 255, 255, 0.55);
    --color-tertiary-label: rgba(255, 255, 255, 0.30);
    --color-separator: rgba(255, 255, 255, 0.10);
    
    --color-background: #000000;
    --color-secondary-background: #1C1C1E;
    --color-tertiary-background: #2C2C2E;
    
    --glass-background: rgba(28, 28, 30, 0.72);
    --glass-border: rgba(255, 255, 255, 0.12);
    --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  }
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-system);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: var(--color-secondary-background);
  color: var(--color-label);
}

#app {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-main {
  flex: 1;
}

/* Fade Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style scoped>
/* Apple-Inspired Navigation Bar with Liquid Glass */
.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--glass-background);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 0.5px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-sm) var(--spacing-lg);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-lg);
  height: 52px; /* Apple standard nav height */
}

.logo-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  min-width: 0;
}

.logo {
  height: 44px; /* @2x retina */
  width: auto;
  padding: 11px; /* Minimum clear space = 1/4 logo height */
  object-fit: contain;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.12));
  transition: transform var(--transition-fast);
}

.logo:hover {
  transform: scale(1.02);
}

.logo-container h1 {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.4px;
  color: var(--color-label);
  white-space: nowrap;
}

.session-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 6px 12px;
  background: var(--color-tertiary-background);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-secondary-label);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transition: background-color var(--transition-base);
}

.status-indicator.status-idle {
  background: var(--color-separator);
}

.status-indicator.status-active {
  background: var(--color-blue);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.status-indicator.status-success {
  background: var(--color-green);
}

.status-indicator.status-error {
  background: var(--color-red);
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.user-controls {
  display: flex;
  gap: var(--spacing-sm);
}

.icon-button {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 50%;
  color: var(--color-label);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.icon-button:hover {
  background: var(--color-separator);
}

.icon-button:active {
  transform: scale(0.96);
}

/* Responsive Design */
@media (max-width: 768px) {
  .header-content {
    padding: var(--spacing-sm) var(--spacing-md);
  }
  
  .logo {
    height: 32px; /* Smaller on mobile */
    padding: 8px;
  }
  
  .logo-container h1 {
    font-size: 17px;
  }
  
  .session-status {
    font-size: 12px;
    padding: 4px 10px;
  }
}

@media (max-width: 480px) {
  .logo-container h1 {
    display: none; /* Hide text on very small screens */
  }
}
</style>
