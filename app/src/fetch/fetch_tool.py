import asyncio
from typing import Sequence
from urllib.parse import urlparse, urlunparse

import httpx
import markdownify
import readabilipy.simple_json
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
from protego import Protego
from pydantic import AnyUrl, BaseModel, Field

from app.base_tool import BaseMCPTool

DEFAULT_USER_AGENT_AUTONOMOUS = "ModelContextProtocol/1.0 (Autonomous; +https://github.com/modelcontextprotocol/servers)"
DEFAULT_USER_AGENT_MANUAL = "ModelContextProtocol/1.0 (User-Specified; +https://github.com/modelcontextprotocol/servers)"


async def extract_content_from_html(html: str) -> str:
    """Extract and convert HTML content to Markdown format.

    Args:
        html: Raw HTML content to process

    Returns:
        Simplified markdown version of the content
    """
    # Run CPU-intensive operation in thread pool to avoid blocking event loop
    return await asyncio.to_thread(_extract_content_from_html_sync, html)


def _extract_content_from_html_sync(html: str) -> str:
    """Synchronous version of HTML content extraction."""
    ret = readabilipy.simple_json.simple_json_from_html_string(
        html,
        use_readability=True,
    )
    if not ret["content"]:
        return "<error>Page failed to be simplified from HTML</error>"
    return markdownify.markdownify(
        ret["content"],
        heading_style=markdownify.ATX,
    )


def get_robots_txt_url(url: str) -> str:
    """Get the robots.txt URL for a given website URL.

    Args:
        url: Website URL to get robots.txt for

    Returns:
        URL of the robots.txt file
    """
    # Parse the URL into components
    parsed = urlparse(url)

    # Reconstruct the base URL with just scheme, netloc, and /robots.txt path
    return urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))


async def check_may_autonomously_fetch_url(url: str, user_agent: str) -> None:
    """
    Check if the URL can be fetched by the user agent according to the robots.txt file.
    Raises a McpError if not.
    """

    robot_txt_url = get_robots_txt_url(url)

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    ) as client:
        try:
            response = await client.get(
                robot_txt_url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
            )
        except httpx.HTTPError:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to fetch robots.txt {robot_txt_url} due to a connection issue",
                ),
            )
        if response.status_code in (401, 403):
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"When fetching robots.txt ({robot_txt_url}), received status {response.status_code} so assuming that autonomous fetching is not allowed, the user can try manually fetching by using the fetch prompt",
                ),
            )
        if 400 <= response.status_code < 500:
            return
        robot_txt = response.text
    processed_robot_txt = "\n".join(
        line for line in robot_txt.splitlines() if not line.strip().startswith("#")
    )
    robot_parser = Protego.parse(processed_robot_txt)
    if not robot_parser.can_fetch(str(url), user_agent):
        raise McpError(
            ErrorData(
                code=INTERNAL_ERROR,
                message=f"The sites robots.txt ({robot_txt_url}), specifies that autonomous fetching of this page is not allowed, "
                f"<useragent>{user_agent}</useragent>\n"
                f"<url>{url}</url>"
                f"<robots>\n{robot_txt}\n</robots>\n"
                f"The assistant must let the user know that it failed to view the page. The assistant may provide further guidance based on the above information.\n"
                f"The assistant can tell the user that they can try manually fetching the page by using the fetch prompt within their UI.",
            ),
        )


async def fetch_url(
    url: str,
    user_agent: str,
    force_raw: bool = False,
) -> tuple[str, str]:
    """
    Fetch the URL and return the content in a form ready for the LLM, as well as a prefix string with status information.
    """

    async with httpx.AsyncClient(
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    ) as client:
        try:
            response = await client.get(
                url,
                follow_redirects=True,
                headers={"User-Agent": user_agent},
                timeout=30,
            )
        except httpx.HTTPError as e:
            raise McpError(
                ErrorData(code=INTERNAL_ERROR, message=f"Failed to fetch {url}: {e!r}"),
            )
        if response.status_code >= 400:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to fetch {url} - status code {response.status_code}",
                ),
            )

        page_raw = response.text

    content_type = response.headers.get("content-type", "")
    is_page_html = (
        "<html" in page_raw[:100] or "text/html" in content_type or not content_type
    )

    if is_page_html and not force_raw:
        return await extract_content_from_html(page_raw), ""

    return (
        page_raw,
        f"Content type {content_type} cannot be simplified to markdown, but here is the raw content:\n",
    )


class FetchParams(BaseModel):
    url: AnyUrl = Field(description="URL to fetch")
    max_length: int = Field(
        default=5000,
        description="Maximum number of characters to return.",
        gt=0,
        lt=1000000,
    )
    start_index: int = Field(
        default=0,
        description="On return output starting at this character index, useful if a previous fetch was truncated and more context is required.",
        ge=0,
    )
    raw: bool = Field(
        default=False,
        description="Get the actual HTML content of the requested page, without simplification.",
    )


class FetchTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> dict:
        return {
            "endpoint": "/tools/fetch",
            "params_class": FetchParams,
        }

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="fetch",
                description="""Fetches a URL from the internet and optionally extracts its contents as markdown.

Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access. Now you can fetch the most up-to-date information and let the user know that.""",
                inputSchema=FetchParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "fetch":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = FetchParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        url = str(args.url)
        if not url:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL is required"))
        if len(url) > 2048:  # Common URL length limit
            raise McpError(ErrorData(code=INVALID_PARAMS, message="URL too long"))

        content, prefix = await fetch_url(
            url,
            DEFAULT_USER_AGENT_AUTONOMOUS,
            force_raw=args.raw,
        )
        original_length = len(content)
        if args.start_index >= original_length:
            content = "<error>No more content available.</error>"
        else:
            truncated_content = content[
                args.start_index : args.start_index + args.max_length
            ]
            if not truncated_content:
                content = "<error>No more content available.</error>"
            else:
                content = truncated_content
                actual_content_length = len(truncated_content)
                remaining_content = original_length - (
                    args.start_index + actual_content_length
                )
                # Only add the prompt to continue fetching if there is still remaining content
                if actual_content_length == args.max_length and remaining_content > 0:
                    next_start = args.start_index + actual_content_length
                    content += f"\n\n<error>Content truncated. Call the fetch tool with a start_index of {next_start} to get more content.</error>"
        return [TextContent(type="text", text=f"{prefix}Contents of {url}:\n{content}")]
