# Automata MCP Server Agentic 接入指南

本文档面向 `AutoUp-Agentic` 等调度端开发者，介绍如何使用 `/tools/{tool_name}/execute` 接口调用 MCP Server 上的业务工具。

本文定义的是 **MCP 当前真实可调用协议**，用于指导现网接入。本文不讨论 `task.session` 等未来演进结构，避免与架构草案混淆。

## 1. 为什么设计这套接口？

在并发调度场景，尤其是浏览器自动化场景下，多个任务同时执行时必须隔离执行上下文。例如多个账号并发发布视频时，每个任务都需要独立的浏览器会话和 CDP 调试地址。

旧版本 `/tools/{tool_name}` 直接传递业务参数，无法干净透传任务级控制信息。新版本 `/tools/{tool_name}/execute` 引入“信封模式 (Envelope Pattern)”，将控制信息（`task`、`session`、`options`）与业务参数（`payload`）分离，便于会话隔离、并发执行和统一治理。

### 1.1 职责边界

推荐按以下边界协作：

- `Agentic` 负责组装任务、申请并透传 `session`、调用 MCP。
- `Coordinator` 负责签发 `session_id + cdp_url`，管理浏览器生命周期和账号会话。
- `MCP` 只消费执行上下文并执行工具，不负责挑选浏览器，也不负责分配账号。

## 2. 接口说明

**Endpoint**: `POST /tools/{tool_name}/execute`
**Content-Type**: `application/json`
**鉴权方式**: 与旧接口保持一致（`Authorization: Bearer <Token>`）

### 2.1 请求体结构

所有走 `/execute` 接口的请求都必须使用如下顶层结构：

```json
{
  "task": {
    "task_id": "string",
    "user_id": "string",
    "account_id": "string",
    "platform": "string",
    "action": "string"
  },
  "session": {
    "session_id": "string",
    "cdp_url": "string"
  },
  "payload": {},
  "options": {
    "timeout": 120,
    "retry": 0
  }
}
```

说明：

- `task` 是任务元信息，对应服务端 `TaskMeta`。
- `session` 是顶层字段，对应服务端 `SessionMeta`，**不属于 `task` 子对象**。
- `payload` 是具体工具的业务参数，对应工具自身 `params_class`。
- `options` 是本次调用的执行控制项，对应服务端 `ExecutionOptions`。

### 2.2 字段约束

#### `task`

`task` 目前固定包含以下 5 个字段，均为必填：

```json
{
  "task_id": "string",
  "user_id": "string",
  "account_id": "string",
  "platform": "string",
  "action": "string"
}
```

- `task_id`: 业务侧唯一任务 ID
- `user_id`: 触发任务的用户 ID，没有可传 `"none"` 或空字符串
- `account_id`: 执行动作的子账号 ID，没有可传 `"none"` 或空字符串
- `platform`: 目标平台，例如 `douyin`、`xiaohongshu`
- `action`: 执行动作，例如 `publish`、`fetch`

#### `session`

`session` 为可选字段，但当工具路由配置了 `requires_session=True` 时必须传入：

```json
{
  "session_id": "string",
  "cdp_url": "string"
}
```

- `session_id`: 上游分配的会话 ID，用于追踪和隔离本次执行
- `cdp_url`: 本次执行使用的专用 CDP 地址

#### `payload`

`payload` 只放工具原有业务参数，不放调度控制字段。

例如抖音视频发布工具：

```json
{
  "video_path": "string",
  "title": "string",
  "description": "string",
  "bearer_token": "string"
}
```

#### `options`

`options` 为可选字段，不传时服务端使用默认值：

```json
{
  "timeout": 120,
  "retry": 0
}
```

- `timeout`: 本次调用超时时间（秒），默认 `120`
- `retry`: 失败重试次数，默认 `0`

### 2.3 响应体格式

响应结构与原接口保持一致，仍使用 `BaseResponse`：

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "type": "text",
        "text": "✅ 视频发布成功"
      }
    ]
  },
  "error": null
}
```

## 3. 当前实现细节

当前 MCP 服务端的实际行为如下：

- `/execute` 会先用 `payload` 反序列化为目标工具的参数对象。
- 对 `requires_session=True` 的工具，会校验 `session` 是否存在、`session.session_id` 是否非空、`session.cdp_url` 是否非空。
- 校验通过后，服务端会将 `task/session/options` 注入请求级执行上下文，再调用具体工具。

浏览器相关工具当前会优先读取请求级 `cdp_url`。只有在请求上下文中没有 `cdp_url` 时，才回退读取环境变量 `PLAYWRIGHT_CDP_URL`。因此：

- `session.cdp_url` 是 `/execute` 模式下的主路径。
- `PLAYWRIGHT_CDP_URL` 仅用于兼容旧模式或本地调试兜底。

## 4. 调用规范与示例

### 4.1 推荐调用链

推荐按如下顺序接入：

1. `Agentic` 创建业务任务。
2. `Agentic` 向 `Coordinator` 申请本次执行所需的 `session_id + cdp_url`。
3. `Agentic` 组装 `task/session/payload/options` 信封并调用 MCP。
4. `MCP` 消费执行上下文并执行工具。
5. 工具执行结束后，由上游按自身流程决定是否释放会话。

### 4.2 并发发布示例

场景：并发调用两个社交平台的发布工具，每个请求使用独立 `session`，避免账号串用。

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
    "description": "自动化发布示例",
    "bearer_token": "your_token"
  },
  "options": {
    "timeout": 120,
    "retry": 0
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
  },
  "options": {
    "timeout": 120,
    "retry": 0
  }
}
```

## 5. 常见问题

**Q1：我如何知道一个工具是否必须传入 `session`？**
A：发布类工具通常在路由注册时设置了 `requires_session=True`。这类工具调用 `/execute` 时，必须提供非空的 `session.session_id` 和 `session.cdp_url`。任一缺失或为空，服务端都会返回 HTTP `422 Unprocessable Entity`。

**Q2：`session` 应该放在 `task` 里面吗？**
A：不应该。当前协议中，`session` 是顶层字段，和 `task`、`payload`、`options` 同级。`task.session` 不属于当前 MCP 可调用协议。

**Q3：非浏览器工具也能走 `/execute` 吗？**
A：可以。对于非浏览器工具，可以继续调用老接口 `/tools/{tool_name}`，也可以调用 `/tools/{tool_name}/execute`。如果该工具没有配置 `requires_session=True`，则 `session` 可以不传或传 `null`。

**Q4：`task` 下的字段有些我暂时没有业务值，怎么办？**
A：`task` 当前由 Pydantic 强校验，5 个字段都必须出现。若暂时没有实际值，请传 `"none"` 或空字符串占位，不要直接删除字段。

## 6. 迁移路线与兼容说明

当前 MCP Server 保持双路兼容：

- 老版本接口 `/tools/{tool_name}` 继续提供服务，通常依赖环境变量 `PLAYWRIGHT_CDP_URL`。
- 新版本接口 `/tools/{tool_name}/execute` 是面向任务隔离、会话透传和并发发布的推荐调用方式。

推荐策略：

1. 非并发、非浏览器场景可以继续使用老接口。
2. 所有需要显式透传会话上下文的编排请求，优先切换到 `/tools/{tool_name}/execute`。
3. 在完全切换前，可以保留老接口作为回退路径，但新接入优先遵循本文档定义的顶层 `task/session/payload/options` 协议。
