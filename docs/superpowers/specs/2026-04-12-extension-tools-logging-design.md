# Extension Tools Logging & Error Handling Improvement

**Date**: 2026-04-12
**Status**: Approved

## Problem

21 tools in `app/AutoUp-MCP-Extension/` have inconsistent logging and error handling:

1. **Zero logging**: `image_generate_jimeng` has no logging at all
2. **print() instead of loguru**: `Reddit_publish/Reddit.py` (~40 calls), `video_pipeline_auto/editor.py` (~15 calls), `video_pipeline_auto/font_utils.py` (mixed)
3. **Dual logging systems**: `Youtube_publish/youtube.py` uses stdlib `logging` while its wrapper uses loguru
4. **Errors as strings**: `image_generate_midjourney` returns error text instead of raising McpError
5. **Wrong exception types**: `sharing_utils/cookie_get.py` raises plain `Exception`
6. **No base class support**: `BaseMCPTool` provides no logging infrastructure; every tool independently imports loguru

## Scope

- **In scope**: `base_tool.py` logging infrastructure + all 21 extension tools
- **Out of scope**: Hardcoded credentials in `zhihu_data_fetch_tool.py` (separate task)

## Design

### 1. BaseMCPTool Enhancement

**File**: `app/base_tool.py`

Add a single field to `__init__`:

```python
from loguru import logger

class BaseMCPTool(ABC):
    def __init__(self):
        self.config_manager = ExtensionConfigManager()
        class_name = self.__class__.__name__
        self.logger = logger.bind(tool=class_name)
```

- All tools automatically get `self.logger` with tool context
- No wrapper methods, no abstract method changes, fully backward compatible
- Existing `from loguru import logger` calls in tools will still work; gradual migration to `self.logger`

### 2. Tool-Level Fixes (Batch 1: Critical)

#### image_generate_jimeng_tool.py
- Add `self.logger.info()` at `call_tool` entry with tool name and arguments
- Add `self.logger.info()` before/after Volcengine API call
- Add `self.logger.error()` in all exception paths
- Add loguru to `config.yaml` packages list

#### Reddit_publish/Reddit.py
- Replace all ~40 `print()` calls with `self.logger.info/debug/error`
- Pass logger from tool wrapper to Reddit.py, or use `logger.bind(tool="RedditPublish")` at module level
- Categorize existing prints: status messages → `info`, debug output → `debug`, errors → `error`

#### video_pipeline_auto/video_core/editor.py
- Replace all ~15 `print()` calls with loguru logger
- FFmpeg commands → `logger.debug`, duration/render status → `logger.info`, errors → `logger.error`

#### video_pipeline_auto/video_core/font_utils.py
- Remove remaining `print()` calls, use existing loguru import consistently

#### Youtube_publish/youtube.py
- Remove `import logging` and `logging.basicConfig()`
- Replace `logging.getLogger("YouTubeUploader")` with `logger.bind(tool="YouTubeUploader")`
- All `self.log.info/error/debug` → `logger.info/error/debug`

### 3. Tool-Level Fixes (Batch 2: Medium)

#### image_generate_midjourney_tool.py
- `_send_request` and `_download_images_sync`: stop returning error strings
- Raise `McpError` with appropriate error code and message instead
- `call_tool`: check for error returns and convert to McpError

#### sharing_utils/cookie_get.py
- Replace `raise Exception(...)` with `raise McpError(...)`

#### douyin_publish_photo_text, douyin_publish_video
- `from loguru import logger` → `self.logger` in tool wrapper files
- Inner modules (douyin_photoText_publish.py, douyin_video_publish.py): keep `from loguru import logger` as-is (these are internal, not subclassed)

#### kuaishou_publish_photo, kuaishou_publish_video
- Same pattern as douyin: `self.logger` in tool wrapper, keep inner module imports

#### workflow_hub_signal_tool.py
- Normalize `config.yaml`: `dependencies` → `packages`

### 4. Tool-Level Fixes (Batch 3: Standardization)

All remaining tools (text_polish, text_to_image, tts_clone_minimax, tts_edge, tts_minimax, video_generate, video_jianying, xiaohongshu_publish, X_publish, zhihu_data_fetch):

- Replace `from loguru import logger` with `self.logger` in tool wrapper classes
- Ensure `call_tool` entry has `self.logger.info(f"Calling tool: {name}")`
- Ensure all exception paths have `self.logger.error()`
- Add loguru to config.yaml packages if missing

## Implementation Order

1. `base_tool.py` — add `self.logger` (1 file)
2. Batch 1 critical fixes — 5 tools with severe issues
3. Batch 2 medium fixes — 7 tools with moderate issues
4. Batch 3 standardization — 9 tools, mechanical replacement

## Risks

- **Low risk**: base_tool.py change is additive only, no breaking changes
- **Medium risk**: print() → logger changes in Reddit.py and editor.py need careful review to not change control flow
- **Medium risk**: image_generate_midjourney error handling change alters API contract (error strings → exceptions), but this is an improvement

## Verification

- Each batch: start dev server (`uv run main.py`), invoke each modified tool, check:
  - Logs appear in console with tool name context
  - Error cases produce McpError (not strings or crashes)
  - WebSocket log viewer at `/api/logs` shows the new log entries
- `ruff check --fix .` and `ruff format .` pass
