<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-brand">
        <h2>Automata MCP 工作流</h2>
      </div>
      <div class="nav-actions">
        <button class="settings-btn" @click="toggleSidebar" title="设置">
          ⚙️
        </button>
      </div>
    </nav>

    <router-view />

    <Sidebar :is-open="sidebarOpen" @close="closeSidebar" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'

const sidebarOpen = ref(false)

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const closeSidebar = () => {
  sidebarOpen.value = false
}
</script>

<style lang="scss">
#app {
  min-height: 100vh;
  margin: 0;
  padding: 0;
}

.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0,0,0,0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  z-index: 100;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.nav-brand h2 {
  margin: 0;
  color: #333;
  font-size: 1.5rem;
  font-weight: 600;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.settings-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background-color 0.3s ease;

  &:hover {
    background: rgba(0,123,255,0.1);
  }
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  padding: 60px 0 0 0; /* 为固定导航栏留出空间 */
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  line-height: 1.6;
  color: #333;
}

button {
  cursor: pointer;
}

input, textarea, button {
  font-family: inherit;
}

@media (max-width: 768px) {
  .navbar {
    padding: 0 15px;
  }

  .nav-brand h2 {
    font-size: 1.3rem;
  }

  body {
    padding-top: 60px;
  }
}
</style>
