import os
from typing import List, Dict, Optional
from openai import AsyncOpenAI
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR


class LLMClient:
    """通用LLM客户端，支持OpenAI兼容的API"""

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None

    async def _get_client(self, base_url: Optional[str] = None) -> AsyncOpenAI:
        """获取或创建OpenAI客户端"""
        if self.client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise McpError(
                    ErrorData(
                        code=INTERNAL_ERROR,
                        message="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.",
                    )
                )

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            self.client = AsyncOpenAI(**client_kwargs)

        return self.client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 2000,
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
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL") or None

        try:
            client = await self._get_client(base_url)
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
