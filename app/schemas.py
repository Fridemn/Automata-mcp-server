from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Base response model for all tool endpoints."""

    success: bool = True
    data: T | None = None
    error: str | None = None

    class Config:
        json_schema_extra: ClassVar[dict] = {
            "example": {
                "success": True,
                "data": {},
                "error": None,
            },
        }


class TaskMeta(BaseModel):
    """Execution metadata passed from the orchestrator layer."""

    task_id: str
    user_id: str
    account_id: str
    platform: str
    action: str


class SessionMeta(BaseModel):
    """Execution session issued by Coordinator."""

    session_id: str
    cdp_url: str


class ExecutionOptions(BaseModel):
    """Execution controls for a single tool invocation."""

    timeout: int = Field(default=120, ge=1)
    retry: int = Field(default=0, ge=0)


class ToolExecutionRequest(BaseModel):
    """Standard execution envelope for request-scoped tool execution."""

    task: TaskMeta
    session: SessionMeta | None = None
    payload: dict
    options: ExecutionOptions = Field(default_factory=ExecutionOptions)
