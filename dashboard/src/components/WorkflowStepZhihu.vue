<template>
  <div class="workflow-step-zhihu">
    <div class="step-inputs">
      <input
        v-model="localZhihuUrl"
        type="url"
        placeholder="输入知乎文章URL"
        class="input-field"
        :disabled="step.status === 'running'"
      />
      <button @click="handleFetchContent" :disabled="step.status === 'running' || !localZhihuUrl" class="btn-primary">
        获取内容
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
  zhihuUrl: string
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  updateZhihuUrl: [url: string]
  updateContentToPolish: [content: string]
  saveState: []
}>()

const localZhihuUrl = ref(props.zhihuUrl)

watch(() => props.zhihuUrl, (newUrl) => {
  localZhihuUrl.value = newUrl
})

const handleFetchContent = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.callZhihuGetTool({ url: localZhihuUrl.value })
    const completedStep = {
      ...updatedStep,
      response: response.data,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
    emit('updateZhihuUrl', localZhihuUrl.value)
    emit('updateContentToPolish', response.data.content?.[0]?.text || '')
    emit('saveState')
  } catch (error: any) {
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '获取知乎内容失败'
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

.input-field {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
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
