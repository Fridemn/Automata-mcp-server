<template>
  <div class="workflow-step-image-xhs">
    <div class="flex flex-col gap-4">
      <button @click="handleGenerateImage" :disabled="step.status === 'running'" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        生成长文本图片
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits } from 'vue'
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
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  saveState: []
}>()

const handleGenerateImage = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.callLongTextContentTool({
      content: props.publishData,
      background_image_path: '/path/to/default/background.jpg' // TODO: 需要配置背景图片路径
    })
    const completedStep = {
      ...updatedStep,
      response: response.data,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
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
