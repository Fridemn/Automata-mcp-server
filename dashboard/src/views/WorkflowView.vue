<template>
  <div class="min-h-[calc(100vh-60px)] p-5 bg-gradient-to-br from-blue-400 to-purple-600 font-['Segoe_UI',_Tahoma,_Geneva,_Verdana,_sans-serif] flex flex-col">
    <h1 class="text-3xl font-bold text-white mb-4">工作流</h1>
    <p class="text-white/80 mb-6">此工作流将执行以下步骤：</p>
    <ol class="text-white/90 mb-8 space-y-1">
      <li>获取抖音或小红书的登录cookie</li>
      <li>输入知乎链接并获取内容</li>
      <li>对获取的内容进行润色</li>
      <li>从润色后的内容生成长文本图片</li>
      <li>发布到小红书</li>
    </ol>

    <div class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">步骤 1: 获取Cookie</h2>
      <div class="flex gap-4 mb-4">
        <button @click="getDouyinCookies" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600">获取抖音Cookie</button>
        <button @click="getXiaohongshuCookies" class="px-4 py-2 bg-gray-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-gray-600">获取小红书Cookie</button>
      </div>
      <div v-if="cookiesResponse" class="mt-4">
        <ApiResponsePreview :response="cookiesResponse" />
      </div>
    </div>

    <div class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">步骤 2: 获取知乎内容</h2>
      <div class="flex flex-col gap-4">
        <input v-model="zhihuUrl" type="text" placeholder="输入知乎URL" class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25" />
        <button @click="fetchZhihuContent" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600">获取内容</button>
      </div>
      <div v-if="zhihuResponse" class="mt-4">
        <ApiResponsePreview :response="zhihuResponse" />
      </div>
    </div>

    <div class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">步骤 3: 润色内容</h2>
      <div class="flex flex-col gap-4">
        <textarea v-model="contentToPolish" placeholder="要润色的内容" class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"></textarea>
        <textarea v-model="polishPrompt" placeholder="润色提示词" class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"></textarea>
        <button @click="polishContent" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600">润色内容</button>
      </div>
      <div v-if="polishResponse" class="mt-4">
        <ApiResponsePreview :response="polishResponse" />
      </div>
    </div>

    <div class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">步骤 4: 生成长文本图片</h2>
      <button @click="generateLongTextImage" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600">生成图片</button>
      <div v-if="imageResponse" class="mt-4">
        <ApiResponsePreview :response="imageResponse" />
      </div>
    </div>

    <div class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">步骤 5: 发布到小红书</h2>
      <div class="flex flex-col gap-4">
        <textarea v-model="publishData" placeholder="要发布的数据" class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"></textarea>
        <button @click="publishToXiaohongshu" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600">发布</button>
      </div>
      <div v-if="publishResponse" class="mt-4">
        <ApiResponsePreview :response="publishResponse" />
      </div>
    </div>

    <div class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">运行完整工作流</h2>
      <div class="flex gap-4 mb-4">
        <button @click="runFullWorkflow" class="px-4 py-2 bg-green-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-green-600">运行工作流</button>
        <button @click="archiveWorkflow" class="px-4 py-2 bg-gray-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-gray-600">归档工作流</button>
      </div>
      <div v-if="workflowStatus" class="mt-4 p-4 bg-gray-50 rounded">
        <pre class="text-sm">{{ workflowStatus }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import * as api from '../api/api';
import ApiResponsePreview from '../components/ApiResponsePreview.vue';

interface WorkflowData {
  zhihuUrl: string
  contentToPolish: string
  polishPrompt: string
  publishData: string
}

interface WorkflowState {
  id: string
  data: WorkflowData
  completed: boolean
  timestamp: number
}

const zhihuUrl = ref('');
const contentToPolish = ref('');
const polishPrompt = ref('将小说内容进行适当的分行分段，并且对内容进行稍微省略，输出的文字使用场景是将文字附在图片上，作为小红书图文发布。\n\n要求：\n1. 500字左右；\n2. 不要使用 markdown 语法，不要使用如"*"等符号；\n3. 只输出正文部分，不要带有 tag、标题、作者等信息；');
const publishData = ref('');
const cookiesResponse = ref<unknown>(null);
const zhihuResponse = ref<unknown>(null);
const polishResponse = ref<unknown>(null);
const imageResponse = ref<unknown>(null);
const publishResponse = ref<unknown>(null);
const workflowStatus = ref('');
const currentWorkflowId = ref<string | null>(null);

// 开始新工作流
const startNewWorkflow = () => {
  const timestamp = Date.now()
  currentWorkflowId.value = `workflow-${timestamp}`

  zhihuUrl.value = ''
  contentToPolish.value = ''
  polishPrompt.value = '将小说内容进行适当的分行分段，并且对内容进行稍微省略，输出的文字使用场景是将文字附在图片上，作为小红书图文发布。\n\n要求：\n1. 500字左右；\n2. 不要使用 markdown 语法，不要使用如"*"等符号；\n3. 只输出正文部分，不要带有 tag、标题、作者等信息；'
  publishData.value = ''
  cookiesResponse.value = null
  zhihuResponse.value = null
  polishResponse.value = null
  imageResponse.value = null
  publishResponse.value = null
  workflowStatus.value = ''

  saveWorkflowState()
}

// 保存工作流状态
const saveWorkflowState = () => {
  if (!currentWorkflowId.value) return

  const data: WorkflowData = {
    zhihuUrl: zhihuUrl.value,
    contentToPolish: contentToPolish.value,
    polishPrompt: polishPrompt.value,
    publishData: publishData.value
  }

  const state: WorkflowState = {
    id: currentWorkflowId.value,
    data,
    completed: false,
    timestamp: parseInt(currentWorkflowId.value.replace('workflow-', ''))
  }
  localStorage.setItem(currentWorkflowId.value, JSON.stringify(state))
}

// 加载工作流状态
const loadWorkflowState = () => {
  try {
    const keys = Object.keys(localStorage).filter(key => key.startsWith('workflow-'))
    if (keys.length === 0) {
      startNewWorkflow()
      return
    }

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
      zhihuUrl.value = latestIncomplete.data.zhihuUrl
      contentToPolish.value = latestIncomplete.data.contentToPolish
      polishPrompt.value = latestIncomplete.data.polishPrompt
      publishData.value = latestIncomplete.data.publishData
      currentWorkflowId.value = latestIncomplete.id
    } else {
      startNewWorkflow()
    }
  } catch (error) {
    console.error('加载工作流状态失败:', error)
    startNewWorkflow()
  }
}

// 归档工作流
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

  startNewWorkflow()
}

// 组件挂载时加载
onMounted(() => {
  loadWorkflowState()
})

const getDouyinCookies = async () => {
  try {
    const response = await api.getDouyinCookies({});
    cookiesResponse.value = response.data;
    saveWorkflowState()
  } catch (error: unknown) {
    cookiesResponse.value = { error: (error as Error).message };
  }
};

const getXiaohongshuCookies = async () => {
  try {
    const response = await api.getXiaohongshuCookies({});
    cookiesResponse.value = response.data;
    saveWorkflowState()
  } catch (error: unknown) {
    cookiesResponse.value = { error: (error as Error).message };
  }
};

const fetchZhihuContent = async () => {
  try {
    const response = await api.callZhihuGetTool({ url: zhihuUrl.value });
    zhihuResponse.value = response.data;
    contentToPolish.value = response.data.content?.[0]?.text || '';
    saveWorkflowState()
  } catch (error: unknown) {
    zhihuResponse.value = { error: (error as Error).message };
  }
};

const polishContent = async () => {
  try {
    const response = await api.callPolishTool({
      original_text: contentToPolish.value,
      prompt: polishPrompt.value
    });
    polishResponse.value = response.data;
    publishData.value = response.data.content?.[0]?.text || '';
    saveWorkflowState()
  } catch (error: unknown) {
    polishResponse.value = { error: (error as Error).message };
  }
};

const generateLongTextImage = async () => {
  try {
    const response = await api.callLongTextContentTool({ text: publishData.value });
    imageResponse.value = response.data;
    saveWorkflowState()
  } catch (error: unknown) {
    imageResponse.value = { error: (error as Error).message };
  }
};

const publishToXiaohongshu = async () => {
  try {
    const response = await api.callXiaohongshuTool({ data: publishData.value });
    publishResponse.value = response.data;
    saveWorkflowState()
  } catch (error: unknown) {
    publishResponse.value = { error: (error as Error).message };
  }
};

const runFullWorkflow = async () => {
  workflowStatus.value = '开始工作流...';
  try {
    // Step 1: Assume cookies are already handled or skip for now
    workflowStatus.value += '\n步骤 1: Cookie 假设已准备就绪';

    // Step 2
    workflowStatus.value += '\n步骤 2: 获取知乎内容...';
    await fetchZhihuContent();

    // Step 3
    workflowStatus.value += '\n步骤 3: 润色内容...';
    await polishContent();

    // Step 4
    workflowStatus.value += '\n步骤 4: 生成长文本图片...';
    await generateLongTextImage();

    // Step 5
    workflowStatus.value += '\n步骤 5: 发布到小红书...';
    await publishToXiaohongshu();

    workflowStatus.value += '\n工作流成功完成!';
    archiveWorkflow() // 归档完成的工作流
  } catch (error: unknown) {
    workflowStatus.value += `\n错误: ${(error as Error).message}`;
  }
};
</script>
