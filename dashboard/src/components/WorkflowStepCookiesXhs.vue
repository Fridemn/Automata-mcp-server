<template>
  <div class="workflow-step-cookies-xhs">
    <div class="mb-4 space-y-3">
      <!-- Cookie状态显示 -->
      <div v-if="cookieStatus" class="p-3 rounded-lg" :class="{
        'bg-green-50 border border-green-200': cookieStatus.valid,
        'bg-yellow-50 border border-yellow-200': !cookieStatus.valid && !cookieStatus.error,
        'bg-red-50 border border-red-200': cookieStatus.error
      }">
        <div class="flex flex-col gap-2">
          <div class="flex items-center gap-2">
            <span v-if="cookieStatus.valid" class="text-green-600 font-medium">✓ Cookie已存在且有效</span>
            <span v-else-if="cookieStatus.error" class="text-red-600 font-medium">✗ {{ cookieStatus.error }}</span>
            <span v-else class="text-yellow-600 font-medium">⚠ Cookie不存在或已过期</span>
          </div>

          <!-- 显示cookie详情 -->
          <div v-if="cookieStatus.valid && cookieStatus.cookies" class="text-sm text-gray-600">
            <div class="mt-1">
              <span class="font-medium">存储位置:</span> data/cookies/xhs.json
            </div>
            <div class="mt-1">
              <span class="font-medium">Cookie数量:</span> {{ getCookieCount(cookieStatus.cookies) }}
            </div>
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="flex gap-2">
        <button
          @click="handleValidateCookies"
          :disabled="step.status === 'running'"
          class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {{ step.status === 'running' ? '验证中...' : '验证Cookie' }}
        </button>
        <button
          v-if="!cookieStatus?.valid"
          @click="handleGetCookies"
          :disabled="step.status === 'running'"
          class="px-4 py-2 bg-gray-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-gray-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {{ step.status === 'running' ? '获取中...' : '获取新Cookie' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, ref, onMounted } from 'vue'
import * as api from '@/api/api'

interface WorkflowStep {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'error'
  response?: any
  error?: string
}

interface CookieStatus {
  valid: boolean
  error?: string
  cookies?: any
}

const props = defineProps<{
  step: WorkflowStep
}>()

const emit = defineEmits<{
  updateStep: [step: WorkflowStep]
  saveState: []
}>()

const cookieStatus = ref<CookieStatus | null>(null)

// 获取cookie数量
const getCookieCount = (cookies: any): number => {
  try {
    if (typeof cookies === 'string') {
      const parsed = JSON.parse(cookies)
      return Array.isArray(parsed) ? parsed.length : Object.keys(parsed).length
    }
    return Array.isArray(cookies) ? cookies.length : Object.keys(cookies).length
  } catch {
    return 0
  }
}

// 验证Cookie
const handleValidateCookies = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.validateXiaohongshuCookies()
    cookieStatus.value = response.data

    if (response.data.valid) {
      // Cookie有效，直接完成这一步
      const completedStep = {
        ...updatedStep,
        response: {
          message: 'Cookie验证成功，存储在 data/cookies/xhs.json',
          ...response.data
        },
        status: 'completed' as const
      }
      emit('updateStep', completedStep)
      emit('saveState')
    } else {
      // Cookie无效或不存在
      const pendingStep = {
        ...updatedStep,
        response: { message: 'Cookie不存在或已过期，请获取新Cookie', ...response.data },
        status: 'pending' as const
      }
      emit('updateStep', pendingStep)
    }
  } catch (error: any) {
    cookieStatus.value = { valid: false, error: error.message }
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '验证Cookie失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}

// 获取新Cookie
const handleGetCookies = async () => {
  const updatedStep = { ...props.step, status: 'running' as const, error: undefined }
  emit('updateStep', updatedStep)

  try {
    const response = await api.getXiaohongshuCookies({})

    // 获取成功后重新验证
    await handleValidateCookies()
  } catch (error: any) {
    cookieStatus.value = { valid: false, error: error.message }
    const errorStep = {
      ...updatedStep,
      status: 'error' as const,
      error: error.message || '获取小红书Cookie失败'
    }
    emit('updateStep', errorStep)
    emit('saveState')
  }
}

// 组件挂载时自动验证Cookie
onMounted(() => {
  handleValidateCookies()
})
</script>
