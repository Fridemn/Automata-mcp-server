<template>
  <div class="workflow-step-zhihu">
    <div class="flex flex-col gap-4">
      <input
        v-model="localZhihuUrl"
        type="url"
        placeholder="输入知乎文章URL"
        class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25"
        :disabled="step.status === 'running'"
      />
      <button @click="handleFetchContent" :disabled="step.status === 'running' || !localZhihuUrl" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed">
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
