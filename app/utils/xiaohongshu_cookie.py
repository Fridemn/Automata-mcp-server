import json
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright


def get_xiaohongshu_cookies() -> str:
    """获取小红书登录cookies

    Returns:
        JSON字符串格式的cookies
    """
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

        # 不加载已保存的cookies，每次都重新登录
        page = context.new_page()

        try:
            logger.info("正在访问小红书主页...")
            page.goto("https://www.xiaohongshu.com")
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


def save_xiaohongshu_cookies(cookies_json: str) -> bool:
    """保存小红书cookies到文件

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
        cookies_file = cookies_dir / "xiaohongshu.json"
        with open(cookies_file, "w", encoding="utf-8") as f:
            f.write(cookies_json)

        logger.info(f"小红书cookies已保存到 {cookies_file}")
        return True
    except Exception as e:
        logger.error(f"保存小红书cookies失败: {e}")
        return False


def load_xiaohongshu_cookies() -> str:
    """加载小红书cookies

    Returns:
        JSON格式的cookies字符串，如果文件不存在返回None
    """
    try:
        cookies_file = Path("data/cookies/xiaohongshu.json")
        if cookies_file.exists():
            with open(cookies_file, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning("小红书cookies文件不存在")
            return None
    except Exception as e:
        logger.error(f"加载小红书cookies失败: {e}")
        return None
