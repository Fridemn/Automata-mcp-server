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
        <pre>{{ JSON.stringify(cookiesResponse, null, 2) }}</pre>
      </div>
    </div>

    <div class="step">
      <h2>步骤 2: 获取知乎内容</h2>
      <input v-model="zhihuUrl" type="text" placeholder="输入知乎URL" />
      <button @click="fetchZhihuContent">获取内容</button>
      <div v-if="zhihuResponse" class="response">
        <pre>{{ JSON.stringify(zhihuResponse, null, 2) }}</pre>
      </div>
    </div>

    <div class="step">
      <h2>步骤 3: 润色内容</h2>
      <textarea v-model="contentToPolish" placeholder="要润色的内容"></textarea>
      <button @click="polishContent">润色内容</button>
      <div v-if="polishResponse" class="response">
        <pre>{{ JSON.stringify(polishResponse, null, 2) }}</pre>
      </div>
    </div>

    <div class="step">
      <h2>步骤 4: 生成长文本图片</h2>
      <button @click="generateLongTextImage">生成图片</button>
      <div v-if="imageResponse" class="response">
        <pre>{{ JSON.stringify(imageResponse, null, 2) }}</pre>
      </div>
    </div>

    <div class="step">
      <h2>步骤 5: 发布到小红书</h2>
      <textarea v-model="publishData" placeholder="要发布的数据"></textarea>
      <button @click="publishToXiaohongshu">发布</button>
      <div v-if="publishResponse" class="response">
        <pre>{{ JSON.stringify(publishResponse, null, 2) }}</pre>
      </div>
    </div>

    <div class="step">
      <h2>运行完整工作流</h2>
      <button @click="runFullWorkflow">运行工作流</button>
      <div v-if="workflowStatus" class="response">
        <pre>{{ workflowStatus }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import * as api from '../api/api';

const zhihuUrl = ref('');
const contentToPolish = ref('');
const publishData = ref('');
const cookiesResponse = ref<unknown>(null);
const zhihuResponse = ref<unknown>(null);
const polishResponse = ref<unknown>(null);
const imageResponse = ref<unknown>(null);
const publishResponse = ref<unknown>(null);
const workflowStatus = ref('');

const getDouyinCookies = async () => {
  try {
    const response = await api.getDouyinCookies({});
    cookiesResponse.value = response.data;
  } catch (error: unknown) {
    cookiesResponse.value = { error: (error as Error).message };
  }
};

const getXiaohongshuCookies = async () => {
  try {
    const response = await api.getXiaohongshuCookies({});
    cookiesResponse.value = response.data;
  } catch (error: unknown) {
    cookiesResponse.value = { error: (error as Error).message };
  }
};

const fetchZhihuContent = async () => {
  try {
    const response = await api.callZhihuGetTool({ url: zhihuUrl.value });
    zhihuResponse.value = response.data;
    contentToPolish.value = response.data.content?.[0]?.text || '';
  } catch (error: unknown) {
    zhihuResponse.value = { error: (error as Error).message };
  }
};

const polishContent = async () => {
  try {
    const response = await api.callPolishTool({
      original_text: contentToPolish.value,
      prompt: '请润色这篇文章，使其更加优美流畅，适合在社交媒体上发布。'
    });
    polishResponse.value = response.data;
    publishData.value = response.data.content?.[0]?.text || '';
  } catch (error: unknown) {
    polishResponse.value = { error: (error as Error).message };
  }
};

const generateLongTextImage = async () => {
  try {
    const response = await api.callLongTextContentTool({ text: publishData.value });
    imageResponse.value = response.data;
  } catch (error: unknown) {
    imageResponse.value = { error: (error as Error).message };
  }
};

const publishToXiaohongshu = async () => {
  try {
    const response = await api.callXiaohongshuTool({ data: publishData.value });
    publishResponse.value = response.data;
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
  } catch (error: unknown) {
    workflowStatus.value += `\n错误: ${(error as Error).message}`;
  }
};
</script>

<style scoped lang="scss">
$primary-bg: #f8f9fa;
$card-bg: white;
$border-color: #dee2e6;
$shadow: 0 4px 20px rgba(0,0,0,0.08);
$primary-color: #007bff;
$success-color: #28a745;
$warning-color: #ffc107;
$info-color: #17a2b8;
$border-radius: 12px;

.workflow {
  min-height: 100vh;
  background: linear-gradient(135deg, $primary-bg 0%, #e9ecef 100%);
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;

  h1 {
    text-align: center;
    color: #333;
    margin-bottom: 20px;
    font-weight: 300;
    font-size: 2.5rem;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  ol {
    text-align: center;
    margin-bottom: 40px;
    color: #666;
    font-size: 1.1rem;
    line-height: 1.6;

    li {
      margin-bottom: 8px;
      padding: 8px 0;
    }
  }
}

.step {
  background: $card-bg;
  border-radius: $border-radius;
  padding: 40px;
  margin-bottom: 40px;
  box-shadow: $shadow;
  border: 1px solid rgba(255,255,255,0.8);
  backdrop-filter: blur(10px);
  transition: transform 0.3s ease, box-shadow 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.12);
  }

  h2 {
    color: #333;
    margin-bottom: 25px;
    font-weight: 500;
    font-size: 1.4rem;
    border-bottom: 3px solid $primary-color;
    padding-bottom: 15px;
    display: inline-block;
  }

  button {
    background: linear-gradient(135deg, $primary-color 0%, #0056b3 100%);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
    font-weight: 600;
    margin-right: 15px;
    margin-bottom: 15px;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba($primary-color, 0.3);

    &:hover {
      background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba($primary-color, 0.4);
    }

    &:active {
      transform: translateY(0);
    }

    &.run-workflow {
      background: linear-gradient(135deg, $success-color 0%, #218838 100%);

      &:hover {
        background: linear-gradient(135deg, #218838 0%, #1e7e34 100%);
      }
    }
  }

  input, textarea {
    width: 100%;
    padding: 12px 16px;
    border: 2px solid $border-color;
    border-radius: 8px;
    font-size: 14px;
    margin-bottom: 20px;
    box-sizing: border-box;
    background: #fff;
    transition: all 0.3s ease;

    &:focus {
      outline: none;
      border-color: $primary-color;
      box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
      transform: translateY(-1px);
    }
  }

  textarea {
    min-height: 120px;
    resize: vertical;
    line-height: 1.5;
  }
}

.response {
  margin-top: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: $border-radius;
  border-left: 4px solid $info-color;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);

  pre {
    background: white;
    padding: 15px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 13px;
    color: #495057;
    border: 1px solid $border-color;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    white-space: pre-wrap;
    word-wrap: break-word;
    max-height: 400px;
    overflow-y: auto;
  }
}

@media (max-width: 768px) {
  .workflow {
    padding: 15px;
  }

  .step {
    padding: 25px;
  }

  .step button {
    width: 100%;
    margin-right: 0;
    margin-bottom: 15px;
  }
}
</style>
