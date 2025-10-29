import asyncio
import base64
import json
import os
import tempfile
from typing import List, Sequence

from loguru import logger
from mcp.shared.exceptions import McpError
from mcp.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    EmbeddedResource,
    ErrorData,
    ImageContent,
    TextContent,
    Tool,
)
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field

from app.base_tool import BaseMCPTool


class XiaohongshuParams(BaseModel):
    cookies: str = Field(description="Xiaohongshu login cookies as JSON string")
    title: str = Field(description="Title of the post")
    content: str = Field(default="", description="Content of the post (optional)")
    images: List[str] = Field(description="List of base64 encoded images")
    tags: List[str] = Field(description="List of tags for the post")


class XiaohongshuTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/tools/xiaohongshu",
                "params_class": XiaohongshuParams,
                "tool_name": "xiaohongshu_publish",
            }
        ]

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="xiaohongshu_publish",
                description="Publish content to Xiaohongshu (小红书). Requires login cookies, title, content, images, and tags.",
                inputSchema=XiaohongshuParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "xiaohongshu_publish":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = XiaohongshuParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        if not args.cookies.strip():
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Cookies are required")
            )

        if not args.title.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Title is required"))

        # Content is optional, can be empty
        # if not args.content.strip():
        #     raise McpError(
        #         ErrorData(code=INVALID_PARAMS, message="Content is required")
        #     )

        if not args.images:
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="At least one image is required")
            )

        # Convert base64 images to bytes
        try:
            image_bytes = []
            for img_b64 in args.images:
                # Remove data URL prefix if present
                if img_b64.startswith("data:"):
                    img_b64 = img_b64.split(",", 1)[1]
                image_bytes.append(base64.b64decode(img_b64))
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INVALID_PARAMS, message=f"Failed to decode images: {str(e)}"
                )
            )

        # Run the publish operation in a thread pool since it uses synchronous Playwright
        try:
            result = await asyncio.to_thread(
                self._publish_xiaohongshu,
                args.cookies,
                args.title,
                args.content,
                image_bytes,
                args.tags,
            )
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to publish to Xiaohongshu: {str(e)}",
                )
            )

        return [TextContent(type="text", text=result)]

    def _publish_xiaohongshu(
        self,
        cookies_json: str,
        title: str,
        content: str,
        images: List[bytes],
        tags: List[str],
    ) -> str:
        """Internal synchronous publish function"""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Load cookies
            try:
                cookies = json.loads(cookies_json)
                context.add_cookies(cookies)
            except Exception as e:
                logger.error(f"Failed to load cookies: {e}")
                return "Failed: Invalid cookies format"

            page = context.new_page()

            try:
                logger.info("Accessing Xiaohongshu creator platform...")
                page.goto(
                    "https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image"
                )
                page.wait_for_load_state("domcontentloaded")

                page.wait_for_load_state("networkidle", timeout=30000)

                if "publish" not in page.url:
                    return "Failed: Could not access publish page"

                # Save images to temporary files
                temp_files = []
                for i, img_bytes in enumerate(images):
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f"_img_{i}.jpg"
                    ) as temp_file:
                        temp_file.write(img_bytes)
                        temp_files.append(temp_file.name)

                # Find upload input element
                logger.info("Looking for upload element...")
                upload_input = page.locator('input.upload-input[type="file"]')

                try:
                    upload_input.wait_for(state="visible", timeout=10000)
                    logger.info("Found upload element")
                except Exception:
                    logger.warning(
                        "Upload input not found, trying alternative selector..."
                    )
                    upload_input = page.locator('input[type="file"]').first
                    upload_input.wait_for(state="visible", timeout=10000)

                # Upload image files
                logger.info(f"Uploading {len(temp_files)} images")
                upload_input.set_input_files(temp_files)

                # Wait for upload to complete
                logger.info("Waiting for upload to complete...")
                page.wait_for_timeout(5000)

                # Wait for page transition to edit page
                logger.info("Waiting for page transition to edit page...")
                try:
                    page.wait_for_url(
                        lambda url: "publish" not in url or "edit" in url, timeout=10000
                    )
                    logger.info("Detected page transition to edit page")
                except Exception:
                    logger.warning("Page transition not detected, continuing...")

                page.wait_for_load_state("networkidle", timeout=10000)
                import time

                time.sleep(2)

                # Fill title
                logger.info("Filling title...")
                try:
                    title_selectors = [
                        'input[placeholder*="标题"]',
                        'input[placeholder*="title"]',
                        ".r-input-box input",
                        'input[type="text"]',
                        '[contenteditable="true"]',
                    ]

                    title_input = None
                    for selector in title_selectors:
                        try:
                            title_input = page.locator(selector).first
                            if title_input.is_visible():
                                logger.info(f"Found title input: {selector}")
                                break
                        except Exception:
                            continue

                    if title_input:
                        title_input.fill(title)
                        logger.info(f"Title filled: {title}")
                    else:
                        logger.warning("Title input not found")

                except Exception as e:
                    logger.error(f"Error filling title: {e}")

                # Fill content
                logger.info("Filling content...")
                try:
                    # Wait for editor to load completely
                    page.wait_for_timeout(3000)

                    # Specifically look for TipTap editor
                    content_selectors = [
                        '.tiptap.ProseMirror[contenteditable="true"]',
                        '.ProseMirror[contenteditable="true"]',
                        '[contenteditable="true"].tiptap',
                        '[contenteditable="true"]',
                    ]

                    content_area = None
                    for selector in content_selectors:
                        try:
                            content_area = page.locator(selector).first
                            if content_area.is_visible():
                                logger.info(f"Found content editor: {selector}")
                                break
                        except Exception:
                            continue

                    if content_area:
                        # Add tags to content
                        full_content = (
                            content + " " + " ".join(f"#{tag}" for tag in tags)
                        )

                        # Escape quotes in content for safe JavaScript embedding
                        escaped_content = full_content.replace("'", r"\'").replace(
                            '"', r"\""
                        )

                        # Use JavaScript to set content directly, more reliable for contenteditable
                        js_code = f"""
                        (() => {{
                            const editor = document.querySelector('{selector}');
                            if (editor) {{
                                editor.innerHTML = '<p>{escaped_content}</p>';
                                editor.focus();
                                // Trigger input event to ensure editor detects content change
                                const event = new Event('input', {{ bubbles: true }});
                                editor.dispatchEvent(event);
                                return true;
                            }}
                            return false;
                        }})()
                        """

                        result = page.evaluate(js_code)
                        if result:
                            logger.info(f"Content filled: {full_content}")
                        else:
                            logger.warning("JavaScript content setting failed")
                    else:
                        logger.warning("Content editor not found")

                except Exception as e:
                    logger.error(f"Error filling content: {e}")

                # Click publish button
                logger.info("Clicking publish button...")
                try:
                    publish_selectors = [
                        ".publishBtn",
                        'button:has-text("发布")',
                        'button:has-text("发表")',
                        'button[type="submit"]',
                        '[data-testid="publish-button"]',
                    ]

                    publish_button = None
                    for selector in publish_selectors:
                        try:
                            publish_button = page.locator(selector).first
                            if publish_button.is_visible():
                                logger.info(f"Found publish button: {selector}")
                                break
                        except Exception:
                            continue

                    if publish_button:
                        import time

                        time.sleep(1)
                        publish_button.click()
                        logger.info("Publish button clicked")
                        return "Success: Content published to Xiaohongshu"
                    else:
                        logger.warning("Publish button not found")
                        return "Failed: Publish button not found"

                except Exception as e:
                    logger.error(f"Error clicking publish button: {e}")
                    return f"Failed: Error clicking publish button - {str(e)}"

            except Exception as e:
                logger.error(f"Error during publishing: {e}")
                return f"Failed: Publishing error - {str(e)}"
            finally:
                # Clean up temporary files
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                browser.close()
