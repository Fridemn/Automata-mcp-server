from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(slots=True)
class ExecutionContext:
    """Request-scoped execution context for a single tool invocation."""

    task_id: str
    user_id: str
    account_id: str
    platform: str
    action: str
    session_id: str | None = None
    cdp_url: str | None = None
    timeout: int = 120
    retry: int = 0


_current_execution_context: ContextVar[ExecutionContext | None] = ContextVar(
    "current_execution_context",
    default=None,
)


def set_execution_context(context: ExecutionContext) -> Token[ExecutionContext | None]:
    return _current_execution_context.set(context)


def reset_execution_context(token: Token[ExecutionContext | None]) -> None:
    _current_execution_context.reset(token)


def get_execution_context() -> ExecutionContext | None:
    return _current_execution_context.get()
