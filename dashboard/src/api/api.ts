import axios from 'axios';

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:8000', // Adjust if backend port is different
  timeout: 10000,
});

// API functions for each endpoint

// Tool endpoints
export const callDouyinTool = (data: Record<string, unknown>) => api.post('/tools/douyin', data);
export const callFetchTool = (data: Record<string, unknown>) => api.post('/tools/fetch', data);
export const callLongTextContentTool = (data: Record<string, unknown>) => api.post('/tools/long-text-content', data);
export const callPolishTool = (data: Record<string, unknown>) => api.post('/tools/polish', data);
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

export default api;
