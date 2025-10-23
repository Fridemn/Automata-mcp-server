import re
from typing import Sequence

import httpx
from mcp.shared.exceptions import McpError
from mcp.types import (
    INVALID_PARAMS,
    ErrorData,
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

from app.base_tool import BaseMCPTool


class ZhihuGetParams(BaseModel):
    url: str = Field(description="The Zhihu URL to get content from")


class Zhihu_getTool(BaseMCPTool):
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0",
    }

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

        # Extract column ID from URL using regex
        column_id = self._extract_column_id(args.url)
        if not column_id:
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Invalid Zhihu paid column URL")
            )

        # Fetch and parse content from the API URL
        content = await self._fetch_and_parse_content(column_id)

        return [TextContent(type="text", text=content)]

    def _extract_column_id(self, url: str) -> str | None:
        """Extract column ID from Zhihu URL using regex pattern"""
        pattern = r".+/section/(\d+).*"
        match = re.match(pattern, url)
        if match:
            return match.group(1)
        return None

    async def _fetch_and_parse_content(self, column_id: str) -> str:
        """Fetch HTML from Zhihu story API and extract content from index-module-root div"""
        fetch_url = f"https://story.zhihu.com/blogger/next-manuscript/paid_column/{column_id}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(fetch_url, headers=self._HEADERS, timeout=30.0)
                response.raise_for_status()

            html_content = response.text

            # Parse HTML and extract content from div with class starting with "index-module-root"
            content = self._extract_root_div_text(html_content)

            if not content.strip():
                return "Error: Could not extract content from the page. The div with class 'index-module-root' was not found or is empty."

            return content

        except httpx.HTTPError as e:
            return f"Error: Failed to fetch content from Zhihu. {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _extract_root_div_text(self, html: str) -> str:
        """Extract all text from the first div element with class starting with 'index-module-root'"""
        import re as regex_module

        # Use regex to find the first div with class starting with "index-module-root"
        # Pattern: <div class="index-module-root..." or <div class='index-module-root...'
        print(html)
        div_pattern = r'<div[^>]*class=["\']index-module-root[^"\']*["\'][^>]*>'

        match = regex_module.search(div_pattern, html)
        if not match:
            return ""

        # Find the starting position of the div
        div_start = match.start()

        # Find the matching closing </div> tag
        # Count opening and closing div tags to find the correct closing tag
        div_end = self._find_closing_div_tag(html, div_start)

        if div_end == -1:
            return ""

        # Extract the div content and remove HTML tags to get text
        div_html = html[div_start:div_end]
        text_content = self._strip_html_tags(div_html)

        return text_content.strip()

    def _find_closing_div_tag(self, html: str, start_pos: int) -> int:
        """Find the position of the closing </div> tag matching the opening div at start_pos"""
        depth = 0
        i = start_pos

        while i < len(html):
            # Look for opening div tags
            if html[i : i + 4] == "<div":
                # Find the end of this tag
                tag_end = html.find(">", i)
                if tag_end != -1:
                    depth += 1
                    i = tag_end + 1
                else:
                    i += 1
            # Look for closing div tags
            elif html[i : i + 6] == "</div>":
                depth -= 1
                if depth == 0:
                    return i + 6
                i += 6
            else:
                i += 1

        return -1

    def _strip_html_tags(self, html: str) -> str:
        """Remove HTML tags and return plain text"""
        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

        # Remove HTML tags
        html = re.sub(r"<[^>]+>", "", html)

        # Decode HTML entities
        html = html.replace("&nbsp;", " ")
        html = html.replace("&lt;", "<")
        html = html.replace("&gt;", ">")
        html = html.replace("&amp;", "&")
        html = html.replace("&quot;", '"')
        html = html.replace("&#39;", "'")

        # Remove extra whitespace
        html = re.sub(r"\s+", " ", html)

        return html
