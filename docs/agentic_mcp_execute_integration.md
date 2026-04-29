# Automata MCP Server Agentic 接入指南

本文档面向 `AutoUp-Agentic` 等调度端开发者，介绍如何使用全新的 `/execute` (信封模式) 接口来调用 MCP Server 上的业务工具。

## 1. 为什么设计这套接口？

在并发调度场景（特别是浏览器自动化场景）下，多个任务同时执行时需要隔离状态。例如：多个抖音账号同时并发发布视频时，每个任务都需要独立的浏览器实例和 CDP 端口。

旧版本 `/tools/{tool_name}` 直接传递业务参数，无法干净地透传这些控制信息。
新版本 `/tools/{tool_name}/execute` 引入了**“信封模式 (Envelope Pattern)”**，将控制信息（`task`、`session`、`options`）和纯业务数据（`payload`）完全分离，实现了底层隔离与高并发能力。

## 2. 接口说明

**Endpoint**: `POST /tools/{tool_name}/execute`
**Content-Type**: `application/json`
**鉴权方式**: 与旧接口保持一致（`Authorization: Bearer <Token>`）

### 2.1 请求体结构 (JSON)

所有走 `/execute` 接口的请求都**必须**遵守以下结构：

```json
{
  "task": {
    "task_id": "string", // [必填] 业务线上的唯一任务 ID
    "user_id": "string", // [必填] 触发任务的用户 ID (没有可填 "none")
    "account_id": "string", // [必填] 执行动作的子账号 ID (没有可填 "none")
    "platform": "string", // [必填] 目标平台, 例如 "douyin", "xiaohongshu"
    "action": "string" // [必填] 执行动作, 例如 "publish", "fetch"
  },
  "session": {
    // [选填] 如果工具的路由配置中指定了 requires_session=True 则必填
    "session_id": "string", // [必填] Agentic 侧分配的并发会话 ID
    "cdp_url": "string" // [必填] 分配给这个会话的专用 Playwright/CDP 调试地址
  },
  "payload": {
    // 这里放原工具定义的所有业务参数
    // 例如抖音视频发布工具：
    "video_path": "string",
    "title": "string",
    "description": "string",
    "bearer_token": "string"
  },
  "options": {
    // [选填] 执行侧选项
    "timeout": 120, // [选填] 本次调用的超时时间(秒)
    "retry": 0 // [选填] 失败重试次数
  }
}
```

### 2.2 响应体格式 (JSON)

响应结构与原接口保持一致（`BaseResponse` 格式）：

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "type": "text",
        "text": "✅ 视频发布成功!..."
      }
    ]
  },
  "error": null
}
```

## 3. 调用规范与落地示例

### 场景：并发调用两个社交平台的发布工具

在 Agentic (Coordinator) 层进行调用时，由于我们要保证它们在不同的浏览器端口运行以防账号串号，你需要为每一个请求动态分配一个 `session`。

**请求 1：发给抖音工具**

```http
POST /tools/douyin_publish_video/execute
```

```json
{
  "task": {
    "task_id": "video_publish_job_001",
    "user_id": "u_999",
    "account_id": "acc_dy_888",
    "platform": "douyin",
    "action": "publish"
  },
  "session": {
    "session_id": "sess_browser_port_9001",
    "cdp_url": "http://127.0.0.1:9001"
  },
  "payload": {
    "video_path": "/data/static/upload_videos/sample.mp4",
    "title": "这是给抖音的视频",
    "bearer_token": "your_token"
  }
}
```

**请求 2：同时发给快手工具**

```http
POST /tools/kuaishou_publish_video/execute
```

```json
{
  "task": {
    "task_id": "video_publish_job_002",
    "user_id": "u_999",
    "account_id": "acc_ks_777",
    "platform": "kuaishou",
    "action": "publish"
  },
  "session": {
    "session_id": "sess_browser_port_9002",
    "cdp_url": "http://127.0.0.1:9002"
  },
  "payload": {
    "video_path": "/data/static/upload_videos/sample.mp4",
    "title": "这是给快手的视频",
    "bearer_token": "your_token"
  }
}
```

## 4. 常见问题 (FAQ)

**Q1：我如何知道一个工具是否**必须**传入 `session`？**
A：所有的发布类工具（那些最终受浏览器驱动发推文/视频的工具）我们在路由注册时都强制设置了 `requires_session=True`。如果你请求 `/execute` 但没有带 `session`，或者 `cdp_url` 为空，服务端会直接拒接返回 HTTP `422 Unprocessable Entity`。

**Q2：对于那些不涉及浏览器的底层工具（如文本润色等），能用这个接口吗？**
A：可以。对于非浏览器工具，您可以继续打老的 `/tools/text_polish`，也可以打新接口 `/tools/text_polish/execute`。如果打新接口，`session` 字段可以选择不传或传 `null`（除非未来扩展了必须控制该工具并发边界的规则）。

**Q3：`task` 下的字段（比如 `account_id`）我有时候没有业务对象对应，怎么办？**
A：`task` 这个 dict 下面的 5 个字段是 Pydantic 强校验的。如果您手头没有这些值，请传入 `"none"` 或者 `""` (空字符串) 作为占位符。千万不能直接把这个 key 从 JSON 中删掉，否则会报校验错误。

## 5. 迁移路线与回退计划

目前 MCP Server 保证了完全的**双向兼容**：

- 老版本路由 (`/tools/{tool_name}`) 继续提供服务。它们依然读取环境变量 (`PLAYWRIGHT_CDP_URL`)。
- 建议所有从 Agentic 发出的**自动化编排、高并发**请求，逐步全量切换到 `/tools/{tool_name}/execute` 接口。
