# -*- coding: utf-8 -*-#
from pathlib import Path

from config.config import Config

# log level
CRITICAL = 50
FATAL = CRITICAL
ERROR = 40
WARNING = 30
WARN = WARNING
INFO = 20
DEBUG = 10
NOTSET = 0

LOG_LEVEL = INFO
LOG_ENABLE_FILE_LOG = True  # 是否启用文件日志
LOG_CONSOLE_ONLY = False  # 是否只打印到控制台（优先于 LOG_ENABLE_FILE_LOG）

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 数据目录路径
DATA_DIR = PROJECT_ROOT / 'data'
STORAGE_DIR = DATA_DIR / 'storage'
CHROMA_DB_DIR = STORAGE_DIR / 'chroma_db'
CHROMA_DB_COLLECTION_NAME = 'chinese_labor_laws'



CONFIG_BAIDU_API = Config.BAIDU_API
CONFIG_ZHIPU_API = Config.ZHIPU_API
CONFIG_RAG = Config.RAG

CONFIG_DASHSCOPE_API = Config.DASHSCOPE_API
CONFIG_DEEPSEEK_API = Config.DEEPSEEK_API

CONFIG_LOCAL_MODEL_CONFIG = Config.LOCAL_MODEL_CONFIG