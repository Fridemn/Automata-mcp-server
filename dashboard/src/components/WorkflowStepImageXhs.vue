<template>
  <div class="workflow-step-image-xhs">
    <div class="flex flex-col gap-4">
      <!-- 长文本内容输入 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">长文本内容</label>
        <textarea
          v-model="localContent"
          placeholder="输入要生成图片的长文本内容"
          class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical w-full"
          :disabled="step.status === 'running'"
        ></textarea>
      </div>

      <!-- 背景图片选择 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">选择背景图片</label>
        <input type="file" @change="handleFileSelect" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100" />
      </div>

      <!-- 背景图片预览 -->
      <div v-if="selectedFile" class="mt-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">背景图片预览</label>
        <img :src="previewUrl" alt="背景图片预览" class="max-w-full h-auto max-h-64 border rounded" />
      </div>

      <!-- 字体颜色选择 -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">字体颜色</label>
        <div class="flex gap-4">
          <label class="flex items-center">
            <input type="radio" v-model="fontColor" value="black" class="mr-2" />
            黑色
          </label>
          <label class="flex items-center">
            <input type="radio" v-model="fontColor" value="white" class="mr-2" />
            白色
          </label>
        </div>
      </div>

      <button @click="handleGenerateImage" :disabled="step.status === 'running' || !selectedFile || !localContent" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        生成长文本图片
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, ref, watch } from 'vue'
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
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  updatePublishData: [data: string]
  saveState: []
}>()

const selectedFile = ref<File | null>(null)
const previewUrl = ref<string>('')
const fontColor = ref<'black' | 'white'>('black')
const localContent = ref(props.publishData)

watch(() => props.publishData, (newContent) => {
  localContent.value = newContent
})

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedFile.value = file
    const reader = new FileReader()
    reader.onload = (e) => {
      previewUrl.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  } else {
    selectedFile.value = null
    previewUrl.value = ''
  }
}

const handleGenerateImage = async () => {
  if (!selectedFile.value) return

  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    // 生成输出目录：data/output_image
    const outputFolderPath = 'data/output_image'

    const formData = new FormData()
    formData.append('content', localContent.value)
    formData.append('background_image', selectedFile.value)
        formData.append('output_folder_path', outputFolderPath)
    formData.append('font_color', fontColor.value)

    const response = await axios.post('http://localhost:8000/tools/long-text-content', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'X-API-Key': '0d000721',
      },
      timeout: 180000,
    })
    const completedStep = {
      ...updatedStep,
      response: response.data,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
    // 更新publishData为生成的图片路径
    emit('updatePublishData', response.data.image_path || `${outputFolderPath}/generated.png`)
    emit('saveState')
  } catch (error: any) {
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '生成长文本图片失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
