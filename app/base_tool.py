from abc import ABC, abstractmethod
from typing import Sequence
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource


class BaseMCPTool(ABC):
    def __init__(self):
        pass

    @abstractmethod
    async def list_tools(self) -> list[Tool]:
        """List the tools provided by this module."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name with given arguments."""
        pass