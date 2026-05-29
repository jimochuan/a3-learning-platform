"""
=============================================================================
A3 v3 Step 1: 画像对话 (Profile Dialogue)
=============================================================================
独立可运行模块 —— 通过自然对话了解学生画像
=============================================================================
"""
import streamlit as st
import json
import re
import sys
import os

# Ensure project root is on path for standalone execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.agents import create_agents, run_with_fallback, stream_chat
from shared.config import PROFILE_DIMENSIONS


# ============================================================================
# Module-level CSS (silently skipped when imported outside Streamlit)
# ============================================================================
try:
    st.markdown("""
<style>
    .phase-title {
        font-size: 1.2rem; font-weight: 700; color: #4A90D9;
        padding: 0.5rem 1rem; background: #eff6ff;
        border-left: 4px solid #4A90D9; border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)
except Exception:
    pass


# ============================================================================
# MOCK_DATA (minimal — Step 1 mostly starts fresh)
# ============================================================================
MOCK_DATA = {
    "step": 1,
    "course_name": "",
    "profile": {},
    "dialogue": [],
}


def render(state):
    """Step 1: AI 对话 —— 选课 + 画像（后台）

    Args:
        state: A Streamlit session_state object or compatible dict.
               When called from main app, state IS st.session_state.
    """

    # ---- Guard: only render Step 1 ----
    if state.step != 1:
        return

    st.markdown('<p class="phase-title">Step 1: 开始学习 —— AI 对话了解你</p>', unsafe_allow_html=True)

    # ---- 对话完成 → 自动进入 Step 2 ----
    if state.get("_profile_complete"):
        st.success("✅ 学习画像分析完成，正在为你生成个性化学习方案...")
        state.step = 2
        st.rerun()

    # ---- AI 对话区 ----
    # 渲染对话历史
    for msg in state.dialogue[-10:]:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])

    # 初始化：AI 发第一条消息
    if not state.dialogue:
        agents = create_agents()
        profile_bot = agents.profile_agent()
        init_prompt = """你是一位友好专业的学习顾问，通过自然对话了解学生。

你需要逐步了解以下信息（不要一次性全问，每次1-3个问题，像聊天一样自然）：
1. 想学什么课程/领域
2. 目前基础如何（零基础/入门/能独立做项目/已经很熟练）
3. 为什么想学这个（考证/找工作/做项目/纯粹兴趣/跟课程）
4. 平时喜欢怎么学新东西（看视频/看书/动手做/听课讨论）
5. 一周大概能投入多少时间学习
6. 之前学过相关内容的体验——哪里容易卡住、什么让你兴奋

对话策略：
- 第一轮：打招呼自我介绍(1句) + 问想学什么 + 给2-3个方向提示
- 根据学生回答自然追问，不要像填问卷
- 如果学生回答很简短，用具体选项引导（比如"你是偏好看视频学，还是喜欢边看文档边动手？"）
- 口语化，保持轻松但专业
- 只输出你要说的话，不要加任何标注或前缀"""
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            for chunk in stream_chat(profile_bot, init_prompt):
                full += chunk
                placeholder.markdown(full + "▌")
            placeholder.markdown(full)
            state.dialogue.append({"role": "assistant", "content": full})

    # 用户输入
    user_input = st.chat_input("在这里和 AI 聊天...", key="step1_chat")
    if user_input:
        state.dialogue.append({"role": "user", "content": user_input})

        # 第一次回复后提取课程名
        if not state.course_name:
            extract_prompt = f"学生说: {user_input}\n提取学生想学的课程名称（1-3个词）。只输出课程名。"
            agents = create_agents()
            tmp_agent = agents.profile_agent()
            course_resp, _ = run_with_fallback(tmp_agent, extract_prompt)
            state.course_name = course_resp.strip().replace("《", "").replace("》", "").replace(" ", "")
            if not state.course_name:
                state.course_name = "未指定课程"

        agents = create_agents(course_name=state.course_name)
        profile_bot = agents.profile_agent()

        history_text = "\n".join([
            f"{'学生' if m['role'] == 'user' else 'AI'}: {m['content'][:400]}"
            for m in state.dialogue[-12:]
        ])

        # 找出还没填的画像维度
        missing_dims = [d for d in PROFILE_DIMENSIONS if not state.profile.get(d) or state.profile.get(d) == "待了解"]
        filled_dims = [d for d in PROFILE_DIMENSIONS if state.profile.get(d) and state.profile.get(d) != "待了解"]

        PROCESS_PROMPT = f"""学习画像分析师。课程:《{state.course_name}》

对话历史:
{history_text}

当前画像（已填维度: {', '.join(filled_dims) if filled_dims else '无'}）:
{json.dumps(state.profile, ensure_ascii=False)}

还需了解的维度: {', '.join(missing_dims) if missing_dims else '全部已填'}

你的任务:
1. 从学生最新回答中提取信息更新画像。一句话概括即可，敷衍回答不强行记录。
2. 判断画像是否已收集充分（≥3个维度充实即可），满足则 next_question 填 "[PROFILE_COMPLETE]"
3. 未完成则追问，但必须遵守以下铁律:

铁律（违反任一条都是错误）:
A. 学生刚回答过的方向，绝不追问！比如学生说"看视频"→认知风格已明确是视觉型，下一问必须切到别的维度
B. 每次追问只瞄准"还需了解"里的维度，不在列表里的不许问
C. 简单回答直接提取: "看视频"→视觉型、"看书做笔记"→读写型、"动手写代码"→动手型、"听课讨论"→听觉型
D. 追问必须口语化 + 括号给2-4个方向提示，让学生不用思考就知道怎么答
E. 先简短回应上一句（半句），再自然过渡到新问题，保持上下文连贯

输出JSON（只输出JSON，不要其他文字）:
{{"profile":{{"知识基础":"...","认知风格":"...","学习目标":"...","薄弱环节":"...","学习节奏":"...","兴趣领域":"..."}},"next_question":"具体追问（含方向提示，或 [PROFILE_COMPLETE]）"}}"""

        with st.spinner("AI 分析中..."):
            resp, _ = run_with_fallback(profile_bot, PROCESS_PROMPT)
            content = resp

        # 解析 JSON
        try:
            result = json.loads(content)
        except Exception:
            try:
                m = re.search(r'\{.*\}', content, re.DOTALL)
                result = json.loads(m.group()) if m else {}
            except Exception:
                result = {"profile": state.profile,
                          "next_question": "好的，我们继续聊聊~ 你觉得自己在学习中最容易卡在什么地方？"}

        # 后台更新画像（不展示）
        new_profile = result.get("profile", {})
        if new_profile:
            state.profile.update(new_profile)

        # 判断完成
        next_q = result.get("next_question", "")
        if "[PROFILE_COMPLETE]" in next_q or "[PROFILE_COMPLETE]" in content:
            state._profile_complete = True
            state.dialogue.append({
                "role": "assistant",
                "content": "好的，我对你的学习情况已经足够了解了！正在为你生成个性化学习方案..."
            })
        else:
            if next_q.strip():
                state.dialogue.append({"role": "assistant", "content": next_q})
        st.rerun()


# ============================================================================
# Standalone runner
# ============================================================================
if __name__ == "__main__":
    st.set_page_config(
        page_title="Step 1 画像对话测试",
        page_icon="\U0001f4da",
        layout="wide",
    )

    from shared.session_state import init_session

    init_session()
    render(st.session_state)
