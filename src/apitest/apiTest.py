# test_law_assistant.py
import sys
import pytest
from pathlib import Path

# 获取当前文件的绝对路径，并向上追溯两级到项目根目录（LaborGuard）
project_root = Path(__file__).resolve().parents[1]  # F:\QIQI\LaborGuard
sys.path.append(str(project_root))
from fastapi.testclient import TestClient
from api.api import app  # 假设您的API代码保存在main.py中
from pydantic import BaseModel
from typing import List, Optional


# 定义测试用的模型（与API中的一致）
class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class ReferenceNode(BaseModel):
    title: str
    source_file: str
    law_name: str
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    reply_text: str
    is_legal: bool
    references: List[ReferenceNode] = []
    thoughts: List[str] = []
    conversation_id: Optional[str] = None


# 创建测试客户端
@pytest.fixture
def client():
    return TestClient(app)


# 测试健康检查端点
def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "劳动法咨询助手服务运行正常"}


# 测试空问题
def test_empty_question(client):
    response = client.post("/api/chat", json={"question": ""})
    assert response.status_code == 400
    assert "问题不能为空" in response.json()["detail"]


# 测试非劳动法问题
def test_non_legal_question(client):
    test_question = "今天天气怎么样？"
    response = client.post("/api/chat", json={"question": test_question})
    assert response.status_code == 200

    # 验证响应模型
    chat_response = ChatResponse(**response.json())
    assert chat_response.is_legal is False
    assert chat_response.reply_text == "对不起，我暂时无法回答劳动法之外的问题哦～"
    assert len(chat_response.references) == 0


# 测试简单劳动法问题
def test_simple_legal_question(client):
    test_question = "劳动合同应该包含哪些内容？"
    response = client.post("/api/chat", json={"question": test_question})
    assert response.status_code == 200

    # 验证响应模型
    chat_response = ChatResponse(**response.json())
    assert chat_response.is_legal is True
    assert len(chat_response.reply_text) > 0
    assert "劳动合同" in chat_response.reply_text

    # 如果有参考内容，验证参考节点
    if chat_response.references:
        for ref in chat_response.references:
            assert ref.title
            assert ref.law_name
            assert ref.score > 0


# 测试带会话ID的多轮对话
def test_conversation_with_id(client):
    # 第一轮对话
    first_question = "加班工资怎么计算？"
    first_response = client.post("/api/chat", json={
        "question": first_question,
        "conversation_id": "test_conv_123"
    })
    assert first_response.status_code == 200

    first_chat_response = ChatResponse(**first_response.json())
    assert first_chat_response.conversation_id == "test_conv_123"
    assert first_chat_response.is_legal is True
    assert "加班" in first_chat_response.reply_text

    # 第二轮对话（引用同一会话ID）
    second_question = "周末加班也一样吗？"
    second_response = client.post("/api/chat", json={
        "question": second_question,
        "conversation_id": "test_conv_123"
    })
    assert second_response.status_code == 200

    second_chat_response = ChatResponse(**second_response.json())
    assert second_chat_response.conversation_id == "test_conv_123"
    assert "周末" in second_chat_response.reply_text


# 测试复杂劳动法问题
@pytest.mark.parametrize("question", [
    "公司解除劳动合同需要支付多少经济补偿？",
    "试用期最长可以约定多久？",
    "工伤认定需要哪些材料？",
    "年假天数如何计算？"
])
def test_various_legal_questions(client, question):
    response = client.post("/api/chat", json={"question": question})
    assert response.status_code == 200

    chat_response = ChatResponse(**response.json())
    assert chat_response.is_legal is True
    assert len(chat_response.reply_text) > 0

    # 验证思维过程（如果有）
    if chat_response.thoughts:
        for thought in chat_response.thoughts:
            assert len(thought.strip()) > 0


# 测试参考文档返回
def test_reference_documents(client):
    test_question = "女职工产假有多少天？"
    response = client.post("/api/chat", json={"question": test_question})
    assert response.status_code == 200

    chat_response = ChatResponse(**response.json())
    if chat_response.references:
        for ref in chat_response.references:
            assert ref.title
            assert ref.source_file
            assert ref.law_name
            assert ref.score > 0
            assert ref.text
            assert "产假" in ref.text or "女职工" in ref.text