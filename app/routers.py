from fastapi import APIRouter, Depends, Header, HTTPException


def create_router(authenticate_func, tools_count_func):
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
        # For now, manually list - this should be dynamic based on registered tools
        tools_info.append(
            {
                "name": "fetch",
                "description": "Fetches a URL from the internet",
            },
        )
        tools_info.append(
            {
                "name": "polish",
                "description": "Polishes text based on a prompt",
            },
        )
        return {"tools": tools_info}

    return router
