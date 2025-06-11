# -*- coding: utf-8 -*-
import re
import sys
from pathlib import Path

# 获取当前文件的绝对路径，并向上追溯两级到项目根目录（LaborGuard）
project_root = Path(__file__).resolve().parents[1]  # F:\QIQI\LaborGuard
sys.path.append(str(project_root))

import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ragflow.ragflow import RagFlow

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("law_assistant")

# 初始化 FastAPI 应用
app = FastAPI(
    title="智能劳动法咨询助手 API",
    description="基于最新劳动法律法规的智能咨询系统",
    version="1.0.0"
)


class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None  # 可选，用于多轮对话跟踪


class ChatResponse(BaseModel):
    answer: str
    reply_text: str
    is_legal: bool
    references: List[dict] = []
    thoughts: List[str] = []
    conversation_id: Optional[str] = None


class ReferenceNode(BaseModel):
    title: str
    source_file: str
    law_name: str
    score: float
    text: str


class ThoughtProcess(BaseModel):
    steps: List[str]


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 RAG 系统"""
    global ragflow
    logger.info("正在构建知识库...")
    ragflow = RagFlow()
    logger.info("知识库构建完成")


def is_legal_question(text: str) -> bool:
    """判断问题是否属于劳动法咨询（基于分级关键词匹配分数）"""
    # 定义法律关键词分级体系（权重0.1-0.5）
    legal_keywords = {
        # 核心概念（0.5）
        "劳动法": 0.5,
        "劳动合同": 0.5,
        "劳动合同法": 0.5,
        "劳动争议": 0.5,

        # 重要权益（0.4）
        "工资": 0.4,
        "加班费": 0.4,
        "工伤": 0.4,
        "赔偿": 0.4,
        "经济补偿": 0.4,
        "解除合同": 0.4,
        "终止合同": 0.4,

        # 主体对象（0.3）
        "用人单位": 0.3,
        "劳动者": 0.3,
        "雇主": 0.3,
        "员工": 0.3,
        "职工": 0.3,

        # 社保福利（0.3）
        "社保": 0.3,
        "社会保险": 0.3,
        "公积金": 0.3,
        "五险一金": 0.3,

        # 合同条款（0.3）
        "试用期": 0.3,
        "竞业限制": 0.3,
        "保密协议": 0.3,
        "劳务派遣": 0.3,

        # 休假制度（0.2）
        "年假": 0.2,
        "产假": 0.2,
        "病假": 0.2,
        "婚假": 0.2,
        "丧假": 0.2,

        # 工作条件（0.2）
        "工作时间": 0.2,
        "休息休假": 0.2,
        "工作环境": 0.2,

        # 争议解决（0.3）
        "劳动仲裁": 0.3,
        "法院起诉": 0.3,
        "调解": 0.2
    }

    # 设置动态匹配阈值（基础0.35，每10字增加0.02）
    base_threshold = 0.35
    length_factor = min(len(text) / 10 * 0.02, 0.1)  # 最多增加0.1
    dynamic_threshold = base_threshold + length_factor

    # 计算问题匹配分数（考虑重复关键词）
    total_score = 0.0
    matched_keywords = set()

    for keyword, weight in legal_keywords.items():
        if keyword in text:
            # 避免重复计算相似关键词
            if not any(kw in matched_keywords for kw in keyword.split()):
                total_score += weight
                matched_keywords.add(keyword)

    # 根据动态阈值判断是否属于劳动法问题
    is_legal = total_score >= dynamic_threshold

    # 调试信息
    debug_info = {
        "text": text,
        "length": len(text),
        "matched_keywords": list(matched_keywords),
        "total_score": total_score,
        "dynamic_threshold": dynamic_threshold,
        "is_legal": is_legal
    }
    logger.debug(f"Legal question check: {debug_info}")

    return is_legal


def process_nodes(nodes) -> List[ReferenceNode]:
    """处理参考节点为结构化数据"""
    references = []
    if not nodes:
        return references

    for node in nodes:
        meta = node.node.metadata
        references.append(ReferenceNode(
            title=meta['full_title'],
            source_file=meta['source_file'],
            law_name=meta['law_name'],
            score=node.score,
            text=node.node.text
        ))
    return references


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    与劳动法咨询助手对话

    参数:
    - question: 用户提问
    - conversation_id: 可选，用于跟踪多轮对话

    返回:
    - 包含回答和相关信息的结构化响应
    """
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="问题不能为空")

        logger.info(f"收到问题: {question}")

        # 初始化响应
        is_legal = is_legal_question(question)
        response = ChatResponse(
            answer="对不起，我暂时无法回答劳动法之外的问题哦～",
            reply_text="对不起，我暂时无法回答劳动法之外的问题哦～",
            is_legal=is_legal,
            conversation_id=request.conversation_id
        )

        if is_legal:
            # RAG流程获取回复内容
            logger.info("正在分析法律问题...")
            answer, nodes = ragflow.answer(question)

            # 处理回复内容
            reply_text = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
            thoughts = re.findall(r'<think>(.*?)</think>', answer, re.DOTALL)

            # 更新响应
            response.answer = answer
            response.reply_text = reply_text
            response.thoughts = thoughts
            response.references = process_nodes(nodes)

        logger.info(f"返回响应: {response.dict()}")
        return response

    except Exception as e:
        logger.error(f"处理问题时出错: {str(e)}")
        raise HTTPException(status_code=500, detail="处理问题时出错")


@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "message": "劳动法咨询助手服务运行正常"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)