import importlib
import os
import pkgutil
from typing import Sequence, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from dotenv import load_dotenv

from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from .base_tool import BaseMCPTool


class MCPRequest(BaseModel):
    method: str
    params: Optional[dict] = None
    id: Optional[str] = None


class MCPResponse(BaseModel):
    jsonrpc: str = '2.0'
    result: Optional[dict] = None
    error: Optional[dict] = None
    id: Optional[str] = None


class AutomataMCPServer:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        self.app = FastAPI(
            title='Automata MCP Server',
            description='A centralized MCP server using FastAPI with plugin architecture',
            version='1.0.0'
        )
        self.tools = {}
        self.api_key = os.getenv('AUTOMATA_API_KEY')  # 从环境变量获取API key
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = int(os.getenv('PORT', '8000'))
        self.discover_tools()
        self.setup_routes()

    def discover_tools(self):
        '''Automatically discover tools in the src directory.'''
        tools_dir = os.path.join(os.path.dirname(__file__), 'src')

        # Iterate through Python packages in src directory
        for importer, modname, ispkg in pkgutil.iter_modules([tools_dir]):
            if ispkg:  # Only import packages, not files
                try:
                    # Import the module
                    module = importlib.import_module(f'app.src.{modname}')
                    # Get the tool class (assume it's named <Modname>Tool)
                    tool_class_name = f'{modname.capitalize()}Tool'
                    tool_class = getattr(module, tool_class_name)
                    # Instantiate the tool
                    tool_instance = tool_class()
                    # Register the tool
                    self.tools[modname] = tool_instance
                    print(f'Tool {modname} discovered and registered successfully')
                except (ImportError, AttributeError) as e:
                    print(f'Failed to load tool {modname}: {e}')

    def authenticate(self, api_key: str) -> bool:
        '''Authenticate using API key.'''
        if not self.api_key:
            return True  # No API key required if not set
        return api_key == self.api_key

    async def list_tools(self) -> list[Tool]:
        '''List all available tools.'''
        tools = []
        for tool_name, tool_instance in self.tools.items():
            tools.extend(await tool_instance.list_tools())
        return tools

    async def call_tool(self, name: str, arguments: dict) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        '''Call a tool by name.'''
        for tool_instance in self.tools.values():
            if name in [tool.name for tool in await tool_instance.list_tools()]:
                return await tool_instance.call_tool(name, arguments)
        raise ValueError(f'Tool \'{name}\' not found')

    def setup_routes(self):
        '''Setup FastAPI routes.'''

        async def verify_api_key(x_api_key: Optional[str] = Header(None, alias='X-API-Key')):
            '''Dependency to verify API key.'''
            if not self.authenticate(x_api_key or ''):
                raise HTTPException(status_code=401, detail='Invalid API key')
            return x_api_key

        @self.app.get('/')
        async def root():
            '''Root endpoint.'''
            return {
                'message': 'Automata MCP Server is running',
                'version': '1.0.0',
                'tools_count': len(self.tools)
            }

        @self.app.get('/health')
        async def health():
            '''Health check endpoint.'''
            return {'status': 'healthy'}

        @self.app.post('/mcp')
        async def handle_mcp_request(
            request: MCPRequest,
            api_key: str = Depends(verify_api_key)
        ):
            '''Handle MCP requests over HTTP.'''
            try:
                if request.method == 'tools/list':
                    tools = await self.list_tools()
                    result = {
                        'tools': [
                            {
                                'name': tool.name,
                                'description': tool.description,
                                'inputSchema': tool.inputSchema
                            }
                            for tool in tools
                        ]
                    }
                    return MCPResponse(result=result, id=request.id)

                elif request.method == 'tools/call':
                    if not request.params or 'name' not in request.params:
                        return MCPResponse(
                            error={'code': -32602, 'message': 'Invalid params'},
                            id=request.id
                        )

                    name = request.params['name']
                    arguments = request.params.get('arguments', {})

                    try:
                        content = await self.call_tool(name, arguments)
                        result = {
                            'content': [
                                {'type': item.type, 'text': item.text}
                                for item in content
                                if isinstance(item, TextContent)
                            ]
                        }
                        return MCPResponse(result=result, id=request.id)
                    except Exception as e:
                        return MCPResponse(
                            error={'code': -32603, 'message': str(e)},
                            id=request.id
                        )

                else:
                    return MCPResponse(
                        error={'code': -32601, 'message': f'Method \'{request.method}\' not found'},
                        id=request.id
                    )

            except Exception as e:
                return MCPResponse(
                    error={'code': -32603, 'message': f'Internal error: {str(e)}'},
                    id=request.id
                )

        @self.app.get('/tools')
        async def list_registered_tools(api_key: str = Depends(verify_api_key)):
            '''List all registered tools (for debugging).'''
            tools = await self.list_tools()
            return {
                'tools': [
                    {
                        'name': tool.name,
                        'description': tool.description
                    }
                    for tool in tools
                ]
            }


def create_app() -> FastAPI:
    '''Create and return the FastAPI application.'''
    server = AutomataMCPServer()
    return server.app


def main():
    '''Main entry point for the Automata MCP Server.'''
    import uvicorn
    app = create_app()
    uvicorn.run(app, host='0.0.0.0', port=8000)


if __name__ == '__main__':
    main()
