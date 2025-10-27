<template>
  <div class="workflow-step-publish-dy">
    <div class="flex flex-col gap-4">
      <button @click="handlePublish" :disabled="step.status === 'running'" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        发布到抖音
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits } from 'vue'

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

const handlePublish = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    // TODO: 实现抖音发布API
    const response = { data: { success: true, message: '发布到抖音成功' } }
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
      error: error.message || '发布到抖音失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
