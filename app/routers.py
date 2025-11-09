import inspect
from typing import Any, Callable

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from loguru import logger

from .base_tool import BaseMCPTool


def verify_api_key_dependency(
    authenticate_func: Callable[[str], bool],
) -> Callable:
    """
    Factory function to create a verify_api_key dependency with authentication function.
    Returns an async dependency function that verifies API key.
    """

    async def verify_api_key(
        x_api_key: str | None = Header(None, alias="X-API-Key"),
    ) -> str:
        """Dependency to verify API key."""
        if not authenticate_func(x_api_key or ""):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return x_api_key or ""

    return verify_api_key


def create_router(
        authenticate_func: Callable[[str], bool],
        tools_count_func: Callable[[], int],
        tools_dict: dict[str, BaseMCPTool]
    ) -> APIRouter:
    """
    Creates the main API router with health checks and tool management endpoints.
    Returns a configured APIRouter instance.
    """
    router = APIRouter()
    verify_api_key = verify_api_key_dependency(authenticate_func)

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
    async def list_registered_tools(_api_key: str = Depends(verify_api_key)) -> dict[str, list[dict[str, str]]]:
        """List all registered tools (for debugging)."""
        tools_info = []
        for modname, tool_instance in tools_dict.items():
            try:
                tool_list = await tool_instance.list_tools()
                for tool in tool_list:
                    tools_info.append(
                        {
                            "name": tool.name,
                            "description": tool.description,
                        }
                    )
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
        }
        validated_configs.append(normalized_config)

    return validated_configs


def create_form_endpoint(
    params_class: type,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_api_key: Callable,
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

    async def tool_endpoint(**kwargs: Any) -> dict[str, Any]:
        """Execute tool with form parameters."""
        # Separate API key from form data
        kwargs.pop("_api_key", None)
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
            content = [
                {"type": item.type, "text": item.text}
                for item in result
                if hasattr(item, "type") and hasattr(item, "text")
            ]
            return {"success": True, "data": {"content": content}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    # Set the signature on the function
    tool_endpoint.__signature__ = sig

    return tool_endpoint


def create_json_endpoint(
    params_class: type,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_api_key: Callable,
) -> Callable:
    """
    Creates a JSON data endpoint handler for a tool.
    Returns an async endpoint function.
    """

    async def tool_endpoint(
        params: params_class,  # type: ignore
        _api_key: str = Depends(verify_api_key),
    ) -> dict[str, Any]:
        """Execute tool with JSON parameters."""
        try:
            result = await tool_instance.call_tool(
                tool_name,
                params.model_dump(),
            )
            # Convert to BaseResponse format
            content = [
                {"type": item.type, "text": item.text}
                for item in result
                if hasattr(item, "type") and hasattr(item, "text")
            ]
            return {"success": True, "data": {"content": content}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    # Set the type annotation dynamically
    tool_endpoint.__annotations__["params"] = params_class
    return tool_endpoint


def create_tool_endpoint(
    params_class: type,
    use_form: bool,
    tool_name: str,
    tool_instance: BaseMCPTool,
    verify_api_key: Callable,
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
            verify_api_key,
        )
    return create_json_endpoint(
        params_class,
        tool_name,
        tool_instance,
        verify_api_key,
    )
