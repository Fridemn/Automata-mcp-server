<template>
  <div class="workflow-step-publish-xhs">
    <div class="flex flex-col gap-4">
      <!-- 图片预览区域 -->
      <div v-if="imageFiles.length > 0" class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">生成的图片预览 ({{ imageFiles.length }} 张)</label>
        <div class="grid grid-cols-2 gap-4">
          <div v-for="(imagePath, index) in imageFiles" :key="index" class="border rounded-lg p-2 bg-gray-50">
            <img
              :src="`http://localhost:8000/${imagePath}`"
              :alt="`生成的图片 ${index + 1}`"
              class="w-full h-auto rounded mb-2"
              @error="handleImageError($event, imagePath)"
            />
            <p class="text-xs text-gray-500 break-all">{{ imagePath }}</p>
          </div>
        </div>
      </div>

      <!-- 无图片提示 -->
      <div v-else class="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded">
        <p class="text-sm text-yellow-700">等待上一步生成图片...</p>
      </div>

      <button
        @click="handlePublish"
        :disabled="step.status === 'running' || imageFiles.length === 0"
        class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        发布到小红书 ({{ imageFiles.length }} 张图片)
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, computed } from 'vue'
import * as api from '@/api/api'

interface WorkflowStep {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'error'
  response?: any
  error?: string
}

const props = defineProps<{
  step: WorkflowStep
  publishData: string
  imageGenerationStep?: WorkflowStep
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  updatePublishData: [data: string]
  saveState: []
}>()

// 解析图片文件列表
const imageFiles = computed(() => {
  const files: string[] = []

  // 从 publishData 解析
  if (props.publishData) {
    try {
      const data = JSON.parse(props.publishData)
      if (data.content && Array.isArray(data.content)) {
        data.content.forEach((item: any) => {
          if (item.type === 'text' && item.text) {
            parseImagePaths(item.text, files)
          }
        })
      }
    } catch (e) {
      // 如果不是 JSON，尝试直接解析
      parseImagePaths(props.publishData, files)
    }
  }

  // 从 imageGenerationStep 的 response 解析
  if (props.imageGenerationStep?.response) {
    const response = props.imageGenerationStep.response
    if (response.content && Array.isArray(response.content)) {
      response.content.forEach((item: any) => {
        if (item.type === 'text' && item.text) {
          parseImagePaths(item.text, files)
        }
      })
    } else if (typeof response === 'string') {
      parseImagePaths(response, files)
    }
  }

  return [...new Set(files)] // 去重
})

// 解析文本中的图片路径
const parseImagePaths = (text: string, files: string[]) => {
  // 匹配输出路径
  const outputPathMatch = text.match(/输出路径:\s*([^\n]+)/)
  const outputPath = outputPathMatch?.[1]?.trim() || 'data/output_image'

  // 匹配文件列表
  const fileListMatch = text.match(/文件列表:\s*([^\n]+)/)
  if (fileListMatch && fileListMatch[1]) {
    const fileList = fileListMatch[1].trim()
    // 分割文件名 (可能是逗号或空格分隔)
    const fileNames = fileList.split(/[,，\s]+/).filter(name => {
      // 过滤掉 generated.png，只保留 img_plan_*.png 格式
      return name && name.endsWith('.png') && name !== 'generated.png' && name.startsWith('img_plan_')
    })
    fileNames.forEach(fileName => {
      files.push(`${outputPath}/${fileName}`)
    })
  }

  // 也尝试直接匹配路径格式，但排除 generated.png
  const pathMatches = text.matchAll(/data\/output_image\/(img_plan_[\w_-]+\.png)/g)
  for (const match of pathMatches) {
    files.push(match[0])
  }
}

// 处理图片加载错误
const handleImageError = (event: Event, imagePath: string) => {
  console.error('Failed to load image:', imagePath)
  const img = event.target as HTMLImageElement
  img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YzZjRmNiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5Y2EzYWYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7lm77niYfliqDovb3lpLHotKU8L3RleHQ+PC9zdmc+'
}

const handlePublish = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    // 使用解析出的图片路径，如果有多张图片，使用第一张或者全部
    const imagePath = imageFiles.value.length > 0 ? imageFiles.value[0] : props.publishData
    const response = await api.callXiaohongshuTool({ image_path: imagePath })
    const completedStep = {
      ...updatedStep,
      response: response.data,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
    emit('updatePublishData', props.publishData)
    emit('saveState')
  } catch (error: any) {
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '发布到小红书失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
