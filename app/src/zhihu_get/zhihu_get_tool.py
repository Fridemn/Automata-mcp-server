from typing import Sequence

from mcp.shared.exceptions import McpError
from mcp.types import (
    INVALID_PARAMS,
    ErrorData,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from app.base_tool import BaseMCPTool

# Harry 待完成


class ZhihuGetParams(BaseModel):
    url: str = Field(description="The Zhihu URL to get content from")


class Zhihu_getTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> dict:
        return {
            "endpoint": "/tools/zhihu_get",
            "params_class": ZhihuGetParams,
        }

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="zhihu_get",
                description="Get content from a Zhihu URL. Returns the title, author, and main content.",
                inputSchema=ZhihuGetParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent]:
        if name != "zhihu_get":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = ZhihuGetParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        if not args.url.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))

        # Simulate getting content from Zhihu
        # In a real implementation, this would fetch the URL and parse the content
        simulated_content = self._simulate_get_content(args.url)

        return [TextContent(type="text", text=simulated_content)]

    def _simulate_get_content(self, url: str) -> str:
        """Simulate getting content from Zhihu URL"""
        # Mock response based on URL
        if "zhihu.com" not in url:
            return "Error: Invalid Zhihu URL"

        # Simulate different content based on URL pattern
        if "question" in url:
            return """Title: 如何学习编程？
Author: 知乎用户
Content: 学习编程需要坚持和实践。首先选择一门语言如Python，然后通过项目练习。推荐资源包括官方文档、在线课程如Coursera，以及社区如Stack Overflow。"""
        elif "answer" in url:
            return """Title: 回答：编程入门建议
Author: 编程专家
Content: 入门编程建议：1. 选择合适的语言；2. 学习基础语法；3. 做小项目；4. 参与开源；5. 持续学习新技术。"""
        else:
            return """Title: 知乎文章标题
Author: 作者名
Content: 这是从知乎获取的模拟内容。实际实现中会解析网页并提取标题、作者和正文内容。"""
