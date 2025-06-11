# -*- coding: utf-8 -*-
import json
import os
from typing import List, Dict, Any, Sequence, Optional

import requests
from llama_index.core.base.llms.types import CompletionResponse, ChatResponse, ChatMessage, CompletionResponseAsyncGen, \
    ChatResponseAsyncGen, CompletionResponseGen, ChatResponseGen, LLMMetadata, MessageRole
from llama_index.core.base.query_pipeline.query import CustomQueryComponent
from llama_index.core.llms import LLM

from common.constants import CONFIG_DASHSCOPE_API
from common.log import get_logger

logger = get_logger()


class QwenAILLM(LLM):
    """自定义通义千问(Qwen)的 LLM 模型"""

    def __init__(
            self,
            api_key: Optional[str] = None,
            model: str = "qwen-plus",  # 默认模型
            temperature: float = 0.3,  # 法律场景建议低随机性
            top_p: float = 0.9,
            base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
            **kwargs
    ):
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or CONFIG_DASHSCOPE_API.get("api_key")
        if not self._api_key:
            logger.critical("请配置通义千问 API_KEY！可以通过环境变量DASHSCOPE_API_KEY或配置文件设置")
            exit(1)
        self._model = model
        self._temperature = temperature
        self._top_p = top_p
        self._base_url = base_url
        logger.info(f"使用通义千问 {self._model} 模型作为 LLM 大语言模型")

    def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """调用通义千问API核心方法"""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable" if kwargs.get("stream", False) else "disable"
        }
        data = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self._temperature),
            "top_p": kwargs.get("top_p", self._top_p),
            **kwargs
        }
        try:
            logger.debug(f"请求通义千问 LLM 大语言模型[{self._model}]：\nurl: {url}\nheaders: {headers}\ndata: {data}")
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            logger.debug(f"response：\n{response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"通义千问 LLM 大语言模型[{self._model}]：API request failed: {str(e)}")
            return {}
        except json.JSONDecodeError:
            logger.error(f"通义千问 LLM 大语言模型[{self._model}]：Failed to parse API response")
        return {}

    # --------- 必须实现的抽象方法 ---------
    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            model_name=self._model,
            is_chat_model=True,
            context_window=32768  # qwen-plus支持32k上下文
        )

    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        messages = [{"role": "user", "content": prompt}]
        response = self._call_api(messages, **kwargs)
        return CompletionResponse(text=response["choices"][0]["message"]["content"])

    async def acomplete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        return self.complete(prompt, **kwargs)

    def stream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponseGen:
        messages = [{"role": "user", "content": prompt}]
        response = self._call_api(messages, stream=True, **kwargs)
        for chunk in response.iter_lines():
            if chunk:
                data = json.loads(chunk.decode("utf-8"))
                yield CompletionResponse(text=data["choices"][0]["delta"]["content"])

    async def astream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponseAsyncGen:
        # 实现异步流式补全
        raise NotImplementedError("通义千问当前版本异步流式补全待实现")

    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        chat_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        response = self._call_api(chat_messages, **kwargs)
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=response["choices"][0]["message"]["content"]
            )
        )

    async def achat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        return self.chat(messages, **kwargs)

    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        chat_messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
        response = self._call_api(chat_messages, stream=True, **kwargs)
        for chunk in response.iter_lines():
            if chunk:
                data = json.loads(chunk.decode("utf-8"))
                yield ChatResponse(
                    message=ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=data["choices"][0]["delta"]["content"]
                    )
                )

    async def astream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseAsyncGen:
        # 实现异步流式对话
        raise NotImplementedError("通义千问当前版本异步流式对话待实现")

    def _as_query_component(self, **kwargs: Any) -> "QueryComponent":
        return CustomQueryComponent(**kwargs)


if __name__ == '__main__':
    qwen = QwenAILLM()
    # 测试complete方法
    completion = qwen.complete("请解释合同法第52条")
    print(f"Completion:\n{completion.text}")

    # 测试chat方法
    messages = [
        ChatMessage(role=MessageRole.USER, content="什么是不可抗力？"),
        ChatMessage(role=MessageRole.ASSISTANT, content="不可抗力是指不能预见、不能避免且不能克服的客观情况。"),
        ChatMessage(role=MessageRole.USER, content="在合同法中如何应用？")
    ]
    chat_response = qwen.chat(messages)
    print(f"Chat:\n{chat_response.message.content}")

    # 测试流式输出
    print("Streaming completion:")
    for chunk in qwen.stream_complete("请用50字介绍杭州"):
        print(chunk.text, end="", flush=True)