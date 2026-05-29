"""
=============================================================================
A3 v3 共享层 —— 所有模块的单一依赖源
=============================================================================
"""
from shared.agents import create_agents, run_with_fallback, stream_chat, StudyAgents
from shared.config import PROFILE_DIMENSIONS, COURSES, SPARK_CONFIG, DEEPSEEK_CONFIG
from shared.session_state import DEFAULTS, init_session, clear_session
from shared.dialogue_resource_agent import create_dialogue_agent
from shared.rag_helper import RAGHelper
