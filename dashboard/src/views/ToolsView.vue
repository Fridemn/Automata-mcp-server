<template>
  <div class="tools">
    <h1>工具</h1>
    <div v-for="tool in tools" :key="tool.name" class="tool-section">
      <h2>{{ tool.name }}</h2>
      <form @submit.prevent="callTool(tool)">
        <div v-for="field in tool.fields" :key="field.name">
          <label>{{ field.label }}:</label>
          <input v-if="field.type === 'text' || field.type === 'number'" :type="field.type" v-model="tool.data[field.name]" :placeholder="field.placeholder" />
          <textarea v-else-if="field.type === 'textarea'" v-model="(tool.data[field.name] as string)" :placeholder="field.placeholder"></textarea>
          <div v-else-if="field.type === 'checkbox'">
            <input type="checkbox" v-model="tool.data[field.name]" />
          </div>
        </div>
        <button type="submit">调用 {{ tool.name }}</button>
      </form>
      <div v-if="tool.response" class="response">
        <h3>响应:</h3>
        <ApiResponsePreview :response="tool.response" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import * as api from '../api/api';
import ApiResponsePreview from '../components/ApiResponsePreview.vue';
import '../assets/styles/ToolsView.scss'

interface ToolField {
  name: string;
  label: string;
  type: string;
  placeholder: string;
}

interface Tool {
  name: string;
  endpoint: string;
  fields: ToolField[];
  data: Record<string, unknown>;
  response: unknown;
}

const tools = ref<Tool[]>([
  {
    name: '抖音',
    endpoint: 'douyin',
    fields: [
      { name: 'cookies', label: '登录Cookie', type: 'textarea', placeholder: '输入抖音登录Cookie (JSON格式)' },
      { name: 'title', label: '标题', type: 'text', placeholder: '输入帖子标题' },
      { name: 'content', label: '内容', type: 'textarea', placeholder: '输入帖子内容' },
      { name: 'images', label: '图片', type: 'textarea', placeholder: '输入base64编码的图片列表 (JSON数组)' },
      { name: 'tags', label: '标签', type: 'text', placeholder: '输入标签，用逗号分隔' }
    ],
    data: {},
    response: null,
  },
  {
    name: '获取',
    endpoint: 'fetch',
    fields: [
      { name: 'url', label: 'URL', type: 'text', placeholder: '输入要获取的URL' },
      { name: 'max_length', label: '最大长度', type: 'number', placeholder: '最大字符数 (默认5000)' },
      { name: 'start_index', label: '起始位置', type: 'number', placeholder: '起始字符索引 (默认0)' },
      { name: 'raw', label: '原始内容', type: 'checkbox', placeholder: '获取原始HTML内容' }
    ],
    data: {},
    response: null,
  },
  {
    name: '长文本内容',
    endpoint: 'long-text-content',
    fields: [
      { name: 'content', label: '文本内容', type: 'textarea', placeholder: '输入长文本内容' },
      { name: 'background_image_path', label: '背景图片路径', type: 'text', placeholder: '输入背景图片文件路径' },
      { name: 'output_folder_path', label: '输出目录', type: 'text', placeholder: '输入输出目录路径 (可选)' },
      { name: 'font_color', label: '字体颜色', type: 'text', placeholder: '输入字体颜色: black 或 white (默认black)' }
    ],
    data: {},
    response: null,
  },
  {
    name: '润色',
    endpoint: 'polish',
    fields: [
      { name: 'original_text', label: '原始文本', type: 'textarea', placeholder: '输入要润色的原始文本' },
      { name: 'prompt', label: '润色提示', type: 'textarea', placeholder: '输入润色指导提示' }
    ],
    data: {},
    response: null,
  },
  {
    name: '小红书',
    endpoint: 'xiaohongshu',
    fields: [
      { name: 'cookies', label: '登录Cookie', type: 'textarea', placeholder: '输入小红书登录Cookie (JSON格式)' },
      { name: 'title', label: '标题', type: 'text', placeholder: '输入帖子标题' },
      { name: 'content', label: '内容', type: 'textarea', placeholder: '输入帖子内容' },
      { name: 'images', label: '图片', type: 'textarea', placeholder: '输入base64编码的图片列表 (JSON数组)' },
      { name: 'tags', label: '标签', type: 'text', placeholder: '输入标签，用逗号分隔' }
    ],
    data: {},
    response: null,
  },
  {
    name: '知乎获取',
    endpoint: 'zhihu_get',
    fields: [
      { name: 'url', label: '知乎URL', type: 'text', placeholder: '输入知乎文章URL' }
    ],
    data: {},
    response: null,
  },
]);

const callTool = async (tool: Tool) => {
  try {
    let response;
    switch (tool.endpoint) {
      case 'douyin':
        response = await api.callDouyinTool(tool.data);
        break;
      case 'fetch':
        response = await api.callFetchTool(tool.data);
        break;
      case 'long-text-content':
        response = await api.callLongTextContentTool(tool.data);
        break;
      case 'polish':
        response = await api.callPolishTool(tool.data);
        break;
      case 'xiaohongshu':
        response = await api.callXiaohongshuTool(tool.data);
        break;
      case 'zhihu_get':
        response = await api.callZhihuGetTool(tool.data);
        break;
    }
    if (response) {
      tool.response = response.data;
    }
  } catch (error: unknown) {
    tool.response = { error: (error as Error).message };
  }
};
</script>
