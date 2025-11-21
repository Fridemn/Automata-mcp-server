"""
实时日志查看器 - WebSocket 实现 (UI Enhanced Version)
提供浏览器端查看服务器日志的功能，包含搜索、过滤和现代化界面。
"""

import asyncio
import os
from collections import deque
from datetime import datetime
from typing import Set

from fastapi import WebSocket


class LogViewerManager:
    """日志查看器管理器 (后端逻辑保持稳定，无需大改)"""

    def __init__(self, max_history: int = 1000):
        self.active_connections: Set[WebSocket] = set()
        self.log_history: deque = deque(maxlen=max_history)
        self.is_tailing = False
        self._tail_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        # 发送历史日志
        for log_entry in list(self.log_history):
            try:
                await websocket.send_json(log_entry)
            except Exception:
                break

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_log(self, log_entry: dict):
        self.log_history.append(log_entry)
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(log_entry)
            except Exception:
                disconnected.add(connection)
        self.active_connections -= disconnected

    def add_log_entry(self, level: str, message: str):
        """同步方法供 loguru sink 调用"""
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "level": level,
            "message": message,
            "id": int(datetime.now().timestamp() * 1000000),  # 用于前端唯一key
        }
        self.log_history.append(log_entry)
        if self.active_connections:
            asyncio.create_task(self.broadcast_log(log_entry))

    # --- 文件监听逻辑省略，与原版保持一致即可 ---
    async def start_log_file_tail(self, log_file_path: str):
        if self.is_tailing:
            return
        self.is_tailing = True
        asyncio.create_task(self._tail_log_file(log_file_path))

    async def _tail_log_file(self, log_file_path: str):
        if not os.path.exists(log_file_path):
            return
        with open(log_file_path, encoding="utf-8") as f:
            f.seek(0, 2)
            while self.is_tailing:
                line = f.readline()
                if line:
                    # 简单模拟解析
                    await self.broadcast_log(
                        {
                            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                            "level": "INFO",
                            "message": line.strip(),
                            "id": int(datetime.now().timestamp() * 1000000),
                        }
                    )
                else:
                    await asyncio.sleep(0.1)


def get_log_viewer_html() -> str:
    """返回优化后的 HTML 页面 (大字体、护眼背景、隔行变色版)"""
    return """
<!DOCTYPE html>
<html lang="zh-CN" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Log Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        // 使用 Slate 色系，比纯黑更护眼
                        slate: {
                            800: '#1e293b',
                            850: '#162032', // 自定义中间色
                            900: '#0f172a',
                            950: '#020617',
                        }
                    },
                    fontFamily: {
                        mono: ['"JetBrains Mono"', '"Consolas"', '"Fira Code"', 'monospace'],
                    }
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

        /* 滚动条样式优化 */
        ::-webkit-scrollbar { width: 12px; height: 12px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb {
            background-color: #334155;
            border: 3px solid #0f172a;
            border-radius: 6px;
        }
        ::-webkit-scrollbar-thumb:hover { background-color: #475569; }

        [x-cloak] { display: none !important; }

        /* 选中文本颜色 */
        ::selection { background: rgba(56, 189, 248, 0.2); color: inherit; }
    </style>
</head>

<body class="bg-slate-900 text-slate-300 h-screen flex flex-col overflow-hidden font-sans"
      x-data="logViewer()"
      x-init="initWebSocket()">

    <header class="h-16 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-6 shrink-0 z-20 shadow-sm">
        <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
                <div class="relative flex h-3 w-3">
                  <span x-show="connected" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-3 w-3" :class="connected ? 'bg-emerald-500' : 'bg-red-500'"></span>
                </div>
                <h1 class="text-lg font-semibold text-slate-100 tracking-tight">Live Monitor</h1>
            </div>

            <div class="hidden md:flex px-3 py-1 rounded-full bg-slate-800 text-xs font-mono text-slate-400 border border-slate-700/50">
                <span x-text="stats.total">0</span> <span class="ml-1 text-slate-500">logs</span>
            </div>
        </div>

        <div class="flex items-center gap-3">
            <div class="relative">
                <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                <input type="text"
                       x-model="searchQuery"
                       placeholder="Type to filter..."
                       class="bg-slate-800 border border-slate-700 text-sm rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500 block w-48 md:w-64 pl-9 p-2 text-slate-200 placeholder-slate-500 transition-all outline-none">
            </div>

            <button @click="clearLogs()" class="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded transition" title="Clear All">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        </div>
    </header>

    <div class="h-10 bg-slate-900/50 border-b border-slate-800 flex items-center px-4 gap-4 shrink-0 overflow-x-auto select-none">
        <template x-for="level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']">
            <label class="flex items-center space-x-1.5 cursor-pointer group">
                <input type="checkbox" class="form-checkbox h-3.5 w-3.5 text-blue-600 rounded border-slate-600 bg-slate-800 focus:ring-0 focus:ring-offset-0 transition" :value="level" x-model="selectedLevels">
                <span class="text-xs font-medium text-slate-400 group-hover:text-slate-200" x-text="level"></span>
            </label>
        </template>
        <div class="flex-1"></div>
        <button @click="toggleAutoScroll()"
                class="text-xs font-medium px-3 py-1 rounded transition-colors flex items-center gap-2"
                :class="autoScroll ? 'text-blue-400 bg-blue-500/10' : 'text-slate-500 hover:text-slate-300'">
            <div class="w-2 h-2 rounded-full" :class="autoScroll ? 'bg-blue-500' : 'bg-slate-600'"></div>
            Auto Scroll
        </button>
    </div>

    <div class="flex-1 overflow-y-auto bg-[#0f172a] scroll-smooth" id="log-container" @scroll="handleScroll">
        <div class="font-mono text-sm leading-6 w-full min-h-full pb-12">

            <div x-show="filteredLogs.length === 0" x-cloak class="flex flex-col items-center justify-center h-64 text-slate-600">
                <p class="text-lg">Waiting for incoming logs...</p>
            </div>

            <template x-for="log in filteredLogs" :key="log.id">
                <div class="flex items-start gap-3 px-4 py-1 hover:bg-slate-800 transition-colors group border-l-[3px]"
                     :class="[log.id % 2 === 0 ? 'bg-transparent' : 'bg-slate-800/30', getLevelBorderColor(log.level)]">

                    <div class="shrink-0 text-slate-500 select-none w-[100px] text-[13px] pt-[1px]" x-text="log.timestamp"></div>

                    <div class="shrink-0 w-[65px]">
                        <span class="inline-block w-full text-center text-[11px] font-bold px-1 rounded-sm"
                              :class="getLevelBadgeStyle(log.level)"
                              x-text="log.level"></span>
                    </div>

                    <div class="flex-1 break-words text-slate-300 whitespace-pre-wrap" x-text="log.message"></div>
                </div>
            </template>
        </div>

        <div x-show="!autoScroll && hasNewLogs"
             x-transition:enter="transition ease-out duration-300"
             x-transition:enter-start="opacity-0 translate-y-4"
             x-transition:enter-end="opacity-100 translate-y-0"
             class="absolute bottom-8 right-8 z-30">
            <button @click="scrollToBottom(true)" class="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded shadow-xl flex items-center gap-2 text-sm font-medium transition-all">
                <span>New logs received</span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"></path></svg>
            </button>
        </div>
    </div>

    <script>
        function logViewer() {
            return {
                ws: null,
                connected: false,
                logs: [],
                searchQuery: '',
                selectedLevels: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                autoScroll: true,
                hasNewLogs: false,
                maxLogs: 3000, // 增加缓存数量

                get stats() { return { total: this.logs.length }; },

                get filteredLogs() {
                    const query = this.searchQuery.toLowerCase();
                    return this.logs.filter(log => {
                        if (!this.selectedLevels.includes(log.level)) return false;
                        if (!query) return true;
                        return log.message.toLowerCase().includes(query) ||
                               log.level.toLowerCase().includes(query);
                    });
                },

                initWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
                    const wsUrl = `${protocol}://${window.location.host}/api/logs/ws`;
                    this.connect(wsUrl);
                },

                connect(url) {
                    this.ws = new WebSocket(url);
                    this.ws.onopen = () => { this.connected = true; };
                    this.ws.onclose = () => {
                        this.connected = false;
                        setTimeout(() => this.connect(url), 2000);
                    };
                    this.ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        if (!data.id) data.id = Date.now() + Math.random();
                        this.logs.push(data);
                        if (this.logs.length > this.maxLogs) this.logs.shift();

                        if (this.autoScroll) {
                            this.$nextTick(() => this.scrollToBottom());
                        } else {
                            this.hasNewLogs = true;
                        }
                    };
                },

                clearLogs() { this.logs = []; },

                toggleAutoScroll() {
                    this.autoScroll = !this.autoScroll;
                    if (this.autoScroll) {
                        this.hasNewLogs = false;
                        this.scrollToBottom();
                    }
                },

                scrollToBottom(force = false) {
                    const container = document.getElementById('log-container');
                    container.scrollTop = container.scrollHeight;
                    if (force) {
                        this.autoScroll = true;
                        this.hasNewLogs = false;
                    }
                },

                handleScroll(e) {
                    const c = e.target;
                    const isBottom = c.scrollHeight - c.scrollTop - c.clientHeight < 50;
                    if (!isBottom && this.autoScroll) this.autoScroll = false;
                    else if (isBottom && !this.autoScroll) {
                        this.autoScroll = true;
                        this.hasNewLogs = false;
                    }
                },

                // 样式辅助：文字颜色与背景色搭配
                getLevelBadgeStyle(level) {
                    const styles = {
                        'DEBUG': 'text-slate-400 bg-slate-800',
                        'INFO': 'text-blue-400 bg-blue-900/20',
                        'SUCCESS': 'text-emerald-400 bg-emerald-900/20',
                        'WARNING': 'text-amber-400 bg-amber-900/20',
                        'ERROR': 'text-rose-400 bg-rose-900/20',
                        'CRITICAL': 'text-white bg-rose-600'
                    };
                    return styles[level] || 'text-slate-400 bg-slate-800';
                },

                // 左侧边框颜色，辅助快速定位
                getLevelBorderColor(level) {
                    const colors = {
                        'DEBUG': 'border-transparent',
                        'INFO': 'border-blue-500/40',
                        'SUCCESS': 'border-emerald-500/40',
                        'WARNING': 'border-amber-500/60',
                        'ERROR': 'border-rose-500',
                        'CRITICAL': 'border-rose-600'
                    };
                    return colors[level] || 'border-transparent';
                }
            }
        }
    </script>
</body>
</html>
    """
