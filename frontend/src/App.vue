<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup>
// App wrapper - just renders the router view
</script>

<style>
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
</style>
