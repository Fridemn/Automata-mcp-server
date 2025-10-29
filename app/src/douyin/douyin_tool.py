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
from playwright_stealth import Stealth
from pydantic import BaseModel, Field

from app.base_tool import BaseMCPTool


class DouyinParams(BaseModel):
    cookies: str = Field(description="Douyin login cookies as JSON string")
    title: str = Field(description="Title of the post")
    content: str = Field(description="Content of the post")
    images: List[str] = Field(description="List of base64 encoded images")
    tags: List[str] = Field(description="List of tags for the post")


class DouyinTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/tools/douyin",
                "params_class": DouyinParams,
            }
        ]

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="douyin_publish",
                description="Publish content to Douyin (抖音). Requires login cookies, title, content, images, and tags.",
                inputSchema=DouyinParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "douyin_publish":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = DouyinParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        if not args.cookies.strip():
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Cookies are required")
            )

        if not args.title.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Title is required"))

        if not args.content.strip():
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Content is required")
            )

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
                self._publish_douyin,
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
                    message=f"Failed to publish to Douyin: {str(e)}",
                )
            )

        return [TextContent(type="text", text=result)]

    def _publish_douyin(
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
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-ipc-flooding-protection",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-field-trial-config",
                    "--disable-back-forward-cache",
                    "--disable-hang-monitor",
                    "--disable-ipc-flooding-protection",
                    "--disable-popup-blocking",
                    "--disable-prompt-on-repost",
                    "--force-color-profile=srgb",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--enable-automation=false",
                    "--password-store=basic",
                    "--use-mock-keychain",
                    "--no-service-autorun",
                    "--export-tagged-pdf=false",
                    "--no-default-browser-check",
                    "--disable-component-update",
                    "--disable-domain-reliability",
                    "--disable-client-side-phishing-detection",
                    "--disable-background-networking",
                    "--no-pings",
                    "--disable-sync",
                    "--disable-translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-crash-upload",
                    "--disable-logging",
                    "--disable-login-animations",
                    "--disable-notifications",
                    "--disable-permissions-api",
                    "--disable-session-crashed-bubble",
                    "--disable-infobars",
                    "--disable-webgl",
                    "--disable-3d-apis",
                    "--disable-accelerated-video-decode",
                    "--disable-accelerated-video-encode",
                    "--disable-gpu-compositing",
                    "--disable-gpu-rasterization",
                    "--disable-gpu-sandbox",
                    "--disable-software-rasterizer",
                    "--disable-background-media-download",
                    "--disable-print-preview",
                    "--disable-component-extensions-with-background-pages",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript-harmony-shipping",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-accessibility",
                    "--disable-web-security",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.76 Safari/537.36",
                ],
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.76 Safari/537.36"
            )

            # Load cookies
            try:
                cookies = json.loads(cookies_json)
                context.add_cookies(cookies)
            except Exception as e:
                logger.error(f"Failed to load cookies: {e}")
                return "Failed: Invalid cookies format"

            page = context.new_page()
            Stealth().apply_stealth_sync(page)

            # Add anti-detection scripts
            page.add_init_script("""
                // Hide automation features
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // Modify plugin information
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                    ],
                });

                // Modify language settings
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en'],
                });

                // Modify platform information
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32',
                });

                // Modify hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8,
                });

                // Modify device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8,
                });

                // Hide cdc_* properties
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;

                // Modify Canvas fingerprint
                const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
                CanvasRenderingContext2D.prototype.getImageData = function(x, y, width, height) {
                    const imageData = originalGetImageData.call(this, x, y, width, height);
                    // Slightly modify pixel data to change fingerprint
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = (imageData.data[i] + 1) % 256;
                    }
                    return imageData;
                };

                // Modify WebGL fingerprint
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
                        return 'Intel(R) Iris(TM) Graphics 6100';
                    }
                    return getParameter.call(this, parameter);
                };

                // Modify permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = function(parameters) {
                    return Promise.resolve({ state: 'granted' });
                };

                // Modify timezone
                Object.defineProperty(Intl, 'DateTimeFormat', {
                    value: class extends Intl.DateTimeFormat {
                        resolvedOptions() {
                            const options = super.resolvedOptions();
                            options.timeZone = 'Asia/Shanghai';
                            return options;
                        }
                    }
                });

                // Modify screen information
                Object.defineProperty(screen, 'width', { get: () => 1920 });
                Object.defineProperty(screen, 'height', { get: () => 1080 });
                Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
                Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
                Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
                Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
            """)

            try:
                logger.info("Accessing Douyin creator center...")
                # Douyin's publish page URL
                page.goto("https://creator.douyin.com/creator-micro/content/upload")
                page.wait_for_load_state("domcontentloaded")

                page.wait_for_load_state("networkidle", timeout=30000)

                if "upload" not in page.url:
                    return "Failed: Could not access upload page"

                # Select "发布图文" tab
                logger.info("Selecting image-text publish tab...")
                try:
                    # Wait for page to load completely
                    page.wait_for_load_state("networkidle", timeout=10000)

                    # Check available tabs
                    all_tabs = page.locator(".tab-item-BcCLTS")
                    tab_count = all_tabs.count()
                    logger.info(f"Found {tab_count} tabs")

                    for i in range(tab_count):
                        tab_text = all_tabs.nth(i).text_content().strip()
                        is_active = all_tabs.nth(i).evaluate(
                            "element => element.classList.contains('active-i8Pu0m')"
                        )
                        logger.info(
                            f"Tab {i}: '{tab_text}' {'(active)' if is_active else ''}"
                        )

                    # Find tab containing "发布图文"
                    image_tab = page.locator('.tab-item-BcCLTS:has-text("发布图文")')
                    if image_tab.count() > 0:
                        # Check if already active
                        if not image_tab.first.evaluate(
                            "element => element.classList.contains('active-i8Pu0m')"
                        ):
                            logger.info("Clicking image-text publish tab")
                            image_tab.first.click()
                            page.wait_for_timeout(
                                3000
                            )  # Wait for page switch, allow more time
                            logger.info("Clicked image-text publish tab")
                        else:
                            logger.info("Image-text publish tab already active")
                    else:
                        logger.info(
                            "Image-text publish tab not found, trying alternative names"
                        )
                        # Try other possible names
                        alt_names = ["图文", "图片", "相册"]
                        for name in alt_names:
                            alt_tab = page.locator(
                                f'.tab-item-BcCLTS:has-text("{name}")'
                            )
                            if alt_tab.count() > 0:
                                logger.info(f"Found alternative tab: {name}")
                                if not alt_tab.first.evaluate(
                                    "element => element.classList.contains('active-i8Pu0m')"
                                ):
                                    alt_tab.first.click()
                                    page.wait_for_timeout(3000)
                                break
                except Exception as e:
                    logger.info(f"Error selecting image-text publish tab: {e}")
                    # Continue if error occurs, might already be on correct tab

                # Save images to temporary files
                temp_files = []
                for i, img_bytes in enumerate(images):
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f"_img_{i}.jpg"
                    ) as temp_file:
                        temp_file.write(img_bytes)
                        temp_files.append(temp_file.name)

                # Locate upload input element or upload button
                logger.info("Looking for upload element...")

                # Check page elements
                try:
                    input_count = page.locator('input[type="file"]').count()
                    button_count = page.locator(".container-drag-btn-k6XmB4").count()
                    area_count = page.locator(".container-drag-info-efu4jl").count()

                    logger.info(
                        f"Page elements: input[type='file']={input_count}, upload buttons={button_count}, upload areas={area_count}"
                    )

                    # Print upload button text
                    for i in range(button_count):
                        btn_text = (
                            page.locator(".container-drag-btn-k6XmB4")
                            .nth(i)
                            .text_content()
                            .strip()
                        )
                        logger.info(f"Upload button {i}: '{btn_text}'")

                except Exception as e:
                    logger.info(f"Error checking page elements: {e}")

                upload_success = False

                # Method 1: Directly find input[type="file"] element
                try:
                    upload_input = page.locator('input[type="file"]')
                    if upload_input.count() > 0:
                        upload_input.first.wait_for(state="visible", timeout=5000)
                        logger.info("Found upload input element")
                        upload_input.first.set_input_files(temp_files)
                        upload_success = True
                    else:
                        logger.info("input[type='file'] element not found")
                except Exception as e:
                    logger.info(f"Direct upload failed: {e}")

                # Method 2: Find input element within upload area
                if not upload_success:
                    try:
                        # Find input within .container-drag-info-efu4jl area
                        upload_area = page.locator(".container-drag-info-efu4jl")
                        if upload_area.count() > 0:
                            upload_input = upload_area.locator('input[type="file"]')
                            if upload_input.count() > 0:
                                upload_input.first.wait_for(
                                    state="visible", timeout=5000
                                )
                                logger.info("Found input element within upload area")
                                upload_input.first.set_input_files(temp_files)
                                upload_success = True
                            else:
                                logger.info(
                                    "Input element not found within upload area"
                                )
                        else:
                            logger.info(
                                ".container-drag-info-efu4jl upload area not found"
                            )
                    except Exception as e:
                        logger.info(f"Upload area search failed: {e}")

                # Method 3: Click "上传图文" button
                if not upload_success:
                    try:
                        upload_button = page.locator(
                            '.container-drag-btn-k6XmB4:has-text("上传图文")'
                        )
                        if upload_button.count() > 0:
                            logger.info(
                                "Found upload image-text button, clicking to upload"
                            )
                            upload_button.first.click()
                            page.wait_for_timeout(
                                2000
                            )  # Wait for file selection dialog

                            # Wait for and find newly appeared input element
                            try:
                                new_upload_input = page.locator(
                                    'input[type="file"]'
                                ).last
                                new_upload_input.wait_for(state="visible", timeout=5000)
                                logger.info(
                                    "Found new input element after button click"
                                )
                                new_upload_input.set_input_files(temp_files)
                                upload_success = True
                            except Exception:
                                logger.info(
                                    "New input element not found after button click"
                                )
                        else:
                            logger.info("Upload image-text button not found")
                    except Exception as e:
                        logger.info(f"Button click upload failed: {e}")

                # Method 4: Trigger file selection via JavaScript
                if not upload_success:
                    try:
                        # Try to find and trigger input element via JavaScript
                        result = page.evaluate("""
                            const inputs = document.querySelectorAll('input[type="file"]');
                            if (inputs.length > 0) {
                                inputs[0].click();
                                return true;
                            }
                            return false;
                        """)
                        if result:
                            logger.info("Triggered file selection via JavaScript")
                            page.wait_for_timeout(2000)
                            # Try setting files again
                            upload_input = page.locator('input[type="file"]').first
                            upload_input.set_input_files(temp_files)
                            upload_success = True
                        else:
                            logger.info("JavaScript found no input elements")
                    except Exception as e:
                        logger.info(f"JavaScript trigger failed: {e}")

                if not upload_success:
                    logger.info("All upload methods failed")
                    return "Failed: All upload methods failed"

                # Wait for upload to complete
                logger.info("Waiting for upload to complete...")
                page.wait_for_timeout(5000)

                # Wait for page transition to edit page
                logger.info("Waiting for page transition to edit page...")
                try:
                    page.wait_for_url(
                        lambda url: "edit" in url or "publish" in url, timeout=15000
                    )
                    logger.info("Detected page transition to edit page")
                except Exception:
                    logger.info("Page transition not detected, continuing...")
                    page.wait_for_timeout(5000)

                page.wait_for_load_state("networkidle", timeout=10000)
                import time

                time.sleep(2)

                # Fill title
                logger.info("Filling title...")
                try:
                    title_selectors = [
                        'input[placeholder*="标题"]',
                        'input[placeholder*="title"]',
                        ".input-box input",
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
                        logger.info("Title input not found")

                except Exception as e:
                    logger.info(f"Error filling title: {e}")

                # Fill content
                logger.info("Filling content...")
                try:
                    # Wait for editor to load completely
                    page.wait_for_timeout(3000)

                    # Find content editor
                    content_selectors = [
                        '[contenteditable="true"]',
                        ".editor-content",
                        ".content-input",
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

                        # Clear editor and focus
                        content_area.clear()
                        content_area.focus()
                        page.wait_for_timeout(500)

                        # Simulate typing input
                        content_area.press_sequentially(full_content, delay=100)
                        logger.info(f"Content typed: {full_content}")
                    else:
                        logger.info("Content editor not found")

                except Exception as e:
                    logger.info(f"Error filling content: {e}")

                # Click publish button
                logger.info("Clicking publish button...")
                try:
                    publish_selectors = [
                        'button:has-text("发布")',
                        'button:has-text("发表")',
                        'button[type="submit"]',
                        '[data-testid="publish-button"]',
                        ".publish-btn",
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
                        time.sleep(1)
                        publish_button.click()
                        logger.info("Publish button clicked")
                        return "Success: Content published to Douyin"
                    else:
                        logger.info("Publish button not found")
                        return "Failed: Publish button not found"

                except Exception as e:
                    logger.info(f"Error clicking publish button: {e}")
                    return f"Failed: Error clicking publish button - {str(e)}"

            except Exception as e:
                logger.info(f"Error during publishing: {e}")
                return f"Failed: Publishing error - {str(e)}"
            finally:
                # Clean up temporary files
                for temp_file in temp_files:
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                browser.close()
