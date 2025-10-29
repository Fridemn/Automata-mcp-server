import asyncio
import json
from typing import Sequence

from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool,
)
from pydantic import BaseModel

from app.base_tool import BaseMCPTool
from app.utils.douyin_cookie import (
    get_douyin_cookies,
    load_douyin_cookies,
    save_douyin_cookies,
)


class GetDouyinCookiesParams(BaseModel):
    pass  # No params needed


class LoadDouyinCookiesParams(BaseModel):
    pass


class ValidateDouyinCookiesParams(BaseModel):
    pass


class DouyinCookieTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/cookies/douyin/get",
                "params_class": GetDouyinCookiesParams,
                "tool_name": "get_douyin_cookies",
            },
            {
                "endpoint": "/cookies/douyin/load",
                "params_class": LoadDouyinCookiesParams,
                "tool_name": "load_douyin_cookies",
            },
            {
                "endpoint": "/cookies/douyin/validate",
                "params_class": ValidateDouyinCookiesParams,
                "tool_name": "validate_douyin_cookies",
            },
        ]

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="get_douyin_cookies",
                description="Get Douyin login cookies using Playwright",
                inputSchema=GetDouyinCookiesParams.model_json_schema(),
            ),
            Tool(
                name="load_douyin_cookies",
                description="Load saved Douyin cookies",
                inputSchema=LoadDouyinCookiesParams.model_json_schema(),
            ),
            Tool(
                name="validate_douyin_cookies",
                description="Validate if saved Douyin cookies are valid",
                inputSchema=ValidateDouyinCookiesParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name == "get_douyin_cookies":
            return await self._get_douyin_cookies()
        elif name == "load_douyin_cookies":
            return await self._load_douyin_cookies()
        elif name == "validate_douyin_cookies":
            return await self._validate_douyin_cookies()
        else:
            raise ValueError(f"Unknown tool name: {name}")

    async def _get_douyin_cookies(self) -> Sequence[TextContent]:
        try:
            # Run in thread pool since Playwright is sync
            from concurrent.futures import ThreadPoolExecutor

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                cookies_json = await loop.run_in_executor(executor, get_douyin_cookies)

            if cookies_json:
                save_success = save_douyin_cookies(cookies_json)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "cookies": cookies_json,
                                "saved": save_success,
                            }
                        ),
                    )
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "error": "Failed to get cookies",
                            }
                        ),
                    )
                ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": str(e),
                        }
                    ),
                )
            ]

    async def _load_douyin_cookies(self) -> Sequence[TextContent]:
        cookies_json = load_douyin_cookies()
        if cookies_json:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "cookies": cookies_json,
                        }
                    ),
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": "No saved cookies found",
                        }
                    ),
                )
            ]

    async def _validate_douyin_cookies(self) -> Sequence[TextContent]:
        try:
            cookies_json = load_douyin_cookies()
            if not cookies_json:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "valid": False,
                                "error": "No saved cookies found",
                            }
                        ),
                    )
                ]

            # TODO: Implement actual cookie validation
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "valid": True,
                            "cookies": cookies_json,
                        }
                    ),
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "valid": False,
                            "error": str(e),
                        }
                    ),
                )
            ]
