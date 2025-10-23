from typing import Sequence

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

from app.base_tool import BaseMCPTool
from app.llm import LLMClient


class PolishParams(BaseModel):
    original_text: str = Field(description="The original text to polish")
    prompt: str = Field(description="The prompt to guide the polishing process")


class PolishTool(BaseMCPTool):
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()

    def get_route_config(self) -> dict:
        return {
            "endpoint": "/tools/polish",
            "params_class": PolishParams,
        }

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="polish",
                description="Polishes text based on the provided prompt. Takes original text and a prompt to guide the polishing process, returns the polished text.",
                inputSchema=PolishParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "polish":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = PolishParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        if not args.original_text.strip():
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Original text is required")
            )

        if not args.prompt.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Prompt is required"))

        try:
            polished_text = await self.llm_client.generate(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional text polisher. Your task is to polish the provided text according to the given prompt.",
                    },
                    {
                        "role": "user",
                        "content": f"Prompt: {args.prompt}\n\nOriginal Text:\n{args.original_text}\n\nPlease provide the polished version:",
                    },
                ],
                max_tokens=2000,
                temperature=0.7,
            )
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to polish text: {str(e)}"
                )
            )

        return [TextContent(type="text", text=polished_text)]
