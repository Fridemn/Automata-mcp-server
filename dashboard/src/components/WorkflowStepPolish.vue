<template>
  <div class="workflow-step-polish">
    <div class="flex flex-col gap-4">
      <textarea
        v-model="localContentToPolish"
        placeholder="要润色的内容"
        class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"
        :disabled="step.status === 'running'"
      ></textarea>
      <textarea
        v-model="localPolishPrompt"
        placeholder="润色提示词"
        class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"
        :disabled="step.status === 'running'"
      ></textarea>
      <button @click="handlePolishContent" :disabled="step.status === 'running' || !localContentToPolish" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
        润色内容
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
  contentToPolish: string
  polishPrompt: string
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  updateContentToPolish: [content: string]
  updatePolishPrompt: [prompt: string]
  updatePublishData: [data: string]
  saveState: []
}>()

const localContentToPolish = ref(props.contentToPolish)
const localPolishPrompt = ref(props.polishPrompt)

watch(() => props.contentToPolish, (newContent) => {
  localContentToPolish.value = newContent
})

watch(() => props.polishPrompt, (newPrompt) => {
  localPolishPrompt.value = newPrompt
})

const handlePolishContent = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.callPolishTool({
      original_text: localContentToPolish.value,
      prompt: localPolishPrompt.value
    })
    const completedStep = {
      ...updatedStep,
      response: response.data,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
    emit('updateContentToPolish', localContentToPolish.value)
    emit('updatePolishPrompt', localPolishPrompt.value)
    emit('updatePublishData', response.data.content?.[0]?.text || '')
    emit('saveState')
  } catch (error: any) {
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '润色内容失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
