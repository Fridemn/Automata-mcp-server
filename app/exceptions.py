"""
自定义异常类和异常处理工具
"""

from typing import Any, Dict, Optional

from loguru import logger


class AutomataError(Exception):
    """Automata MCP Server 基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式，用于日志和响应"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ToolError(AutomataError):
    """工具相关错误"""


class ToolLoadError(ToolError):
    """工具加载错误"""


class ToolExecutionError(ToolError):
    """工具执行错误"""


class DependencyError(AutomataError):
    """依赖相关错误"""


class DependencyInstallError(DependencyError):
    """依赖安装错误"""


class ConfigurationError(AutomataError):
    """配置相关错误"""


class ValidationError(AutomataError):
    """验证相关错误"""


class ExternalServiceError(AutomataError):
    """外部服务错误"""


class NetworkError(ExternalServiceError):
    """网络相关错误"""


class APIError(ExternalServiceError):
    """API 调用错误"""


def handle_exception(
    exc: Exception,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    统一异常处理函数

    Args:
        exc: 异常对象
        context: 额外的上下文信息

    Returns:
        标准化的错误信息字典
    """
    context = context or {}

    if isinstance(exc, AutomataError):
        error_info = exc.to_dict()
        log_level = "WARNING" if exc.error_code.endswith("Warning") else "ERROR"
    else:
        # 处理非自定义异常
        error_info = {
            "error_code": "UnexpectedError",
            "message": str(exc),
            "details": {
                "exception_type": type(exc).__name__,
                **context,
            },
        }
        log_level = "ERROR"

    # 记录异常信息
    logger.log(
        log_level,
        f"Exception occurred: {error_info['message']}",
        extra={
            "error_code": error_info["error_code"],
            "details": error_info["details"],
            **context,
        },
    )

    return error_info


def with_exception_handling(operation_name: str, reraise: bool = True):
    """
    异常处理装饰器

    Args:
        operation_name: 操作名称，用于日志记录
        reraise: 是否重新抛出异常

    Returns:
        装饰器函数
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                context = {
                    "operation": operation_name,
                    "function": func.__name__,
                    "args": str(args) if args else None,
                    "kwargs": str(kwargs) if kwargs else None,
                }

                error_info = handle_exception(exc, context)

                if reraise:
                    # 重新抛出异常，保持原有行为
                    raise
                # 返回错误信息
                return {"error": error_info}

        return wrapper

    return decorator
