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

<style scoped lang="scss">
.api-response-preview {
  width: 100%;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  background: #fafbfc;
}

.response-content {
  padding: 16px;
}

.response-item {
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.text-content {
  .json-content {
    background: #f6f8fa;
    border: 1px solid #e1e5e9;
    border-radius: 6px;
    padding: 12px;
    margin: 0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 12px;
    line-height: 1.4;
    color: #24292f;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .plain-text {
    background: white;
    border: 1px solid #e1e5e9;
    border-radius: 6px;
    padding: 12px;
    line-height: 1.5;
    color: #24292f;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.image-content {
  text-align: center;

  img {
    max-width: 100%;
    max-height: 300px;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.unknown-content {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 6px;
  padding: 12px;

  strong {
    color: #856404;
  }

  pre {
    background: #f8f9fa;
    border: 1px solid #e1e5e9;
    border-radius: 4px;
    padding: 8px;
    margin: 8px 0 0 0;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 11px;
    color: #495057;
    overflow-x: auto;
  }
}

.error-content {
  padding: 16px;
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  color: #721c24;

  .error-message {
    strong {
      color: #721c24;
    }
  }
}

.no-content {
  padding: 32px 16px;
  text-align: center;
  color: #6c757d;
  font-style: italic;

  .no-data {
    opacity: 0.7;
  }
}

/* 滚动条样式 */
.api-response-preview::-webkit-scrollbar {
  width: 8px;
}

.api-response-preview::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.api-response-preview::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.api-response-preview::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
