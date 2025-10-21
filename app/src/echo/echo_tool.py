from app.base_tool import BaseMCPTool
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field


class EchoParams(BaseModel):
    message: str = Field(description="Message to echo back")


class EchoTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="echo",
                description="Echo back a message",
                inputSchema=EchoParams.model_json_schema(),
            )
        ]

    async def call_tool(
        self, name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "echo":
            raise ValueError(f"Unknown tool: {name}")

        params = EchoParams(**arguments)
        return [TextContent(type="text", text=f"Echo: {params.message}")]
