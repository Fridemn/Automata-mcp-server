<template>
  <div class="min-h-[calc(100vh-60px)] p-5 bg-gradient-to-br from-blue-400 to-purple-600 font-['Segoe_UI',_Tahoma,_Geneva,_Verdana,_sans-serif] flex flex-col">
    <h1 class="text-3xl font-bold text-white mb-8">工具</h1>
    <div v-for="tool in tools" :key="tool.name" class="bg-white/95 backdrop-blur-[10px] rounded-2xl p-6 mb-6 shadow-lg border border-white/20">
      <h2 class="text-xl font-semibold text-gray-800 mb-4">{{ tool.name }}</h2>
      <form @submit.prevent="callTool(tool)" class="space-y-4">
        <div v-for="field in tool.fields" :key="field.name" class="flex flex-col gap-2">
          <label class="font-medium text-gray-700">{{ field.label }}:</label>
          <input v-if="field.type === 'text' || field.type === 'number'" :type="field.type" v-model="tool.data[field.name]" :placeholder="field.placeholder" class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25" />
          <textarea v-else-if="field.type === 'textarea'" v-model="(tool.data[field.name] as string)" :placeholder="field.placeholder" class="px-3 py-2 border border-gray-300 rounded focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 min-h-[100px] resize-vertical"></textarea>
          <div v-else-if="field.type === 'checkbox'" class="flex items-center gap-2">
            <input type="checkbox" v-model="tool.data[field.name]" class="w-4 h-4" />
            <span class="text-gray-700">{{ field.label }}</span>
          </div>
        </div>
        <button type="submit" class="px-4 py-2 bg-blue-500 text-white border-none rounded cursor-pointer transition-colors duration-200 hover:bg-blue-600">调用 {{ tool.name }}</button>
      </form>
      <div v-if="tool.response" class="mt-6 p-4 bg-gray-50 rounded-lg">
        <h3 class="text-lg font-semibold text-gray-800 mb-2">响应:</h3>
        <ApiResponsePreview :response="tool.response" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import * as api from '../api/api';
import ApiResponsePreview from '../components/ApiResponsePreview.vue';

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
