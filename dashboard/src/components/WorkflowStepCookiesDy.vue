<template>
  <div class="workflow-step-cookies-dy">
    <div class="mb-4">
      <button @click="handleGetCookies" :disabled="step.status === 'running'" class="px-4 py-2 bg-gray-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-gray-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        获取抖音Cookie
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
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  saveState: []
}>()

const handleGetCookies = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.getDouyinCookies({})
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
      error: error.message || '获取抖音Cookie失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
