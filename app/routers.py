from fastapi import APIRouter, Depends, Header, HTTPException
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.utils.douyin_cookie import (
    get_douyin_cookies,
    save_douyin_cookies,
    load_douyin_cookies,
)
from app.utils.xiaohongshu_cookie import (
    get_xiaohongshu_cookies,
    save_xiaohongshu_cookies,
    load_xiaohongshu_cookies,
)


def create_router(authenticate_func, tools_count_func):
    router = APIRouter()

    def verify_api_key(api_key: str | None = Header(None, alias="X-API-Key")):
        """Dependency to verify API key."""
        if not authenticate_func(api_key or ""):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return api_key

    @router.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Automata MCP Server is running",
            "version": "1.0.0",
            "tools_count": tools_count_func(),
        }

    @router.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    @router.get("/tools")
    async def list_registered_tools(_api_key: str = Depends(verify_api_key)):
        """List all registered tools (for debugging)."""
        tools_info = []
        # For now, manually list - this should be dynamic based on registered tools
        tools_info.append(
            {
                "name": "fetch",
                "description": "Fetches a URL from the internet",
            },
        )
        tools_info.append(
            {
                "name": "polish",
                "description": "Polishes text based on a prompt",
            },
        )
        tools_info.append(
            {
                "name": "douyin_publish",
                "description": "Publish content to Douyin (抖音)",
            },
        )
        tools_info.append(
            {
                "name": "xiaohongshu_publish",
                "description": "Publish content to Xiaohongshu (小红书)",
            },
        )
        tools_info.append(
            {
                "name": "create_long_text_content",
                "description": "Generate long text content images for novels etc.",
            },
        )
        return {"tools": tools_info}

    @router.post("/cookies/douyin/get")
    async def get_douyin_login_cookies(_api_key: str = Depends(verify_api_key)):
        """获取抖音登录cookies"""
        try:
            # 在线程池中运行同步的Playwright代码
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                cookies_json = await loop.run_in_executor(executor, get_douyin_cookies)

            if cookies_json:
                # 保存cookies
                save_success = save_douyin_cookies(cookies_json)
                return {"success": True, "cookies": cookies_json, "saved": save_success}
            else:
                return {"success": False, "error": "Failed to get cookies"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @router.post("/cookies/xiaohongshu/get")
    async def get_xiaohongshu_login_cookies(_api_key: str = Depends(verify_api_key)):
        """获取小红书登录cookies"""
        try:
            # 在线程池中运行同步的Playwright代码
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                cookies_json = await loop.run_in_executor(
                    executor, get_xiaohongshu_cookies
                )

            if cookies_json:
                # 保存cookies
                save_success = save_xiaohongshu_cookies(cookies_json)
                return {"success": True, "cookies": cookies_json, "saved": save_success}
            else:
                return {"success": False, "error": "Failed to get cookies"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @router.get("/cookies/douyin/load")
    async def load_douyin_saved_cookies(_api_key: str = Depends(verify_api_key)):
        """加载已保存的抖音cookies"""
        cookies_json = load_douyin_cookies()
        if cookies_json:
            return {"success": True, "cookies": cookies_json}
        else:
            return {"success": False, "error": "No saved cookies found"}

    @router.get("/cookies/xiaohongshu/load")
    async def load_xiaohongshu_saved_cookies(_api_key: str = Depends(verify_api_key)):
        """加载已保存的小红书cookies"""
        cookies_json = load_xiaohongshu_cookies()
        if cookies_json:
            return {"success": True, "cookies": cookies_json}
        else:
            return {"success": False, "error": "No saved cookies found"}

    return router
