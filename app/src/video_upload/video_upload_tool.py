"""
Video upload tool for Automata MCP Server
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import List, Sequence

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel

from ...base_tool import BaseMCPTool
from ...exceptions import handle_exception
from ...routers import verify_api_key_dependency


class VideoUploadParams(BaseModel):
    """Parameters for video upload operations."""

    file: UploadFile


class VideoUploadTool(BaseMCPTool):
    """Tool for handling video uploads and management."""

    def __init__(self):
        super().__init__()
        self.router = APIRouter()
        self._setup_routes()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/tools/video_upload",
                "params_class": VideoUploadParams,
                "use_form": True,
            },
        ]

    async def _upload_single_video(self, file: UploadFile) -> dict:
        """Upload a single video file and return result info."""
        # Validate file type
        allowed_extensions = {
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".webm",
            ".flv",
            ".wmv",
            ".m4v",
            ".3gp",
        }
        file_extension = Path(file.filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}",
            )

        # Validate file size (max 500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size: 500MB",
            )

        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        uploads_dir = get_uploads_dir()
        file_path = uploads_dir / unique_filename

        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)

        return {
            "filename": unique_filename,
            "original_filename": file.filename,
            "url": f"/static/upload_videos/{unique_filename}",
            "size": len(file_content),
        }

    def _setup_routes(self):
        """Setup the REST API routes for video upload."""

        # Create a simple authenticate function
        def simple_authenticate(api_key: str) -> bool:  # noqa: ARG001
            return True

        @self.router.post("/upload/video")
        async def upload_video(
            file: UploadFile,
        ):
            """
            Upload a single video file.

            Args:
                file: The video file to upload

            Returns:
                JSON response with upload result
            """
            try:
                result = await self._upload_single_video(file)
                return JSONResponse(
                    content={
                        "success": True,
                        "filename": result["filename"],
                        "original_filename": result["original_filename"],
                        "url": result["url"],
                        "size": result["size"],
                        "message": "Video uploaded successfully",
                    },
                    status_code=200,
                )
            except HTTPException as e:
                return JSONResponse(
                    content={"success": False, "error": e.detail},
                    status_code=e.status_code,
                )
            except Exception as e:
                handle_exception(e, {"operation": "upload_video"})
                return JSONResponse(
                    content={"success": False, "error": "Internal server error"},
                    status_code=500,
                )

        @self.router.post("/upload/videos")
        async def upload_multiple_videos(
            files: list[UploadFile],
        ):
            """
            Upload multiple video files.

            Args:
                files: List of video files to upload

            Returns:
                JSON response with upload results
            """
            try:
                results = []
                errors = []

                for i, file in enumerate(files):
                    try:
                        # Validate file type
                        allowed_extensions = {
                            ".mp4",
                            ".avi",
                            ".mov",
                            ".mkv",
                            ".webm",
                            ".flv",
                            ".wmv",
                            ".m4v",
                            ".3gp",
                        }
                        file_extension = Path(file.filename).suffix.lower()

                        if file_extension not in allowed_extensions:
                            errors.append(
                                {
                                    "index": i,
                                    "filename": file.filename,
                                    "error": f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}",
                                },
                            )
                            continue

                        # Validate file size (max 500MB per file)
                        max_size = 500 * 1024 * 1024  # 500MB
                        file_content = await file.read()
                        if len(file_content) > max_size:
                            errors.append(
                                {
                                    "index": i,
                                    "filename": file.filename,
                                    "error": "File too large. Maximum size: 500MB",
                                },
                            )
                            continue

                        # Generate unique filename
                        unique_filename = f"{uuid.uuid4()}{file_extension}"
                        uploads_dir = get_uploads_dir()
                        file_path = uploads_dir / unique_filename

                        # Save file
                        with open(file_path, "wb") as buffer:
                            buffer.write(file_content)

                        results.append(
                            {
                                "index": i,
                                "filename": unique_filename,
                                "original_filename": file.filename,
                                "url": f"/static/upload_videos/{unique_filename}",
                                "size": len(file_content),
                            },
                        )

                    except Exception as e:
                        errors.append(
                            {
                                "index": i,
                                "filename": file.filename,
                                "error": str(e),
                            },
                        )

                return JSONResponse(
                    content={
                        "success": len(results) > 0,
                        "uploaded": results,
                        "errors": errors,
                        "total_uploaded": len(results),
                        "total_errors": len(errors),
                        "message": f"Uploaded {len(results)} videos successfully",
                    },
                    status_code=200,
                )

            except Exception as e:
                handle_exception(e, {"operation": "multiple_videos_upload"})
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.router.delete("/upload/video/{filename}")
        async def delete_video(
            filename: str,
        ):
            """
            Delete an uploaded video file.

            Args:
                filename: The filename to delete

            Returns:
                JSON response with deletion result
            """
            uploads_dir = get_uploads_dir()
            file_path = uploads_dir / filename

            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")

            try:
                # Delete file
                file_path.unlink()

                return JSONResponse(
                    content={
                        "success": True,
                        "filename": filename,
                        "message": "Video deleted successfully",
                    },
                    status_code=200,
                )

            except Exception as e:
                handle_exception(e, {"operation": "video_delete", "filename": filename})
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.router.get("/upload/videos")
        async def list_uploaded_videos():
            """
            List all uploaded video files.

            Returns:
                JSON response with list of uploaded videos
            """
            try:
                uploads_dir = get_uploads_dir()
                videos = []

                if uploads_dir.exists():
                    for file_path in uploads_dir.iterdir():
                        if file_path.is_file():
                            stat = file_path.stat()
                            videos.append(
                                {
                                    "filename": file_path.name,
                                    "url": f"/static/upload_videos/{file_path.name}",
                                    "size": stat.st_size,
                                    "created": stat.st_ctime,
                                    "modified": stat.st_mtime,
                                },
                            )

                return JSONResponse(
                    content={
                        "success": True,
                        "videos": videos,
                        "total": len(videos),
                        "message": f"Found {len(videos)} uploaded videos",
                    },
                    status_code=200,
                )

            except Exception as e:
                handle_exception(e, {"operation": "list_videos"})
                raise HTTPException(status_code=500, detail="Internal server error")

    async def list_tools(self) -> list[Tool]:
        """List the tools provided by this module."""
        return [
            Tool(
                name="video_upload",
                description="Upload and manage video files. Supports single/multiple uploads, deletion, and listing.",
                inputSchema=VideoUploadParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name with given arguments."""
        if name != "video_upload":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        # Handle file upload if file is provided in arguments
        if "file" in arguments and arguments["file"] is not None:
            file = arguments["file"]
            try:
                result = await self._upload_single_video(file)
                return [
                    TextContent(
                        type="text",
                        text=f"Video uploaded successfully: {result['filename']} ({result['size']} bytes)\nURL: {result['url']}",
                    ),
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Failed to upload video: {e!s}",
                    ),
                ]

        # Return usage information when no file is provided
        return [
            TextContent(
                type="text",
                text="Video upload functionality is available through REST API endpoints. Use the following endpoints:\n"
                "- POST /api/upload/video - Upload single video\n"
                "- POST /api/upload/videos - Upload multiple videos\n"
                "- DELETE /api/upload/video/{filename} - Delete video\n"
                "- GET /api/upload/videos - List uploaded videos",
            ),
        ]

    def get_router(self) -> APIRouter:
        """Get the router for this tool."""
        return self.router


def get_static_dir() -> Path:
    """Get the static directory path"""
    return Path(__file__).parent.parent.parent.parent / "data" / "static"


def get_uploads_dir() -> Path:
    """Get the uploads directory path"""
    static_dir = get_static_dir()
    uploads_dir = static_dir / "upload_videos"
    uploads_dir.mkdir(exist_ok=True)
    return uploads_dir
