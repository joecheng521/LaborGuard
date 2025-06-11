import json
import requests
from typing import List, Optional
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.bridge.pydantic import PrivateAttr
from common.constants import CONFIG_DASHSCOPE_API
from common.log import get_logger

logger = get_logger()


class DashScopeEmbedding(BaseEmbedding):
    """DashScope Embedding 模型（兼容 LlamaIndex）"""

    _api_key: str = PrivateAttr()
    _model: str = PrivateAttr()
    _embed_batch_size: int = PrivateAttr()

    def __init__(
            self,
            api_key: str,
            model: str = "text-embedding-v2",
            embed_batch_size: int = 10,
            ** kwargs
    ):
        super().__init__(**kwargs)
        self._api_key = api_key
        if not self._api_key:
            logger.critical("请先填写阿里云百炼 API_KEY！")
            exit(1)
        self._model = model
        self._embed_batch_size = embed_batch_size
        logger.info(f"使用阿里云百炼 {self._model} 模型作为 embedding 嵌入模型")

    def _get_embedding(self, text: str) -> List[float]:
        if not text:
            logger.error("请输入需要向量化的文本")
            return []

        url = "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"

        payload = {
            "model": self._model,
            "input": {
                "texts": [text]
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._api_key}'
        }

        try:
            logger.debug(f"请求阿里云百炼 embedding 嵌入模型[{self._model}]")
            response = requests.post(
                url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            response_data = response.json()
            logger.debug(f"响应数据：{response_data}")

            if 'output' in response_data and 'embeddings' in response_data['output']:
                return response_data['output']['embeddings'][0]['embedding']

            logger.error(f"响应数据格式异常：{response_data}")
            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"错误详情：{e.response.text}")
            return []
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析API响应失败: {str(e)}")
            return []

    # --------- 必须实现的抽象方法 ---------
    def _get_text_embedding(self, text: str) -> List[float]:
        """文本嵌入（用于文档内容）"""
        return self._get_embedding(text)

    def _get_query_embedding(self, query: str) -> List[float]:
        """查询嵌入（用于查询语句）"""
        return self._get_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        """异步文本嵌入"""
        return self._get_embedding(text)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        """异步查询嵌入"""
        return self._get_embedding(query)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量文本嵌入"""
        return [self._get_embedding(text) for text in texts]

    @classmethod
    def class_name(cls) -> str:
        return "DashScopeEmbedding"


if __name__ == '__main__':
    embedding_model = DashScopeEmbedding(
        api_key=CONFIG_DASHSCOPE_API['api_key'],
        model="text-embedding-v2"
    )
    test_embedding = embedding_model.get_text_embedding("测试文本")
    print(f"Embedding维度验证：{len(test_embedding)}")