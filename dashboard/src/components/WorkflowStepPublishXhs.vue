<template>
  <div class="workflow-step-publish-xhs">
    <div class="flex flex-col gap-4">
      <button
        @click="handlePublish"
        :disabled="step.status === 'running' || !hasValidImages || !hasGeneratedInfo"
        class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {{ getButtonText() }}
      </button>

      <!-- 显示将要发布的信息 -->
      <div v-if="hasGeneratedInfo && hasValidImages" class="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
        <h3 class="text-sm font-semibold text-gray-700 mb-2">发布信息预览：</h3>
        <div class="mb-2">
          <span class="text-xs font-semibold text-gray-600">标题：</span>
          <p class="text-sm text-gray-800">{{ generatedTitle }}</p>
        </div>
        <div class="mb-2">
          <span class="text-xs font-semibold text-gray-600">标签：</span>
          <p class="text-sm text-gray-800">{{ generatedTagsText }}</p>
        </div>
        <div>
          <span class="text-xs font-semibold text-gray-600">图片数量：</span>
          <p class="text-sm text-gray-800">{{ imageFiles.length }} 张</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, computed } from 'vue'
import * as api from '@/api/api'
import axios from 'axios'

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
  generateInfoStep?: WorkflowStep
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

// 检查是否有有效的图片
const hasValidImages = computed(() => imageFiles.value.length > 0)

// 从生成信息步骤获取标题
const generatedTitle = computed(() => {
  if (!props.generateInfoStep?.response) return ''
  const response = props.generateInfoStep.response
  return response.generated?.title || ''
})

// 从生成信息步骤获取标签文本
const generatedTagsText = computed(() => {
  if (!props.generateInfoStep?.response) return ''
  const response = props.generateInfoStep.response
  return response.generated?.tags || ''
})

// 解析标签文本为数组
const generatedTags = computed(() => {
  const tagsText = generatedTagsText.value
  if (!tagsText) return []
  // 提取所有 #标签 格式的内容
  const matches = tagsText.matchAll(/#([^\s#]+)/g)
  const tags: string[] = []
  for (const match of matches) {
    tags.push(match[1])
  }
  return tags
})

// 检查是否有生成的信息
const hasGeneratedInfo = computed(() => {
  return generatedTitle.value.trim() !== '' || generatedTags.value.length > 0
})

// 获取按钮文本
const getButtonText = () => {
  if (!hasValidImages.value) return '等待生成图片...'
  if (!hasGeneratedInfo.value) return '等待生成标题和标签...'
  return `发布到小红书 (${imageFiles.value.length} 张图片)`
}

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

// 将图片文件转换为 base64
const convertImageToBase64 = async (imagePath: string): Promise<string> => {
  try {
    // 使用 axios 获取图片
    const response = await axios.get(`http://localhost:8000/${imagePath}`, {
      responseType: 'arraybuffer'
    })
    const base64 = btoa(
      new Uint8Array(response.data).reduce((data, byte) => data + String.fromCharCode(byte), '')
    )
    return base64
  } catch (error) {
    console.error('Failed to load image:', imagePath, error)
    throw error
  }
}

const handlePublish = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    // 加载 cookies
    const cookiesResponse = await axios.get('http://localhost:8000/cookies/xiaohongshu/load', {
      headers: {
        'X-API-Key': '0d000721'
      }
    })

    if (!cookiesResponse.data.success) {
      throw new Error(cookiesResponse.data.error || '加载 cookies 失败')
    }

    const cookies = cookiesResponse.data.cookies

    // 转换所有图片为 base64
    const imageBase64List: string[] = []
    for (const imagePath of imageFiles.value) {
      const base64 = await convertImageToBase64(imagePath)
      imageBase64List.push(base64)
    }

    // 准备发布参数
    const publishParams = {
      cookies: cookies,
      title: generatedTitle.value,
      content: '', // 根据要求，content 为空
      images: imageBase64List,
      tags: generatedTags.value
    }

    // 调用小红书发布接口
    const response = await api.callXiaohongshuTool(publishParams)

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
      error: error.response?.data?.message || error.message || '发布到小红书失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
