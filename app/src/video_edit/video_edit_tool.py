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


class VideoEditParams(BaseModel):
    workflow_id: str
    # Add other params as needed


class VideoEditTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/video/edit",
                "params_class": VideoEditParams,
                "tool_name": "edit_video",
            },
        ]

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="edit_video",
                description="Edit video based on workflow",
                inputSchema=VideoEditParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name == "edit_video":
            return await self._edit_video(arguments)
        else:
            raise ValueError(f"Unknown tool name: {name}")

    async def _edit_video(self, arguments: dict) -> Sequence[TextContent]:
        try:
            # TODO: Implement actual video editing logic
            # For now, return mock result
            workflow_id = arguments.get("workflow_id", "unknown")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": True,
                            "message": "视频剪辑完成",
                            "video_path": f"output_{workflow_id}.mp4",
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
