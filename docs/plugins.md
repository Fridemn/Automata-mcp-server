# Automata MCP Server 插件文档

本文档列出所有已注册的工具插件及其接口说明。

## 核心工具 (`app/src/`)

### 1. fetch — 网页内容抓取

抓取指定 URL 的网页内容并转换为 Markdown 格式返回。

- **端点**: `POST /tools/fetch`
- **认证**: Bearer Token

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `url` | string (URL) | 是 | — | 要抓取的网页 URL |
| `max_length` | int | 否 | 5000 | 返回的最大字符数 (0 < x < 1,000,000) |
| `start_index` | int | 否 | 0 | 从第几个字符开始返回（用于分页抓取） |
| `raw` | bool | 否 | false | 是否返回原始 HTML（不转换为 Markdown） |

- **依赖**: requests, httpx, beautifulsoup4, html2text, protego
- **行为**: 自动检测编码（UTF-8 → GBK → ISO-8859-1），遵循 robots.txt 规则，自动提取页面主体内容

---

### 2. flow_wait — 工作流等待

在工作流中实现指定秒数的延迟。

- **端点**: `POST /tools/flow_wait`
- **参数编码**: Form Data

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `seconds` | float | 是 | — | 等待秒数 (0.1 ~ 3600) |

- **依赖**: 无

---

### 3. image_upload — 图片上传管理

上传和管理图片文件，支持单张/批量上传、删除和列表查看。

- **路由**: 使用独立 APIRouter（非标准 get_route_config 模式）

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/upload/image` | 上传单张图片 |
| POST | `/upload/images` | 批量上传图片 |
| DELETE | `/upload/image/{filename}` | 删除指定图片 |
| GET | `/upload/images` | 列出所有已上传图片 |

| 参数 | 类型 | 说明 |
|------|------|------|
| `file` | UploadFile | 图片文件 |

- **限制**: 支持 jpg/jpeg/png/gif/bmp/webp，单文件最大 10 MB
- **存储**: `data/static/upload_images/`，文件名使用 UUID

---

### 4. video_upload — 视频上传管理

上传和管理视频文件，支持单文件/批量上传、删除和列表查看。

- **路由**: 使用独立 APIRouter（非标准 get_route_config 模式）

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/upload/video` | 上传单个视频 |
| POST | `/upload/videos` | 批量上传视频 |
| DELETE | `/upload/video/{filename}` | 删除指定视频 |
| GET | `/upload/videos` | 列出所有已上传视频 |

| 参数 | 类型 | 说明 |
|------|------|------|
| `file` | UploadFile | 视频文件 |

- **限制**: 支持 mp4/avi/mov/mkv/webm/flv/wmv/m4v/3gp，单文件最大 500 MB
- **存储**: `data/static/upload_videos/`，文件名使用 UUID

---

## 扩展工具 (`app/AutoUp-MCP-Extension/`)

### 5. douyin_publish_photo_text — 抖音图文发布

发布图文内容到抖音平台，自动从远程服务器获取登录状态。

- **端点**: `POST /tools/douyin_publish_photo_text`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image_paths` | string | 是 | — | 图片路径（分号分隔，1~35 张） |
| `title` | string | 是 | — | 标题（最多 30 字） |
| `content` | string | 否 | 等于 title | 正文内容 |
| `tags` | list[str] | 否 | — | 标签列表 |
| `bearer_token` | string | 是 | — | 用于远程获取 Cookie |
| `headless` | bool | 否 | true | 是否无头模式运行浏览器 |

- **依赖**: playwright, playwright-stealth

---

### 6. douyin_publish_video — 抖音视频发布

发布视频到抖音平台，自动从远程服务器获取登录状态。

- **端点**: `POST /tools/douyin_publish_video`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `video_path` | string | 是 | — | 视频路径（文件名/相对路径/绝对路径） |
| `title` | string | 是 | — | 标题（最多 30 字） |
| `description` | string | 否 | — | 描述 |
| `cover_path` | string | 否 | — | 封面图路径 |
| `bearer_token` | string | 是 | — | 用于远程获取 Cookie |
| `headless` | bool | 否 | true | 是否无头模式 |

- **依赖**: playwright, playwright-stealth

---

### 7. kuaishou_publish_photo — 快手图文发布

发布图片内容到快手平台，使用 UUID 获取登录 Cookie。

- **端点**: `POST /tools/kuaishou_publish_photo`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `uuid` | string | 是 | — | 用于获取 Cookie 的 UUID |
| `image_urls` | list[str] | 是 | — | 图片路径（HTTP URL / 本地路径） |
| `title` | string | 是 | — | 标题 |
| `content` | string | 否 | — | 正文内容 |
| `tags` | string | 否 | — | 标签（逗号分隔） |
| `cover_path` | string | 否 | — | 封面图路径 |

- **依赖**: playwright, playwright-stealth, requests

---

### 8. kuaishou_publish_video — 快手视频发布

发布视频到快手平台，使用 UUID 获取登录 Cookie。

- **端点**: `POST /tools/kuaishou_publish_video`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `uuid` | string | 是 | — | 用于获取 Cookie 的 UUID |
| `video_urls` | list[str] | 是 | — | 视频路径列表（仅上传第一个） |
| `title` | string | 是 | — | 标题 |
| `content` | string | 否 | — | 正文内容 |
| `tags` | string | 否 | — | 标签（逗号分隔） |
| `cover_path` | string | 否 | — | 封面图路径 |

- **依赖**: playwright, playwright-stealth, requests

---

### 9. Reddit_publish — Reddit 发布

发布帖子到 Reddit，支持文本、媒体和链接三种类型。

- **端点**: `POST /tools/reddit_publish`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `subreddit` | string | 是 | — | 目标 subreddit |
| `post_type` | string | 是 | — | 帖子类型: text / media / link |
| `title` | string | 是 | — | 标题（最多 300 字） |
| `body_text` | string | 否 | — | 正文（Markdown 格式，text 类型必填） |
| `file_path` | string | 条件 | — | 媒体文件路径（media 类型必填） |
| `link_url` | string | 条件 | — | 链接 URL（link 类型必填） |
| `bearer_token` | string | 是 | — | 用于远程获取 Cookie |
| `headless` | bool | 否 | true | 是否无头模式 |

- **依赖**: playwright, playwright-stealth

---

### 10. X_publish — X/Twitter 发布

发布推文到 X (Twitter) 平台，支持文本和媒体内容。

- **端点**: `POST /tools/x_publish`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 是 | — | 推文内容（最多 280 字） |
| `media_paths` | list[str] | 否 | — | 媒体文件路径（文件名/相对/绝对/URL） |
| `bearer_token` | string | 是 | — | 用于远程获取 Cookie |
| `headless` | bool | 否 | true | 是否无头模式 |
| `proxy` | string | 否 | — | 代理地址 |

- **依赖**: playwright, playwright-stealth, requests

---

### 11. xiaohongshu_publish — 小红书发布

发布内容到小红书平台，需要提供登录 Cookie。

- **端点**: `POST /tools/xiaohongshu_tool`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `cookies` | string | 是 | — | Cookie JSON 字符串 |
| `title` | string | 是 | — | 标题 |
| `content` | string | 否 | — | 正文内容 |
| `images` | list[str] | 是 | — | 图片列表（base64 编码） |
| `tags` | list[str] | 否 | — | 标签列表 |

- **依赖**: playwright, playwright-stealth
- **注意**: 始终以非无头模式运行（headless=False），图片需 base64 编码

---

### 12. Youtube_publish — YouTube 发布

发布视频到 YouTube 平台，自动从远程服务器获取登录状态。

- **端点**: `POST /tools/youtube_publish`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `video_path` | string | 是 | — | 视频路径（文件名/相对/绝对路径） |
| `title` | string | 是 | — | 标题（最多 100 字） |
| `description` | string | 否 | — | 视频描述 |
| `bearer_token` | string | 是 | — | 用于远程获取 Cookie |
| `headless` | bool | 否 | **false** | 是否无头模式（默认 false，YouTube 需要可见界面处理验证） |
| `proxy` | string | 否 | — | 代理地址 |

- **依赖**: playwright, playwright-stealth
- **注意**: 默认非无头模式，因 YouTube 上传可能需要处理验证码

---

### 13. image_generate_jimeng — 即梦图片生成

调用火山引擎即梦 API，根据提示词和可选参考图片生成图片。

- **端点**: `POST /tools/image_generate_jimeng`
- **配置要求**: `ak`（火山引擎 Access Key）、`sk`（火山引擎 Secret Key）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | 是 | — | 图片描述提示词（最多 800 字） |
| `image_urls` | list[str] | 否 | — | 参考图片 URL（最多 10 张） |
| `width` | int | 否 | 2048 | 图片宽度 (1024~4096) |
| `height` | int | 否 | 2048 | 图片高度 (1024~4096) |
| `scale` | int | 否 | 5 | 生成质量 (0~10) |

- **依赖**: httpx
- **行为**: 异步提交 → 轮询结果（最多 60 次，间隔 3s），返回分号分隔的图片 URL

---

### 14. image_generate_midjourney — Midjourney 图片生成

提交提示词到 Midjourney API 生成图片，并下载结果。

- **端点 1**: `POST /tools/image_generate_midjourney` — 提交生成任务
- **端点 2**: `POST /tools/midjourney_get_images` — 下载生成的图片
- **配置要求**: `cookie`（Midjourney 网站Cookie）、`channel_id`

| 参数 | 端点 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `prompt` | 生成 | string | 是 | 图片描述提示词 |
| `job_id` | 下载 | string | 是 | 生成任务返回的 job_id |

- **依赖**: cloudscraper, playwright
- **存储**: `data/static/image_generate_midjourney/`，每次生成 4 张图片

---

### 15. text_polish — 文本润色

使用 LLM 对文本进行润色优化。

- **端点**: `POST /tools/text_polish`
- **参数编码**: Form Data

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `original_text` | string | 是 | 原始文本 |
| `prompt` | string | 是 | 润色要求/指导提示 |

- **依赖**: openai
- **配置**: 使用 `OPENAI_API_KEY`、`OPENAI_MODEL`、`OPENAI_BASE_URL` 环境变量

---

### 16. text_to_image — 文字转图片

将文本内容渲染为图片，支持多页、自定义字体和背景图。

- **端点**: `POST /tools/text_to_image`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 否 | "" | 要渲染的文本 |
| `text_file` | string | 否 | — | 文本文件路径（替代 text） |
| `font_path` | string | 否 | "MicrosoftYaHei" | 字体名称或路径 |
| `font_size` | int | 否 | 40 | 字体大小 |
| `text_color` | string | 否 | "white" | 文字颜色 |
| `bg_image_path` | string | 否 | — | 背景图路径（分号分隔多张） |
| `aspect_ratio` | string | 否 | "3:4" | 宽高比（格式 "数字:数字"） |
| `line_spacing` | int | 否 | 15 | 行间距 |
| `paragraph_spacing` | int | 否 | 25 | 段落间距 |
| `margin_top/bottom/left/right` | int | 否 | 100 | 页边距 |
| `title` | string | 否 | — | 首页标题 |
| `title_position` | string | 否 | — | 标题位置: top / center / bottom |
| `bg_overlay_opacity` | int | 否 | 150 | 背景遮罩透明度 (0~255) |
| `optimize_layout` | bool | 否 | true | 是否优化排版 |

- **依赖**: Pillow
- **存储**: `data/static/t2i/`

---

### 17. tts_edge — Edge TTS 语音合成

使用微软 Edge TTS 将文字转语音，无需 API Key。

- **端点 1**: `POST /tools/tts_edge` — 文字转语音
- **端点 2**: `POST /tools/list_edge_voices` — 列出可用语音

**tts_edge 参数:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 是 | — | 要合成的文本（分号分隔多句，生成多个音频） |
| `voice` | string | 否 | "zh-CN-XiaoxiaoNeural" | 语音角色 |
| `rate` | string | 否 | "+0%" | 语速调整 |
| `volume` | string | 否 | "+0%" | 音量调整 |
| `pitch` | string | 否 | "+0Hz" | 音调调整 |

**list_edge_voices 参数:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `language` | string | 否 | "" | 按语言筛选（如 "zh"） |

- **依赖**: edge-tts>=7.0.0
- **存储**: `data/static/edge_tts/`
- **注意**: 免费，无需 API Key；多句之间自动插入 1~3 秒随机间隔

---

### 18. tts_minimax — MiniMax TTS 语音合成

使用 MiniMax TTS API 将文字转语音。

- **端点 1**: `POST /tools/tts_minimax` — 文字转语音
- **端点 2**: `POST /tools/list_minimax_voices` — 列出可用语音
- **配置要求**: `api_key`（MiniMax API Key）

**tts_minimax 参数:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 是 | — | 要合成的文本 |
| `voice_id` | string | 否 | "wumei_yujie" | 语音角色 ID |
| `model` | string | 否 | "speech-02-hd" | 模型名称 |
| `mode` | string | 否 | "sync" | 模式: sync（同步）/ async（异步） |

**list_minimax_voices 参数:**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `voice_type` | string | 否 | "all" | 语音类型筛选 |

- **依赖**: requests, httpx
- **存储**: `data/static/minimax/`
- **API**: `https://api.minimaxi.com`

---

### 19. tts_clone_minimax — MiniMax 语音克隆

使用 MiniMax API 克隆声音并合成语音。

- **端点**: `POST /tools/tts_clone_minimax`
- **配置要求**: 复用 `tts_minimax` 的 `api_key`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `clone_file` | string | 是 | — | 克隆音频文件路径/URL（8s~5min，<20MB） |
| `prompt_file` | string | 是 | — | 提示音频文件路径/URL（最多 7s） |
| `voice_id` | string | 是 | — | 声音 ID（8~256 字符，字母开头） |
| `prompt_text` | string | 是 | — | 提示音频对应文本（须以标点结尾） |
| `text` | string | 是 | — | 要合成的文本 |
| `model` | string | 否 | "speech-2.6-hd" | 模型名称 |

- **依赖**: requests, httpx, pydub

---

### 20. video_generate — 视频生成

根据文本生成 TTS 音频、字幕和剪映视频草稿。

- **端点**: `POST /tools/video_generate`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `text` | string | 是 | — | 要转化的文本 |
| `videos_path` | string/list | 是 | — | 背景视频路径 |
| `draft_name` | string | 是 | — | 草稿名称 |
| `audio_output_file` | string | 否 | "generated_audio.mp3" | 音频输出文件名 |
| `vtt_output_file` | string | 否 | "generated_subtitle.vtt" | 字幕输出文件名 |
| `voice` | string | 否 | "zh-CN-YunxiNeural" | TTS 语音角色 |
| `rate` | string | 否 | "+0%" | 语速 |
| `volume` | string | 否 | "+0%" | 音量 |
| `pitch` | string | 否 | "+0Hz" | 音调 |
| `video_ratio` | string | 否 | "9:16" | 视频比例 |
| `music_path` | string | 否 | "" | 背景音乐路径 |

- **依赖**: moviepy, webvtt-py, edge-tts

---

### 21. video_jianying — 剪映视频草稿生成

根据 script.json 配置生成剪映视频草稿，支持多种场景类型、特效和转场。

- **端点**: `POST /tools/video_jianying`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `script_config` | dict/string | 是 | — | 脚本配置（JSON 对象或 JSON 字符串） |

- **依赖**: moviepy, webvtt-py, mutagen, pymediainfo
- **行为**: 返回 `draft_content` 和 `draft_meta_info`（剪映草稿格式），支持 opener、speech_scene 等场景类型

---

### 22. video_pipeline_auto — 自动化视频流水线

完整的视频生成流水线：TTS 音频 → 字幕 → 标题叠加 → 字幕烧录 → FFmpeg 渲染。

- **端点**: `POST /tools/video_pipeline_auto`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `script` | string | 是 | — | 脚本文本 |
| `background_video` | string | 是 | — | 背景视频（路径/URL/base64） |
| `voice` | string | 否 | "zh-CN-YunxiNeural" | TTS 语音角色 |
| `output_name` | string | 是 | — | 输出文件名 |
| `output_dir` | string | 是 | — | 输出目录 |
| `font` | string | 否 | "FangZhengSongJian" | 字体 |
| `font_size` | int | 否 | 15 | 字体大小 |
| `width` | int | 否 | 1080 | 视频宽度 |
| `height` | int | 否 | 1920 | 视频高度 |
| `fps` | int | 否 | 25 | 帧率 |
| `title` | string | 否 | — | 视频标题 |
| `title_font_size` | int | 否 | 90 | 标题字体大小 |
| `title_color` | string | 否 | "yellow" | 标题颜色 |
| `title_position` | string | 否 | "top" | 标题位置 |
| `max_chars_per_line` | int | 否 | 11 | 每行最大字符数 |
| `preview` | bool | 否 | false | 预览模式（仅渲染前 10 秒） |
| `rate` / `volume` / `pitch` | string | 否 | "+0%" / "+0%" / "+0Hz" | TTS 参数 |

- **依赖**: edge-tts==7.0.0, openai-whisper
- **存储**: `data/static/auto_video_pipeline/`

---

### 23. workflow_hub_signal — 工作流信号

向 Workflow Hub 发送信号，实时展示生成的媒体内容。

- **端点**: `POST /tools/workflow_hub_signal`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `workflow_name` | string | 是 | — | 工作流名称 |
| `path_suffix` | string | 是 | — | 媒体路径（相对路径/完整 URL/本地路径） |
| `media_type` | string | 否 | "image" | 媒体类型: image / video |
| `prompt` | string | 否 | — | 描述信息 |

- **依赖**: httpx
- **行为**: POST 到 `{hub_url}/api/signal`，用于实时仪表盘展示

---

### 24. zhihu_data_fetch — 知乎数据抓取

从知乎 URL 获取文章内容，包括标题、作者和正文。

- **端点**: `POST /tools/zhihu_data_fetch`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | 是 | 知乎文章 URL（支持付费专栏和 Soia 链接） |

- **依赖**: httpx

---

## 辅助模块

### sharing_utils — 共享工具库

提供各发布工具共用的 Cookie 获取功能，非独立工具（`enabled: false`）。

- 提供 `get_douyin_cookies`、`get_reddit_cookies`、`get_x_cookies`、`get_youtube_cookies`
- 各发布工具会尝试从此模块导入，失败时使用内联的 fallback 实现
- **配置要求**: `COOKIES_API_BASE`（Cookie 远程服务地址）
