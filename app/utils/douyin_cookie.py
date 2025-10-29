import json
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


def get_douyin_cookies() -> str:
    """获取抖音登录cookies

    Returns:
        JSON字符串格式的cookies
    """
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

        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        # 添加反检测脚本
        page.add_init_script("""
            // 隐藏自动化特征
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // 修改插件信息
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                ],
            });

            // 修改语言设置
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });

            // 修改平台信息
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
            });

            // 修改硬件并发数
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
            });

            // 修改设备内存
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
            });

            // 隐藏cdc_*属性
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;

            // 修改Canvas指纹
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(x, y, width, height) {
                const imageData = originalGetImageData.call(this, x, y, width, height);
                // 轻微修改像素数据来改变指纹
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = (imageData.data[i] + 1) % 256;
                }
                return imageData;
            };

            // 修改WebGL指纹
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

            // 修改权限API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = function(parameters) {
                return Promise.resolve({ state: 'granted' });
            };

            // 修改时区
            Object.defineProperty(Intl, 'DateTimeFormat', {
                value: class extends Intl.DateTimeFormat {
                    resolvedOptions() {
                        const options = super.resolvedOptions();
                        options.timeZone = 'Asia/Shanghai';
                        return options;
                    }
                }
            });

            // 修改屏幕信息
            Object.defineProperty(screen, 'width', { get: () => 1920 });
            Object.defineProperty(screen, 'height', { get: () => 1080 });
            Object.defineProperty(screen, 'availWidth', { get: () => 1920 });
            Object.defineProperty(screen, 'availHeight', { get: () => 1040 });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
            Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
        """)

        try:
            logger.info("正在访问抖音主页...")
            page.goto("https://www.douyin.com")
            page.wait_for_load_state("domcontentloaded")
            import time

            time.sleep(2)

            login_required = False
            if "login" in page.url.lower() or "登录" in page.title():
                login_required = True
            else:
                try:
                    login_indicators = [
                        "text=登录",
                        "text=login",
                        '[data-testid="login-button"]',
                        ".login-btn",
                    ]
                    for indicator in login_indicators:
                        if page.locator(indicator).count() > 0:
                            login_required = True
                            break
                except Exception:
                    pass

            if login_required:
                logger.info("检测到需要登录页面，请在浏览器中手动登录...")
                logger.info("脚本将每5秒自动检查登录状态，无需手动确认")

                while True:
                    time.sleep(5)

                    current_url = page.url.lower()
                    current_title = page.title().lower()

                    logged_in = True

                    if "login" in current_url or "登录" in current_title:
                        logged_in = False
                    else:
                        try:
                            for indicator in login_indicators:
                                if page.locator(indicator).count() > 0:
                                    if page.locator(indicator).first.is_visible():
                                        logged_in = False
                                        break
                        except Exception:
                            pass

                    if logged_in:
                        logger.info("检测到已登录")
                        cookies = context.cookies()
                        return json.dumps(cookies, ensure_ascii=False, indent=2)
                    else:
                        logger.info("等待登录中... (每5秒检查一次)")
            else:
                logger.info("使用已保存的登录状态")
                cookies = context.cookies()
                return json.dumps(cookies, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            return None
        finally:
            browser.close()


def save_douyin_cookies(cookies_json: str) -> bool:
    """保存抖音cookies到文件

    Args:
        cookies_json: JSON格式的cookies字符串

    Returns:
        保存是否成功
    """
    try:
        # 确保data/cookies目录存在
        cookies_dir = Path("data/cookies")
        cookies_dir.mkdir(parents=True, exist_ok=True)

        # 保存到文件
        cookies_file = cookies_dir / "douyin.json"
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write(cookies_json)

        logger.info(f"抖音cookies已保存到 {cookies_file}")
        return True
    except Exception as e:
        logger.error(f"保存抖音cookies失败: {e}")
        return False


def load_douyin_cookies() -> str:
    """加载抖音cookies

    Returns:
        JSON格式的cookies字符串，如果文件不存在返回None
    """
    try:
        cookies_file = Path("data/cookies/douyin.json")
        if cookies_file.exists():
            with open(cookies_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning("抖音cookies文件不存在")
            return None
    except Exception as e:
        logger.error(f"加载抖音cookies失败: {e}")
        return None
