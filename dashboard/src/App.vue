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
import './assets/styles/App.scss'

const sidebarOpen = ref(false)

const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value
}

const closeSidebar = () => {
  sidebarOpen.value = false
}
</script>
