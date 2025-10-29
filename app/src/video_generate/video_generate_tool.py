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
from .generate import generate_video_from_text


class VideoGenerateParams(BaseModel):
    text: str = Field(description="Input text for generating audio and subtitles")
    videos_path: str | list[str] = Field(
        description="Video file path (single string or list of paths)"
    )
    draft_name: str = Field(description="Name of the draft")
    audio_output_file: str = Field(
        default="generated_audio.mp3",
        description="Path for the generated audio file",
    )
    vtt_output_file: str = Field(
        default="generated_subtitle.vtt",
        description="Path for the generated subtitle file",
    )
    voice: str = Field(
        default="zh-CN-YunxiNeural",
        description="TTS voice to use",
    )
    rate: str = Field(default="+0%", description="Speech rate adjustment")
    volume: str = Field(default="+0%", description="Volume adjustment")
    pitch: str = Field(default="+0Hz", description="Pitch adjustment")
    video_ratio: str = Field(
        default="9:16",
        description="Video aspect ratio (9:16, 16:9, or 1:1)",
    )
    drafts_root: str = Field(
        default="",
        description="Root directory for saving drafts",
    )
    music_path: str = Field(
        default="",
        description="Background music path (optional)",
    )


class VideoGenerateTool(BaseMCPTool):
    def __init__(self):
        super().__init__()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/tools/video_generate",
                "params_class": VideoGenerateParams,
                "use_form": True,
            }
        ]

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="video_generate",
                description="Generate video from text by creating audio, subtitles, and video draft. Takes input text and video paths, generates TTS audio and subtitles, then creates a video draft.",
                inputSchema=VideoGenerateParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        if name != "video_generate":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        try:
            args = VideoGenerateParams(**arguments)
        except ValueError as e:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

        if not args.text.strip():
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Text is required"))

        if not args.draft_name.strip():
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Draft name is required")
            )

        try:
            success = await generate_video_from_text(
                text=args.text,
                videos_path=args.videos_path,
                draft_name=args.draft_name,
                audio_output_file=args.audio_output_file,
                vtt_output_file=args.vtt_output_file,
                voice=args.voice,
                rate=args.rate,
                volume=args.volume,
                pitch=args.pitch,
                video_ratio=args.video_ratio,
                drafts_root=args.drafts_root,
                music_path=args.music_path,
            )

            if success:
                return [
                    TextContent(
                        type="text",
                        text=f"Video draft '{args.draft_name}' generated successfully! Audio and subtitles created from text.",
                    )
                ]
            else:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="Video generation failed. Check logs for details.",
                    )
                )
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR,
                    message=f"Failed to generate video: {str(e)}",
                )
            )
