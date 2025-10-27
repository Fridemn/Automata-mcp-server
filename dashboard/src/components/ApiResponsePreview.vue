<template>
  <div class="api-response-preview">
    <div v-if="response && response.content && response.content.length > 0" class="space-y-4">
      <div v-for="(item, index) in response.content" :key="index" class="border border-gray-200 rounded-lg p-4">
        <div v-if="item.type === 'text' && item.text" class="text-content">
          <pre v-if="isJsonString(item.text)" class="bg-gray-100 p-3 rounded text-sm overflow-x-auto">{{ formatJson(item.text) }}</pre>
          <div v-else class="text-gray-800 whitespace-pre-wrap">{{ item.text }}</div>
        </div>
        <div v-else-if="item.type === 'image'" class="image-content">
          <img :src="item.image_url" :alt="item.description || 'Response image'" class="max-w-full h-auto rounded border" />
        </div>
        <div v-else class="unknown-content">
          <strong class="text-gray-700">{{ item.type }}:</strong>
          <pre class="bg-gray-100 p-3 rounded text-sm overflow-x-auto mt-2">{{ JSON.stringify(item, null, 2) }}</pre>
        </div>
      </div>
    </div>
    <div v-else-if="response && response.error" class="p-4 bg-red-50 border border-red-200 rounded-lg">
      <div class="text-red-800">
        <strong>错误:</strong> {{ response.error }}
      </div>
    </div>
    <div v-else class="p-4 bg-gray-50 border border-gray-200 rounded-lg text-center">
      <span class="text-gray-500">暂无响应数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

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
