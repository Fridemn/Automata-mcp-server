<template>
  <div class="min-h-[calc(100vh-64px)] bg-gradient-to-br from-blue-400 to-purple-600 font-['Segoe_UI',_Tahoma,_Geneva,_Verdana,_sans-serif]">
    <div class="max-w-[1400px] mx-auto px-5 py-5 flex flex-col lg:flex-row gap-5">
      <!-- 主内容区域 -->
      <div class="flex-1 order-2 lg:order-1">
        <div class="workflow-container">
          <div class="workflow-header mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">智能内容发布工作流</h1>
            <p class="text-white/80 text-lg">从知乎获取内容，AI润色，生成图片，一键发布到小红书</p>
          </div>

          <div class="workflow-steps">
          <div
            v-for="(step, index) in workflowSteps"
            :key="step.id"
            class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-5 mb-4 shadow-lg border border-white/20"
            :class="{
              'ring-2 ring-blue-500': currentStep === index,
              'bg-green-50 border-green-200': step.status === 'completed',
              'bg-red-50 border-red-200': step.status === 'error'
            }"
          >
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-semibold text-sm">{{ index + 1 }}</div>
                <div class="font-semibold text-gray-800">{{ step.title }}</div>
              </div>
              <div class="text-sm">
                <span v-if="step.status === 'pending'" class="px-2 py-1 bg-gray-200 text-gray-700 rounded">待执行</span>
                <span v-if="step.status === 'running'" class="px-2 py-1 bg-blue-500 text-white rounded animate-pulse">执行中</span>
                <span v-if="step.status === 'completed'" class="px-2 py-1 bg-green-500 text-white rounded">完成</span>
                <span v-if="step.status === 'error'" class="px-2 py-1 bg-red-500 text-white rounded">错误</span>
              </div>
            </div>

            <div class="step-content">
              <p class="text-gray-600 mb-4">{{ step.description }}</p>

              <!-- 步骤特定内容 -->
              <WorkflowStepCookiesXhs
                v-if="step.id === 'xiaohongshu-cookie'"
                :step="step"
                @update-step="updateStepStatus"
                @save-state="saveWorkflowState"
              />

              <WorkflowStepZhihu
                v-else-if="step.id === 'zhihu-get'"
                :step="step"
                :zhihu-url="zhihuUrl"
                @update-step="updateStepStatus"
                @update-zhihu-url="zhihuUrl = $event"
                @update-content-to-polish="contentToPolish = $event"
                @save-state="saveWorkflowState"
              />

              <WorkflowStepPolish
                v-else-if="step.id === 'polish'"
                :step="step"
                :content-to-polish="contentToPolish"
                :polish-prompt="polishPrompt"
                @update-step="updateStepStatus"
                @update-content-to-polish="contentToPolish = $event"
                @update-polish-prompt="polishPrompt = $event"
                @update-publish-data="polishedContent = $event"
                @save-state="saveWorkflowState"
              />

              <WorkflowStepImageXhs
                v-else-if="step.id === 'long-text-image'"
                :step="step"
                :publish-data="polishedContent"
                @update-step="updateStepStatus"
                @update-publish-data="imagePath = $event"
                @save-state="saveWorkflowState"
              />

              <WorkflowStepPublishXhs
                v-else-if="step.id === 'xiaohongshu-publish'"
                :step="step"
                :publish-data="imagePath"
                :image-generation-step="workflowSteps.find(s => s.id === 'long-text-image')"
                @update-step="updateStepStatus"
                @update-publish-data="imagePath = $event"
                @save-state="saveWorkflowState"
              />

              <div v-else class="text-center text-gray-500 py-4">
                步骤 {{ index + 1 }}: {{ step.title }}
              </div>

              <!-- 错误信息显示 -->
              <div v-if="step.error" class="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                <strong>错误:</strong> {{ step.error }}
              </div>

              <!-- 响应数据预览 -->
              <div v-if="step.response && step.status === 'completed'" class="mt-4">
                <details class="bg-gray-50 rounded p-3">
                  <summary class="cursor-pointer text-sm font-medium text-gray-700">查看响应数据</summary>
                  <pre class="mt-2 text-xs overflow-auto max-h-40 bg-white p-2 rounded border">{{ JSON.stringify(step.response, null, 2) }}</pre>
                </details>
              </div>
            </div>
          </div>
        </div>

        <div v-if="workflowProgress > 0" class="mt-6 w-full bg-white/20 rounded-full h-3 overflow-hidden relative">
          <div class="h-full bg-white transition-all duration-300" :style="{ width: workflowProgress + '%' }"></div>
          <span class="absolute inset-0 flex items-center justify-center text-white font-medium text-sm">{{ Math.round(workflowProgress) }}% 完成</span>
        </div>
      </div>
    </div>

    <!-- 右侧工作流控制侧边栏 -->
    <div class="w-full lg:w-[300px] order-1 lg:order-2">
      <div class="bg-white/95 rounded-2xl p-5 shadow-lg border border-white/20 lg:sticky lg:top-20">
        <div class="mb-5">
          <h3 class="m-0 text-gray-800 text-lg font-semibold">工作流控制</h3>
        </div>
        <div class="flex flex-col gap-3">
          <div class="mb-5 p-4 bg-black/5 rounded-lg">
            <h4 class="m-0 mb-3 text-gray-800 text-sm font-semibold">发布平台配置 <span class="text-red-500">*</span></h4>
            <p class="text-xs text-gray-500 mb-3">至少选择一个平台</p>
            <div class="flex flex-col gap-2">
              <label class="flex items-center gap-2 cursor-pointer text-sm text-gray-600">
                <input v-model="workflowConfig.platforms.xiaohongshu" type="checkbox" class="m-0" />
                <span>小红书</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer text-sm text-gray-600 opacity-50">
                <input v-model="workflowConfig.platforms.douyin" type="checkbox" class="m-0" disabled />
                <span>抖音 (即将推出)</span>
              </label>
            </div>
            <p v-if="!isAnyPlatformSelected" class="text-xs text-red-500 mt-2">请至少选择一个发布平台</p>
          </div>

          <button
            @click="runFullWorkflow"
            :disabled="isWorkflowRunning || !isAnyPlatformSelected"
            class="px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white border-none rounded-lg font-medium cursor-pointer transition-all duration-200 hover:shadow-lg disabled:bg-gray-400 disabled:cursor-not-allowed"
            :class="{ 'opacity-50': !isAnyPlatformSelected }"
          >
            {{ isWorkflowRunning ? '工作流执行中...' : '运行完整工作流' }}
          </button>
          <button @click="resetWorkflow" class="px-4 py-3 bg-gray-600 text-white border-none rounded-lg font-medium cursor-pointer transition-colors duration-200 hover:bg-gray-700">重置工作流</button>

          <div class="mt-4 p-3 bg-white/50 rounded-lg" v-if="currentWorkflowId">
            <p class="m-0 mb-1"><strong class="text-gray-800">当前工作流:</strong></p>
            <p class="m-0 mb-1 text-gray-700 text-sm break-all">{{ currentWorkflowId }}</p>
            <p class="m-0"><strong class="text-gray-800">进度:</strong> {{ Math.round(workflowProgress) }}%</p>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import WorkflowStepCookiesXhs from '@/components/WorkflowStepCookiesXhs.vue'
import WorkflowStepZhihu from '@/components/WorkflowStepZhihu.vue'
import WorkflowStepPolish from '@/components/WorkflowStepPolish.vue'
import WorkflowStepImageXhs from '@/components/WorkflowStepImageXhs.vue'
import WorkflowStepPublishXhs from '@/components/WorkflowStepPublishXhs.vue'

interface WorkflowStep {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'error'
  endpoint?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  response?: any
  error?: string
}

interface WorkflowConfig {
  platforms: {
    xiaohongshu: boolean
    douyin: boolean
  }
}

const workflowSteps = ref<WorkflowStep[]>([
  {
    id: 'xiaohongshu-cookie',
    title: '获取小红书Cookie',
    description: '获取小红书登录凭证，用于后续发布操作',
    status: 'pending',
    endpoint: '/cookies/xiaohongshu/get',
    method: 'POST'
  },
  {
    id: 'zhihu-get',
    title: '知乎内容获取',
    description: '从知乎文章URL获取原始内容',
    status: 'pending',
    endpoint: '/tools/zhihu-get',
    method: 'POST'
  },
  {
    id: 'polish',
    title: '内容润色',
    description: '使用AI对获取的内容进行润色优化',
    status: 'pending',
    endpoint: '/tools/polish',
    method: 'POST'
  },
  {
    id: 'long-text-image',
    title: '长文本生成图片',
    description: '将长文本内容转换为图片格式',
    status: 'pending',
    endpoint: '/tools/long-text-content',
    method: 'POST'
  },
  {
    id: 'xiaohongshu-publish',
    title: '小红书发布',
    description: '发布内容到小红书平台',
    status: 'pending',
    endpoint: '/tools/xiaohongshu',
    method: 'POST'
  }
])

const currentStep = ref(0)
const isWorkflowRunning = ref(false)
const workflowProgress = ref(0)
const currentWorkflowId = ref<string | null>('workflow-test')

// 工作流数据状态
const zhihuUrl = ref('')
const contentToPolish = ref('')
const polishPrompt = ref(`将小说内容进行适当的分行分段，并且对内容进行稍微省略，输出的文字使用场景是将文字附在图片上，作为小红书图文发布。

要求：
1. 500字左右；
2. 不要使用 markdown 语法，不要使用如"*"等符号；
3. 只输出正文部分，不要带有 tag、标题、作者等信息；`)
const polishedContent = ref('') // 润色后的内容，用于生成图片
const imagePath = ref('') // 生成的图片路径，用于发布

const workflowConfig = ref<WorkflowConfig>({
  platforms: {
    xiaohongshu: true,
    douyin: false
  }
})

// 检查是否至少选择了一个平台
const isAnyPlatformSelected = computed(() => {
  return workflowConfig.value.platforms.xiaohongshu || workflowConfig.value.platforms.douyin
})

const runFullWorkflow = () => {
  if (!isAnyPlatformSelected.value) {
    alert('请至少选择一个发布平台')
    return
  }

  isWorkflowRunning.value = true
  workflowProgress.value = 0
  currentStep.value = 0

  // 执行工作流
  executeWorkflow()
}

const executeWorkflow = async () => {
  for (let i = 0; i < workflowSteps.value.length; i++) {
    const step = workflowSteps.value[i]
    if (!step) continue

    currentStep.value = i
    step.status = 'running'

    // 模拟步骤执行
    await new Promise(resolve => setTimeout(resolve, 1000))

    step.status = 'completed'
    workflowProgress.value = ((i + 1) / workflowSteps.value.length) * 100
  }

  isWorkflowRunning.value = false
}

const resetWorkflow = () => {
  workflowSteps.value.forEach(step => {
    step.status = 'pending'
    step.error = undefined
    step.response = undefined
  })
  currentStep.value = 0
  workflowProgress.value = 0
  isWorkflowRunning.value = false

  // 重置工作流数据
  zhihuUrl.value = ''
  contentToPolish.value = ''
  polishedContent.value = ''
  imagePath.value = ''

  saveWorkflowState()
}

// 更新步骤状态
const updateStepStatus = (updatedStep: WorkflowStep) => {
  const index = workflowSteps.value.findIndex(s => s.id === updatedStep.id)
  if (index !== -1) {
    workflowSteps.value[index] = updatedStep
  }
}

// 保存工作流状态到 localStorage
const saveWorkflowState = () => {
  const state = {
    steps: workflowSteps.value,
    zhihuUrl: zhihuUrl.value,
    contentToPolish: contentToPolish.value,
    polishPrompt: polishPrompt.value,
    polishedContent: polishedContent.value,
    imagePath: imagePath.value,
    currentStep: currentStep.value,
    workflowProgress: workflowProgress.value,
    currentWorkflowId: currentWorkflowId.value
  }
  localStorage.setItem('workflow-state', JSON.stringify(state))
}

// 从 localStorage 加载工作流状态
const loadWorkflowState = () => {
  const savedState = localStorage.getItem('workflow-state')
  if (savedState) {
    try {
      const state = JSON.parse(savedState)
      if (state.steps) workflowSteps.value = state.steps
      if (state.zhihuUrl) zhihuUrl.value = state.zhihuUrl
      if (state.contentToPolish) contentToPolish.value = state.contentToPolish
      if (state.polishPrompt) polishPrompt.value = state.polishPrompt
      if (state.polishedContent) polishedContent.value = state.polishedContent
      if (state.imagePath) imagePath.value = state.imagePath
      if (state.currentStep !== undefined) currentStep.value = state.currentStep
      if (state.workflowProgress !== undefined) workflowProgress.value = state.workflowProgress
      if (state.currentWorkflowId) currentWorkflowId.value = state.currentWorkflowId
    } catch (e) {
      console.error('Failed to load workflow state:', e)
    }
  }
}

onMounted(() => {
  loadWorkflowState()
})
</script>
