import asyncio
from typing import Sequence

from app.base_tool import BaseMCPTool
from loguru import logger
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
from pydantic import BaseModel, Field


class FlowWaitParams(BaseModel):
    """Parameters for wait operations."""

    seconds: float = Field(
        description="Number of seconds to wait",
        ge=0.1,
        le=3600,  # 最大等待1小时
    )


class FlowWaitTool(BaseMCPTool):
    """Tool for waiting a specified number of seconds."""

    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/tools/flow_wait",
                "params_class": FlowWaitParams,
                "use_form": True,
            },
        ]

    async def list_tools(self) -> list[Tool]:
        """List the tools provided by this module."""
        return [
            Tool(
                name="flow_wait",
                description="Wait for a specified number of seconds. Useful for implementing delays in workflows or waiting between operations.",
                inputSchema=FlowWaitParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name with given arguments."""
        logger.info("Starting flow_wait tool execution")

        if name != "flow_wait":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = FlowWaitParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        try:
            logger.info(f"Waiting for {args.seconds} seconds...")
            await asyncio.sleep(args.seconds)
            logger.info(f"Successfully waited for {args.seconds} seconds")

            return [
                TextContent(
                    type="text",
                    text=f"✅ Successfully waited for {args.seconds} seconds",
                ),
            ]

        except Exception as e:
            logger.error(f"Failed to wait: {e!s}")
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to wait: {e!s}",
                ),
            )
