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

<style scoped lang="scss">
.sidebar {
  position: fixed;
  top: 0;
  right: -400px;
  width: 400px;
  height: 100vh;
  background: white;
  box-shadow: -2px 0 10px rgba(0,0,0,0.1);
  transition: right 0.3s ease;
  z-index: 1000;

  &.sidebar-open {
    right: 0;
  }
}

.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0,0,0,0.5);
  z-index: -1;
}

.sidebar-content {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
  background: #f8f9fa;

  h3 {
    margin: 0;
    color: #333;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #666;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;

    &:hover {
      background: #e9ecef;
    }
  }
}

.config-sections {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.config-section {
  margin-bottom: 30px;

  h4 {
    margin-bottom: 15px;
    color: #333;
    border-bottom: 2px solid #007bff;
    padding-bottom: 5px;
  }
}

.form-group {
  margin-bottom: 15px;

  label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #555;
  }

  input, select {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: #007bff;
      box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
    }
  }

  input[type="checkbox"] {
    width: auto;
    margin-right: 8px;
  }
}

.config-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid #eee;

  button {
    padding: 10px 15px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.3s ease;

    &.btn-primary {
      background: #007bff;
      color: white;

      &:hover {
        background: #0056b3;
      }
    }

    &.btn-secondary {
      background: #6c757d;
      color: white;

      &:hover {
        background: #545b62;
      }
    }

    &.btn-danger {
      background: #dc3545;
      color: white;

      &:hover {
        background: #c82333;
      }
    }
  }
}

@media (max-width: 480px) {
  .sidebar {
    width: 100vw;
    right: -100vw;

    &.sidebar-open {
      right: 0;
    }
  }
}
</style>
