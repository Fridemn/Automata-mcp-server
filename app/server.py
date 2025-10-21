import importlib
import os
from pathlib import Path
from typing import Optional, Sequence

import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from loguru import logger
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel

from .base_tool import BaseMCPTool


class MCPRequest(BaseModel):
    method: str
    params: dict | None = None
    id: str | None = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: dict | None = None
    error: dict | None = None
    id: str | None = None


class AutomataMCPServer:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()

        self.app = FastAPI(
            title="Automata MCP Server",
            description="A centralized MCP server using FastAPI with plugin architecture",
            version="1.0.0",
        )
        self.tools = {}
        self.api_key = os.getenv("AUTOMATA_API_KEY")  # 从环境变量获取API key
        self.host = os.getenv("HOST")
        self.port = os.getenv("PORT")
        # 配置工具目录路径，支持绝对路径和相对路径
        tools_dir_env = os.getenv("TOOLS_DIR")
        if tools_dir_env is None:
            tools_dir_env = "src"
        if Path(tools_dir_env).is_absolute():
            self.tools_dir = Path(tools_dir_env)
        else:
            self.tools_dir = Path(__file__).parent / tools_dir_env
        self.discover_tools()
        self.setup_routes()

    def discover_tools(self):
        """Automatically discover tools in the configured tools directory."""
        if not self.tools_dir.exists():
            logger.warning(
                f"Tools directory {self.tools_dir} does not exist, skipping tool discovery",
            )
            return

        if not self.tools_dir.is_dir():
            logger.warning(
                f"Tools directory {self.tools_dir} is not a directory, skipping tool discovery",
            )
            return

        # Iterate through Python packages in tools directory
        for item in self.tools_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                modname = item.name
                config_path = item / "config.yaml"
                if not config_path.exists():
                    logger.warning(
                        f"Config file not found for tool {modname} at {config_path}, skipping",
                    )
                    continue

                try:
                    with open(config_path, encoding="utf-8") as f:
                        config = yaml.safe_load(f)

                    if not config.get("enabled", False):
                        logger.info(f"Tool {modname} is disabled, skipping")
                        continue

                    # Import the module
                    module = importlib.import_module(f"app.src.{modname}")
                    # Get the tool class (assume it's named <Modname>Tool)
                    tool_class_name = f"{modname.capitalize()}Tool"
                    tool_class = getattr(module, tool_class_name)
                    # Instantiate the tool
                    tool_instance = tool_class()
                    # Register the tool
                    self.tools[modname] = tool_instance
                    logger.info(
                        f"Tool {modname} discovered and registered successfully",
                    )
                except (
                    ImportError,
                    AttributeError,
                    yaml.YAMLError,
                    FileNotFoundError,
                ) as e:
                    logger.error(f"Failed to load tool {modname}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error loading tool {modname}: {e}")

    def authenticate(self, api_key: str) -> bool:
        """Authenticate using API key."""
        if not self.api_key:
            return True  # No API key required if not set
        return api_key == self.api_key

    async def list_tools(self) -> list[Tool]:
        """List all available tools."""
        tools = []
        for tool_instance in self.tools.values():
            tools.extend(await tool_instance.list_tools())
        return tools

    async def call_tool(
        self,
        name: str,
        arguments: dict,
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Call a tool by name."""
        for tool_instance in self.tools.values():
            if name in [tool.name for tool in await tool_instance.list_tools()]:
                return await tool_instance.call_tool(name, arguments)
        msg = f"Tool '{name}' not found"
        raise ValueError(msg)

    def setup_routes(self):
        """Setup FastAPI routes."""

        async def verify_api_key(
            x_api_key: str | None = Header(None, alias="X-API-Key"),
        ):
            """Dependency to verify API key."""
            if not self.authenticate(x_api_key or ""):
                raise HTTPException(status_code=401, detail="Invalid API key")
            return x_api_key

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "Automata MCP Server is running",
                "version": "1.0.0",
                "tools_count": len(self.tools),
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.app.post("/mcp")
        async def handle_mcp_request(
            request: MCPRequest,
            _api_key: str = Depends(verify_api_key),
        ):
            """Handle MCP requests over HTTP."""
            try:
                if request.method == "tools/list":
                    tools = await self.list_tools()
                    result = {
                        "tools": [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema,
                            }
                            for tool in tools
                        ],
                    }
                    return MCPResponse(result=result, id=request.id)

                if request.method == "tools/call":
                    if not request.params or "name" not in request.params:
                        return MCPResponse(
                            error={"code": -32602, "message": "Invalid params"},
                            id=request.id,
                        )

                    name = request.params["name"]
                    arguments = request.params.get("arguments", {})

                    try:
                        content = await self.call_tool(name, arguments)
                        result = {
                            "content": [
                                {"type": item.type, "text": item.text}
                                for item in content
                                if isinstance(item, TextContent)
                            ],
                        }
                        return MCPResponse(result=result, id=request.id)
                    except Exception as e:
                        return MCPResponse(
                            error={"code": -32603, "message": str(e)},
                            id=request.id,
                        )

                else:
                    return MCPResponse(
                        error={
                            "code": -32601,
                            "message": f"Method '{request.method}' not found",
                        },
                        id=request.id,
                    )

            except Exception as e:
                return MCPResponse(
                    error={"code": -32603, "message": f"Internal error: {e!s}"},
                    id=request.id,
                )

        @self.app.get("/tools")
        async def list_registered_tools(_api_key: str = Depends(verify_api_key)):
            """List all registered tools (for debugging)."""
            tools = await self.list_tools()
            return {
                "tools": [
                    {"name": tool.name, "description": tool.description}
                    for tool in tools
                ],
            }


def create_app() -> FastAPI:
    """Create and return the FastAPI application."""
    server = AutomataMCPServer()
    return server.app


def main():
    """Main entry point for the Automata MCP Server."""

    server = AutomataMCPServer()
    host = server.host
    port = int(server.port)
    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    main()
