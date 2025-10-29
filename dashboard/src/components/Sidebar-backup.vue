<template>
  <!-- 遮罩层 -->
  <div v-if="isOpen"
       class="fixed top-0 left-0 w-screen h-screen bg-black"
       style="opacity: 0.5; z-index: 999;"
       @click="closeSidebar">
  </div>

  <!-- 侧边栏 -->
  <div class="fixed top-0 h-screen bg-white transition-all duration-300"
       style="width: 400px; z-index: 1000; box-shadow: -2px 0 10px rgba(0,0,0,0.1);"
       :style="{ right: isOpen ? '0' : '-400px' }">
    <div class="h-full flex flex-col justify-start">
      <div class="flex justify-between items-center p-5 border-b border-gray-200 bg-gray-50">
        <h3 class="m-0 text-gray-800">配置管理</h3>
        <button class="border-none text-xl cursor-pointer p-0 flex items-center justify-center rounded-full"
                style="background: none; width: 40px; height: 40px;"
                @click="closeSidebar">×</button>
      </div>

      <div class="flex-1 overflow-y-auto p-5">
        <div class="mb-8">
          <h4 class="mb-4 text-gray-800 border-b-2 border-blue-500 pb-1">API配置</h4>
          <div class="mb-4">
            <label class="block mb-1 font-medium text-gray-600">后端地址:</label>
            <input v-model="config.backendUrl" type="text" placeholder="http://localhost:8000" class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25" />
          </div>
          <div class="mb-4">
            <label class="block mb-1 font-medium text-gray-600">API Key:</label>
            <input v-model="config.apiKey" type="password" placeholder="输入API Key" class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25" />
          </div>
        </div>

        <div class="mb-8">
          <h4 class="mb-4 text-gray-800 border-b-2 border-blue-500 pb-1">工作流配置</h4>
          <div class="mb-4">
            <label class="block mb-1 font-medium text-gray-600">自动保存间隔 (秒):</label>
            <input v-model.number="config.autoSaveInterval" type="number" min="10" max="300" class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25" />
          </div>
          <div class="mb-4">
            <label class="flex items-center">
              <input v-model="config.enableNotifications" type="checkbox" class="mr-2" />
              <span class="text-gray-600">启用通知</span>
            </label>
          </div>
        </div>

        <div class="mb-8">
          <h4 class="mb-4 text-gray-800 border-b-2 border-blue-500 pb-1">界面配置</h4>
          <div class="mb-4">
            <label class="block mb-1 font-medium text-gray-600">主题:</label>
            <select v-model="config.theme" class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25">
              <option value="light">浅色</option>
              <option value="dark">深色</option>
              <option value="auto">自动</option>
            </select>
          </div>
          <div class="mb-4">
            <label class="block mb-1 font-medium text-gray-600">语言:</label>
            <select v-model="config.language" class="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25">
              <option value="zh-CN">中文</option>
              <option value="en-US">English</option>
            </select>
          </div>
        </div>

        <div class="flex flex-col gap-3 pt-5 border-t border-gray-200">
          <button class="px-4 py-3 bg-blue-500 text-white border-none rounded cursor-pointer font-medium transition-colors hover:bg-blue-600" @click="saveConfig">保存配置</button>
          <button class="px-4 py-3 bg-gray-600 text-white border-none rounded cursor-pointer font-medium transition-colors hover:bg-gray-700" @click="resetConfig">重置</button>
          <button class="px-4 py-3 bg-red-500 text-white border-none rounded cursor-pointer font-medium transition-colors hover:bg-red-600" @click="clearWorkflowState">清除工作流状态</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

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

watch(() => props.isOpen, (newVal) => {
  console.log('Sidebar isOpen changed to:', newVal)
})

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
