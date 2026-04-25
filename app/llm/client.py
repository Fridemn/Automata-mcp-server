import os
from typing import List, Dict, Optional
import httpx
from openai import AsyncOpenAI
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR

from ..exceptions import ConfigurationError


class LLMClient:
    """通用LLM客户端，支持OpenAI兼容的API"""

    def __init__(self):
        self._api_key: Optional[str] = None
        self._base_url: Optional[str] = None

    async def _create_client(self, base_url: Optional[str] = None) -> AsyncOpenAI:
        """创建新的OpenAI客户端（每次请求创建新实例避免连接复用问题）"""
        if self._api_key is None:
            self._api_key = os.getenv("OPENAI_API_KEY")
            if not self._api_key:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
                    )
                )
            self._base_url = os.getenv("OPENAI_BASE_URL") or None

        client_kwargs = {"api_key": self._api_key}
        effective_base_url = base_url or self._base_url
        if effective_base_url:
            client_kwargs["base_url"] = effective_base_url

        # Create new httpx client for each request to avoid BrokenResourceError
        # from connection reuse issues with some API providers
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0),
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
        )
        client_kwargs["http_client"] = http_client

        return AsyncOpenAI(**client_kwargs)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 6000,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """生成文本响应

        Args:
            messages: 消息列表
            model: 模型名称（如果不提供，从环境变量OPENAI_MODEL读取，默认gpt-4o-mini）
            base_url: 自定义API端点（如果不提供，从环境变量OPENAI_BASE_URL读取）
            max_tokens: 最大token数
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        # 从环境变量获取默认值
        if model is None:
            model = os.getenv("OPENAI_MODEL")
            if model is None:
                raise ConfigurationError(
                    "OPENAI_MODEL environment variable must be set",
                    details={"required_var": "OPENAI_MODEL"},
                )

        client = await self._create_client(base_url)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise McpError(
                ErrorData(
                    code=INTERNAL_ERROR, message=f"Failed to generate text: {str(e)}"
                )
            )
        finally:
            await client.close()
