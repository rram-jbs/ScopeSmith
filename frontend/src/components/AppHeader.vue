<template>
  <header class="app-header">
    <div class="header-container">
      <!-- Logo & Branding -->
      <div class="brand">
        <div class="logo">
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="16" cy="16" r="14" stroke="currentColor" stroke-width="2"/>
            <path d="M16 10v12M10 16h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h1>ScopeSmith</h1>
      </div>

      <!-- Navigation -->
      <nav class="nav-menu">
        <router-link to="/" class="nav-item" :class="{ active: isActive('/') }">
          Dashboard
        </router-link>
        <router-link to="/assessment" class="nav-item" :class="{ active: isActive('/assessment') }">
          Assessment
        </router-link>
        <a href="#" class="nav-item">Documentation</a>
      </nav>

      <!-- Right Actions -->
      <div class="header-actions">
        <button class="icon-button" title="Notifications">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
        </button>

        <button class="icon-button" title="Settings">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m6.08 6.08l4.24 4.24M1 12h6m6 0h6m-17.78 7.78l4.24-4.24m6.08-6.08l4.24-4.24"/>
          </svg>
        </button>

        <!-- User Menu -->
        <div class="user-menu">
          <button class="user-button" @click="toggleMenu" :class="{ active: menuOpen }">
            <span class="avatar">A</span>
          </button>

          <Transition name="dropdown">
            <div v-if="menuOpen" class="dropdown-menu">
              <a href="#" class="dropdown-item">
                <span class="icon">👤</span>
                Profile
              </a>
              <a href="#" class="dropdown-item">
                <span class="icon">⚙️</span>
                Settings
              </a>
              <a href="#" class="dropdown-item">
                <span class="icon">📚</span>
                Help
              </a>
              <div class="dropdown-divider"></div>
              <a href="#" class="dropdown-item logout">
                <span class="icon">🚪</span>
                Sign Out
              </a>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

export default {
  name: 'AppHeader',
  setup() {
    const menuOpen = ref(false)
    const route = useRoute()

    const toggleMenu = () => {
      menuOpen.value = !menuOpen.value
    }

    const isActive = (path) => {
      return route.path === path
    }

    return {
      menuOpen,
      toggleMenu,
      isActive
    }
  }
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-backdrop);
  border-bottom: var(--glass-border);
  box-shadow: var(--shadow-sm);
}

.header-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--spacing-md) var(--spacing-lg);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-xl);
}

/* Brand */
.brand {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  text-decoration: none;
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: 1.25rem;
  letter-spacing: -0.01em;
  min-width: fit-content;
}

.logo {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-blue), var(--color-purple));
  border-radius: var(--radius-md);
  color: white;
  flex-shrink: 0;
}

.logo svg {
  width: 20px;
  height: 20px;
}

/* Navigation */
.nav-menu {
  display: flex;
  align-items: center;
  gap: var(--spacing-xl);
  flex: 1;
  margin-left: var(--spacing-xl);
}

.nav-item {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
  position: relative;
  padding: var(--spacing-xs) 0;
  transition: color var(--transition-fast);
}

.nav-item:hover {
  color: var(--color-text-primary);
}

.nav-item.active {
  color: var(--color-blue);
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-blue);
  border-radius: 1px;
}

/* Header Actions */
.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-left: auto;
}

.icon-button {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all var(--transition-fast);
}

.icon-button:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-primary);
}

.icon-button svg {
  width: 20px;
  height: 20px;
}

/* User Menu */
.user-menu {
  position: relative;
}

.user-button {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--color-blue);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.9rem;
  padding: 0;
  transition: all var(--transition-fast);
}

.user-button:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

.user-button.active {
  background: var(--color-blue);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.2);
}

.avatar {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Dropdown Menu */
.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: var(--spacing-md);
  background: var(--glass-bg);
  backdrop-filter: var(--glass-backdrop);
  border: var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 200px;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  color: var(--color-text-primary);
  transition: all var(--transition-fast);
  font-size: 0.95rem;
}

.dropdown-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

.dropdown-item.logout:hover {
  background: rgba(255, 59, 48, 0.1);
  color: var(--color-red);
}

.dropdown-item .icon {
  font-size: 1.1rem;
  width: 20px;
}

.dropdown-divider {
  height: 1px;
  background: rgba(0, 0, 0, 0.1);
  margin: var(--spacing-xs) 0;
}

/* Transitions */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all var(--transition-fast);
}

.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Responsive */
@media (max-width: 768px) {
  .nav-menu {
    display: none;
  }

  .header-container {
    gap: var(--spacing-md);
  }
}
</style>