"""
=============================================================================
Step 3: 学习路径规划 —— 精简5-8步，优化界面
=============================================================================
"""
import json

import streamlit as st

from shared.agents import create_agents, run_with_fallback


def render(state):
    """渲染 Step 3: 学习路径规划

    Args:
        state: session_state 对象，包含 course_name, profile, roadmap 等字段
    """
    st.markdown('<p class="phase-title">Step 3: 学习路径规划</p>', unsafe_allow_html=True)
    st.caption(f"📖 课程：{state.course_name} | 精简高效的学习路径")

    if not state.roadmap:
        with st.spinner("正在规划你的学习路径..."):
            agents = create_agents(
                course_name=state.course_name,
                student_info=state.profile
            )
            roadmap_agent = agents.roadmap_agent()
            profile_str = json.dumps(state.profile, ensure_ascii=False)
            prompt = f"""课程: {state.course_name}
学生画像: {profile_str}

规划5-8步精简学习路径。输出Markdown表格:

| 步骤 | 难度 | 学习目标 | 推荐资源 |
|------|------|----------|----------|
| 1. xx | ★★ | xx | xx |

从易到难，关键节点设检查点，针对薄弱环节加强。"""
            resp, _ = run_with_fallback(roadmap_agent, prompt)
            state.roadmap = resp
        st.rerun()

    # 美化显示
    roadmap = state.roadmap

    # 统计卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="metric-box"><div class="value">5-8</div>'
            '<div class="label">学习步骤</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        completed_dims = sum(
            1 for v in state.profile.values() if v and v != "待了解"
        )
        st.markdown(
            f'<div class="metric-box"><div class="value">{completed_dims}/6</div>'
            f'<div class="label">画像维度</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-box"><div class="value">{state.course_name[:4]}</div>'
            f'<div class="label">当前课程</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown(roadmap)

    # 导航
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⬅ 返回资源生成", use_container_width=True):
            state.step = 2
            st.rerun()
    with c2:
        if st.button("→ 进入辅导", type="primary", use_container_width=True):
            state.step = 4
            st.rerun()
    with c3:
        if st.button("📊 学习评估（加分项）", use_container_width=True):
            state.step = 5
            st.rerun()


# ============================================================================
# 独立运行测试
# ============================================================================
if __name__ == "__main__":
    import streamlit as st
    from shared.session_state import DEFAULTS

    st.set_page_config(page_title="Step 3 路径规划测试", page_icon="📚", layout="wide")
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # Mock data
    st.session_state.course_name = "Python程序设计"
    st.session_state.profile = {
        "知识基础": "入门",
        "认知风格": "视觉型",
        "学习目标": "通过期末项目",
        "薄弱环节": "面向对象",
        "学习节奏": "每周8小时",
        "兴趣领域": "Web开发",
    }
    st.session_state.roadmap = None
    render(st.session_state)
