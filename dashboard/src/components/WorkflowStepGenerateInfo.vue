<template>
  <div class="workflow-step-generate-info">
    <div class="flex flex-col gap-4">
      <button
        @click="handleGenerateInfo"
        :disabled="step.status === 'running' || !hasPolishedContent"
        class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {{ hasPolishedContent ? '生成标题和Tag' : '等待上一步润色内容...' }}
      </button>

      <!-- 显示生成的标题和Tag -->
      <div v-if="generatedTitle || generatedTags" class="mt-4 p-4 bg-gray-50 rounded border border-gray-200">
        <div v-if="generatedTitle" class="mb-3">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">生成的标题：</h3>
          <p class="text-gray-800">{{ generatedTitle }}</p>
        </div>
        <div v-if="generatedTags">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">生成的Tag：</h3>
          <p class="text-gray-800">{{ generatedTags }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, computed, ref } from 'vue'
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
  polishStep?: WorkflowStep
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  saveState: []
}>()

const generatedTitle = ref('')
const generatedTags = ref('')

// 检查是否有润色后的内容
const hasPolishedContent = computed(() => {
  if (!props.polishStep?.response) return false
  const response = props.polishStep.response
  if (response.content && Array.isArray(response.content)) {
    return response.content.some((item: any) => item.type === 'text' && item.text)
  }
  return false
})

// 从润色步骤中提取文本内容
const getPolishedText = (): string => {
  if (!props.polishStep?.response) return ''
  const response = props.polishStep.response
  if (response.content && Array.isArray(response.content)) {
    const textItem = response.content.find((item: any) => item.type === 'text')
    return textItem?.text || ''
  }
  return ''
}

const handleGenerateInfo = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const polishedText = getPolishedText()

    // 第一次调用：生成标题
    const titlePrompt = '请为以下小红书内容生成一个吸引人的标题，要求简洁、有吸引力、符合小红书风格，不超过20字。只输出标题文本，不要其他内容。'
    const titleResponse = await api.callPolishTool({
      original_text: polishedText,
      prompt: titlePrompt
    })

    // 提取标题
    if (titleResponse.data.content && Array.isArray(titleResponse.data.content)) {
      const textItem = titleResponse.data.content.find((item: any) => item.type === 'text')
      generatedTitle.value = textItem?.text || ''
    }

    // 第二次调用：生成Tag
    const tagPrompt = '请为以下小红书内容生成5-10个相关的话题标签(tag)，要求热门、相关性强、符合小红书风格。格式为：#标签1 #标签2 #标签3，只输出标签，不要其他内容。'
    const tagResponse = await api.callPolishTool({
      original_text: polishedText,
      prompt: tagPrompt
    })

    // 提取Tag
    if (tagResponse.data.content && Array.isArray(tagResponse.data.content)) {
      const textItem = tagResponse.data.content.find((item: any) => item.type === 'text')
      generatedTags.value = textItem?.text || ''
    }

    // 合并两次调用的结果
    const combinedResponse = {
      title: titleResponse.data,
      tags: tagResponse.data,
      generated: {
        title: generatedTitle.value,
        tags: generatedTags.value
      }
    }

    const completedStep = {
      ...updatedStep,
      response: combinedResponse,
      status: 'completed' as const
    }
    emit('updateStep', completedStep)
    emit('saveState')
  } catch (error: any) {
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '生成标题和Tag失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}
</script>
