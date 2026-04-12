# Extension Tools Logging & Error Handling Improvement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify logging and error handling across all 21 extension tools by adding `self.logger` to `BaseMCPTool` and migrating all tools.

**Architecture:** Add `self.logger = logger.bind(tool=class_name)` to `BaseMCPTool.__init__`. Then fix tools in 3 batches: critical (zero logging / print / dual systems), medium (wrong exception types), and standardization (mechanical `logger` → `self.logger` migration).

**Tech Stack:** Python 3, loguru, mcp SDK (McpError)

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `app/base_tool.py` | Modify | Add `self.logger` field |
| `app/AutoUp-MCP-Extension/image_generate_jimeng/image_generate_jimeng_tool.py` | Modify | Add missing logging |
| `app/AutoUp-MCP-Extension/image_generate_jimeng/config.yaml` | Modify | Add loguru to packages |
| `app/AutoUp-MCP-Extension/Reddit_publish/Reddit.py` | Modify | Replace ~40 `print()` → `logger` |
| `app/AutoUp-MCP-Extension/video_pipeline_auto/video_core/editor.py` | Modify | Replace ~15 `print()` → `logger` |
| `app/AutoUp-MCP-Extension/video_pipeline_auto/video_core/font_utils.py` | Modify | Replace `print()` in `__main__` block |
| `app/AutoUp-MCP-Extension/Youtube_publish/youtube.py` | Modify | Replace stdlib `logging` → `loguru` |
| `app/AutoUp-MCP-Extension/image_generate_midjourney/image_generate_midjourney_tool.py` | Modify | Return error strings → raise `McpError` |
| `app/AutoUp-MCP-Extension/sharing_utils/cookie_get.py` | Modify | `raise Exception` → `raise McpError` |
| `app/AutoUp-MCP-Extension/workflow_hub_signal/config.yaml` | Modify | `dependencies` → `packages` |
| `app/AutoUp-MCP-Extension/workflow_hub_signal/workflow_hub_signal_tool.py` | Modify | `logger` → `self.logger` |
| 13 remaining tool wrappers | Modify | `logger` → `self.logger` |

---

## Task 1: Add `self.logger` to BaseMCPTool

**Files:**
- Modify: `app/base_tool.py`

- [ ] **Step 1: Add logger to BaseMCPTool.\_\_init\_\_**

```python
# app/base_tool.py — full replacement
from abc import ABC, abstractmethod
from typing import Sequence

from loguru import logger
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from .extension_config import ExtensionConfigManager
from .schemas import BaseResponse


class BaseMCPTool(ABC):
    def __init__(self):
        self.config_manager = ExtensionConfigManager()
        class_name = self.__class__.__name__
        self.logger = logger.bind(tool=class_name)

    def get_response_model(self) -> type[BaseResponse]:
        """Get the response model for this tool's endpoints.
        Can be overridden by subclasses to provide custom response models.
        """
        return BaseResponse

    @abstractmethod
    async def list_tools(self) -> list[Tool]:
        """List the tools provided by this module."""

    @abstractmethod
    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name with given arguments."""

    @abstractmethod
    def get_route_config(self) -> list[dict]:
        """Get route configurations for this tool.

        Returns:
            list[dict]: List of configurations containing 'endpoint', 'params_class', etc.
        """
```

- [ ] **Step 2: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/base_tool.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add app/base_tool.py
git commit -m "feat: add self.logger to BaseMCPTool with tool name binding"
```

---

## Task 2: Fix image_generate_jimeng — add logging (zero → complete)

**Files:**
- Modify: `app/AutoUp-MCP-Extension/image_generate_jimeng/image_generate_jimeng_tool.py`
- Modify: `app/AutoUp-MCP-Extension/image_generate_jimeng/config.yaml`

- [ ] **Step 1: Add logging to image_generate_jimeng_tool.py**

Replace `from .volcengine_sign import volcengine_request` import block (line 17) — keep it as-is. The change is to replace the bare `from app.base_tool import BaseMCPTool` with usage of `self.logger`.

In `call_tool` (starting at line 255), add logging:

```python
    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | TextResourceContents]:
        self.logger.info(f"Calling tool: {name}")

        if name != "image_generate_jimeng":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = JimengImageGenerateParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        # 验证参数
        if not args.prompt.strip():
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Prompt cannot be empty"),
            )

        if len(args.prompt) > 800:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message="Prompt cannot exceed 800 characters",
                ),
            )

        if args.image_urls and len(args.image_urls) > 10:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message="Cannot input more than 10 reference images",
                ),
            )

        self.logger.info(f"Generating image with prompt: {args.prompt[:50]}...")

        # 获取AK和SK from config
        ak = self.config_manager.get_config_value("image_generate_jimeng", "ak")
        sk = self.config_manager.get_config_value("image_generate_jimeng", "sk")

        if not ak or not sk:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS,
                    message="Jimeng API credentials not configured. Please set 'ak' and 'sk' in config/config.json under 'image_generate_jimeng' section.",
                ),
            )

        try:
            # 提交任务
            self.logger.debug("Submitting task to Volcengine API")
            task_id = await self._submit_task(
                ak,
                sk,
                args.prompt,
                args.image_urls,
                args.width,
                args.height,
                args.scale,
            )
            self.logger.info(f"Task submitted, task_id: {task_id}")

            # 轮询结果
            self.logger.debug(f"Polling for task result, task_id: {task_id}")
            image_urls = await self._poll_task_result(ak, sk, task_id)

            # 构建返回消息
            urls_str = ";".join(image_urls)
            resources = [TextContent(type="text", text=urls_str)]

            self.logger.info(f"Image generation completed, {len(image_urls)} URLs returned")
            return resources

        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e!s}")
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Unexpected error: {e!s}"),
            )
```

Also add logging to `_submit_task` (line 76), add after `body = json.dumps(body_dict)` (line 100):

```python
        self.logger.debug(f"Submitting task with body: {body[:200]}")
```

And in `_poll_task_result` (line 161), add inside the polling loop after `status = data.get("status")` (line 168):

```python
                self.logger.debug(f"Polling task {task_id}, status: {status}")
```

- [ ] **Step 2: Remove `from loguru import logger` since we use `self.logger` now**

The file `image_generate_jimeng_tool.py` does NOT currently import loguru at all, so no removal needed.

- [ ] **Step 3: Add loguru to config.yaml packages**

Replace `app/AutoUp-MCP-Extension/image_generate_jimeng/config.yaml`:

```yaml
enabled: true
packages:
  - httpx
  - loguru

config_requirements:
  ak:
    type: "string"
    description: "火山引擎即梦 API 的 Access Key ID"
    required: true
    default: ""
  sk:
    type: "string"
    description: "火山引擎即梦 API 的 Secret Access Key"
    required: true
    default: ""
```

- [ ] **Step 4: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/image_generate_jimeng/`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add app/AutoUp-MCP-Extension/image_generate_jimeng/
git commit -m "feat: add logging to image_generate_jimeng tool"
```

---

## Task 3: Fix Reddit.py — replace print() with loguru

**Files:**
- Modify: `app/AutoUp-MCP-Extension/Reddit_publish/Reddit.py`

- [ ] **Step 1: Replace print() with logger in Reddit.py**

At the top of the file, add the logger import after the existing imports (after line 5):

```python
from loguru import logger
```

Replace ALL `print()` calls with logger equivalents. Here is the complete list of replacements:

```python
# Line 34: print("✅ Cookies injected from data successfully.")
logger.info("Cookies injected from data successfully")

# Line 39: print("✅ Cookies injected from file successfully.")
logger.info("Cookies injected from file successfully")

# Line 41: print("⚠️ Warning: No cookies data or file found!")
logger.warning("No cookies data or file found")

# Line 62: print(f"👉 Selecting community: {subreddit_name}")
logger.info(f"Selecting community: {subreddit_name}")

# Line 78: print(f"⌨️ Typed '{subreddit_name}'. Waiting 3 seconds for search results...")
logger.info(f"Typed '{subreddit_name}'. Waiting for search results...")

# Line 92: print(f"🎯 Looking for element with selector: {target_selector}")
logger.debug(f"Looking for element with selector: {target_selector}")

# Line 101: print(f"✅ Clicked target for {subreddit_name}")
logger.info(f"Clicked target for {subreddit_name}")

# Line 104: print(f"⚠️ Click selection failed: {e}")
logger.warning(f"Click selection failed: {e}")

# Line 107: print("👉 Trying fallback: Searching by text content...")
logger.info("Trying fallback: Searching by text content...")

# Line 115: print(f"⚠️ Fallback also failed. Using Enter key. Error: {e2}")
logger.warning(f"Fallback also failed. Using Enter key. Error: {e2}")

# Lines 119-121: print("⏳ Community selected. Waiting 3 seconds...")
logger.info("Community selected. Waiting for page configuration reload...")

# Line 130: print(f"⚠️ Warning: Title box unstable after selection. Error: {e}")
logger.warning(f"Title box unstable after selection. Error: {e}")

# Line 138: print(f"✍️ Filling title: {title}")
logger.info(f"Filling title: {title}")

# Line 144: print(f"✍️ Filling body text: {body_text[:20]}...")
logger.info(f"Filling body text: {body_text[:20]}...")

# Line 157: print("   -> Detected Media Post Editor")
logger.debug("Detected Media Post Editor")

# Line 162: print("   -> Detected Text Post Editor")
logger.debug("Detected Text Post Editor")

# Line 167: print("   -> Using generic fallback for body text")
logger.debug("Using generic fallback for body text")

# Line 175: print(f"⚠️ Failed to fill body text: {e}")
logger.warning(f"Failed to fill body text: {e}")

# Line 182: print(f"📤 Uploading file: {file_path}")
logger.info(f"Uploading file: {file_path}")

# Line 199-200: print(f"   -> Found visible upload button at index {i}, clicking...")
logger.debug(f"Found visible upload button at index {i}, clicking...")

# Line 208-210: print("⚠️ No visible upload button found, forcing click...")
logger.warning("No visible upload button found, forcing click on first index...")

# Line 217: print("⏳ File uploaded. Waiting 15 seconds as requested...")
logger.info("File uploaded. Waiting 15 seconds...")

# Line 222: print("🚀 Clicking Post button...")
logger.info("Clicking Post button...")

# Line 230: print("⚠️ Submit button not enabled yet, waiting...")
logger.warning("Submit button not enabled yet, waiting...")

# Line 234: print("⏳ Post submitted. Waiting 15 seconds before closing browser...")
logger.info("Post submitted. Waiting before closing browser...")

# Line 250: print("🔹 Creating TEXT post")
logger.info("Creating TEXT post")

# Line 264: print("🔹 Creating MEDIA post")
logger.info("Creating MEDIA post")

# Line 280: print("📝 Now filling body text after upload...")
logger.info("Now filling body text after upload...")

# Line 285: print("🔹 Creating LINK post")
logger.info("Creating LINK post")

# Line 300: print(f"🔗 Filling URL: {link_url}")
logger.info(f"Filling URL: {link_url}")

# Line 308: print(f"❌ Error occurred: {e}")
logger.error(f"Error occurred: {e}")
```

- [ ] **Step 2: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/Reddit_publish/Reddit.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add app/AutoUp-MCP-Extension/Reddit_publish/Reddit.py
git commit -m "fix: replace print() with loguru in Reddit.py"
```

---

## Task 4: Fix editor.py and font_utils.py — replace print() with loguru

**Files:**
- Modify: `app/AutoUp-MCP-Extension/video_pipeline_auto/video_core/editor.py`
- Modify: `app/AutoUp-MCP-Extension/video_pipeline_auto/video_core/font_utils.py`

- [ ] **Step 1: Replace print() in editor.py**

At the top of editor.py, add after the existing imports (after line 5):

```python
from loguru import logger
```

Replace all `print()` calls:

```python
# Line 44: print(f"获取媒体时长失败: {e}")
# becomes:
logger.error(f"获取媒体时长失败: {e}")

# Line 62: print(f"添加音频轨道: {media_file_full_name}")
# becomes:
logger.info(f"添加音频轨道: {media_file_full_name}")

# Line 73: print(f"添加背景视频/图片: {media_file_full_name}")
# becomes:
logger.info(f"添加背景视频/图片: {media_file_full_name}")

# Line 247: print("错误: 没有媒体输入")
# becomes:
logger.error("错误: 没有媒体输入")

# Line 363: print(f"系统核心数: {total_cores}, 优化 FFmpeg 线程数: {threads_count}")
# becomes:
logger.info(f"系统核心数: {total_cores}, 优化 FFmpeg 线程数: {threads_count}")

# Line 384: print(f"执行纯 FFmpeg 渲染...\nCMD: {' '.join(cmd)}")
# becomes:
logger.info(f"执行纯 FFmpeg 渲染, CMD: {' '.join(cmd)}")

# Line 388: print(f"渲染完成: {output_path}")
# becomes:
logger.info(f"渲染完成: {output_path}")

# Line 390: print(f"FFmpeg 渲染失败: {e}")
# becomes:
logger.error(f"FFmpeg 渲染失败: {e}")
```

- [ ] **Step 2: Replace print() in font_utils.py `__main__` block**

In `font_utils.py`, the `__main__` block (lines 156-170) uses `print()`. Replace:

```python
if __name__ == "__main__":
    logger.info("检查 fc-scan 是否可用...")
    if check_fc_scan_available():
        logger.info("fc-scan 可用")
    else:
        logger.info("fc-scan 不可用，请安装 fontconfig")

    # 测试获取字体信息
    fonts_dir = Path(__file__).parent.parent / "fonts"
    if fonts_dir.exists():
        logger.info(f"扫描字体目录: {fonts_dir}")
        font_map = get_font_info_from_dir(str(fonts_dir))
        for file_name, family_name in font_map.items():
            logger.info(f"  {file_name} -> {family_name}")
```

- [ ] **Step 3: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/video_pipeline_auto/video_core/`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add app/AutoUp-MCP-Extension/video_pipeline_auto/video_core/
git commit -m "fix: replace print() with loguru in editor.py and font_utils.py"
```

---

## Task 5: Fix youtube.py — replace stdlib logging with loguru

**Files:**
- Modify: `app/AutoUp-MCP-Extension/Youtube_publish/youtube.py`

- [ ] **Step 1: Replace stdlib logging with loguru in youtube.py**

Replace `import logging` (line 2) with:

```python
from loguru import logger
```

Replace the `__init__` logger setup (lines 31-38). Remove the entire block:

```python
        # 初始化日志记录器
        self.logger = logging.getLogger("YouTubeUploader")
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
```

Replace with:

```python
        self.logger = logger.bind(tool="YouTubeUploader")
```

All `self.logger.info/error/warning` calls remain the same — they now go through loguru instead of stdlib logging.

- [ ] **Step 2: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/Youtube_publish/youtube.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add app/AutoUp-MCP-Extension/Youtube_publish/youtube.py
git commit -m "fix: replace stdlib logging with loguru in youtube.py"
```

---

## Task 6: Fix image_generate_midjourney — error strings → McpError

**Files:**
- Modify: `app/AutoUp-MCP-Extension/image_generate_midjourney/image_generate_midjourney_tool.py`

- [ ] **Step 1: Replace `from loguru import logger` (line 8) with nothing**

Remove line 8: `from loguru import logger`. This tool will use `self.logger`.

Add at the beginning of `call_tool` (after line 90):

```python
        self.logger.info(f"Calling tool: {name}")
```

- [ ] **Step 2: Fix `_send_request` to raise McpError instead of returning error strings**

Replace the `_send_request` method (lines 266-306). The method currently returns error strings on failure. Change it to raise `McpError`:

```python
    def _send_request(self, url: str, headers: dict, data: dict) -> str:
        """Send POST request using cloudscraper and return job_id"""
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
            response = scraper.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                try:
                    result = response.json()

                    if (
                        "success" in result
                        and isinstance(result["success"], list)
                        and len(result["success"]) > 0
                    ):
                        job_id = result["success"][0]["job_id"]
                        self.logger.info(f"Successfully got job_id: {job_id}")
                        return job_id

                    error_msg = f"Request failed: No success in response. Response: {response.text[:500]}"
                    self.logger.error(error_msg)
                    raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))
                except McpError:
                    raise
                except Exception as e:
                    error_msg = f"Failed to parse JSON: {e}. Response text: {response.text[:500]}"
                    self.logger.error(error_msg)
                    raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))
            else:
                error_msg = f"Request failed with status code: {response.status_code}. Response: {response.text[:1000]}"
                self.logger.error(error_msg)
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))
        except McpError:
            raise
        except Exception as e:
            error_msg = f"Exception during request: {type(e).__name__}: {str(e)}"
            self.logger.error(error_msg)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))
```

- [ ] **Step 3: Fix `_download_images_sync` to raise McpError instead of returning error strings**

Replace the `_download_images_sync` method (lines 202-264). Same pattern — error strings become `McpError` raises:

```python
    def _download_images_sync(self, job_id: str, output_dir: str) -> str:
        """Download images synchronously using cloudscraper"""

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'sec-ch-ua': '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Dest': 'image',
            'Referer': 'https://www.midjourney.com/',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6'
        }

        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
        except Exception as e:
            error_msg = f"Failed to create scraper: {type(e).__name__}: {str(e)}"
            self.logger.error(error_msg)
            raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))

        image_urls = []

        for i in range(4):
            url = f"https://cdn.midjourney.com/{job_id}/0_{i}.jpeg"

            try:
                response = scraper.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    image_filename = f"{job_id}_image_{i}.jpeg"
                    image_path = os.path.join(output_dir, image_filename)

                    with open(image_path, 'wb') as f:
                        f.write(response.content)

                    image_url = f"/static/image_generate_midjourney/{image_filename}"
                    image_urls.append(image_url)
                    self.logger.info(f"Downloaded image {i} to {image_path} ({len(response.content)} bytes)")
                else:
                    error_msg = f"Failed to download image {i}: HTTP {response.status_code}"
                    self.logger.error(error_msg)
                    raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))
            except McpError:
                raise
            except Exception as e:
                error_msg = f"Failed to download image {i}: {type(e).__name__}: {str(e)}"
                self.logger.error(error_msg)
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=error_msg))

        result_message = ";".join(image_urls)
        self.logger.info(f"Successfully downloaded all 4 images for job_id: {job_id}")
        return result_message
```

- [ ] **Step 4: Fix `_handle_generate` and `_handle_get_images` — replace `logger.` with `self.logger.`**

In `_handle_generate` (line 98):
- Line 100-102: `logger.info(...)` → `self.logger.info(...)`
- Line 172: `logger.info(...)` → `self.logger.info(...)`

In `_handle_get_images` (line 175):
- Line 177-179: `logger.info(...)` → `self.logger.info(...)`

- [ ] **Step 5: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/image_generate_midjourney/`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add app/AutoUp-MCP-Extension/image_generate_midjourney/
git commit -m "fix: image_generate_midjourney raise McpError instead of returning error strings"
```

---

## Task 7: Fix sharing_utils cookie_get.py and workflow_hub_signal config.yaml

**Files:**
- Modify: `app/AutoUp-MCP-Extension/sharing_utils/cookie_get.py`
- Modify: `app/AutoUp-MCP-Extension/workflow_hub_signal/config.yaml`
- Modify: `app/AutoUp-MCP-Extension/workflow_hub_signal/workflow_hub_signal_tool.py`

- [ ] **Step 1: Fix cookie_get.py — replace `raise Exception` with `raise McpError`**

Replace the import section (lines 1-6):

```python
from typing import Any

import requests
from loguru import logger
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS

from app.extension_config import ExtensionConfigManager
```

Then replace all `raise Exception(...)` calls:

```python
# Line 37: raise Exception(f"API返回错误: {data.get('msg', 'unknown error')}")
raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"API返回错误: {data.get('msg', 'unknown error')}"))

# Line 41: raise Exception("未获取到cookies")
raise McpError(ErrorData(code=INTERNAL_ERROR, message="未获取到cookies"))

# Line 48: raise Exception(f"获取cookies失败: {e}")
raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"获取cookies失败: {e}"))

# Line 50: (inside except Exception) raise Exception(f"解析cookies失败: {e}")
raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"解析cookies失败: {e}"))

# Line 81: raise Exception(f"API返回错误: {data.get('msg', 'unknown error')}")
raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"API返回错误: {data.get('msg', 'unknown error')}"))

# Line 85: raise Exception("未获取到cookies")
raise McpError(ErrorData(code=INTERNAL_ERROR, message="未获取到cookies"))

# Line 95: raise Exception(f"获取cookies失败: {e}")
raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"获取cookies失败: {e}"))

# Line 98: raise Exception(f"解析cookies失败: {e}")
raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"解析cookies失败: {e}"))
```

- [ ] **Step 2: Fix workflow_hub_signal config.yaml**

Read the current config.yaml and change the `dependencies` key to `packages`. The rest of the file stays the same.

- [ ] **Step 3: Migrate workflow_hub_signal_tool.py to self.logger**

In `workflow_hub_signal_tool.py`:
- Remove `from loguru import logger` (line 6)
- Replace all `logger.info/error/debug` with `self.logger.info/error/debug` (11 occurrences at lines 53, 54, 84, 109, 136, 137, 145, 149, 155-156, 162, 168)

- [ ] **Step 4: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/sharing_utils/ app/AutoUp-MCP-Extension/workflow_hub_signal/`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add app/AutoUp-MCP-Extension/sharing_utils/cookie_get.py app/AutoUp-MCP-Extension/workflow_hub_signal/
git commit -m "fix: cookie_get.py use McpError, workflow_hub_signal normalize config and migrate to self.logger"
```

---

## Task 8: Batch migrate — douyin_publish_photo_text and douyin_publish_video

**Files:**
- Modify: `app/AutoUp-MCP-Extension/douyin_publish_photo_text/douyin_publish_photo_text_tool.py`
- Modify: `app/AutoUp-MCP-Extension/douyin_publish_video/douyin_publish_video_tool.py`

- [ ] **Step 1: Migrate douyin_publish_photo_text_tool.py**

Remove `from loguru import logger` (line 13).

Replace all `logger.` calls with `self.logger.`:
- Line 144: `logger.info(...)` → `self.logger.info(...)`
- Lines 178-180: `logger.info(...)` → `self.logger.info(...)`
- Line 202: `logger.success(...)` → `self.logger.success(...)`
- Line 205: `logger.error(...)` → `self.logger.error(...)`
- Line 213: `logger.error(...)` → `self.logger.error(...)`
- Line 223: `logger.error(...)` → `self.logger.error(...)`
- Line 237: `logger.error(...)` → `self.logger.error(...)`

- [ ] **Step 2: Migrate douyin_publish_video_tool.py**

Same pattern. Remove `from loguru import logger` (line 13).

Replace all `logger.` calls with `self.logger.`:
- Line 144: `logger.info(...)` → `self.logger.info(...)`
- Lines 169-171: `logger.info(...)` → `self.logger.info(...)`
- Line 192: `logger.success(...)` → `self.logger.success(...)`
- Line 195: `logger.error(...)` → `self.logger.error(...)`
- Line 203: `logger.error(...)` → `self.logger.error(...)`
- Line 213: `logger.error(...)` → `self.logger.error(...)`
- Line 227: `logger.error(...)` → `self.logger.error(...)`

- [ ] **Step 3: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/douyin_publish_photo_text/ app/AutoUp-MCP-Extension/douyin_publish_video/`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add app/AutoUp-MCP-Extension/douyin_publish_photo_text/douyin_publish_photo_text_tool.py app/AutoUp-MCP-Extension/douyin_publish_video/douyin_publish_video_tool.py
git commit -m "refactor: migrate douyin tools from logger to self.logger"
```

---

## Task 9: Batch migrate — kuaishou_publish_photo and kuaishou_publish_video

**Files:**
- Modify: `app/AutoUp-MCP-Extension/kuaishou_publish_photo/kuaishou_publish_photo_tool.py`
- Modify: `app/AutoUp-MCP-Extension/kuaishou_publish_video/kuaishou_publish_video_tool.py`

- [ ] **Step 1: Migrate kuaishou_publish_photo_tool.py**

Remove `from loguru import logger` (line 11).

Replace all `logger.` calls with `self.logger.` (22 occurrences across lines 130, 135, 149-151, 160, 163, 168, 171, 184, 189, 203-205, 213, 216, 220, 238, 240, 244, 248, 297, 325-327, 351, 354, 364).

- [ ] **Step 2: Migrate kuaishou_publish_video_tool.py**

Remove `from loguru import logger` (line 11).

Replace all `logger.` calls with `self.logger.` (22 occurrences across lines 95, 116, 120, 131-132, 142, 145, 150, 154, 173, 178, 192-193, 202, 205, 209, 229, 231, 235, 239, 271, 297, 320, 323, 333).

- [ ] **Step 3: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/kuaishou_publish_photo/ app/AutoUp-MCP-Extension/kuaishou_publish_video/`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add app/AutoUp-MCP-Extension/kuaishou_publish_photo/ app/AutoUp-MCP-Extension/kuaishou_publish_video/
git commit -m "refactor: migrate kuaishou tools from logger to self.logger"
```

---

## Task 10: Batch migrate — Batch 3 standardization (9 tools)

**Files:**
- Modify: `app/AutoUp-MCP-Extension/text_polish/text_polish_tool.py`
- Modify: `app/AutoUp-MCP-Extension/text_to_image/text_to_image_tool.py`
- Modify: `app/AutoUp-MCP-Extension/tts_clone_minimax/tts_clone_minimax_tool.py`
- Modify: `app/AutoUp-MCP-Extension/tts_edge/tts_edge_tool.py`
- Modify: `app/AutoUp-MCP-Extension/tts_minimax/tts_minimax_tool.py`
- Modify: `app/AutoUp-MCP-Extension/video_generate/video_generate_tool.py`
- Modify: `app/AutoUp-MCP-Extension/video_jianying/video_jianying_tool.py`
- Modify: `app/AutoUp-MCP-Extension/xiaohongshu_publish/xiaohongshu_publish_tool.py`
- Modify: `app/AutoUp-MCP-Extension/X_publish/X_publish_tool.py`
- Modify: `app/AutoUp-MCP-Extension/zhihu_data_fetch/zhihu_data_fetch_tool.py`

For each file, the same mechanical transformation applies:
1. Remove `from loguru import logger` import line
2. Replace all `logger.` → `self.logger.`

- [ ] **Step 1: text_polish_tool.py** — Remove import (line 5), replace 3 occurrences (lines 52, 86, 94)

- [ ] **Step 2: text_to_image_tool.py** — Remove import (line 4), replace 2 occurrences (lines 45, 69)

- [ ] **Step 3: tts_clone_minimax_tool.py** — Remove import (line 5), replace 2 occurrences (lines 46, 59)

- [ ] **Step 4: tts_edge_tool.py** — Remove import (line 5), replace 3 occurrences (lines 63, 84, 106)

- [ ] **Step 5: tts_minimax_tool.py** — Remove import (line 5), replace 3 occurrences (lines 58, 79, 97)

- [ ] **Step 6: video_generate_tool.py** — Remove import (line 8), replace 4 occurrences (lines 86-88, 123, 130, 135)

- [ ] **Step 7: video_jianying_tool.py** — Remove import (line 10), replace 4 occurrences (lines 79, 97, 105, 114)

- [ ] **Step 8: xiaohongshu_publish_tool.py** — Remove import (line 10), replace all ~35 occurrences

- [ ] **Step 9: X_publish_tool.py** — Remove import (line 13), replace 7 occurrences (lines 137, 161-163, 181, 184, 190, 200, 214)

- [ ] **Step 10: zhihu_data_fetch_tool.py** — Remove import (line 7), replace 6 occurrences (lines 57-59, 79-81, 83, 97-99, 101, 286-288)

- [ ] **Step 11: Verify with linter**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check app/AutoUp-MCP-Extension/`
Expected: No errors

- [ ] **Step 12: Commit**

```bash
git add app/AutoUp-MCP-Extension/
git commit -m "refactor: migrate batch 3 tools from logger to self.logger"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run full linter check**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && uv run ruff check --fix . && uv run ruff format .`
Expected: All checks pass

- [ ] **Step 2: Verify no remaining print() in tool code**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && grep -rn "print(" app/AutoUp-MCP-Extension/ --include="*.py"`
Expected: Only `__main__` blocks or comment lines, no active `print()` in tool logic

- [ ] **Step 3: Verify no remaining bare `from loguru import logger` in tool wrapper files**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && grep -rn "from loguru import logger" app/AutoUp-MCP-Extension/ --include="*_tool.py"`
Expected: Zero results — all tool wrappers should use `self.logger`

- [ ] **Step 4: Verify no remaining `raise Exception` in sharing_utils**

Run: `cd D:/codes/EgooAI/AutoUp/Automata-mcp-server && grep -rn "raise Exception" app/AutoUp-MCP-Extension/sharing_utils/`
Expected: Zero results
