from fastapi import APIRouter, Depends, Header, HTTPException


def create_router(authenticate_func, tools_count_func, tools_dict):
    router = APIRouter()

    def verify_api_key(api_key: str | None = Header(None, alias="X-API-Key")):
        """Dependency to verify API key."""
        if not authenticate_func(api_key or ""):
            raise HTTPException(status_code=401, detail="Invalid API key")
        return api_key

    @router.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "Automata MCP Server is running",
            "version": "1.0.0",
            "tools_count": tools_count_func(),
        }

    @router.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    @router.get("/tools")
    async def list_registered_tools(_api_key: str = Depends(verify_api_key)):
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
            except Exception:
                # Log error if needed, but for now skip
                pass
        return {"tools": tools_info}

    return router
