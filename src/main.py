# -*- coding: utf-8 -*-#
import re
import streamlit as st

from common.log import set_default_logger_name, get_logger
from msg.msg import Msg

set_default_logger_name("law_assistant")
from ragflow.ragflow import RagFlow

logger = get_logger()


def disable_streamlit_watcher():
    """禁用 Streamlit 文件热重载"""

    def _on_script_changed(_):
        return

    # 确保在 Streamlit 运行时初始化后调用
    if hasattr(st, 'runtime') and hasattr(st.runtime, 'get_instance'):
        st.runtime.get_instance()._on_script_changed = _on_script_changed


def set_streamlit_config():
    """配置 Streamlit"""
    st.title("⚖️ 智能劳动法咨询助手")
    st.markdown("欢迎使用劳动法智能咨询系统～请输入您的问题，我们将基于最新劳动法律法规为您解答。")
    # 初始化会话状态
    if "history" not in st.session_state:
        st.session_state.history = []


def show_reference(nodes):
    """展示参考依据"""
    if not nodes:
        return
    with st.expander("查看法律依据"):
        for idx, node in enumerate(nodes, 1):
            meta = node.node.metadata
            st.markdown(f"**[{idx}] {meta['full_title']}**")
            st.caption(f"来源文件：{meta['source_file']} | 法律名称：{meta['law_name']}")
            st.markdown(f"相关度：`{node.score:.4f}`")
            st.info(f"{node.node.text}")


def show_think(title, think_text):
    """展示思维过程"""
    if not think_text:
        return
    with st.expander(title):
        think_contents = ""
        for think_content in think_text:
            formatted_content = think_content.strip().replace("\n", "<br/>")
            item = f'<span style="color: #808080">{formatted_content}</span>'
            think_contents += item

        st.markdown(think_contents, unsafe_allow_html=True)


def show_chat_content(msg: Msg, show_log: bool = True):
    """展示聊天内容"""
    with st.chat_message(msg.role):
        st.markdown(msg.reply_text if msg.reply_text else msg.content)
    if show_log and msg.role == "user":
        logger.info(f"用户提问：{msg.content}")
    if msg.role == "assistant":
        if show_log:
            logger.info(f"助手回复：{msg.reply_text if msg.reply_text else msg.content}")
        # 展示思维过程
        show_think(title="📝 模型思考过程（点击展开）", think_text=msg.think_text)
        # 展示参考依据
        show_reference(msg.reference_nodes)


def init_chat_interface():
    """初始化聊天界面"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        show_chat_content(msg, show_log=False)


def add_msg_to_history(msg: Msg):
    """添加会话消息到历史"""
    st.session_state.messages.append(msg)


def handle_msg(msg: Msg):
    """处理消息"""
    # 展示聊天内容
    show_chat_content(msg)
    # 添加消息到历史
    add_msg_to_history(msg)


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

    # 调试信息（实际使用时可以去掉）
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

def run():
    disable_streamlit_watcher()
    set_streamlit_config()
    init_chat_interface()

    logger.debug(f"历史消息: {st.session_state.messages}")
    with st.spinner("正在构建知识库..."):
        ragflow = RagFlow()

    if question := st.chat_input("请输入劳动法相关问题"):
        question = question.strip()
        # 处理用户问题
        handle_msg(Msg(role="user", content=question))

        # 获取回复
        assistant_msg = Msg(
            role="assistant",
            content="对不起，我暂时无法回答劳动法之外的问题哦～"
        )
        if is_legal_question(question):
            # RAG流程获取回复内容
            with st.spinner("正在分析问题，请稍等..."):
                assistant_msg.content, assistant_msg.reference_nodes = ragflow.answer(question)
                assistant_msg.reply_text = re.sub(r'<think>.*?</think>', '', assistant_msg.content,
                                                  flags=re.DOTALL).strip()
                assistant_msg.think_text = re.findall(r'<think>(.*?)</think>', assistant_msg.content, re.DOTALL)
        handle_msg(assistant_msg)

    logger.info("=" * 50)


if __name__ == '__main__':
    run()
