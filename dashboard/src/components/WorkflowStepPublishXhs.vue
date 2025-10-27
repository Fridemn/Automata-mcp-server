<template>
  <div class="workflow-step-publish-xhs">
    <div class="flex flex-col gap-4">
      <textarea
        v-model="localPublishData"
        placeholder="要发布的内容"
        class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"
        :disabled="step.status === 'running'"
      ></textarea>
      <button @click="handlePublish" :disabled="step.status === 'running' || !localPublishData" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        发布到小红书
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, ref, watch } from 'vue'
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

const localPublishData = ref(props.publishData)

watch(() => props.publishData, (newData) => {
  localPublishData.value = newData
})

const handlePublish = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.callXiaohongshuTool({ data: localPublishData.value })
    const completedStep = {
      ...updatedStep,
      response: response.data,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
    emit('updatePublishData', localPublishData.value)
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
