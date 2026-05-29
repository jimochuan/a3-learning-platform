"""
=============================================================================
Step 2: 个性化学习资源
对话式偏好提取 + 双层资源推荐
=============================================================================
独立可运行的模块。在主 app 中使用 `render(state)` 调用；
直接运行本文件可进入 standalone 测试模式。
=============================================================================
"""
import streamlit as st
import re

from shared.dialogue_resource_agent import create_dialogue_agent


# ============================================================================
# Mock 测试数据
# ============================================================================
MOCK_DATA = {
    "course_name": "Python程序设计",
    "profile": {
        "知识基础": "入门",
        "认知风格": "视觉型 + 动手型",
        "学习目标": "通过期末项目",
        "薄弱环节": "面向对象",
        "学习节奏": "每周8小时",
        "兴趣领域": "Web开发",
    },
    "step2_agent": None,
    "step2_messages": [],
    "step2_active": True,
    "resources": None,
}


# ============================================================================
# render(state) —— 主渲染函数
# ============================================================================
def render(state):
    """渲染 Step 2 全部逻辑。

    Args:
        state: session_state 对象或兼容的 dict/object，
               需包含 course_name, profile, step2_agent,
               step2_messages, step2_active, resources 等属性。
    """
    # ---- 标题 ----
    st.markdown(
        '<p class="phase-title">Step 2: 个性化学习资源</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"📖 课程：{state.course_name} | AI 对话了解你的偏好，双层资源精准推荐"
    )

    # ---- 初始化对话智能体 ----
    if state.step2_agent is None:
        state.step2_agent = create_dialogue_agent(
            course_name=state.course_name,
            profile=state.profile,
        )
        state.step2_messages = []
        state.step2_active = True

    agent = state.step2_agent

    # ================================================================
    # 对话阶段
    # ================================================================
    if state.step2_active:
        # 首次加载，显示第一个问题
        if not state.step2_messages:
            first_q = agent.get_first_question()
            state.step2_messages.append({"role": "assistant", "content": first_q})

        # 渲染对话历史
        chat_container = st.container()
        with chat_container:
            for msg in state.step2_messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        # 用户输入
        user_input = st.chat_input(
            "在这里自然回答就可以了，比如「我喜欢看视频+动手写代码」..."
        )
        if user_input:
            state.step2_messages.append({"role": "user", "content": user_input})
            result = agent.process_input(user_input)

            if result["is_complete"]:
                # 对话完成，生成报告
                state.step2_active = False
                state.resources = agent.generate_report()
                state.step2_messages.append({
                    "role": "assistant",
                    "content": "好的，我已经了解你的学习偏好了！下面是我为你定制的双层资源推荐 👇",
                })
                st.rerun()
            else:
                # 下一问
                state.step2_messages.append({
                    "role": "assistant",
                    "content": result["next_question"],
                })
                st.rerun()

    # ================================================================
    # 报告展示阶段
    # ================================================================
    if not state.step2_active and state.resources:
        # 先回放完整对话
        with st.expander("💬 查看偏好提取对话", expanded=False):
            for msg in state.step2_messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        # 显示资源报告
        resources = state.resources
        # 给 ## 标题加 resource-section 样式
        resources = re.sub(
            r'^##\s+(.+)',
            r'<div class="resource-section"><h3>\1</h3>',
            resources,
            flags=re.MULTILINE,
        )
        parts = resources.split('<div class="resource-section">')
        result = parts[0]
        for part in parts[1:]:
            next_div = part.find('<div class="resource-section">')
            if next_div >= 0:
                result += (
                    '<div class="resource-section">'
                    + part[:next_div]
                    + '</div>'
                    + part[next_div:]
                )
            else:
                result += '<div class="resource-section">' + part + '</div>'
        st.markdown(result, unsafe_allow_html=True)

        # ---- 导航按钮 ----
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⬅ 返回修改画像", use_container_width=True):
                state._profile_complete = False
                state.resources = None
                state.step2_agent = None
                state.step2_messages = []
                state.step2_active = True
                state.step = 1
                st.rerun()
        with c2:
            if st.button("🔄 重新对话", use_container_width=True):
                state.step2_agent = None
                state.step2_messages = []
                state.step2_active = True
                state.resources = None
                st.rerun()
        with c3:
            if st.button("→ 进入路径规划", type="primary", use_container_width=True):
                state.step = 3
                st.rerun()


# ============================================================================
# 独立运行入口
# ============================================================================
if __name__ == "__main__":
    st.set_page_config(
        page_title="Step 2 资源推荐测试",
        page_icon="📚",
        layout="wide",
    )
    from shared.session_state import DEFAULTS, init_session

    init_session(DEFAULTS)

    # 注入 Mock 数据（只填充缺失的 key）
    for k, v in MOCK_DATA.items():
        if k not in st.session_state:
            st.session_state[k] = v

    render(st.session_state)
