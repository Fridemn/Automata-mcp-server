<template>
  <div class="workflow">
    <h1>工作流</h1>
    <p>此工作流将执行以下步骤：</p>
    <ol>
      <li>获取抖音或小红书的登录cookie</li>
      <li>输入知乎链接并获取内容</li>
      <li>对获取的内容进行润色</li>
      <li>从润色后的内容生成长文本图片</li>
      <li>发布到小红书</li>
    </ol>

    <div class="step">
      <h2>步骤 1: 获取Cookie</h2>
      <button @click="getDouyinCookies">获取抖音Cookie</button>
      <button @click="getXiaohongshuCookies">获取小红书Cookie</button>
      <div v-if="cookiesResponse" class="response">
        <ApiResponsePreview :response="cookiesResponse" />
      </div>
    </div>

    <div class="step">
      <h2>步骤 2: 获取知乎内容</h2>
      <input v-model="zhihuUrl" type="text" placeholder="输入知乎URL" />
      <button @click="fetchZhihuContent">获取内容</button>
      <div v-if="zhihuResponse" class="response">
        <ApiResponsePreview :response="zhihuResponse" />
      </div>
    </div>

    <div class="step">
      <h2>步骤 3: 润色内容</h2>
      <textarea v-model="contentToPolish" placeholder="要润色的内容"></textarea>
      <textarea v-model="polishPrompt" placeholder="润色提示词"></textarea>
      <button @click="polishContent">润色内容</button>
      <div v-if="polishResponse" class="response">
        <ApiResponsePreview :response="polishResponse" />
      </div>
    </div>

    <div class="step">
      <h2>步骤 4: 生成长文本图片</h2>
      <button @click="generateLongTextImage">生成图片</button>
      <div v-if="imageResponse" class="response">
        <ApiResponsePreview :response="imageResponse" />
      </div>
    </div>

    <div class="step">
      <h2>步骤 5: 发布到小红书</h2>
      <textarea v-model="publishData" placeholder="要发布的数据"></textarea>
      <button @click="publishToXiaohongshu">发布</button>
      <div v-if="publishResponse" class="response">
        <ApiResponsePreview :response="publishResponse" />
      </div>
    </div>

    <div class="step">
      <h2>运行完整工作流</h2>
      <button @click="runFullWorkflow">运行工作流</button>
      <button @click="archiveWorkflow">归档工作流</button>
      <div v-if="workflowStatus" class="response">
        <pre>{{ workflowStatus }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import * as api from '../api/api';
import ApiResponsePreview from '../components/ApiResponsePreview.vue';
import '../assets/styles/WorkflowView.scss'

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
