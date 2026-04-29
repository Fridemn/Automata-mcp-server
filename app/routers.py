import inspect
from typing import Any, Callable

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger
from mcp.types import Tool

from .base_tool import BaseMCPTool
from .execution_context import (
    ExecutionContext,
    reset_execution_context,
    set_execution_context,
)
from .schemas import ToolExecutionRequest


def verify_access_token_dependency(
    authenticate_func: Callable[[str], bool],
) -> Callable:
    """
    Factory function to create a verify_access_token dependency with authentication function.
    Returns an async dependency function that verifies Access Token.
    """
    security = HTTPBearer()

    async def verify_access_token(
        auth: HTTPAuthorizationCredentials = Depends(security),
    ) -> str:
        """Dependency to verify Access Token."""
        token = auth.credentials

        if not authenticate_func(token):
            raise HTTPException(status_code=401, detail="Invalid Access Token")
        return token

    return verify_access_token


def create_router(
    authenticate_func: Callable[[str], bool],
    tools_count_func: Callable[[], int],
    tools_dict: dict[str, BaseMCPTool],
) -> APIRouter:
    """
    Creates the main API router with health checks and tool management endpoints.
    Returns a configured APIRouter instance.
    """
    router = APIRouter()
    verify_access_token = verify_access_token_dependency(authenticate_func)

    @router.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint."""
        return {
            "message": "Automata MCP Server is running",
            "version": "1.0.0",
            "tools_count": tools_count_func(),
        }

    @router.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @router.get("/tools")
    async def list_registered_tools(
        _token: str = Depends(verify_access_token),
    ) -> dict[str, list[Tool]]:
        """List all registered tools (for debugging)."""
        tools_info = []
        for modname, tool_instance in tools_dict.items():
            try:
                tool_list = await tool_instance.list_tools()
                tools_info.extend(tool_list)
            except Exception:  # noqa: BLE001
                # Log error if needed, but for now skip
                pass
        return {"tools": tools_info}

    return router


# Tool Route Registration Functions


def get_route_configs(
    tool_instance: BaseMCPTool,
    modname: str,
) -> list[dict[str, Any]]:
    """Gets and validates route configurations from a tool instance.
    Returns a list of validated route configuration dictionaries.
    """
    route_configs = tool_instance.get_route_config()
    if isinstance(route_configs, dict):
        route_configs = [route_configs]
    if not isinstance(route_configs, (list, tuple)):
        logger.error(
            f"Tool {modname} get_route_config must return a dict or list of dicts, got {type(route_configs)}",
        )
        return []

    # Validate and normalize configurations
    validated_configs = []
    for route_config in route_configs:
        if not isinstance(route_config, dict):
            logger.error(f"Invalid route config for {modname}: {route_config}")
            continue

        # Ensure required fields exist
        if not route_config.get("endpoint") or not route_config.get("params_class"):
            logger.error(
                f"Route config for {modname} missing 'endpoint' or 'params_class': {route_config}",
            )
            continue

        # Set defaults
        normalized_config = {
            "endpoint": route_config["endpoint"],
            "params_class": route_config["params_class"],
            "use_form": route_config.get("use_form", False),
            "tool_name": route_config.get("tool_name", modname),
            "requires_session": route_config.get("requires_session", False),
            "platform": route_config.get("platform"),
            "action": route_config.get("action"),
            "enable_execution": route_config.get(
                "enable_execution",
                not route_config.get("use_form", False),
            ),
        }
        validated_configs.append(normalized_config)

    return validated_configs


def create_form_endpoint(
    params_class: type,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_access_token: Callable,
) -> Callable:
    """
    Creates a form data endpoint handler for a tool.
    Returns an async endpoint function.
    """
    # Get the fields from the params class
    fields = params_class.model_fields

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

        # Get the field type annotation
        field_annotation = field_info.annotation

        if field_info.is_required():
            params.append(
                inspect.Parameter(
                    field_name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=form_func(
                        ...,
                        description=field_info.description or "",
                    ),
                    annotation=field_annotation,
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
                    annotation=field_annotation,
                ),
            )

    # Add Access Token parameter
    params.append(
        inspect.Parameter(
            "_token",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=Depends(verify_access_token),
        ),
    )

    # Create the function signature
    sig = inspect.Signature(params)

    async def tool_endpoint(**kwargs: Any) -> dict[str, Any]:
        """Execute tool with form parameters."""
        # Separate Access Token from form data
        kwargs.pop("_token", None)
        form_data = kwargs

        # Validate form data with the params_class
        try:
            params_obj = params_class(**form_data)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        try:
            result = await tool_instance.call_tool(
                tool_name,
                params_obj.model_dump(),
            )
            # Convert to BaseResponse format
            content = []
            for item in result:
                if hasattr(item, "type"):
                    if item.type == "text" and hasattr(item, "text"):
                        content.append({"type": item.type, "text": item.text})
                    elif item.type == "image" and hasattr(item, "data"):
                        content.append(
                            {
                                "type": item.type,
                                "data": item.data,
                                "mimeType": getattr(item, "mimeType", "image/png"),
                            }
                        )
            return {"success": True, "data": {"content": content}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    # Set the signature on the function
    tool_endpoint.__signature__ = sig
    tool_endpoint.__name__ = tool_name

    return tool_endpoint


def create_json_endpoint(
    params_class: type,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_access_token: Callable,
) -> Callable:
    """
    Creates a JSON data endpoint handler for a tool.
    Returns an async endpoint function.
    """

    async def tool_endpoint(
        params: params_class,  # type: ignore
        _token: str = Depends(verify_access_token),
    ) -> dict[str, Any]:
        """Execute tool with JSON parameters."""
        try:
            result = await tool_instance.call_tool(
                tool_name,
                params.model_dump(),
            )
            # Convert to BaseResponse format
            content = []
            for item in result:
                if hasattr(item, "type"):
                    if item.type == "text" and hasattr(item, "text"):
                        content.append({"type": item.type, "text": item.text})
                    elif item.type == "image" and hasattr(item, "data"):
                        content.append(
                            {
                                "type": item.type,
                                "data": item.data,
                                "mimeType": getattr(item, "mimeType", "image/png"),
                            }
                        )
            return {"success": True, "data": {"content": content}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    # Set the type annotation dynamically
    tool_endpoint.__name__ = tool_name
    tool_endpoint.__annotations__["params"] = params_class
    return tool_endpoint


def _format_tool_result(result: Any) -> dict[str, Any]:
    """Convert MCP content items into the standard HTTP response shape."""
    content = []
    for item in result:
        if hasattr(item, "type"):
            if item.type == "text" and hasattr(item, "text"):
                content.append({"type": item.type, "text": item.text})
            elif item.type == "image" and hasattr(item, "data"):
                content.append(
                    {
                        "type": item.type,
                        "data": item.data,
                        "mimeType": getattr(item, "mimeType", "image/png"),
                    }
                )
    return {"success": True, "data": {"content": content}, "error": None}


def _build_execution_context(request: ToolExecutionRequest) -> ExecutionContext:
    session = request.session
    return ExecutionContext(
        task_id=request.task.task_id,
        user_id=request.task.user_id,
        account_id=request.task.account_id,
        platform=request.task.platform,
        action=request.task.action,
        session_id=session.session_id if session else None,
        cdp_url=session.cdp_url if session else None,
        timeout=request.options.timeout,
        retry=request.options.retry,
    )


def _validate_execution_session(
    request: ToolExecutionRequest,
    tool_name: str,
    requires_session: bool,
) -> None:
    """Validate execution envelope structure for session-aware tools."""
    if not requires_session:
        return

    if request.session is None:
        raise HTTPException(
            status_code=422,
            detail=f"Tool {tool_name} requires session data",
        )

    if not request.session.session_id.strip():
        raise HTTPException(
            status_code=422,
            detail=f"Tool {tool_name} requires a non-empty session_id",
        )

    if not request.session.cdp_url.strip():
        raise HTTPException(
            status_code=422,
            detail=f"Tool {tool_name} requires a non-empty cdp_url",
        )


def create_execution_endpoint(
    params_class: type,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_access_token: Callable,
    requires_session: bool = False,
) -> Callable:
    """
    Creates an execution-envelope endpoint handler for a tool.
    Returns an async endpoint function.
    """

    async def tool_execution_endpoint(
        request: ToolExecutionRequest,
        _token: str = Depends(verify_access_token),
    ) -> dict[str, Any]:
        """Execute tool with a standard task/session/payload envelope."""
        try:
            params_obj = params_class(**request.payload)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        _validate_execution_session(request, tool_name, requires_session)
        token = set_execution_context(_build_execution_context(request))

        try:
            result = await tool_instance.call_tool(
                tool_name,
                params_obj.model_dump(),
            )
            return _format_tool_result(result)
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        finally:
            reset_execution_context(token)

    tool_execution_endpoint.__name__ = f"{tool_name}_execute"
    return tool_execution_endpoint


def create_tool_endpoint(
    params_class: type,
    use_form: bool,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_access_token: Callable,
) -> Callable:
    """
    Creates a tool endpoint (form or JSON based on use_form flag).
    Returns an async endpoint function.
    """
    if use_form:
        return create_form_endpoint(
            params_class,
            tool_name,
            tool_instance,
            verify_access_token,
        )
    return create_json_endpoint(
        params_class,
        tool_name,
        tool_instance,
        verify_access_token,
    )
