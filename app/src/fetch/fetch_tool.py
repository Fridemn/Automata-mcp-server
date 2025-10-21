from app.base_tool import BaseMCPTool
import requests
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field, AnyUrl


class FetchParams(BaseModel):
    url: AnyUrl = Field(description="URL to fetch")
    max_length: int = Field(default=5000, description="Maximum number of characters to return", gt=0, lt=1000000)


class FetchTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="fetch",
                description="Fetches a URL from the internet and extracts its contents as text.",
                inputSchema=FetchParams.model_json_schema(),
            )
        ]

    async def call_tool(self, name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "fetch":
            raise ValueError(f"Unknown tool: {name}")

        params = FetchParams(**arguments)
        url = str(params.url)

        try:
            response = requests.get(url)
            response.raise_for_status()
            content = response.text

            # Truncate if necessary
            if len(content) > params.max_length:
                content = content[:params.max_length] + "\n\n[Content truncated]"

            return [TextContent(type="text", text=f"Contents of {url}:\n{content}")]
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch {url}: {str(e)}")