<template>
  <div class="sidebar" :class="{ 'sidebar-open': isOpen }">
    <div class="sidebar-overlay" v-if="isOpen" @click="closeSidebar"></div>
    <div class="sidebar-content">
      <div class="sidebar-header">
        <h3>配置管理</h3>
        <button class="close-btn" @click="closeSidebar">×</button>
      </div>

      <div class="config-sections">
        <div class="config-section">
          <h4>API配置</h4>
          <div class="form-group">
            <label>后端地址:</label>
            <input v-model="config.backendUrl" type="text" placeholder="http://localhost:8000" />
          </div>
          <div class="form-group">
            <label>API Key:</label>
            <input v-model="config.apiKey" type="password" placeholder="输入API Key" />
          </div>
        </div>

        <div class="config-section">
          <h4>工作流配置</h4>
          <div class="form-group">
            <label>自动保存间隔 (秒):</label>
            <input v-model.number="config.autoSaveInterval" type="number" min="10" max="300" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="config.enableNotifications" type="checkbox" />
              启用通知
            </label>
          </div>
        </div>

        <div class="config-section">
          <h4>界面配置</h4>
          <div class="form-group">
            <label>主题:</label>
            <select v-model="config.theme">
              <option value="light">浅色</option>
              <option value="dark">深色</option>
              <option value="auto">自动</option>
            </select>
          </div>
          <div class="form-group">
            <label>语言:</label>
            <select v-model="config.language">
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </div>
        </div>

        <div class="config-actions">
          <button class="btn-primary" @click="saveConfig">保存配置</button>
          <button class="btn-secondary" @click="resetConfig">重置</button>
          <button class="btn-danger" @click="clearWorkflowState">清除工作流状态</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import '../assets/styles/Sidebar.scss'

interface Config {
  backendUrl: string
  apiKey: string
  autoSaveInterval: number
  enableNotifications: boolean
  theme: string
  language: string
}

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const config = ref<Config>({
  backendUrl: 'http://localhost:8000',
  apiKey: '',
  autoSaveInterval: 30,
  enableNotifications: true,
  theme: 'light',
  language: 'zh-CN'
})

const closeSidebar = () => {
  emit('close')
}

const saveConfig = () => {
  localStorage.setItem('workflow-config', JSON.stringify(config.value))
  alert('配置已保存')
  closeSidebar()
}

const resetConfig = () => {
  config.value = {
    backendUrl: 'http://localhost:8000',
    apiKey: '',
    autoSaveInterval: 30,
    enableNotifications: true,
    theme: 'light',
    language: 'zh-CN'
  }
}

const clearWorkflowState = () => {
  if (confirm('确定要清除所有工作流状态吗？此操作不可恢复。')) {
    localStorage.removeItem('workflow-state')
    alert('工作流状态已清除')
  }
}

onMounted(() => {
  const savedConfig = localStorage.getItem('workflow-config')
  if (savedConfig) {
    try {
      config.value = { ...config.value, ...JSON.parse(savedConfig) }
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  }
})
</script>
