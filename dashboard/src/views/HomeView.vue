<template>
  <div class="workflow-home">
    <!-- 左侧侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>工作流控制</h3>
      </div>
      <div class="sidebar-content">
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
            <div v-if="step.id === 'cookies'" class="step-inputs">
              <div class="cookie-buttons">
                <button @click="getDouyinCookies" :disabled="step.status === 'running'" class="btn-secondary">
                  获取抖音Cookie
                </button>
                <button @click="getXiaohongshuCookies" :disabled="step.status === 'running'" class="btn-secondary">
                  获取小红书Cookie
                </button>
              </div>
            </div>

            <!-- 知乎内容获取步骤 -->
            <div v-if="step.id === 'zhihu'" class="step-inputs">
              <input
                v-model="workflowData.zhihuUrl"
                type="url"
                placeholder="输入知乎文章URL"
                class="input-field"
                :disabled="step.status === 'running'"
              />
              <button @click="executeStep(step)" :disabled="step.status === 'running' || !workflowData.zhihuUrl" class="btn-primary">
                获取内容
              </button>
            </div>

            <!-- 内容润色步骤 -->
            <div v-if="step.id === 'polish'" class="step-inputs">
              <textarea
                v-model="workflowData.contentToPolish"
                placeholder="要润色的内容"
                class="textarea-field"
                :disabled="step.status === 'running'"
              ></textarea>
              <textarea
                v-model="workflowData.polishPrompt"
                placeholder="润色提示词"
                class="textarea-field"
                :disabled="step.status === 'running'"
              ></textarea>
              <button @click="executeStep(step)" :disabled="step.status === 'running' || !workflowData.contentToPolish" class="btn-primary">
                润色内容
              </button>
            </div>

            <!-- 长文本图片生成步骤 -->
            <div v-if="step.id === 'image'" class="step-inputs">
              <button @click="executeStep(step)" :disabled="step.status === 'running'" class="btn-primary">
                生成长文本图片
              </button>
            </div>

            <!-- 小红书发布步骤 -->
            <div v-if="step.id === 'publish'" class="step-inputs">
              <textarea
                v-model="workflowData.publishData"
                placeholder="要发布的内容"
                class="textarea-field"
                :disabled="step.status === 'running'"
              ></textarea>
              <button @click="executeStep(step)" :disabled="step.status === 'running' || !workflowData.publishData" class="btn-primary">
                发布到小红书
              </button>
            </div>

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

interface WorkflowState {
  id: string
  steps: WorkflowStep[]
  data: WorkflowData
  currentStep: number
  progress: number
  completed: boolean
  timestamp: number
}

const workflowSteps = ref<WorkflowStep[]>([
  {
    id: 'cookies',
    title: '获取Cookie',
    description: '获取抖音或小红书的登录Cookie',
    status: 'pending'
  },
  {
    id: 'zhihu',
    title: '获取知乎内容',
    description: '从知乎文章URL获取内容',
    status: 'pending'
  },
  {
    id: 'polish',
    title: '润色内容',
    description: '对获取的内容进行AI润色',
    status: 'pending'
  },
  {
    id: 'image',
    title: '生成长文本图片',
    description: '将润色后的内容转换为长文本图片',
    status: 'pending'
  },
  {
    id: 'publish',
    title: '发布到小红书',
    description: '将最终内容发布到小红书',
    status: 'pending'
  }
])

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

// 计算属性：当前步骤
const currentStepData = computed(() => workflowSteps.value[currentStep.value])

// 开始新工作流
const startNewWorkflow = () => {
  const timestamp = Date.now()
  currentWorkflowId.value = `workflow-${timestamp}`

  // 重置所有状态
  workflowSteps.value.forEach(step => {
    step.status = 'pending'
    step.response = undefined
    step.error = undefined
  })
  workflowData.value = {
    zhihuUrl: '',
    contentToPolish: '',
    polishPrompt: '将小说内容进行适当的分行分段，并且对内容进行稍微省略，输出的文字使用场景是将文字附在图片上，作为小红书图文发布。\n\n要求：\n1. 500字左右；\n2. 不要使用 markdown 语法，不要使用如"*"等符号；\n3. 只输出正文部分，不要带有 tag、标题、作者等信息；',
    publishData: ''
  }
  currentStep.value = 0
  workflowProgress.value = 0
  isWorkflowRunning.value = false

  // 保存初始状态
  saveWorkflowState()
}

// 获取抖音Cookie
const getDouyinCookies = async () => {
  const step = workflowSteps.value.find(s => s.id === 'cookies')
  if (!step) return

  step.status = 'running'
  try {
    const response = await api.getDouyinCookies({})
    step.response = response.data
    step.status = 'completed'
    step.error = undefined
  } catch (error: any) {
    step.status = 'error'
    step.error = error.message || '获取抖音Cookie失败'
  }
}

// 获取小红书Cookie
const getXiaohongshuCookies = async () => {
  const step = workflowSteps.value.find(s => s.id === 'cookies')
  if (!step) return

  step.status = 'running'
  try {
    const response = await api.getXiaohongshuCookies({})
    step.response = response.data
    step.status = 'completed'
    step.error = undefined
  } catch (error: any) {
    step.status = 'error'
    step.error = error.message || '获取小红书Cookie失败'
  }
}

// 执行单个步骤
const executeStep = async (step: WorkflowStep) => {
  step.status = 'running'
  step.error = undefined

  try {
    let response
    switch (step.id) {
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
      case 'image':
        response = await api.callLongTextContentTool({
          content: workflowData.value.publishData,
          background_image_path: '/path/to/default/background.jpg' // TODO: 需要配置背景图片路径
        })
        break
      case 'publish':
        response = await api.callXiaohongshuTool({ data: workflowData.value.publishData })
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

// 重试步骤
const retryStep = (step: WorkflowStep) => {
  executeStep(step)
}

// 运行完整工作流
const runFullWorkflow = async () => {
  isWorkflowRunning.value = true
  workflowProgress.value = 0

  for (let i = 0; i < workflowSteps.value.length; i++) {
    const step = workflowSteps.value[i]
    if (!step) continue

    currentStep.value = i

    if (step.id === 'cookies') {
      // Cookie步骤需要手动处理，跳过自动执行
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
    currentStep: currentStep.value,
    progress: workflowProgress.value,
    completed: false,
    timestamp: parseInt(currentWorkflowId.value.replace('workflow-', ''))
  }
  localStorage.setItem(currentWorkflowId.value, JSON.stringify(state))
}

// 从localStorage加载工作流状态
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

<style scoped lang="scss">
.workflow-home {
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  display: flex;
}

.sidebar {
  width: 280px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 20px;
  margin-right: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  height: fit-content;
  position: sticky;
  top: 20px;
}

.sidebar-header {
  margin-bottom: 20px;

  h3 {
    margin: 0;
    color: #333;
    font-size: 1.2rem;
    font-weight: 600;
  }
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-content button {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
}

.btn-workflow {
  background: linear-gradient(135deg, #007bff, #0056b3);
  color: white;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #0056b3, #004085);
    transform: translateY(-1px);
  }

  &:disabled {
    background: #6c757d;
    cursor: not-allowed;
  }
}

.btn-reset {
  background: #6c757d;
  color: white;

  &:hover {
    background: #5a6268;
  }
}

.btn-archive {
  background: #28a745;
  color: white;

  &:hover {
    background: #218838;
  }
}

.btn-save {
  background: #ffc107;
  color: #212529;

  &:hover {
    background: #e0a800;
  }
}

.btn-load {
  background: #17a2b8;
  color: white;

  &:hover {
    background: #138496;
  }
}

.workflow-info {
  margin-top: 20px;
  padding: 15px;
  background: rgba(0,0,0,0.05);
  border-radius: 8px;
  font-size: 13px;

  p {
    margin: 5px 0;
    color: #666;

    strong {
      color: #333;
    }
  }
}

.main-content {
  flex: 1;
  min-width: 0;
}

.workflow-container {
  max-width: 1200px;
  margin: 0 auto;
}

.workflow-header {
  text-align: center;
  margin-bottom: 40px;
  color: white;

  h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
    font-weight: 300;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
  }

  p {
    font-size: 1.2rem;
    opacity: 0.9;
    margin: 0;
  }
}

.workflow-steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 40px;
}

.step-card {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 30px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;

  &.active {
    border-color: #007bff;
    box-shadow: 0 8px 32px rgba(0,123,255,0.2);
  }

  &.completed {
    border-color: #28a745;
    background: rgba(40, 167, 69, 0.05);
  }

  &.error {
    border-color: #dc3545;
    background: rgba(220, 53, 69, 0.05);
  }
}

.step-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 15px;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #007bff;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.2rem;
}

.step-card.completed .step-number {
  background: #28a745;
}

.step-card.error .step-number {
  background: #dc3545;
}

.step-title {
  font-size: 1.4rem;
  font-weight: 600;
  color: #333;
  flex: 1;
}

.step-status {
  .status {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 500;

    &.pending {
      background: #e9ecef;
      color: #6c757d;
    }

    &.running {
      background: #cce5ff;
      color: #007bff;
    }

    &.completed {
      background: #d4edda;
      color: #155724;
    }

    &.error {
      background: #f8d7da;
      color: #721c24;
    }
  }
}

.step-description {
  color: #666;
  margin-bottom: 20px;
  line-height: 1.5;
}

.step-inputs {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.cookie-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.input-field, .textarea-field {
  padding: 12px 16px;
  border: 2px solid #dee2e6;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.3s ease;

  &:focus {
    outline: none;
    border-color: #007bff;
    box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
  }

  &:disabled {
    background: #f8f9fa;
    cursor: not-allowed;
  }
}

.textarea-field {
  min-height: 120px;
  resize: vertical;
  line-height: 1.5;
}

.btn-primary, .btn-secondary, .btn-workflow, .btn-reset, .btn-save, .btn-load, .btn-retry {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
  color: white;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
    transform: translateY(-2px);
  }
}

.btn-secondary {
  background: #6c757d;
  color: white;

  &:hover:not(:disabled) {
    background: #5a6268;
    transform: translateY(-2px);
  }
}

.btn-workflow {
  background: linear-gradient(135deg, #28a745 0%, #218838 100%);
  color: white;
  font-size: 16px;
  padding: 15px 30px;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
    transform: translateY(-2px);
  }
}

.btn-reset {
  background: #dc3545;
  color: white;

  &:hover:not(:disabled) {
    background: #c82333;
    transform: translateY(-2px);
  }
}

.btn-save, .btn-load {
  background: #ffc107;
  color: #212529;

  &:hover:not(:disabled) {
    background: #e0a800;
    transform: translateY(-2px);
  }
}

.btn-retry {
  background: #17a2b8;
  color: white;
  font-size: 12px;
  padding: 8px 16px;

  &:hover:not(:disabled) {
    background: #138496;
    transform: translateY(-2px);
  }
}

.step-response, .step-error {
  margin-top: 20px;
  padding: 15px;
  border-radius: 8px;
}

.step-response {
  background: #f8f9fa;
  border-left: 4px solid #17a2b8;

  pre {
    background: white;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 12px;
    margin: 0;
    max-height: 300px;
    overflow-y: auto;
  }
}

.step-error {
  background: #f8d7da;
  border-left: 4px solid #dc3545;
  color: #721c24;

  p {
    margin: 0 0 10px 0;
  }
}

.workflow-controls {
  display: flex;
  justify-content: center;
  gap: 15px;
  margin-bottom: 30px;
  flex-wrap: wrap;
}

.progress-bar {
  width: 100%;
  height: 30px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 15px;
  overflow: hidden;
  position: relative;

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
    transition: width 0.3s ease;
  }

  .progress-text {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-weight: 600;
    font-size: 14px;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
  }
}

@media (max-width: 768px) {
  .workflow-home {
    padding: 15px;
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    margin-right: 0;
    margin-bottom: 20px;
    position: static;
  }

  .workflow-header h1 {
    font-size: 2rem;
  }

  .step-card {
    padding: 20px;
  }

  .step-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .cookie-buttons {
    flex-direction: column;
  }

  .btn-primary, .btn-secondary, .btn-workflow, .btn-reset, .btn-save, .btn-load, .btn-archive {
    width: 100%;
  }
}
</style>
