import importlib
import inspect
import os
import subprocess
from pathlib import Path

# Core server module for Automata MCP Server
import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from fastapi_mcp import FastApiMCP
from loguru import logger
from pydantic import BaseModel

from .base_tool import BaseMCPTool
from .exceptions import (
    AutomataError,
    ConfigurationError,
    DependencyInstallError,
    ToolLoadError,
    handle_exception,
    with_exception_handling,
)
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

        # Add CORS middleware with secure defaults
        allowed_origins = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        )
        allowed_origins_list = [
            origin.strip() for origin in allowed_origins.split(",") if origin.strip()
        ]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins_list,  # Only allow specified origins
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],  # Only allow necessary methods
            allow_headers=[
                "X-API-Key",
                "Content-Type",
                "Authorization",
            ],  # Only allow necessary headers
        )

        # Add security headers middleware
        @self.app.middleware("http")
        async def add_security_headers(request: Request, call_next):
            """Add security headers to all responses."""
            response = await call_next(request)

            # Security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Remove server header for security
            if "Server" in response.headers:
                del response.headers["Server"]

            return response

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
        self.extension_dir = Path(__file__).parent / "AutoUp-MCP-Extension"
        self.tools_dirs = [self.tools_dir]
        if self.extension_dir.exists() and self.extension_dir.is_dir():
            self.tools_dirs.append(self.extension_dir)
        self.install_dependencies_for_enabled_tools()
        self.discover_tools()
        # Initialize FastApiMCP
        self.mcp = FastApiMCP(self.app)
        self.mcp.mount_http()

        # Include routers
        self.app.include_router(
            create_router(self.authenticate, lambda: len(self.tools), self.tools),
        )

        # 验证安全配置
        self._validate_security_config()

    def _validate_security_config(self):
        """验证安全配置"""
        # 检查API key配置
        if not self.api_key:
            logger.warning(
                "SECURITY: No API key configured. Consider setting AUTOMATA_API_KEY environment variable.",
            )

        # 检查CORS配置
        allowed_origins = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        )
        if "*" in allowed_origins:
            logger.warning(
                "SECURITY: CORS allows all origins. Consider restricting ALLOWED_ORIGINS.",
            )

        # 检查调试模式
        if os.getenv("DEBUG", "false").lower() == "true":
            logger.warning(
                "SECURITY: Debug mode is enabled. Sensitive information may be exposed in error responses.",
            )

    @with_exception_handling("dependency_installation")
    def install_dependencies_for_enabled_tools(self):
        """Install dependencies for all tools with improved error handling."""
        for tools_dir in self.tools_dirs:
            self._install_dependencies_for_directory_safe(tools_dir)

    def _install_dependencies_for_directory_safe(self, tools_dir: Path):
        """安全地为目录安装依赖，处理异常"""
        try:
            self._validate_tools_directory(tools_dir)
            self._install_dependencies_for_directory(tools_dir)
        except Exception as e:
            # 继续处理其他目录，但记录错误
            handle_exception(e, {"tools_dir": str(tools_dir)})

    def _validate_tools_directory(self, tools_dir: Path):
        """验证工具目录"""
        if not tools_dir.exists():
            error_msg = f"Tools directory does not exist: {tools_dir}"
            raise ConfigurationError(
                error_msg,
                details={"tools_dir": str(tools_dir)},
            )

        if not tools_dir.is_dir():
            error_msg = f"Path is not a directory: {tools_dir}"
            raise ConfigurationError(
                error_msg,
                details={"tools_dir": str(tools_dir)},
            )

    def _install_dependencies_for_directory(self, tools_dir: Path):
        """为指定目录安装依赖"""
        for item in tools_dir.iterdir():
            if not (item.is_dir() and (item / "__init__.py").exists()):
                continue

            modname = item.name
            try:
                self._install_tool_dependencies(item, modname)
            except Exception as e:
                # 继续处理其他工具，但记录错误
                handle_exception(e, {"tool": modname, "tools_dir": str(tools_dir)})
                continue

    def _install_tool_dependencies(self, tool_dir: Path, modname: str):
        """安装单个工具的依赖"""
        config_path = tool_dir / "config.yaml"
        config = self._load_tool_config(config_path, modname)

        packages = config.get("packages", [])
        if not packages:
            return

        logger.info(f"Installing packages for tool {modname}: {packages}")

        try:
            self._run_pip_install(packages, tool_dir.parent.parent)
            logger.info(f"Successfully installed packages for {modname}")
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to install packages for {modname}"
            raise DependencyInstallError(
                error_msg,
                details={
                    "tool": modname,
                    "packages": packages,
                    "return_code": e.returncode,
                    "stderr": e.stderr,
                },
            )
        except subprocess.TimeoutExpired:
            error_msg = f"Package installation timed out for {modname}"
            raise DependencyInstallError(
                error_msg,
                details={"tool": modname, "packages": packages},
            )
        except Exception as e:
            error_msg = f"Unexpected error installing packages for {modname}: {e}"
            raise DependencyInstallError(
                error_msg,
                details={"tool": modname, "packages": packages},
            )

    def _load_tool_config(self, config_path: Path, modname: str) -> dict:
        """加载工具配置"""
        if not config_path.exists():
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in config file for tool {modname}"
            raise ConfigurationError(
                error_msg,
                details={
                    "tool": modname,
                    "config_path": str(config_path),
                    "yaml_error": str(e),
                },
            )
        except OSError as e:
            error_msg = f"Cannot read config file for tool {modname}"
            raise ConfigurationError(
                error_msg,
                details={
                    "tool": modname,
                    "config_path": str(config_path),
                    "io_error": str(e),
                },
            )

    def _run_pip_install(self, packages: list[str], cwd: Path):
        """运行 pip 安装命令"""
        # 验证包名安全性（基本检查）
        if not packages:
            return

        for package in packages:
            if not isinstance(package, str) or not package.strip():
                error_msg = f"Invalid package name: {package}"
                raise ValueError(error_msg)

        cmd = ["uv", "pip", "install", *packages]
        # S603: subprocess call is safe because packages are validated above
        subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300,  # 5分钟超时
            check=True,
        )

    @with_exception_handling("tool_discovery")
    def discover_tools(self):
        """Automatically discover tools with improved error handling."""
        for tools_dir in self.tools_dirs:
            self._discover_tools_in_directory_safe(tools_dir)

    def _discover_tools_in_directory_safe(self, tools_dir: Path):
        """安全地在目录中发现工具，处理异常"""
        try:
            self._validate_tools_directory(tools_dir)
            self._discover_tools_in_directory(tools_dir)
        except Exception as e:
            handle_exception(e, {"tools_dir": str(tools_dir)})

    def _discover_tools_in_directory(self, tools_dir: Path):
        """在指定目录中发现工具"""
        for item in tools_dir.iterdir():
            if not (item.is_dir() and (item / "__init__.py").exists()):
                continue

            modname = item.name
            try:
                self._load_and_register_tool(item, modname, tools_dir)
            except Exception as e:
                handle_exception(e, {"tool": modname, "tools_dir": str(tools_dir)})
                continue

    def _load_and_register_tool(self, tool_dir: Path, modname: str, tools_dir: Path):
        """加载并注册工具"""
        tool_file = tool_dir / f"{modname}_tool.py"
        if not tool_file.exists():
            error_msg = f"Tool file not found: {tool_file}"
            raise ToolLoadError(
                error_msg,
                details={"tool": modname, "expected_file": str(tool_file)},
            )

        try:
            # 计算模块路径
            app_dir = Path(__file__).parent
            relative_path = tools_dir.relative_to(app_dir)
            module_path = f"app.{relative_path}.{modname}".replace("/", ".").replace(
                "\\",
                ".",
            )

            # 导入模块
            module = importlib.import_module(module_path)

            # 获取工具类
            tool_class_name = (
                "".join(word.capitalize() for word in modname.split("_")) + "Tool"
            )

            tool_class = self._get_tool_class(
                module,
                tool_class_name,
                module_path,
                modname,
            )
            self._validate_tool_class(tool_class, tool_class_name, modname)

            # 实例化工具
            tool_instance = tool_class()

            # 注册工具
            self.tools[modname] = tool_instance
            self.register_tool_routes(tool_instance, modname)

            logger.info(f"Tool {modname} discovered and registered successfully")

        except ImportError as e:
            error_msg = f"Failed to import tool module {module_path}"
            raise ToolLoadError(
                error_msg,
                details={
                    "tool": modname,
                    "module_path": module_path,
                    "import_error": str(e),
                },
            )
        except AttributeError as e:
            error_msg = f"Failed to load tool class from module {module_path}"
            raise ToolLoadError(
                error_msg,
                details={
                    "tool": modname,
                    "module_path": module_path,
                    "attribute_error": str(e),
                },
            )
        except Exception as e:
            error_msg = f"Unexpected error loading tool {modname}"
            raise ToolLoadError(
                error_msg,
                details={"tool": modname, "error": str(e)},
            )

    def _get_tool_class(
        self,
        module,
        tool_class_name: str,
        module_path: str,
        modname: str,
    ):
        """获取工具类，如果不存在则抛出异常"""
        if not hasattr(module, tool_class_name):
            available_classes = [name for name in dir(module) if name.endswith("Tool")]
            error_msg = (
                f"Tool class {tool_class_name} not found in module {module_path}"
            )
            raise ToolLoadError(
                error_msg,
                details={
                    "tool": modname,
                    "module_path": module_path,
                    "expected_class": tool_class_name,
                    "available_classes": available_classes,
                },
            )
        return getattr(module, tool_class_name)

    def _validate_tool_class(self, tool_class, tool_class_name: str, modname: str):
        """验证工具类是否继承自 BaseMCPTool"""
        if not issubclass(tool_class, BaseMCPTool):
            error_msg = f"Tool class {tool_class_name} must inherit from BaseMCPTool"
            raise ToolLoadError(
                error_msg,
                details={"tool": modname, "class_name": tool_class_name},
            )

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
        """Authenticate using API key with enhanced security."""
        # If no API key is configured, allow access (development mode)
        if not self.api_key:
            logger.warning("No API key configured - allowing unauthenticated access")
            return True

        # Validate API key format (basic security check)
        if not api_key or not isinstance(api_key, str):
            logger.warning("Invalid API key format")
            return False

        # Check API key length (prevent timing attacks with very short keys)
        if len(api_key.strip()) < 8:
            logger.warning("API key too short")
            return False

        # Use constant-time comparison to prevent timing attacks
        import hmac

        return hmac.compare_digest(api_key.strip(), self.api_key.strip())


def create_app() -> FastAPI:
    """Create and return the FastAPI application."""
    server = AutomataMCPServer()
    app = server.app

    # 添加全局异常处理器
    @app.exception_handler(AutomataError)
    async def automata_error_handler(_request: Request, exc: AutomataError):
        """处理自定义异常"""
        error_info = exc.to_dict()
        return JSONResponse(
            status_code=400,
            content={"error": error_info},
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        """处理未捕获的异常，防止信息泄露"""
        # 记录详细错误信息到日志
        error_info = handle_exception(
            exc,
            {
                "url": str(request.url),
                "method": request.method,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent", "Unknown"),
            },
        )

        # 返回安全的错误响应，不包含敏感信息
        safe_error = {
            "error_code": "InternalServerError",
            "message": "An internal server error occurred",
            "timestamp": error_info.get("timestamp", None),
        }

        # 在开发模式下包含更多信息
        if os.getenv("DEBUG", "false").lower() == "true":
            safe_error["details"] = error_info.get("details", {})

        return JSONResponse(
            status_code=500,
            content={"error": safe_error},
        )

    return app


# 创建全局 app 实例供 uvicorn 热重载使用
app = create_app()


def main():
    """Main entry point for the Automata MCP Server."""

    # 从环境变量读取配置
    load_dotenv()
    host = os.getenv("HOST")
    port = int(os.getenv("PORT"))

    # 启用热重载功能，当代码文件发生变化时自动重启服务器
    uvicorn.run(
        "app.server:app",
        host=host,
        port=port,
        reload=True,
        reload_includes=["**/*.py"],  # 监听所有 Python 文件的变化
    )


if __name__ == "__main__":
    main()
