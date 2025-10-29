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
from app.utils.xiaohongshu_cookie import (
    get_xiaohongshu_cookies,
    load_xiaohongshu_cookies,
    save_xiaohongshu_cookies,
)


class GetXiaohongshuCookiesParams(BaseModel):
    pass


class LoadXiaohongshuCookiesParams(BaseModel):
    pass


class ValidateXiaohongshuCookiesParams(BaseModel):
    pass


class XiaohongshuCookieTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/cookies/xiaohongshu/get",
                "params_class": GetXiaohongshuCookiesParams,
                "tool_name": "get_xiaohongshu_cookies",
            },
            {
                "endpoint": "/cookies/xiaohongshu/load",
                "params_class": LoadXiaohongshuCookiesParams,
                "tool_name": "load_xiaohongshu_cookies",
            },
            {
                "endpoint": "/cookies/xiaohongshu/validate",
                "params_class": ValidateXiaohongshuCookiesParams,
                "tool_name": "validate_xiaohongshu_cookies",
            },
        ]

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="get_xiaohongshu_cookies",
                description="Get Xiaohongshu login cookies using Playwright",
                inputSchema=GetXiaohongshuCookiesParams.model_json_schema(),
            ),
            Tool(
                name="load_xiaohongshu_cookies",
                description="Load saved Xiaohongshu cookies",
                inputSchema=LoadXiaohongshuCookiesParams.model_json_schema(),
            ),
            Tool(
                name="validate_xiaohongshu_cookies",
                description="Validate if saved Xiaohongshu cookies are valid",
                inputSchema=ValidateXiaohongshuCookiesParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name == "get_xiaohongshu_cookies":
            return await self._get_xiaohongshu_cookies()
        elif name == "load_xiaohongshu_cookies":
            return await self._load_xiaohongshu_cookies()
        elif name == "validate_xiaohongshu_cookies":
            return await self._validate_xiaohongshu_cookies()
        else:
            raise ValueError(f"Unknown tool name: {name}")

    async def _get_xiaohongshu_cookies(self) -> Sequence[TextContent]:
        try:
            from concurrent.futures import ThreadPoolExecutor

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                cookies_json = await loop.run_in_executor(
                    executor, get_xiaohongshu_cookies
                )

            if cookies_json:
                save_success = save_xiaohongshu_cookies(cookies_json)
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

    async def _load_xiaohongshu_cookies(self) -> Sequence[TextContent]:
        cookies_json = load_xiaohongshu_cookies()
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

    async def _validate_xiaohongshu_cookies(self) -> Sequence[TextContent]:
        try:
            cookies_json = load_xiaohongshu_cookies()
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
