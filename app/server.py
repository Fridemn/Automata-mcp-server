import importlib
import inspect
import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

# Core server module for Automata MCP Server
import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from loguru import logger
from pydantic import BaseModel

from .base_tool import BaseMCPTool
from .routers import create_router


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

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allows all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allows all methods
            allow_headers=["*"],  # Allows all headers
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
        self.install_dependencies_for_enabled_tools()
        self.discover_tools()
        # Initialize FastApiMCP
        self.mcp = FastApiMCP(self.app)
        self.mcp.mount_http()

        # Mount data directory for serving generated images and other files
        data_path = Path(__file__).parent.parent / "data"
        self.app.mount(
            "/data",
            StaticFiles(directory=str(data_path)),
            name="data",
        )

        # Include routers
        self.app.include_router(
            create_router(self.authenticate, lambda: len(self.tools), self.tools),
        )

    def install_dependencies_for_enabled_tools(self):
        """Install dependencies for all tools."""
        if not self.tools_dir.exists():
            logger.warning(
                f"Tools directory {self.tools_dir} does not exist, skipping dependency installation",
            )
            return

        if not self.tools_dir.is_dir():
            logger.warning(
                f"Tools directory {self.tools_dir} is not a directory, skipping dependency installation",
            )
            return

        # Iterate through Python packages in tools directory
        for item in self.tools_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                modname = item.name
                config_path = item / "config.yaml"
                config = {}
                if config_path.exists():
                    try:
                        with open(config_path, encoding="utf-8") as f:
                            config = yaml.safe_load(f)
                    except (
                        yaml.YAMLError,
                        FileNotFoundError,
                    ) as e:
                        logger.error(f"Failed to load config for tool {modname}: {e}")
                        continue

                packages = config.get("packages", [])
                if packages:
                    logger.info(
                        f"Installing packages for tool {modname}: {packages}",
                    )
                    try:
                        # Use uv pip install to install packages
                        cmd = ["uv", "pip", "install", *packages]
                        result = subprocess.run(  # noqa: S603
                            cmd,
                            capture_output=True,
                            text=True,
                            cwd=self.tools_dir.parent.parent,
                            check=False,
                        )
                        if result.returncode != 0:
                            logger.error(
                                f"Failed to install packages for {modname}: {result.stderr}",
                            )
                            continue
                        logger.info(
                            f"Successfully installed packages for {modname}",
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error installing packages for {modname}: {e}",
                        )
                        continue

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
                # config.yaml is optional for discovery; we don't need to load it here

                # Import the module
                tool_file = item / f"{modname}_tool.py"
                if not tool_file.exists():
                    logger.warning(
                        f"Tool file {tool_file} not found for tool {modname}, skipping",
                    )
                    continue

                try:
                    # Import the module - calculate relative path from app package
                    app_dir = Path(__file__).parent
                    relative_path = self.tools_dir.relative_to(app_dir)
                    module_path = f"app.{relative_path}.{modname}".replace(
                        "/",
                        ".",
                    ).replace("\\", ".")
                    module = importlib.import_module(module_path)
                    # Get the tool class (assume it's named <Modname>Tool)
                    tool_class_name = (
                        "".join(word.capitalize() for word in modname.split("_"))
                        + "Tool"
                    )
                    logger.info(
                        f"Looking for class {tool_class_name} in module {module_path}",
                    )
                    if not hasattr(module, tool_class_name):
                        logger.error(
                            f"Module {module_path} does not have attribute {tool_class_name}, available: {dir(module)}",
                        )
                        continue
                    tool_class = getattr(module, tool_class_name)
                    # Instantiate the tool
                    tool_instance = tool_class()
                    # Register the tool
                    self.tools[modname] = tool_instance
                    # Register routes for the tool
                    self.register_tool_routes(tool_instance, modname)
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
                    logger.exception(f"Unexpected error loading tool {modname}: {e}")

    def register_tool_routes(self, tool_instance: BaseMCPTool, modname: str):
        """Register FastAPI routes for the tool."""

        route_configs = tool_instance.get_route_config()
        if isinstance(route_configs, dict):
            route_configs = [route_configs]
        if not isinstance(route_configs, list | tuple):
            logger.error(
                f"Tool {modname} get_route_config must return a dict or list of dicts, got {type(route_configs)}",
            )
            return

        async def verify_api_key(
            x_api_key: str | None = Header(None, alias="X-API-Key"),
        ):
            """Dependency to verify API key."""
            if not self.authenticate(x_api_key or ""):
                raise HTTPException(status_code=401, detail="Invalid API key")
            return x_api_key

        def create_tool_endpoint(p_class, use_form_flag, tool_name_default):
            if use_form_flag:
                # For form data, create a dynamic function with proper Form parameters

                # Get the fields from the params class
                fields = p_class.model_fields

                # Create parameter list for function signature
                params = []

                for field_name, field_info in fields.items():
                    # Check if the field is UploadFile
                    if field_info.annotation == UploadFile or (
                        hasattr(field_info.annotation, "__origin__")
                        and field_info.annotation.__origin__ == UploadFile
                    ):
                        form_func = File
                    else:
                        form_func = Form

                    if field_info.is_required():
                        params.append(
                            inspect.Parameter(
                                field_name,
                                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                default=form_func(
                                    ...,
                                    description=field_info.description or "",
                                ),
                            ),
                        )
                    else:
                        params.append(
                            inspect.Parameter(
                                field_name,
                                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                default=form_func(
                                    field_info.default,
                                    description=field_info.description or "",
                                ),
                            ),
                        )

                # Add API key parameter
                params.append(
                    inspect.Parameter(
                        "_api_key",
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        default=Depends(verify_api_key),
                    ),
                )

                # Create the function signature
                sig = inspect.Signature(params)

                async def tool_endpoint(**kwargs):
                    # The function will receive form parameters directly
                    # Separate API key from form data
                    kwargs.pop("_api_key", None)
                    form_data = kwargs

                    # Validate form data with the params_class
                    try:
                        params_obj = p_class(**form_data)
                    except ValueError as e:
                        raise HTTPException(status_code=422, detail=str(e))

                    # Use the provided tool_name_default captured in closure
                    tool_name = tool_name_default
                    result = await tool_instance.call_tool(
                        tool_name,
                        params_obj.model_dump(),
                    )
                    # Convert to dict for JSON response
                    return {
                        "content": [
                            {"type": item.type, "text": item.text}
                            for item in result
                            if hasattr(item, "type") and hasattr(item, "text")
                        ],
                    }

                # Set the signature on the function
                tool_endpoint.__signature__ = sig

                return tool_endpoint

            async def tool_endpoint(
                params,  # type: ignore
                _api_key: str = Depends(verify_api_key),
            ):
                # params is already validated by FastAPI as the correct type
                # Use the provided tool_name_default captured in closure
                tool_name = tool_name_default
                result = await tool_instance.call_tool(
                    tool_name,
                    params.model_dump(),
                )
                # Convert to dict for JSON response
                return {
                    "content": [
                        {"type": item.type, "text": item.text}
                        for item in result
                        if hasattr(item, "type") and hasattr(item, "text")
                    ],
                }

            # Set the type annotation dynamically
            if not use_form_flag:
                tool_endpoint.__annotations__["params"] = p_class
            return tool_endpoint

        # Register each route config separately, capturing values per-iteration
        for route_config in route_configs:
            if not isinstance(route_config, dict):
                logger.error(f"Invalid route config for {modname}: {route_config}")
                continue
            endpoint = route_config.get("endpoint")
            params_class = route_config.get("params_class")
            use_form = route_config.get("use_form", False)
            tool_name_default = route_config.get("tool_name", modname)

            if not endpoint or not params_class:
                logger.error(
                    f"Route config for {modname} missing 'endpoint' or 'params_class': {route_config}",
                )
                continue

            tool_endpoint_func = create_tool_endpoint(
                params_class,
                use_form,
                tool_name_default,
            )
            self.app.post(endpoint)(tool_endpoint_func)
            logger.info(f"Registered route {endpoint} for tool {modname}")

    def authenticate(self, api_key: str) -> bool:
        """Authenticate using API key."""
        if not self.api_key:
            return True  # No API key required if not set
        return api_key == self.api_key


def create_app() -> FastAPI:
    """Create and return the FastAPI application."""
    server = AutomataMCPServer()
    return server.app


def main():
    """Main entry point for the Automata MCP Server."""

    server = AutomataMCPServer()
    host = server.host
    port = int(server.port)

    # Open browser after server starts
    def open_browser():
        time.sleep(2)  # Wait for server to fully start
        url = f"http://{host}:{port}/dashboard"
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    main()
