# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automata MCP Server is a plugin-based Model Context Protocol server built on FastAPI. Tools are auto-discovered from directories using convention-over-configuration. The project and its documentation are primarily in Chinese.

## Commands

- **Run dev server**: `uv run main.py` (hot reload enabled, watches `app/` directory)
- **Run production**: `uvicorn app.server:create_app --host $HOST --port $PORT --factory`
- **Install deps**: `uv sync`
- **Lint/format**: `ruff check --fix .` and `ruff format .` (also via pre-commit)
- **Setup pre-commit**: `pre-commit install`

No test framework is configured.

## Architecture

### Entry Point Chain

`main.py` (logging + .env setup) → `app.main()` → `uvicorn.run("app.server:create_app", factory=True)` → `AutomataMCPServer.__init__()` does all setup in one pass.

### Plugin System

Tools are auto-discovered from two directories scanned at startup:
- `app/src/` — core tools (configurable via `TOOLS_DIR` env var)
- `app/AutoUp-MCP-Extension/` — extension tools (social media publishing, TTS, image generation, etc.)

**Naming convention is strictly enforced:**
- Directory: `snake_case` (e.g. `text_polish`)
- Tool file: `{name}_tool.py` (e.g. `text_polish_tool.py`)
- Class: `{PascalCase}Tool` (e.g. `TextPolishTool`)
- Must inherit `BaseMCPTool` from `app/base_tool.py`

**Discovery flow** (`app/server.py`):
1. `install_dependencies_for_enabled_tools()` — reads `packages` from each tool's `config.yaml`, runs `uv pip install`
2. `discover_tools()` — imports modules via `importlib.import_module()`, validates class inheritance, instantiates
3. `register_tool_routes()` — calls each tool's `get_route_config()`, creates FastAPI POST endpoints

### BaseMCPTool (app/base_tool.py)

All tools must implement three abstract methods:
- `list_tools()` → returns MCP `Tool` definitions
- `call_tool(name, arguments)` → executes tool logic, returns `Sequence[TextContent | ImageContent | EmbeddedResource]`
- `get_route_config()` → returns list of dicts with `endpoint`, `params_class`, `use_form`, `tool_name`

Optional: `get_router()` to provide a full `APIRouter`, and `get_response_model()` for custom response schemas.

### Route Types (app/routers.py)

- **JSON endpoints** (`use_form=False`): Pydantic model from JSON body
- **Form endpoints** (`use_form=True`): Form fields with `UploadFile` support

All endpoints use Bearer token auth via `AUTOMATA_ACCESS_TOKEN`.

### Key Files

| File | Purpose |
|---|---|
| `app/server.py` | Core `AutomataMCPServer` class, tool discovery, route registration, middleware |
| `app/base_tool.py` | `BaseMCPTool` abstract base class all tools inherit from |
| `app/routers.py` | Route creation helpers, JSON and form endpoint factories |
| `app/schemas.py` | `BaseResponse` Pydantic model |
| `app/exceptions.py` | Exception hierarchy (`AutomataError` → `ToolError`, `ConfigurationError`, etc.) + `with_exception_handling` decorator |
| `app/llm/client.py` | OpenAI-compatible LLM client wrapper |
| `app/extension_config/config_manager.py` | YAML-based config with auto-sync to `config/config.json` |
| `app/log_viewer.py` | WebSocket live log viewer at `/api/logs` |

### Authentication

Bearer token via `AUTOMATA_ACCESS_TOKEN`. Public (no auth): `/docs`, `/redoc`, `/openapi.json`, `/health`, `/static`. Uses `hmac.compare_digest()` for constant-time comparison.

### Extension Config

Each tool can define `config_requirements` in its `config.yaml`. `ExtensionConfigManager` auto-creates missing entries in `config/config.json`. Tools access config via `self.config_manager.get_extension_config(modname)`.

## Environment Variables

Required: `HOST`, `PORT`, `ALLOWED_ORIGINS`, `ALLOWED_METHODS`
Important: `AUTOMATA_ACCESS_TOKEN` (warns if missing), `DEBUG=true` (verbose errors)
Tool-specific: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `JIMENG_AK/SK`

## Key Dependencies

- `fastapi` + `uvicorn` — web framework
- `mcp` + `fastapi-mcp` — MCP SDK and FastAPI bridge (provides `/sse` endpoint)
- `playwright` + `playwright-stealth` — browser automation for social media publishing tools
- `edge-tts` (pinned to 7.0.0) — Microsoft TTS
- `loguru` — structured logging with WebSocket broadcast
- `pyyaml` — tool config files
