"""
=============================================================================
A3 v3 会话状态管理 —— 所有模块共享的 DEFAULTS + init/clear
=============================================================================
"""
import streamlit as st


DEFAULTS = {
    "step": 1,
    "course_name": "",
    "profile": {},
    "dialogue": [],
    "resources": None,
    "roadmap": None,
    "tutor_history": [],
    "weakness_list": [],
    "eval_report": None,
    "rag_helper": None,
    "rag_doc_count": 0,
    "step2_agent": None,
    "step2_messages": [],
    "step2_active": True,
}


def init_session(defaults: dict = None):
    """初始化 session_state：只填充缺失的 key，不覆盖已有值"""
    if defaults is None:
        defaults = DEFAULTS
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def clear_session(defaults: dict = None):
    """清空 session_state 并重新初始化"""
    if defaults is None:
        defaults = DEFAULTS
    for k in list(st.session_state.keys()):
        if not k.startswith("_"):
            del st.session_state[k]
    for k, v in defaults.items():
        st.session_state[k] = v
