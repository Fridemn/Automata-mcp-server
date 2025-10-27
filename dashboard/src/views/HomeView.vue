<template>
  <div class="workflow-home">
    <!-- 左侧侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>工作流控制</h3>
      </div>
      <div class="sidebar-content">
        <div class="platform-config">
          <h4>发布平台配置</h4>
          <div class="platform-options">
            <label class="platform-option">
              <input v-model="workflowConfig.platforms.xiaohongshu" type="checkbox" />
              <span>小红书</span>
            </label>
            <label class="platform-option">
              <input v-model="workflowConfig.platforms.douyin" type="checkbox" />
              <span>抖音</span>
            </label>
          </div>
        </div>

        <button @click="runFullWorkflow" :disabled="isWorkflowRunning" class="btn-workflow">
          {{ isWorkflowRunning ? '工作流执行中...' : '运行完整工作流' }}
        </button>
        <button @click="resetWorkflow" class="btn-reset">重置工作流</button>
        <button @click="archiveWorkflow" class="btn-archive">归档工作流</button>
        <button @click="saveWorkflowState" class="btn-save">保存状态</button>
        <button @click="loadWorkflowState" class="btn-load">恢复状态</button>

        <div class="workflow-info" v-if="currentWorkflowId">
          <p><strong>当前工作流:</strong></p>
          <p>{{ currentWorkflowId }}</p>
          <p><strong>进度:</strong> {{ Math.round(workflowProgress) }}%</p>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <div class="workflow-container">
        <div class="workflow-header">
          <h1>智能内容发布工作流</h1>
          <p>自动化从知乎获取内容到发布到小红书的完整流程</p>
        </div>

        <div class="workflow-steps">
          <div
            v-for="(step, index) in workflowSteps"
            :key="step.id"
            class="step-card"
            :class="{ active: currentStep === index, completed: step.status === 'completed', error: step.status === 'error' }"
          >
          <div class="step-header">
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-title">{{ step.title }}</div>
            <div class="step-status">
              <span v-if="step.status === 'pending'" class="status pending">待执行</span>
              <span v-if="step.status === 'running'" class="status running">执行中</span>
              <span v-if="step.status === 'completed'" class="status completed">完成</span>
              <span v-if="step.status === 'error'" class="status error">错误</span>
            </div>
          </div>

          <div class="step-content">
            <p class="step-description">{{ step.description }}</p>

            <!-- Cookie获取步骤 -->
            <WorkflowStepCookiesXhs
              v-if="step.id === 'cookies-xhs'"
              :step="step"
              @update-step="updateStep"
              @save-state="saveWorkflowState"
            />

            <WorkflowStepCookiesDy
              v-if="step.id === 'cookies-dy'"
              :step="step"
              @update-step="updateStep"
              @save-state="saveWorkflowState"
            />

            <!-- 知乎内容获取步骤 -->
            <WorkflowStepZhihu
              v-if="step.id === 'zhihu'"
              :step="step"
              :zhihu-url="workflowData.zhihuUrl"
              @update-step="updateStep"
              @update-zhihu-url="updateZhihuUrl"
              @update-content-to-polish="updateContentToPolish"
              @save-state="saveWorkflowState"
            />

            <!-- 内容润色步骤 -->
            <WorkflowStepPolish
              v-if="step.id === 'polish'"
              :step="step"
              :content-to-polish="workflowData.contentToPolish"
              :polish-prompt="workflowData.polishPrompt"
              @update-step="updateStep"
              @update-content-to-polish="updateContentToPolish"
              @update-polish-prompt="updatePolishPrompt"
              @update-publish-data="updatePublishData"
              @save-state="saveWorkflowState"
            />

            <!-- 长文本图片生成步骤 -->
            <WorkflowStepImageXhs
              v-if="step.id === 'image-xhs'"
              :step="step"
              :publish-data="workflowData.publishData"
              @update-step="updateStep"
              @save-state="saveWorkflowState"
            />

            <!-- 视频剪辑步骤 -->
            <WorkflowStepVideoEdit
              v-if="step.id === 'video-edit'"
              :step="step"
              :publish-data="workflowData.publishData"
              :workflow-id="currentWorkflowId"
              @update-step="updateStep"
              @save-state="saveWorkflowState"
            />

            <!-- 小红书发布步骤 -->
            <WorkflowStepPublishXhs
              v-if="step.id === 'publish-xhs'"
              :step="step"
              :publish-data="workflowData.publishData"
              @update-step="updateStep"
              @update-publish-data="updatePublishData"
              @save-state="saveWorkflowState"
            />

            <!-- 抖音发布步骤 -->
            <WorkflowStepPublishDy
              v-if="step.id === 'publish-dy'"
              :step="step"
              @update-step="updateStep"
              @save-state="saveWorkflowState"
            />

            <!-- 响应显示 -->
            <div v-if="step.response" class="step-response">
              <ApiResponsePreview :response="step.response" />
            </div>

            <!-- 错误显示 -->
            <div v-if="step.error" class="step-error">
              <p>{{ step.error }}</p>
              <button @click="retryStep(step)" class="btn-retry">重试</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="workflowProgress > 0" class="progress-bar">
        <div class="progress-fill" :style="{ width: workflowProgress + '%' }"></div>
        <span class="progress-text">{{ Math.round(workflowProgress) }}% 完成</span>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as api from '../api/api'
import ApiResponsePreview from '../components/ApiResponsePreview.vue'
import WorkflowStepCookiesXhs from '../components/WorkflowStepCookiesXhs.vue'
import WorkflowStepCookiesDy from '../components/WorkflowStepCookiesDy.vue'
import WorkflowStepZhihu from '../components/WorkflowStepZhihu.vue'
import WorkflowStepPolish from '../components/WorkflowStepPolish.vue'
import WorkflowStepImageXhs from '../components/WorkflowStepImageXhs.vue'
import WorkflowStepVideoEdit from '../components/WorkflowStepVideoEdit.vue'
import WorkflowStepPublishXhs from '../components/WorkflowStepPublishXhs.vue'
import WorkflowStepPublishDy from '../components/WorkflowStepPublishDy.vue'
import '../assets/styles/HomeView.scss'

interface WorkflowStep {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'error'
  response?: any
  error?: string
}

interface WorkflowData {
  zhihuUrl: string
  contentToPolish: string
  polishPrompt: string
  publishData: string
}

interface WorkflowConfig {
  platforms: {
    xiaohongshu: boolean
    douyin: boolean
  }
}

interface WorkflowState {
  id: string
  steps: WorkflowStep[]
  data: WorkflowData
  config: WorkflowConfig
  currentStep: number
  progress: number
  completed: boolean
  timestamp: number
}

const workflowSteps = ref<WorkflowStep[]>([])

const workflowData = ref<WorkflowData>({
  zhihuUrl: '',
  contentToPolish: '',
  polishPrompt: '将小说内容进行适当的分行分段，并且对内容进行稍微省略，输出的文字使用场景是将文字附在图片上，作为小红书图文发布。\n\n要求：\n1. 500字左右；\n2. 不要使用 markdown 语法，不要使用如"*"等符号；\n3. 只输出正文部分，不要带有 tag、标题、作者等信息；',
  publishData: ''
})

const currentStep = ref(0)
const isWorkflowRunning = ref(false)
const workflowProgress = ref(0)
const currentWorkflowId = ref<string | null>(null)
const workflowConfig = ref<WorkflowConfig>({
  platforms: {
    xiaohongshu: true,
    douyin: false
  }
})

// 计算属性：当前步骤
const currentStepData = computed(() => workflowSteps.value[currentStep.value])

// 根据配置生成工作流步骤
const generateWorkflowSteps = (): WorkflowStep[] => {
  const steps: WorkflowStep[] = []

  // Cookie获取步骤 - 根据平台选择
  if (workflowConfig.value.platforms.xiaohongshu) {
    steps.push({
      id: 'cookies-xhs',
      title: '获取小红书Cookie',
      description: '获取小红书的登录Cookie',
      status: 'pending'
    })
  }

  if (workflowConfig.value.platforms.douyin) {
    steps.push({
      id: 'cookies-dy',
      title: '获取抖音Cookie',
      description: '获取抖音的登录Cookie',
      status: 'pending'
    })
  }

  // 知乎内容获取
  steps.push({
    id: 'zhihu',
    title: '获取知乎内容',
    description: '从知乎文章URL获取内容',
    status: 'pending'
  })

  // 内容润色
  steps.push({
    id: 'polish',
    title: '润色内容',
    description: '对获取的内容进行AI润色',
    status: 'pending'
  })

  // 根据平台添加后续步骤
  if (workflowConfig.value.platforms.xiaohongshu) {
    steps.push({
      id: 'image-xhs',
      title: '生成长文本图片',
      description: '将润色后的内容转换为长文本图片',
      status: 'pending'
    })

    steps.push({
      id: 'publish-xhs',
      title: '发布到小红书',
      description: '将最终内容发布到小红书',
      status: 'pending'
    })
  }

  if (workflowConfig.value.platforms.douyin) {
    steps.push({
      id: 'video-edit',
      title: '剪辑视频',
      description: '使用剪映对内容进行视频剪辑',
      status: 'pending'
    })

    steps.push({
      id: 'publish-dy',
      title: '发布到抖音',
      description: '将剪辑后的视频发布到抖音',
      status: 'pending'
    })
  }

  return steps
}

// 开始新工作流
const startNewWorkflow = () => {
  const timestamp = Date.now()
  currentWorkflowId.value = `workflow-${timestamp}`

  // 重置所有状态
  workflowSteps.value = generateWorkflowSteps()
  workflowData.value = {
    zhihuUrl: '',
    contentToPolish: '',
    polishPrompt: '将小说内容进行适当的分行分段，并且对内容进行稍微省略，输出的文字使用场景是将文字附在图片上，作为小红书图文发布。\n\n要求：\n1. 500字左右；\n2. 不要使用 markdown 语法，不要使用如"*"等符号；\n3. 只输出正文部分，不要带有 tag、标题、作者等信息；',
    publishData: ''
  }
  workflowConfig.value = {
    platforms: {
      xiaohongshu: true,
      douyin: false
    }
  }
  currentStep.value = 0
  workflowProgress.value = 0
  isWorkflowRunning.value = false

  // 保存初始状态
  saveWorkflowState()
}// 检查并获取必要的cookies
const checkAndGetCookies = async () => {
  const platforms = workflowConfig.value.platforms

  if (platforms.xiaohongshu) {
    try {
      const validation = await api.validateXiaohongshuCookies()
      if (!validation.data.valid) {
        // Cookie无效，需要重新获取
        await getXiaohongshuCookies()
      }
    } catch (error) {
      // 验证失败，尝试获取
      await getXiaohongshuCookies()
    }
  }

  if (platforms.douyin) {
    try {
      const validation = await api.validateDouyinCookies()
      if (!validation.data.valid) {
        // Cookie无效，需要重新获取
        await getDouyinCookies()
      }
    } catch (error) {
      // 验证失败，尝试获取
      await getDouyinCookies()
    }
  }
}

// 获取抖音Cookie
const getDouyinCookies = async () => {
  const step = workflowSteps.value.find(s => s.id === 'cookies-dy')
  if (!step) return

  step.status = 'running'
  try {
    const response = await api.getDouyinCookies({})
    step.response = response.data
    step.status = 'completed'
    step.error = undefined
    saveWorkflowState()
  } catch (error: any) {
    step.status = 'error'
    step.error = error.message || '获取抖音Cookie失败'
    saveWorkflowState()
  }
}

// 获取小红书Cookie
const getXiaohongshuCookies = async () => {
  const step = workflowSteps.value.find(s => s.id === 'cookies-xhs')
  if (!step) return

  step.status = 'running'
  try {
    const response = await api.getXiaohongshuCookies({})
    step.response = response.data
    step.status = 'completed'
    step.error = undefined
    saveWorkflowState()
  } catch (error: any) {
    step.status = 'error'
    step.error = error.message || '获取小红书Cookie失败'
    saveWorkflowState()
  }
}

// 执行单个步骤
const executeStep = async (step: WorkflowStep) => {
  step.status = 'running'
  step.error = undefined

  try {
    let response
    switch (step.id) {
      case 'cookies-xhs':
        response = await api.getXiaohongshuCookies({})
        break
      case 'cookies-dy':
        response = await api.getDouyinCookies({})
        break
      case 'zhihu':
        response = await api.callZhihuGetTool({ url: workflowData.value.zhihuUrl })
        workflowData.value.contentToPolish = response.data.content?.[0]?.text || ''
        break
      case 'polish':
        response = await api.callPolishTool({
          original_text: workflowData.value.contentToPolish,
          prompt: workflowData.value.polishPrompt
        })
        workflowData.value.publishData = response.data.content?.[0]?.text || ''
        break
      case 'image-xhs':
        response = await api.callLongTextContentTool({
          content: workflowData.value.publishData,
          background_image_path: '/path/to/default/background.jpg' // TODO: 需要配置背景图片路径
        })
        break
      case 'publish-xhs':
        response = await api.callXiaohongshuTool({ data: workflowData.value.publishData })
        break
      case 'video-edit':
        response = await api.editVideo({
          content: workflowData.value.publishData,
          workflow_id: currentWorkflowId.value
        })
        break
      case 'publish-dy':
        // TODO: 抖音发布API
        response = { data: { success: true, message: '发布到抖音成功' } }
        break
    }

    step.response = response?.data
    step.status = 'completed'
    saveWorkflowState() // 保存状态
  } catch (error: any) {
    step.status = 'error'
    step.error = error.message || `${step.title}执行失败`
    saveWorkflowState() // 保存状态
  }
}

// 更新步骤状态
const updateStep = (updatedStep: WorkflowStep) => {
  const index = workflowSteps.value.findIndex(s => s.id === updatedStep.id)
  if (index !== -1) {
    workflowSteps.value[index] = updatedStep
  }
}

// 更新知乎URL
const updateZhihuUrl = (url: string) => {
  workflowData.value.zhihuUrl = url
}

// 更新待润色内容
const updateContentToPolish = (content: string) => {
  workflowData.value.contentToPolish = content
}

// 更新润色提示词
const updatePolishPrompt = (prompt: string) => {
  workflowData.value.polishPrompt = prompt
}

// 更新发布数据
const updatePublishData = (data: string) => {
  workflowData.value.publishData = data
}

// 重试步骤
const retryStep = (step: WorkflowStep) => {
  executeStep(step)
}

// 运行完整工作流
const runFullWorkflow = async () => {
  isWorkflowRunning.value = true
  workflowProgress.value = 0

  // 重新生成步骤以确保使用最新配置
  workflowSteps.value = generateWorkflowSteps()

  // 首先检查并获取必要的cookies
  await checkAndGetCookies()

  for (let i = 0; i < workflowSteps.value.length; i++) {
    const step = workflowSteps.value[i]
    if (!step) continue

    currentStep.value = i

    // Cookie步骤已经处理过了，跳过
    if (step.id.startsWith('cookies-')) {
      continue
    }

    await executeStep(step)
    workflowProgress.value = ((i + 1) / workflowSteps.value.length) * 100

    if (step.status === 'error') {
      break // 如果有错误，停止工作流
    }
  }

  isWorkflowRunning.value = false
  archiveWorkflow() // 自动归档完成的工作流
}

// 归档当前工作流
const archiveWorkflow = () => {
  if (!currentWorkflowId.value) return

  try {
    const saved = localStorage.getItem(currentWorkflowId.value)
    if (saved) {
      const state: WorkflowState = JSON.parse(saved)
      state.completed = true
      localStorage.setItem(currentWorkflowId.value, JSON.stringify(state))
    }
  } catch (error) {
    console.error('归档工作流失败:', error)
  }

  // 开始新工作流
  startNewWorkflow()
}

// 重置工作流
const resetWorkflow = () => {
  startNewWorkflow()
}

// 保存工作流状态到localStorage
const saveWorkflowState = () => {
  if (!currentWorkflowId.value) return

  const state: WorkflowState = {
    id: currentWorkflowId.value,
    steps: workflowSteps.value,
    data: workflowData.value,
    config: workflowConfig.value,
    currentStep: currentStep.value,
    progress: workflowProgress.value,
    completed: false,
    timestamp: parseInt(currentWorkflowId.value.replace('workflow-', ''))
  }
  localStorage.setItem(currentWorkflowId.value, JSON.stringify(state))
}// 从localStorage加载工作流状态
const loadWorkflowState = () => {
  try {
    // 查找所有工作流keys
    const keys = Object.keys(localStorage).filter(key => key.startsWith('workflow-'))
    if (keys.length === 0) {
      startNewWorkflow()
      return
    }

    // 找到最新的未完成工作流
    let latestIncomplete: WorkflowState | null = null
    for (const key of keys) {
      const saved = localStorage.getItem(key)
      if (saved) {
        const state: WorkflowState = JSON.parse(saved)
        if (!state.completed && (!latestIncomplete || state.timestamp > latestIncomplete.timestamp)) {
          latestIncomplete = state
        }
      }
    }

    if (latestIncomplete) {
      // 加载未完成的工作流
      workflowSteps.value = latestIncomplete.steps
      workflowData.value = latestIncomplete.data
      workflowConfig.value = latestIncomplete.config || { platforms: { xiaohongshu: true, douyin: false } }
      currentStep.value = latestIncomplete.currentStep
      workflowProgress.value = latestIncomplete.progress
      currentWorkflowId.value = latestIncomplete.id
    } else {
      // 没有未完成的工作流，开始新的
      startNewWorkflow()
    }
  } catch (error) {
    console.error('加载工作流状态失败:', error)
    startNewWorkflow()
  }
}

// 组件挂载时加载状态
onMounted(() => {
  loadWorkflowState()
})
</script>
