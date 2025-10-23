from abc import ABC, abstractmethod
from typing import Sequence

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool


class BaseMCPTool(ABC):
    def __init__(self):
        pass

    @abstractmethod
    async def list_tools(self) -> list[Tool]:
        """List the tools provided by this module."""

    @abstractmethod
    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name with given arguments."""

    @abstractmethod
    def get_route_config(self) -> dict:
        """Get route configuration for this tool.

        Returns:
            dict: Configuration containing 'endpoint', 'params_class', etc.
        """
