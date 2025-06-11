import json
import requests
from typing import List, Optional
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from pydantic import Field

from common.constants import CONFIG_DASHSCOPE_API
from common.log import get_logger

logger = get_logger()


class DashscopeRerankerPostprocessor(BaseNodePostprocessor):
    """阿里云 DashScope Rerank 模型实现（兼容 LlamaIndex）"""
    top_n: int = Field(default=10, description="返回的重排序结果数量")

    def __init__(
            self,
            api_key: str,
            top_n: int = 10,
            model: str = "gte-rerank",  # 改用已验证的模型
            ** kwargs
    ):
        super().__init__(top_n=top_n, ** kwargs)
        self._api_key = api_key
        if not self._api_key:
            logger.critical("请先填写阿里云 DashScope API_KEY！")
            exit(1)
        self._model = model
        logger.info(f"使用阿里云 DashScope {self._model} 模型作为 rerank 重排序模型")

    def _call_dashscope_rerank(self, query: str, documents: List[str]) -> List[dict]:
        """调用阿里云 DashScope Rerank API"""
        url = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"

        # 经过验证的正确参数格式
        payload = {
            "model": self._model,
            "input": {
                "query": query,
                "documents": documents
            },
            "params": {  # 注意这里使用params而不是parameters
                "top_n": min(len(documents), 20),
                "return_documents": False
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._api_key}'
        }

        try:
            logger.debug(f"请求参数：{json.dumps(payload, indent=2, ensure_ascii=False)}")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            response_data = response.json()
            logger.debug(f"响应数据：{json.dumps(response_data, indent=2, ensure_ascii=False)}")

            # 解析响应格式
            if not response_data.get('output', {}).get('results'):
                logger.error(f"无有效返回结果：{response_data}")
                return []

            return response_data['output']['results']

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"错误详情：{e.response.text}")
            return []
        except Exception as e:
            logger.error(f"处理响应时出错: {str(e)}")
            return []

    def _postprocess_nodes(self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None) -> List[
        NodeWithScore]:
        if not query_bundle or not nodes:
            return nodes[:self.top_n]

        try:
            batch_size = 20
            all_results = []

            for i in range(0, len(nodes), batch_size):
                batch_nodes = nodes[i:i + batch_size]
                batch_texts = [node.node.get_content() for node in batch_nodes]

                rerank_results = self._call_dashscope_rerank(
                    query_bundle.query_str,
                    batch_texts
                )

                # 更新分数
                for node, result in zip(batch_nodes, rerank_results):
                    node.score = float(result.get('relevance_score', 0))
                    all_results.append(node)

            # 全局排序
            all_results.sort(key=lambda x: x.score, reverse=True)
            return all_results[:self.top_n]

        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            return nodes[:self.top_n]

    @classmethod
    def class_name(cls) -> str:
        return "DashscopeRerankerPostprocessor"


if __name__ == '__main__':
    def test_rerank():
        reranker = DashscopeRerankerPostprocessor(
            api_key=CONFIG_DASHSCOPE_API['api_key'],
            model="gte-rerank",  # 使用已验证的模型
            top_n=3
        )

        test_cases = [
            {
                "query": "劳动合同解除赔偿标准",
                "documents": [
                    "劳动合同解除后，经济补偿按工作年限计算。",
                    "月工资超过本地区上年度职工月平均工资三倍的，补偿年限最高十二年。",
                    "经济补偿按N+1标准计算，其中N为工作年限。",
                    "劳动者主动辞职一般没有经济补偿。",
                    "足球比赛规则与劳动合同无关。"
                ]
            }
        ]

        for case in test_cases:
            print(f"\n查询: {case['query']}")
            print("原始文档:")
            for i, doc in enumerate(case['documents']):
                print(f"{i + 1}. {doc}")

            # 创建符合要求的节点
            nodes = [
                NodeWithScore(
                    node=TextNode(text=text),
                    score=0
                ) for text in case['documents']
            ]

            sorted_nodes = reranker._postprocess_nodes(
                nodes,
                QueryBundle(case['query'])
            )

            print("\n重排序结果:")
            for i, node in enumerate(sorted_nodes):
                print(f"{i + 1}. [分数: {node.score:.4f}] {node.node.text}")


    test_rerank()