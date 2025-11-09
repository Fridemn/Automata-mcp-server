"""
Image upload tool for Automata MCP Server
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


class ImageUploadParams(BaseModel):
    """Parameters for image upload operations."""

    file: UploadFile


class ImageUploadTool(BaseMCPTool):
    """Tool for handling image uploads and management."""

    def __init__(self):
        super().__init__()
        self.router = APIRouter()
        self._setup_routes()

    def get_route_config(self) -> list[dict]:
        return [
            {
                "endpoint": "/tools/image_upload",
                "params_class": ImageUploadParams,
                "use_form": True,
            },
        ]

    async def _upload_single_image(self, file: UploadFile) -> dict:
        """Upload a single image file and return result info."""
        # Validate file type
        allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        file_extension = Path(file.filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}",
            )

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size: 10MB",
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
            "url": f"/static/uploads/{unique_filename}",
            "size": len(file_content),
        }

    def _setup_routes(self):
        """Setup the REST API routes for image upload."""

        # Create a simple authenticate function
        def simple_authenticate(api_key: str) -> bool:  # noqa: ARG001
            return True

        @self.router.post("/upload/image")
        async def upload_image(
            file: UploadFile,
        ):
            """
            Upload a single image file.

            Args:
                file: The image file to upload

            Returns:
                JSON response with upload result
            """
            try:
                result = await self._upload_single_image(file)
                return JSONResponse(
                    content={
                        "success": True,
                        "filename": result["filename"],
                        "original_filename": result["original_filename"],
                        "url": result["url"],
                        "size": result["size"],
                        "message": "Image uploaded successfully",
                    },
                    status_code=200,
                )
            except HTTPException as e:
                return JSONResponse(
                    content={"success": False, "error": e.detail},
                    status_code=e.status_code,
                )
            except Exception as e:
                handle_exception(e, {"operation": "upload_image"})
                return JSONResponse(
                    content={"success": False, "error": "Internal server error"},
                    status_code=500,
                )

        @self.router.post("/upload/images")
        async def upload_multiple_images(
            files: list[UploadFile],
        ):
            """
            Upload multiple image files.

            Args:
                files: List of image files to upload

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
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".gif",
                            ".bmp",
                            ".webp",
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

                        # Validate file size (max 10MB per file)
                        max_size = 10 * 1024 * 1024  # 10MB
                        file_content = await file.read()
                        if len(file_content) > max_size:
                            errors.append(
                                {
                                    "index": i,
                                    "filename": file.filename,
                                    "error": "File too large. Maximum size: 10MB",
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
                                "url": f"/static/uploads/{unique_filename}",
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
                        "message": f"Uploaded {len(results)} files successfully",
                    },
                    status_code=200,
                )

            except Exception as e:
                handle_exception(e, {"operation": "multiple_images_upload"})
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.router.delete("/upload/image/{filename}")
        async def delete_image(
            filename: str,
        ):
            """
            Delete an uploaded image file.

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
                        "message": "Image deleted successfully",
                    },
                    status_code=200,
                )

            except Exception as e:
                handle_exception(e, {"operation": "image_delete", "filename": filename})
                raise HTTPException(status_code=500, detail="Internal server error")

        @self.router.get("/upload/images")
        async def list_uploaded_images():
            """
            List all uploaded image files.

            Returns:
                JSON response with list of uploaded images
            """
            try:
                uploads_dir = get_uploads_dir()
                images = []

                if uploads_dir.exists():
                    for file_path in uploads_dir.iterdir():
                        if file_path.is_file():
                            stat = file_path.stat()
                            images.append(
                                {
                                    "filename": file_path.name,
                                    "url": f"/static/uploads/{file_path.name}",
                                    "size": stat.st_size,
                                    "created": stat.st_ctime,
                                    "modified": stat.st_mtime,
                                },
                            )

                return JSONResponse(
                    content={
                        "success": True,
                        "images": images,
                        "total": len(images),
                        "message": f"Found {len(images)} uploaded images",
                    },
                    status_code=200,
                )

            except Exception as e:
                handle_exception(e, {"operation": "list_images"})
                raise HTTPException(status_code=500, detail="Internal server error")

    async def list_tools(self) -> list[Tool]:
        """List the tools provided by this module."""
        return [
            Tool(
                name="image_upload",
                description="Upload and manage image files. Supports single/multiple uploads, deletion, and listing.",
                inputSchema=ImageUploadParams.model_json_schema(),
            ),
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name with given arguments."""
        if name != "image_upload":
            msg = f"Unknown tool: {name}"
            raise ValueError(msg)

        # Handle file upload if file is provided in arguments
        if "file" in arguments and arguments["file"] is not None:
            file = arguments["file"]
            try:
                result = await self._upload_single_image(file)
                return [
                    TextContent(
                        type="text",
                        text=f"Image uploaded successfully: {result['filename']} ({result['size']} bytes)\nURL: {result['url']}",
                    ),
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"Failed to upload image: {e!s}",
                    ),
                ]

        # Return usage information when no file is provided
        return [
            TextContent(
                type="text",
                text="Image upload functionality is available through REST API endpoints. Use the following endpoints:\n"
                "- POST /api/upload/image - Upload single image\n"
                "- POST /api/upload/images - Upload multiple images\n"
                "- DELETE /api/upload/image/{filename} - Delete image\n"
                "- GET /api/upload/images - List uploaded images",
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
    uploads_dir = static_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    return uploads_dir
