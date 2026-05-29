"""
=============================================================================
Step 4: 智能辅导 + RAG（Tab 切换）—— 独立模块
包含概念辅导（Tab 1）和 RAG 文档问答（Tab 2）
=============================================================================
"""
import json
import re
from datetime import datetime

import streamlit as st

from shared.agents import create_agents, run_with_fallback, stream_chat


def render(state):
    """渲染 Step 4 智能辅导页面。state 为 session_state 对象。"""

    st.markdown('<p class="phase-title">Step 4: 智能辅导</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 概念辅导", "📚 RAG 文档问答"])

    # ========================================================================
    # Tab 1: 双向互动辅导
    # ========================================================================
    with tab1:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown("### 双向互动辅导")
            st.caption("AI 会回答你的问题，也可能在讲解后出题测试你的理解。答不上来会帮你补充学习资源。")

            question = st.text_area("输入你的内容",
                                    placeholder="可以提问、回答 AI 的测验、或者说「考考我」主动要求测试",
                                    height=100, key="tutor_question")

            context_hint = st.text_input("补充上下文（可选）",
                                         placeholder="比如：我在学机器学习第三章，卡在优化算法部分",
                                         key="tutor_context")

            if st.button("💬 发送", type="primary", disabled=not question.strip()):
                agents = create_agents(
                    course_name=state.course_name,
                    student_info=state.profile
                )
                tutor = agents.tutor_agent()
                profile_str = json.dumps(state.profile, ensure_ascii=False)

                # 构建对话历史
                history_text = ""
                for h in state.tutor_history[-4:]:
                    history_text += f"学生: {h['question']}\nAI: {h['answer'][:300]}\n\n"

                prompt = f"""学生画像: {profile_str}
当前课程: {state.course_name}
补充信息: {context_hint if context_hint else '无'}

最近对话:
{history_text}

学生最新消息: {question}

根据上下文判断学生是在提问/回答测验/要求测试/拒绝测验，用对应的模式回应。
如果是回答测验，必须判断对错。答错时在回复末尾加一行:
[WEAKNESS:知识点|学生答案|正确答案]"""

                with st.status("辅导老师正在回答...", expanded=True) as status:
                    placeholder = st.empty()
                    full = ""
                    for chunk in stream_chat(tutor, prompt):
                        full += chunk
                        placeholder.markdown(full + "▌")
                    status.update(label="回答完成", state="complete")

                # 检测薄弱点标记
                weakness_match = re.search(r'\[WEAKNESS:(.+?)\|(.+?)\|(.+?)\]', full)
                if weakness_match:
                    topic = weakness_match.group(1)
                    student_ans = weakness_match.group(2)
                    correct_ans = weakness_match.group(3)
                    # 移除标记，不在前端显示
                    full = re.sub(r'\n?\[WEAKNESS:.+?\]', '', full)

                    # 调用弱点分析 agent
                    with st.spinner("正在分析薄弱点并生成补救方案..."):
                        wa = agents.weakness_agent()
                        wa_prompt = f"""课程: {state.course_name}
学生画像: {profile_str}
薄弱知识点: {topic}
学生错误回答: {student_ans}
正确答案: {correct_ans}
当前学习路径:
{state.roadmap[:1500] if state.roadmap else '未生成'}

分析薄弱点并生成补救方案。"""
                        wa_resp, _ = run_with_fallback(wa, wa_prompt)
                        full += "\n\n---\n\n## 📍 薄弱点分析与补救方案\n\n" + wa_resp
                        status.update(label="薄弱点分析完成", state="complete")

                    # 存储薄弱点
                    state.weakness_list.append({
                        "topic": topic,
                        "student_ans": student_ans,
                        "correct_ans": correct_ans,
                        "analysis": wa_resp[:500],
                        "time": datetime.now().strftime("%H:%M:%S"),
                    })

                placeholder.markdown(full)
                state.tutor_history.append({
                    "question": question,
                    "answer": full,
                    "time": datetime.now().strftime("%H:%M:%S"),
                })

            # 显示历史
            if state.tutor_history:
                st.markdown("---")
                st.markdown("### 对话历史")
                for i, entry in enumerate(reversed(state.tutor_history)):
                    with st.expander(f"Q: {entry['question'][:50]}... ({entry['time']})", expanded=(i == 0)):
                        st.markdown(entry["answer"])

        with col2:
            st.markdown("### 学习统计")
            st.metric("互动次数", len(state.tutor_history))
            # 薄弱点
            if state.weakness_list:
                st.markdown("### 🔴 薄弱环节")
                for w in reversed(state.weakness_list[-5:]):
                    st.caption(f"• {w['topic']} ({w['time']})")
            if state.profile:
                st.caption("AI 根据你的画像调整讲解方式")
                for dim in ["认知风格", "知识基础"]:
                    val = state.profile.get(dim, "")
                    if val and val != "待了解":
                        st.caption(f"• {dim}: {val}")

    # ========================================================================
    # Tab 2: RAG 文档问答
    # ========================================================================
    with tab2:
        col_r1, col_r2 = st.columns([2, 1])

        with col_r1:
            st.markdown("### 基于教材提问")

            if state.rag_doc_count == 0:
                st.info("还没有上传教材文档。请在左侧栏上传PDF或TXT教材，然后在这里提问。")
            else:
                rag_question = st.text_area("输入问题",
                                            placeholder="比如：第三章的核心概念是什么？",
                                            height=100, key="rag_question")

                if st.button("🔍 搜索答案", type="primary", disabled=not rag_question.strip()):
                    with st.spinner("搜索中..."):
                        agents = create_agents(course_name=state.course_name)
                        relevant = state.rag_helper.query(rag_question, k=4)
                        context = "\n\n".join(relevant)

                        rag_bot = agents.rag_tutor_agent()
                        prompt = f"""## 教材检索内容
{context}

## 学生问题
{rag_question}

基于教材内容回答。没有的信息明确告知。引用时标注来源。"""

                        resp, _ = run_with_fallback(rag_bot, prompt)
                        state.rag_answer = resp

                if getattr(state, 'rag_answer', None):
                    st.markdown("### 答案")
                    st.markdown(state.rag_answer)

        with col_r2:
            st.markdown("### 知识库状态")
            st.metric("文档块数", state.rag_doc_count)

    # ========================================================================
    # 导航
    # ========================================================================
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅ 返回路径规划", use_container_width=True):
            state.step = 3
            st.rerun()
    with c2:
        if st.button("📊 学习评估（加分项）", use_container_width=True):
            state.step = 5
            st.rerun()


# ============================================================================
# Standalone runner for testing
# ============================================================================
if __name__ == "__main__":
    import streamlit as st
    from shared.session_state import DEFAULTS

    st.set_page_config(page_title="Step 4 辅导测试", page_icon="📚", layout="wide")
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # Rich mock data for testing
    st.session_state.course_name = "Python程序设计"
    st.session_state.profile = {
        "知识基础": "入门，能写简单函数和循环",
        "认知风格": "视觉型 + 动手型",
        "学习目标": "通过期末项目（Web应用）",
        "薄弱环节": "面向对象编程、装饰器",
        "学习节奏": "每周8小时，偏好快速推进",
        "兴趣领域": "Web开发、数据分析",
    }
    st.session_state.roadmap = "Mock roadmap: 1.Python基础回顾 → 2.函数进阶 → 3.OOP入门 → 4.模块与包 → 5.Flask基础"
    st.session_state.tutor_history = []
    st.session_state.weakness_list = []
    st.session_state.rag_doc_count = 0
    st.session_state.rag_helper = None
    try:
        from shared.rag_helper import RAGHelper
        st.session_state.rag_helper = RAGHelper(collection_name="a3_knowledge_base")
        st.session_state.rag_doc_count = st.session_state.rag_helper.get_doc_count()
    except:
        pass
    render(st.session_state)
