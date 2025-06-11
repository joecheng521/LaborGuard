import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    # RAG 配置
    RAG = {
        "top_k": int(os.getenv("RAG_TOP_K", 20)),
        "rerank_top_n": int(os.getenv("RAG_RERANK_TOP_N", 20)),
        "rerank_min_score": float(os.getenv("RAG_RERANK_MIN_SCORE", 0.5)),
        "llm_temperature": float(os.getenv("LLM_TEMPERATURE", 0.7)),
        "llm_top_p": float(os.getenv("LLM_TOP_P", 0.9))
    }

    # 百度API配置
    BAIDU_API = {
        "api_key": os.getenv("BAIDU_API_KEY"),
        "embedding_model": os.getenv("BAIDU_EMBEDDING_MODEL", "bge-large-zh"),
        "rerank_model": os.getenv("BAIDU_RERANK_MODEL", "bce_reranker_base")
    }

    # 智谱API配置
    ZHIPU_API = {
        "api_key": os.getenv("ZHIPU_API_KEY"),
        "llm_model": os.getenv("ZHIPU_LLM_MODEL", "glm-z1-airx")
    }

    # DashScope API配置
    DASHSCOPE_API = {
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
        "embedding_model": os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v1"),
        "rerank_model": os.getenv("DASHSCOPE_RERANK_MODEL", "gte-rerank"),
        "llm_model": os.getenv("DASHSCOPE_LLM_MODEL", "qwen-plus")
    }

    # DeepSeek API配置
    DEEPSEEK_API = {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "llm_model": os.getenv("DEEPSEEK_LLM_MODEL", "deepseek-chat")
    }