<template>
  <div class="workflow-step-publish-xhs">
    <div class="flex flex-col gap-4">
      <div v-if="props.publishData" class="mb-4">
        <label class="block text-sm font-medium text-gray-700 mb-2">生成的图片路径</label>
        <p class="text-sm text-gray-600">{{ props.publishData }}</p>
      </div>
      <button @click="handlePublish" :disabled="step.status === 'running' || !props.publishData" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        发布到小红书
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
  updatePublishData: [data: string]
  saveState: []
}>()

const handlePublish = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.callXiaohongshuTool({ image_path: props.publishData })
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
