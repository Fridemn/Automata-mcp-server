import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000', // Match backend host
  timeout: 180000, // Increased to 3 minutes for long-running tasks like polish
  headers: {
    'X-API-Key': '0d000721', // API key from .env file
  },
});

// API functions for each endpoint

// Tool endpoints
export const callDouyinTool = (data: Record<string, unknown>) => api.post('/tools/douyin', data);
export const callFetchTool = (data: Record<string, unknown>) => api.post('/tools/fetch', data);
export const callLongTextContentTool = (data: Record<string, unknown>) => {
  // Use form data for this endpoint
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, value as string);
  });
  return api.post('/tools/long-text-content', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};
export const callPolishTool = (data: Record<string, unknown>) => {
  // Use form data for this endpoint
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, value as string);
  });
  return api.post('/tools/polish', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
};
export const callXiaohongshuTool = (data: Record<string, unknown>) => api.post('/tools/xiaohongshu', data);
export const callZhihuGetTool = (data: Record<string, unknown>) => api.post('/tools/zhihu_get', data);

// General endpoints
export const getRoot = () => api.get('/');
export const getHealth = () => api.get('/health');
export const getTools = () => api.get('/tools');

// Cookie endpoints
export const getDouyinCookies = (data: Record<string, unknown>) => api.post('/cookies/douyin/get', data);
export const getXiaohongshuCookies = (data: Record<string, unknown>) => api.post('/cookies/xiaohongshu/get', data);
export const loadDouyinCookies = () => api.get('/cookies/douyin/load');
export const loadXiaohongshuCookies = () => api.get('/cookies/xiaohongshu/load');
export const validateDouyinCookies = () => api.get('/cookies/douyin/validate');
export const validateXiaohongshuCookies = () => api.get('/cookies/xiaohongshu/validate');
export const editVideo = (data: Record<string, unknown>) => api.post('/video/edit', data);

export default api;
