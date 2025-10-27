<template>
  <div class="api-response-preview">
    <div v-if="response && response.content && response.content.length > 0" class="response-content">
      <div v-for="(item, index) in response.content" :key="index" class="response-item">
        <div v-if="item.type === 'text' && item.text" class="text-content">
          <pre v-if="isJsonString(item.text)" class="json-content">{{ formatJson(item.text) }}</pre>
          <div v-else class="plain-text">{{ item.text }}</div>
        </div>
        <div v-else-if="item.type === 'image'" class="image-content">
          <img :src="item.image_url" :alt="item.description || 'Response image'" />
        </div>
        <div v-else class="unknown-content">
          <strong>{{ item.type }}:</strong>
          <pre>{{ JSON.stringify(item, null, 2) }}</pre>
        </div>
      </div>
    </div>
    <div v-else-if="response && response.error" class="error-content">
      <div class="error-message">
        <strong>错误:</strong> {{ response.error }}
      </div>
    </div>
    <div v-else class="no-content">
      <span class="no-data">暂无响应数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import '../assets/styles/ApiResponsePreview.scss'

interface ResponseItem {
  type: string
  text?: string
  image_url?: string
  description?: string
  [key: string]: any
}

interface ApiResponse {
  content?: ResponseItem[]
  error?: string
  [key: string]: any
}

interface Props {
  response: ApiResponse | null
}

const props = defineProps<Props>()

// 检查字符串是否为JSON格式
const isJsonString = (str: string): boolean => {
  try {
    JSON.parse(str)
    return true
  } catch {
    return false
  }
}

// 格式化JSON字符串
const formatJson = (str: string): string => {
  try {
    const parsed = JSON.parse(str)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return str
  }
}
</script>
