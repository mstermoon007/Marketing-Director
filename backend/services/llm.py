"""
LLM 调用封装层
参考开发思路文档：第5.4节

封装两款模型：
- DeepSeek V3（文本主模型）→ 诊断、执行引擎、复盘报告
- GPT-4o（多模态）→ 截图数据解析

设计原则：统一接口，支持 json_mode 结构化输出。
"""

import base64
import json
import logging
from typing import Any, Optional


try:
    from openai import AsyncOpenAI as _AsyncOpenAI
except ModuleNotFoundError:  # pragma: no cover - exercised when optional dependency is absent
    _AsyncOpenAI = None

from backend.config.settings import llm_config


logger = logging.getLogger(__name__)


class _MissingOpenAIClient:
    """Fallback client used when the optional OpenAI SDK is not installed."""

    def __init__(self, *args: Any, **kwargs: Any):
        raise RuntimeError(
            "OpenAI SDK is not installed. Install the 'openai' package to use LLM features."
        )


AsyncOpenAI = _AsyncOpenAI or _MissingOpenAIClient


class LLMProvider:
    """
    LLM 调用统一封装

    参考文档 5.1 技术选型：
    - 文本：DeepSeek V3（中文强，成本低）
    - 多模态：GPT-4o（截图解析）
    """

    def __init__(self):
        # 使用懒加载：不在 __init__ 中创建客户端，避免无 API Key 时崩溃
        self._text_client = None
        self._vision_client = None

    @property
    def text_client(self):
        """懒加载文本客户端"""
        if self._text_client is None:
            api_key = llm_config.text_api_key
            if not api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY 未设置。请在 .env 文件中配置 DEEPSEEK_API_KEY。"
                )
            self._text_client = AsyncOpenAI(
                api_key=api_key,
                base_url=llm_config.text_api_base,
                timeout=llm_config.request_timeout,
            )
        return self._text_client

    @property
    def vision_client(self):
        """懒加载多模态客户端"""
        if self._vision_client is None:
            api_key = llm_config.vision_api_key or llm_config.text_api_key
            self._vision_client = AsyncOpenAI(
                api_key=api_key,
                base_url=llm_config.vision_api_base or llm_config.text_api_base,
                timeout=llm_config.request_timeout,
            )
        return self._vision_client

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        json_mode: bool = False,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        文本对话调用

        Args:
            system_prompt: 系统提示
            user_message: 用户消息
            json_mode: 是否要求结构化JSON输出
            model: 覆盖默认模型
            temperature: 覆盖默认温度

        Returns:
            模型响应文本
        """
        model = model or llm_config.text_model
        temperature = temperature or llm_config.temperature

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        logger.info(
            "LLM chat | model=%s | json_mode=%s | prompt_len=%d",
            model, json_mode, len(user_message)
        )

        response = await self.text_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=llm_config.max_tokens,
        )

        content = response.choices[0].message.content or ""
        logger.info("LLM chat done | response_len=%d | tokens=%d",
                     len(content),
                     response.usage.total_tokens if response.usage else 0)

        # 如果要求 JSON 模式，尝试解析并重新格式化
        if json_mode:
            content = self._extract_json(content)

        return content

    async def chat_with_images(
        self,
        system_prompt: str,
        image_paths: list[str],
        model: Optional[str] = None,
    ) -> str:
        """
        多模态对话调用（用于截图解析）

        Args:
            system_prompt: 系统提示
            image_paths: 图片文件路径列表
            model: 覆盖默认模型

        Returns:
            模型响应文本
        """
        model = model or llm_config.vision_model

        # 构建多模态消息内容
        content_parts = [{"type": "text", "text": system_prompt}]

        for img_path in image_paths:
            base64_image = self._encode_image(img_path)
            if base64_image:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "high"
                    }
                })

        messages = [{"role": "user", "content": content_parts}]

        logger.info(
            "LLM vision | model=%s | images=%d",
            model, len(image_paths)
        )

        response = await self.vision_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=llm_config.max_tokens,
        )

        content = response.choices[0].message.content or ""
        logger.info("LLM vision done | response_len=%d", len(content))

        return content

    @staticmethod
    def _extract_json(text: str) -> str:
        """从 LLM 响应中提取 JSON"""
        text = text.strip()

        # 尝试移除 markdown 代码块
        if text.startswith("```"):
            lines = text.split("\n")
            # 移除首行 ```json 和末行 ```
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1])
            text = text.strip()

        # 验证是否为合法 JSON
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON 对象
            for start_char, end_char in [("{", "}"), ("[", "]")]:
                try:
                    start = text.index(start_char)
                    end = text.rindex(end_char) + 1
                    extracted = text[start:end]
                    json.loads(extracted)
                    return extracted
                except (ValueError, json.JSONDecodeError):
                    continue

        logger.warning("Failed to extract valid JSON, returning raw text")
        return text

    @staticmethod
    def _encode_image(image_path: str) -> Optional[str]:
        """将图片编码为 base64"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error("Failed to encode image %s: %s", image_path, e)
            return None


# 全局单例
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """获取 LLMProvider 单例"""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider()
    return _llm_provider
