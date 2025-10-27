<template>
  <div class="workflow-step-polish">
    <div class="step-inputs">
      <textarea
        v-model="localContentToPolish"
        placeholder="要润色的内容"
        class="textarea-field"
        :disabled="step.status === 'running'"
      ></textarea>
      <textarea
        v-model="localPolishPrompt"
        placeholder="润色提示词"
        class="textarea-field"
        :disabled="step.status === 'running'"
      ></textarea>
      <button @click="handlePolishContent" :disabled="step.status === 'running' || !localContentToPolish" class="btn-primary">
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

<style scoped>
.step-inputs {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.textarea-field {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  min-height: 100px;
  resize: vertical;
}

.btn-primary {
  padding: 0.5rem 1rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
