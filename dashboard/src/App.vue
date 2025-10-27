<template>
  <div id="app" class="min-h-screen m-0 p-0">
    <nav class="fixed top-0 left-0 right-0 bg-white/95 border-b border-black/10 flex justify-between items-center px-5 shadow-lg" style="height: 64px; z-index: 100; backdrop-filter: blur(10px);">
      <div class="nav-brand">
        <h2 class="m-0 text-gray-800 text-xl font-semibold">Automata MCP 工作流</h2>
      </div>
      <div class="nav-actions flex items-center gap-4">
        <button class="settings-btn border-none text-xl cursor-pointer p-2 rounded-full transition-colors duration-300" style="background: none;" @click="toggleSidebar" title="设置">
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
