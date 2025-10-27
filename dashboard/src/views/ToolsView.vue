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
        <pre>{{ JSON.stringify(tool.response, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import * as api from '../api/api';

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

<style scoped lang="scss">
$primary-bg: #f8f9fa;
$card-bg: white;
$border-color: #dee2e6;
$shadow: 0 4px 20px rgba(0,0,0,0.08);
$primary-color: #007bff;
$success-color: #28a745;
$danger-color: #dc3545;
$border-radius: 12px;

.tools {
  min-height: 100vh;
  background: linear-gradient(135deg, $primary-bg 0%, #e9ecef 100%);
  padding: 20px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;

  h1 {
    text-align: center;
    color: #333;
    margin-bottom: 40px;
    font-weight: 300;
    font-size: 2.5rem;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }
}

.tool-section {
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
    margin-bottom: 30px;
    font-weight: 500;
    font-size: 1.5rem;
    border-bottom: 3px solid $primary-color;
    padding-bottom: 15px;
    display: inline-block;
  }

  form {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 30px;

    .full-width {
      grid-column: 1 / -1;
    }

    label {
      font-weight: 600;
      color: #495057;
      margin-bottom: 8px;
      display: block;
      font-size: 0.95rem;
    }

    input, textarea {
      width: 100%;
      padding: 12px 16px;
      border: 2px solid $border-color;
      border-radius: 8px;
      font-size: 14px;
      transition: all 0.3s ease;
      box-sizing: border-box;
      background: #fff;

      &:focus {
        outline: none;
        border-color: $primary-color;
        box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
        transform: translateY(-1px);
      }

      &[type="checkbox"] {
        width: auto;
        margin-right: 8px;
      }
    }

    textarea {
      min-height: 120px;
      resize: vertical;
      line-height: 1.5;
    }
  }

  button {
    background: linear-gradient(135deg, $primary-color 0%, #0056b3 100%);
    color: white;
    border: none;
    padding: 14px 32px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 16px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba($primary-color, 0.3);
    grid-column: 1 / -1;
    justify-self: center;

    &:hover {
      background: linear-gradient(135deg, #0056b3 0%, #004085 100%);
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba($primary-color, 0.4);
    }

    &:active {
      transform: translateY(0);
    }
  }
}

.response {
  margin-top: 30px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: $border-radius;
  border-left: 4px solid $success-color;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);

  h3 {
    margin-bottom: 15px;
    color: #333;
    font-weight: 600;
    font-size: 1.1rem;
  }

  pre {
    background: white;
    padding: 15px;
    border-radius: 6px;
    overflow-x: auto;
    font-size: 13px;
    color: #495057;
    border: 1px solid $border-color;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    max-height: 400px;
    overflow-y: auto;
  }
}

@media (max-width: 768px) {
  .tools {
    padding: 15px;
  }

  .tool-section {
    padding: 25px;
  }

  .tool-section form {
    grid-template-columns: 1fr;
  }

  .tool-section button {
    width: 100%;
  }
}
</style>
