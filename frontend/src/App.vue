<template>
  <div id="app">
    <header class="app-header">
      <div class="header-content">
        <div class="logo-container">
          <img src="/logo.png" alt="ScopeSmith" class="logo" />
          <h1>ScopeSmith</h1>
        </div>
        <nav class="main-nav">
          <router-link to="/" class="nav-link">Home</router-link>
          <router-link to="/projects" class="nav-link">Projects</router-link>
        </nav>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
    <footer class="app-footer">
      <p>Powered by Amazon Nova Pro</p>
    </footer>
  </div>
</template>

<script setup>
// App wrapper - just renders the router view
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

#app {
  width: 100%;
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1.5rem 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo {
  height: 40px;
  width: auto;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.logo-container h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.main-nav {
  display: flex;
  gap: 1.5rem;
}

.nav-link {
  color: white;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.nav-link:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.nav-link.router-link-active {
  background-color: rgba(255, 255, 255, 0.2);
}

.app-footer {
  background: #2d3748;
  color: #a0aec0;
  text-align: center;
  padding: 1.5rem;
  margin-top: auto;
}

.app-footer p {
  margin: 0;
  font-size: 0.875rem;
}
</style>
