"""
=============================================================================
Step 5: 学习评估（加分项，可选）
DeepSeek 评估 + 星火交叉验证，融合生成综合诊断报告
=============================================================================
"""
import json

import streamlit as st

from shared.agents import create_agents
from shared.session_state import DEFAULTS


def render(state):
    """渲染 Step 5: 学习评估

    Args:
        state: session_state 对象，包含 profile, resources, roadmap,
               tutor_history, eval_report, _glm_raw, _spark_raw, _spark_label 等字段
    """
    st.markdown(
        '<p class="phase-title">Step 5: 学习评估（加分项）</p>',
        unsafe_allow_html=True,
    )
    st.info("DeepSeek 评估 + 星火交叉验证，给你最客观的学习诊断。")

    # ---- 生成评估 ----
    if not state.eval_report:
        # 收集评估数据
        eval_data = f"""## 学生画像
{json.dumps(state.profile, ensure_ascii=False, indent=2)}

## 学习资源摘要
{state.resources[:2000] if state.resources else '未生成'}

## 学习路径摘要
{state.roadmap[:2000] if state.roadmap else '未生成'}

## 辅导历史
{json.dumps([{'q': h['question'], 't': h['time']} for h in state.tutor_history[-5:]], ensure_ascii=False) if state.tutor_history else '暂无提问'}"""

        agents = create_agents(course_name=state.course_name)
        with st.spinner("DeepSeek + 星火 交叉验证评估中..."):
            result = agents.cross_validate(eval_data)
            report = result["merged"]
            state._glm_raw = result.get("glm")
            state._spark_raw = result.get("spark")
            state._spark_label = result.get("spark_label", "星火")

        state.eval_report = report
        st.rerun()

    # ---- 显示评估报告 ----
    report = state.eval_report
    st.markdown(report)

    # ---- 显示双模型原始报告 ----
    if state.get("_glm_raw") and state.get("_spark_raw"):
        with st.expander("查看双模型原始报告"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### DeepSeek 评估")
                st.markdown(state._glm_raw)
            with col_b:
                spark_label = state.get("_spark_label", "星火")
                st.markdown(f"#### {spark_label} 评估")
                st.markdown(state._spark_raw)

    # ---- 导航 ----
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⬅ 返回辅导", use_container_width=True):
            state.step = 4
            st.rerun()
    with c2:
        if st.button("\U0001f504 重新开始", use_container_width=True):
            for k in list(state.keys()):
                if not k.startswith("_"):
                    del state[k]
            for k, v in DEFAULTS.items():
                state[k] = v
            st.rerun()


# ============================================================================
# 独立运行测试
# ============================================================================
if __name__ == "__main__":
    import streamlit as st
    from shared.session_state import DEFAULTS

    st.set_page_config(
        page_title="Step 5 评估测试", page_icon="📚", layout="wide"
    )
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # Rich mock data
    st.session_state.course_name = "Python程序设计"
    st.session_state.profile = {
        "知识基础": "入门",
        "认知风格": "视觉型 + 动手型",
        "学习目标": "通过期末项目",
        "薄弱环节": "面向对象",
        "学习节奏": "每周8小时",
        "兴趣领域": "Web开发",
    }
    st.session_state.resources = (
        "Mock resources: ## 课程讲解\nPython基础讲解内容..."
    )
    st.session_state.roadmap = (
        "Mock roadmap: 1.Python基础 → 2.函数 → 3.OOP → 4.模块 → 5.项目"
    )
    st.session_state.tutor_history = [
        {"question": "什么是装饰器？", "answer": "装饰器是...", "time": "14:30"},
        {"question": "类和实例的区别？", "answer": "类是模板...", "time": "14:35"},
    ]
    st.session_state.eval_report = None
    st.session_state._glm_raw = None
    st.session_state._spark_raw = None
    st.session_state._spark_label = "星火"
    render(st.session_state)
