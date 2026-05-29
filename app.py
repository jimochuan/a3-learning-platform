"""
=============================================================================
A3 v3 Streamlit UI -- 6-agent learning system with user authentication
Main: DeepSeek | Cross-validate: XF Spark
Run: streamlit run app.py
=============================================================================
"""
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import json
import re
import os
import logging
from datetime import datetime
from openai import OpenAI

from config import PROFILE_DIMENSIONS, DEEPSEEK_CONFIG, test_api_connectivity
from agents import create_agents, run_with_fallback, stream_chat
from rag_helper import RAGHelper
from dialogue_resource_agent import create_dialogue_agent
from auth import (
    generate_uid, hash_password, verify_password,
    SECURITY_QUESTION, verify_security_answer, validate_login
)
from user_store import (
    load_user, save_user, create_user as store_create_user, delete_user,
    save_checkpoint, delete_checkpoint, has_checkpoint, rollback_to_checkpoint,
    list_all_uids, user_has_history,
    atomic_update,
    save_student_snapshot, detect_changes,
)
from auth_pages import render_login_page, render_register_page, render_forgot_pwd_page, render_admin_page

# ============================================================================
# Page config
# ============================================================================
st.set_page_config(
    page_title="A3 Personalised Learning v3",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS
# ============================================================================
st.markdown("""
<style>
    .workflow-progress { display: none !important; }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 1.5rem; border-radius: 12px;
        text-align: center; margin-bottom: 1.5rem;
    }
    .main-header h1 { color: white; font-size: 1.8rem; margin: 0; }
    .main-header p { color: rgba(255,255,255,0.85); margin: 0.3rem 0 0 0; }
    .phase-title {
        font-size: 1.2rem; font-weight: 700; color: #4A90D9;
        padding: 0.5rem 1rem; background: #eff6ff;
        border-left: 4px solid #4A90D9; border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
    }
    .resource-section {
        margin: 1rem 0; padding: 1.2rem;
        background: #fafbff; border-radius: 10px;
        border: 1px solid #e8ecf4;
    }
    .resource-section h3 {
        color: #3B5998; font-size: 1.1rem;
        border-bottom: 2px solid #e0e6f0; padding-bottom: 0.4rem;
    }
    .metric-box {
        text-align: center; padding: 1rem; background: #f8fafc;
        border-radius: 8px; border: 1px solid #e2e8f0;
    }
    .metric-box .value { font-size: 2rem; font-weight: 700; color: #4A90D9; }
    .metric-box .label { font-size: 0.85rem; color: #64748b; }
    .footer { text-align: center; color: #94a3b8; padding: 1.5rem 1.8rem 0; font-size: 0.8rem; }
    [data-testid="stExpanderDetails"] { font-size: 0.92rem; line-height: 1.7; }
    .roadmap-table { width: 100%; border-collapse: collapse; }
    .roadmap-table th {
        background: #4A90D9; color: white; padding: 0.6rem; font-size: 0.9rem;
    }
    .roadmap-table td {
        padding: 0.5rem; border-bottom: 1px solid #e2e8f0; font-size: 0.9rem;
    }
    .roadmap-table tr:nth-child(even) { background: #f8fafc; }
    .step-badge {
        display: inline-block; background: #4A90D9; color: white;
        border-radius: 50%; width: 28px; height: 28px; text-align: center;
        line-height: 28px; font-weight: 700; font-size: 0.85rem;
    }
    /* ---- Auth pages — minimal centered card ---- */
    [data-testid="stForm"] {
        max-width: 400px; margin: 0 auto;
    }
    /* AI change summary */
    .ai-summary {
        background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
        border-left: 4px solid #667eea; border-radius: 8px;
        padding: 1rem 1.2rem; margin: 0.5rem 0 1rem 0;
        font-size: 0.95rem; line-height: 1.7; color: #1e293b;
    }
    /* Auth header */
    .auth-header { text-align: center; padding: 0 0 1.5rem 0; }
    .auth-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; font-size: 1.6rem; margin: 0 0 0.4rem 0; font-weight: 700;
    }
    .auth-subtitle { color: #94a3b8; font-size: 0.88rem; margin: 0; }
    /* Auth footer */
    .auth-footer {
        max-width: 420px; margin: 0.8rem auto 0 auto; text-align: center;
    }
    .auth-divider { border: none; border-top: 1px solid #f1f5f9; margin: 1rem 0; }
    /* Placeholder: hide on focus, show again if empty on blur */
    input:focus::placeholder { opacity: 0; }
    /* Hide Streamlit "Press Enter to submit form" hint */
    [data-testid="stForm"] small { display: none !important; }
    /* Footer compact buttons */
    .auth-footer .stButton button {
        font-size: 0.82rem; padding: 0.35rem 0.8rem; border-radius: 6px;
        background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0;
    }
    .auth-footer .stButton button:hover {
        background: #f1f5f9; color: #475569; border-color: #cbd5e1;
    }
    /* Misc */
    .uid-display {
        text-align: center; font-size: 3rem; font-weight: 700; color: #4A90D9;
        letter-spacing: 0.5rem; padding: 1rem;
    }
    .auth-msg-success {
        text-align: center; padding: 0.75rem; border-radius: 8px; margin: 0.75rem 0;
        background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; font-size: 0.9rem;
    }
    .auth-msg-error {
        text-align: center; padding: 0.75rem; border-radius: 8px; margin: 0.75rem 0;
        background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; font-size: 0.9rem;
    }
    .stButton button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Auth state init
# ============================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_uid = None
    st.session_state.session_resolved = False
    st.session_state.auth_page = "login"
    st.session_state.auth_msg = ""
    st.session_state.auth_msg_type = "info"
    st.session_state.show_exit_confirm = False

# ============================================================================
# Auth helpers
# ============================================================================
def auto_save():
    """Auto-save current learning state to user JSON file (atomic read-modify-write)."""
    if not st.session_state.get("authenticated"):
        return
    uid = st.session_state.get("current_uid")
    if not uid:
        return

    def _update(user_data):
        # Collect session data from current state
        session_data = {
            "course_name": st.session_state.get("course_name", ""),
            "step": st.session_state.get("step", 1),
            "dialogue": st.session_state.get("dialogue", []),
            "resources": st.session_state.get("resources"),
            "roadmap": st.session_state.get("roadmap"),
            "tutor_history": st.session_state.get("tutor_history", []),
            "weakness_list": st.session_state.get("weakness_list", []),
            "eval_report": st.session_state.get("eval_report"),
        }

        user_data["user_portrait"] = st.session_state.get("profile", {})
        user_data["session_records"] = session_data
        user_data["latest_progress"] = f"Step {st.session_state.get('step', 1)}: {st.session_state.get('course_name', '')}"

        # Append to history_progress (only when step or course actually changes)
        progress_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "step": st.session_state.get("step", 1),
            "course": st.session_state.get("course_name", ""),
        }
        if "history_progress" not in user_data:
            user_data["history_progress"] = []
        existing = user_data["history_progress"]
        if not existing or existing[-1].get("step") != progress_entry["step"] or existing[-1].get("course") != progress_entry["course"]:
            existing.append(progress_entry)
            if len(existing) > 200:
                user_data["history_progress"] = existing[-200:]
        return user_data

    atomic_update(uid, _update)


def auto_save_and_rerun():
    """Auto-save then rerun the Streamlit app."""
    auto_save()
    st.rerun()


def load_session_from_user(uid):
    """Load learning state from user JSON into session_state."""
    user_data = load_user(uid)
    if user_data is None:
        return
    records = user_data.get("session_records", {})
    if isinstance(records, dict) and records:
        st.session_state.course_name = records.get("course_name", "")
        st.session_state.step = records.get("step", 1)
        st.session_state.dialogue = records.get("dialogue", [])
        st.session_state.resources = records.get("resources")
        st.session_state.roadmap = records.get("roadmap")
        st.session_state.tutor_history = records.get("tutor_history", [])
        st.session_state.weakness_list = records.get("weakness_list", [])
        st.session_state.eval_report = records.get("eval_report")
    st.session_state.profile = user_data.get("user_portrait", {})


def persist_and_exit(save: bool):
    """Handle exit: save or rollback, then clear session and return to login."""
    uid = st.session_state.get("current_uid")
    if not uid:
        return

    if save:
        auto_save()
        save_student_snapshot(uid)
        delete_checkpoint(uid)
    else:
        has_hist = user_has_history(uid)
        if has_checkpoint(uid):
            rollback_to_checkpoint(uid)
        elif not has_hist:
            delete_user(uid)

    # Clear ALL session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def delete_conversation_ui():
    """Clear current chat display only, keep history intact."""
    st.session_state.dialogue = []
    st.session_state.tutor_history = []
    st.session_state.step2_messages = []
    st.session_state.step2_agent = None
    st.session_state.step2_active = True
    auto_save()


def reset_and_switch_user():
    """Save current user data, clear UI, return to login page."""
    uid = st.session_state.get("current_uid")
    if uid:
        auto_save()
        delete_checkpoint(uid)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# ============================================================================
# AUTH GATE — force login before accessing learning features
# ============================================================================
if not st.session_state.authenticated:
    page = st.session_state.auth_page
    if page == "register":
        render_register_page()
    elif page == "forgot_pwd":
        render_forgot_pwd_page()
    elif page == "admin":
        render_admin_page()
    else:
        render_login_page()
    st.stop()


# ============================================================================
# API 连通性诊断 —— 启动时实际调用各家 API 验证是否可用
# ============================================================================
if "api_test_done" not in st.session_state:
    with st.spinner("正在检测 AI 模型连通性..."):
        st.session_state._api_results = test_api_connectivity()
    st.session_state.api_test_done = True

_api = st.session_state._api_results
_primary_key = _api.get("primary_key", "deepseek")

# ---- 全部不通 -> 阻塞 ----
if not _api["any_connected"]:
    st.markdown("""
<div class="auth-header">
    <h1>未检测到可用的 AI 模型</h1>
    <p class="auth-subtitle">至少需要接入一个 API 才能使用学习功能</p>
</div>
""", unsafe_allow_html=True)

    st.error("所有 API 均无法连接，请按下面指引配置")

    _providers_to_show = [k for k, v in _api.items()
                          if k not in ("any_connected", "primary_connected", "primary_key", "_primary")]
    for _pk in _providers_to_show:
        _pi = _api[_pk]
        _emoji = "推荐" if _pk == "deepseek" else ""
        with st.expander(f"{_emoji} {_pi['label']} - {_pi['desc']}", expanded=(_pk == "deepseek")):
            st.markdown(f"""
注册地址: [{_pi['register_url']}]({_pi['register_url']})

{_pi['howto']}

在 .env 中填入 Key 后重启即可。
""")

    st.info("配置好 .env 后按 F5 刷新页面即可重新检测。系统已预置星火作为兜底。")
    st.stop()

# ---- 辅助函数：写配置到 .env ----
def _save_to_env(provider_key: str = None, api_key: str = None, primary_model: str = None):
    """将 API Key 或主力模型写入 .env 文件"""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    env_var_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "qwen": "QWEN_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "glm": "GLM_API_KEY",
        "baichuan": "BAICHUAN_API_KEY",
        "spark": "SPARK_API_KEY",
    }

    # 如果 .env 不存在，从模板复制
    if not os.path.exists(env_path):
        import shutil
        example_path = os.path.join(os.path.dirname(__file__), ".env.example")
        if os.path.exists(example_path):
            shutil.copy(example_path, env_path)

    if not os.path.exists(env_path):
        return False

    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    import re as _re

    # 写 API Key
    if provider_key and api_key is not None:
        var_name = env_var_map.get(provider_key)
        if var_name:
            pattern = _re.compile(rf"^{var_name}=.*$", _re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f"{var_name}={api_key}", content)
            else:
                content += f"\n{var_name}={api_key}\n"
            os.environ[var_name] = api_key

    # 写主力模型
    if primary_model:
        pattern = _re.compile(r"^PRIMARY_MODEL=.*$", _re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f"PRIMARY_MODEL={primary_model}", content)
        else:
            content += f"\nPRIMARY_MODEL={primary_model}\n"
        os.environ["PRIMARY_MODEL"] = primary_model

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


# ---- 所有可配置的供应商列表 ----
_ALL_PROVIDERS = [
    k for k, v in _api.items()
    if k not in ("any_connected", "primary_connected", "primary_key", "_primary")
]

# ---- 至少有一个通了 -> 侧边栏状态灯 ----
with st.sidebar:
    with st.expander("API Status", expanded=not _api["primary_connected"]):
        # 状态摘要
        for _pk in _ALL_PROVIDERS:
            _pi = _api[_pk]
            if not _pi["ready"]:
                st.caption(f"○ {_pi['label']}: not configured")
            elif _pi["connected"]:
                _mark = "●" if _pk == _primary_key else "○"
                _active = "(当前)" if _pk == _primary_key else ""
                st.caption(f"{_mark} {_pi['label']}: {_pi['latency_ms']}ms OK {_active}")
            else:
                st.caption(f"⚠ {_pi['label']}: {_pi['error']}")

        st.divider()

        # ---- 切换主力模型 ----
        _current_primary = os.getenv("PRIMARY_MODEL", "deepseek")
        _primary_options = {_api[k]["label"]: k for k in _ALL_PROVIDERS if _api[k]["ready"]}
        _primary_labels = list(_primary_options.keys())
        if _primary_labels:
            _current_label = _api.get(_current_primary, {}).get("label", "DeepSeek")
            if _current_label in _primary_labels:
                _default_idx = _primary_labels.index(_current_label)
            else:
                _default_idx = 0

            _chosen_label = st.selectbox(
                "主力模型",
                _primary_labels,
                index=_default_idx,
                key="primary_model_selector",
            )
            _chosen_key = _primary_options[_chosen_label]
            if _chosen_key != _current_primary:
                if _save_to_env(primary_model=_chosen_key):
                    st.session_state.api_test_done = False
                    st.rerun()

        # ---- 配置 / 更换 API Key ----
        _need_rerun = False
        for _pk in _ALL_PROVIDERS:
            _pi = _api[_pk]
            _status_icon = "●" if (_pi["ready"] and _pi["connected"]) else "○"
            with st.expander(f"{_status_icon} {_pi['label']}", expanded=False):
                st.caption(_pi["desc"])
                st.caption(f"注册: {_pi['register_url']}")
                _current_key = os.getenv(
                    {"deepseek": "DEEPSEEK_API_KEY", "qwen": "QWEN_API_KEY",
                     "moonshot": "MOONSHOT_API_KEY", "glm": "GLM_API_KEY",
                     "baichuan": "BAICHUAN_API_KEY", "spark": "SPARK_API_KEY"}.get(_pk, ""), "")
                _has_key = bool(_current_key and _current_key not in ("你的Key填这里", ""))
                if _has_key:
                    _masked = _current_key[:6] + "****" + _current_key[-4:] if len(_current_key) > 10 else "****"
                    st.caption(f"当前 Key: {_masked}")

                with st.form(key=f"apikey_form_{_pk}", clear_on_submit=True):
                    _col1, _col2 = st.columns([3, 1])
                    with _col1:
                        _new_key = st.text_input(
                            "Key",
                            type="password",
                            placeholder="sk-..." if not _has_key else "粘贴新 Key 替换",
                            key=f"apikey_input_{_pk}",
                            label_visibility="collapsed",
                        )
                    with _col2:
                        _submitted = st.form_submit_button("保存", use_container_width=True)
                    if _submitted and _new_key.strip():
                        if _save_to_env(provider_key=_pk, api_key=_new_key.strip()):
                            st.caption("✓ 已保存")
                            _need_rerun = True

        if _need_rerun:
            st.session_state.api_test_done = False
            st.rerun()

    if not _api["primary_connected"]:
        _expected_label = _api["_primary"]["label"]
        st.warning(f"Your {_expected_label} is not working. Using Spark as fallback.")

# ---- 用户的 Key 有问题 -> 顶部展开详情 ----
if not _api["primary_connected"]:
    _user_providers = {k: v for k, v in _api.items()
                       if k not in ("any_connected", "primary_connected", "primary_key", "_primary", "spark")
                       and v["ready"] and not v["connected"]}
    if _user_providers:
        with st.expander("Your API Key Issues - Click for details", expanded=True):
            for _pk, _pi in _user_providers.items():
                st.error(f"**{_pi['label']}**: {_pi['error']}")
                st.markdown(f"Sign up: [{_pi['register_url']}]({_pi['register_url']})")
                st.caption(f"{_pi['howto']}")
            st.info("System auto-fellback to Spark. All features work normally.")


# ============================================================================
# Helper: AI 变化摘要 + 画像维度选项
# ============================================================================
logger = logging.getLogger(__name__)

PROFILE_OPTIONS = {
    "知识基础": ["零基础", "入门", "熟练", "精通"],
    "认知风格": ["视觉型", "听觉型", "动手型", "读写型"],
    "学习目标": ["通过考试", "找实习", "提升技能", "转行", "考研", "兴趣探索"],
    "薄弱环节": [],  # 不预填，用户自定义
    "学习节奏": ["快速（每周10h+）", "正常（每周4-8h）", "慢速（每周2-3h）"],
    "兴趣领域": [],  # 不预填，用户自定义
}


def _generate_change_summary(changes_info: dict) -> str:
    """调用 DeepSeek 生成自然语言变化摘要。失败时返回纯文本列表。"""
    changes = changes_info.get("changes", [])
    if not changes:
        return ""

    changes_text = "\n".join(f"- {c}" for c in changes)
    prompt = f"""你是A3个性化学习系统的AI助教。学生在学习过程中发生了以下变化：

{changes_text}

请用1-2句友好的中文总结学生的学习状态变化，语气亲切自然。
不要逐条罗列——给出一个整体的概括。直接输出总结文字。"""

    try:
        client = OpenAI(
            api_key=DEEPSEEK_CONFIG.get("API_KEY", os.getenv("DEEPSEEK_API_KEY", "")),
            base_url=DEEPSEEK_CONFIG.get("BASE_URL", "https://api.deepseek.com/v1"),
        )
        resp = client.chat.completions.create(
            model=DEEPSEEK_CONFIG.get("MODEL", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
            timeout=15,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("AI change summary failed: %s", e)
        return ""


def _render_profile_editor(changes_info: dict) -> dict:
    """渲染内联画像编辑器。返回编辑后的 profile 字典。"""
    profile_now = dict(changes_info.get("profile_now", {}))
    profile_then = dict(changes_info.get("profile_then", {}))
    edited = dict(profile_now)

    if not profile_then:
        st.caption("（无历史画像可对比，所有维度均为新数据）")
        return edited

    changed_dims = []
    for dim in PROFILE_DIMENSIONS:
        old_val = profile_then.get(dim, "")
        new_val = profile_now.get(dim, "")
        if old_val and new_val and old_val != new_val and old_val != "待了解" and new_val != "待了解":
            changed_dims.append((dim, old_val, new_val))

    if not changed_dims:
        return edited

    st.markdown("###### ✏️ 微调画像（可选）")
    for dim, old_val, new_val in changed_dims:
        options = list(PROFILE_OPTIONS.get(dim, []))
        # 确保新旧值都在选项中
        if new_val not in options:
            options.insert(0, new_val)
        if old_val not in options:
            options.append(old_val)
        # 加一个自定义输入选项
        if "✍️ 自定义..." not in options:
            options.append("✍️ 自定义...")

        try:
            idx = options.index(new_val)
        except ValueError:
            idx = 0

        col_label, col_select = st.columns([1, 2])
        with col_label:
            st.caption(f"{dim}")
            st.caption(f"*{old_val} →*")
        with col_select:
            selected = st.selectbox(
                dim, options, index=idx,
                key=f"profile_edit_{dim}",
                label_visibility="collapsed",
            )
            if selected == "✍️ 自定义...":
                custom = st.text_input(f"自定义{dim}", value=new_val, key=f"custom_{dim}", label_visibility="collapsed", placeholder="输入自定义值...")
                edited[dim] = custom if custom else new_val
            else:
                edited[dim] = selected

    return edited


# ============================================================================
# SESSION RESUME GATE — after login, choose resume or new
# ============================================================================
if not st.session_state.session_resolved:
    uid = st.session_state.current_uid
    has_hist = user_has_history(uid)

    st.markdown(
        '<div class="auth-header">'
        '<h1>A3 个性化学习系统</h1>'
        '<p class="auth-subtitle" style="color:#64748b;">已登录：UID {}</p>'
        '</div>'.format(uid), unsafe_allow_html=True)

    if not has_hist:
        st.info("欢迎使用 A3 学习系统！这是你的第一次使用，开启全新学习之旅。")
        if st.button("开始学习", type="primary", use_container_width=True):
            st.session_state.session_resolved = True
            st.rerun()
    else:
        # ---- Phase 3: AI 智能总结 + 一键确认更新 ----
        changes_info = detect_changes(uid)
        user_data = load_user(uid)
        last_time = user_data.get("last_save_time", "未知") if user_data else "未知"
        last_progress = user_data.get("latest_progress", "无") if user_data else "无"

        with st.container():
            st.markdown("### 会话选择")
            st.caption(f"上次保存时间：{last_time}")
            st.caption(f"上次进度：{last_progress}")

            # ---- AI 变化摘要 ----
            if changes_info.get("has_changes"):
                st.markdown("---")

                # 生成 AI 摘要（缓存到 session_state，避免重复调用）
                cache_key = f"_ai_summary_{uid}"
                if cache_key not in st.session_state:
                    with st.spinner("🤖 AI 正在分析你的学习变化..."):
                        st.session_state[cache_key] = _generate_change_summary(changes_info)

                ai_summary = st.session_state[cache_key]
                if ai_summary:
                    st.markdown(
                        f'<div class="ai-summary">🤖 {ai_summary}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("#### 🔍 检测到你的学习状态有变化")
                    for ch in changes_info["changes"]:
                        st.markdown(f"- {ch}")

                # ---- 内联画像编辑器 ----
                edited_profile = _render_profile_editor(changes_info)

                st.markdown("---")
                # ---- 操作按钮 ----
                col_confirm, col_reeval = st.columns(2)

                with col_confirm:
                    if st.button("🔄 确认更新", type="primary", use_container_width=True):
                        # 1. 写入编辑后的 profile 到 user_store
                        def _apply_profile_update(data):
                            data["user_portrait"] = edited_profile
                            return data
                        atomic_update(uid, _apply_profile_update)
                        # 2. 保存新快照
                        save_student_snapshot(uid)
                        # 3. 加载到 session_state
                        load_session_from_user(uid)
                        st.session_state.session_resolved = True
                        # 4. 标记刷新资源 + 路径
                        st.session_state._refresh_resources = True
                        st.session_state._refresh_roadmap = True
                        st.session_state.resources = None
                        st.session_state.step2_agent = None
                        st.session_state.step2_messages = []
                        st.session_state.step2_active = True
                        st.session_state.roadmap = None
                        st.session_state.step = 2
                        # 清理缓存
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()

                with col_reeval:
                    if st.button("📝 重新评估（完整对话）", use_container_width=True):
                        load_session_from_user(uid)
                        st.session_state.session_resolved = True
                        st.session_state._refresh_resources = True
                        st.session_state._refresh_roadmap = True
                        st.session_state.resources = None
                        st.session_state.step2_agent = None
                        st.session_state.step2_messages = []
                        st.session_state.step2_active = True
                        st.session_state.roadmap = None
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()

                # ---- 次要选项 ----
                st.markdown("")
                col_resume, col_fresh = st.columns(2)
                with col_resume:
                    if st.button("📂 返回上次学习进度", use_container_width=True):
                        load_session_from_user(uid)
                        st.session_state.session_resolved = True
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()
                with col_fresh:
                    if st.button("🆕 开启全新课程", use_container_width=True):
                        st.session_state.session_resolved = True
                        if cache_key in st.session_state:
                            del st.session_state[cache_key]
                        st.rerun()
            else:
                # ---- 无变化：简洁的二选一 ----
                col_choice_1, col_choice_2 = st.columns(2)
                with col_choice_1:
                    if st.button("📂 返回上次学习进度", type="primary", use_container_width=True):
                        load_session_from_user(uid)
                        st.session_state.session_resolved = True
                        st.rerun()
                with col_choice_2:
                    if st.button("🆕 开启全新课程", use_container_width=True):
                        st.session_state.session_resolved = True
                        st.rerun()

    st.stop()


# ============================================================================
# Learning state init
# ============================================================================
LEARNING_DEFAULTS = {
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
    # Phase 2: 智能刷新标记
    "_refresh_resources": False,         # 老用户回来时需要重新生成 Step 2 资源
    "_refresh_roadmap": False,           # 老用户回来时需要重新生成 Step 3 路径
    "_refresh_resources_was_auto": False,  # 标记资源是自动生成的（用于提示）
    "step2_messages": [],
    "step2_active": True,
    "_profile_complete": False,
}
for k, v in LEARNING_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================================
# Header
# ============================================================================
st.markdown(f"""
<div class="main-header">
    <h1>A3 个性化学习系统 v3</h1>
    <p>六智能体协同 · 个性化学习 · UID: {st.session_state.current_uid}</p>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# Sidebar
# ============================================================================
with st.sidebar:
    st.markdown("## ⚙️ 控制台")

    st.markdown(f"### 👤 用户: {st.session_state.current_uid}")

    col_exit1, col_exit2 = st.columns(2)
    with col_exit1:
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.show_exit_confirm = True
    with col_exit2:
        if st.button("🔄 切换用户", use_container_width=True):
            reset_and_switch_user()

    if st.session_state.get("show_exit_confirm"):
        st.markdown("---")
        st.markdown("### 退出确认")
        c_save, c_nosave = st.columns(2)
        with c_save:
            if st.button("💾 保存并退出", type="primary", use_container_width=True):
                st.session_state.show_exit_confirm = False
                persist_and_exit(save=True)
        with c_nosave:
            if st.button("🗑️ 不保存并退出", use_container_width=True):
                st.session_state.show_exit_confirm = False
                persist_and_exit(save=False)
        if st.button("❌ 取消", use_container_width=True):
            st.session_state.show_exit_confirm = False
            st.rerun()

    if "show_delete_confirm" not in st.session_state:
        st.session_state.show_delete_confirm = False

    if st.button("🗑️ 删除本次对话", use_container_width=True):
        st.session_state.show_delete_confirm = True

    if st.session_state.show_delete_confirm:
        st.warning("⚠️ 确定要删除本次对话吗？此操作不可恢复，所有当前对话内容将被清除。")
        c_del1, c_del2 = st.columns(2)
        with c_del1:
            if st.button("✅ 确认删除", type="primary", use_container_width=True):
                st.session_state.show_delete_confirm = False
                delete_conversation_ui()
                st.rerun()
        with c_del2:
            if st.button("❌ 取消", use_container_width=True):
                st.session_state.show_delete_confirm = False
                st.rerun()

    st.divider()

    if st.button("🧹 重新开始", type="primary", use_container_width=True):
        for k in list(st.session_state.keys()):
            if not k.startswith("_") and k not in ("authenticated", "current_uid", "session_resolved"):
                del st.session_state[k]
        for k, v in LEARNING_DEFAULTS.items():
            st.session_state[k] = v
        auto_save_and_rerun()


# ============================================================================
# Step 1: AI 对话 —— 选课 + 画像（后台）
# ============================================================================
if st.session_state.step == 1:
    st.markdown('<p class="phase-title">Step 1: 开始学习 —— AI 对话了解你</p>', unsafe_allow_html=True)

    # ---- 对话完成 → 自动进入 Step 2 ----
    if st.session_state.get("_profile_complete"):
        st.success("✅ 学习画像分析完成，正在为你生成个性化学习方案...")
        st.session_state.step = 2
        auto_save_and_rerun()

    # ---- AI 对话区 ----
    for msg in st.session_state.dialogue[-10:]:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])

    # 初始化：AI 发第一条消息
    if not st.session_state.dialogue:
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
            st.session_state.dialogue.append({"role": "assistant", "content": full})

    # 用户输入
    user_input = st.chat_input("在这里和 AI 聊天...", key="step1_chat")
    if user_input:
        st.session_state.dialogue.append({"role": "user", "content": user_input})

        # 第一次回复后提取课程名
        if not st.session_state.course_name:
            extract_prompt = f"学生说: {user_input}\n提取学生想学的课程名称（1-3个词）。只输出课程名。"
            agents = create_agents()
            tmp_agent = agents.profile_agent()
            course_resp, _ = run_with_fallback(tmp_agent, extract_prompt)
            st.session_state.course_name = course_resp.strip().replace("《", "").replace("》", "").replace(" ", "")
            if not st.session_state.course_name:
                st.session_state.course_name = "未指定课程"

        agents = create_agents(course_name=st.session_state.course_name)
        profile_bot = agents.profile_agent()

        history_text = "\n".join([
            f"{'学生' if m['role'] == 'user' else 'AI'}: {m['content'][:400]}"
            for m in st.session_state.dialogue[-12:]
        ])

        # 找出还没填的画像维度
        missing_dims = [d for d in PROFILE_DIMENSIONS if not st.session_state.profile.get(d) or st.session_state.profile.get(d) == "待了解"]
        filled_dims = [d for d in PROFILE_DIMENSIONS if st.session_state.profile.get(d) and st.session_state.profile.get(d) != "待了解"]

        PROCESS_PROMPT = f"""学习画像分析师。课程:《{st.session_state.course_name}》

对话历史:
{history_text}

当前画像（已填维度: {', '.join(filled_dims) if filled_dims else '无'}）:
{json.dumps(st.session_state.profile, ensure_ascii=False)}

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
                result = {"profile": st.session_state.profile,
                          "next_question": "好的，我们继续聊聊~ 你觉得自己在学习中最容易卡在什么地方？"}

        # 后台更新画像（不展示）
        new_profile = result.get("profile", {})
        if new_profile:
            st.session_state.profile.update(new_profile)

        # 判断完成
        next_q = result.get("next_question", "")
        if "[PROFILE_COMPLETE]" in next_q or "[PROFILE_COMPLETE]" in content:
            st.session_state._profile_complete = True
            st.session_state.dialogue.append({
                "role": "assistant",
                "content": "好的，我对你的学习情况已经足够了解了！正在为你生成个性化学习方案..."
            })
        else:
            if next_q.strip():
                st.session_state.dialogue.append({"role": "assistant", "content": next_q})
        auto_save_and_rerun()



# ============================================================================
# Step 2: 对话式偏好提取 + 双层资源推荐
# ============================================================================
elif st.session_state.step == 2:
    st.markdown('<p class="phase-title">Step 2: 个性化学习资源</p>', unsafe_allow_html=True)
    st.caption(f"📖 课程：{st.session_state.course_name} | AI 对话了解你的偏好，双层资源精准推荐")

    if st.session_state.step2_agent is None:
        st.session_state.step2_agent = create_dialogue_agent(
            course_name=st.session_state.course_name,
            profile=st.session_state.profile
        )
        st.session_state.step2_messages = []
        st.session_state.step2_active = True

        # Phase 2: 如果 profile 完整且无问题需要追问，直接生成资源
        agent_temp = st.session_state.step2_agent
        if len(agent_temp.questions) == 0 and st.session_state.profile:
            st.session_state.resources = agent_temp.generate_report()
            st.session_state.step2_active = False
            st.session_state._refresh_resources = False
            st.session_state._refresh_resources_was_auto = True

    agent = st.session_state.step2_agent

    if st.session_state.step2_active:
        if not st.session_state.step2_messages:
            first_q = agent.get_first_question()
            st.session_state.step2_messages.append({"role": "assistant", "content": first_q})

        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.step2_messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        user_input = st.chat_input("在这里自然回答就可以了，比如「我喜欢看视频+动手写代码」...")
        if user_input:
            st.session_state.step2_messages.append({"role": "user", "content": user_input})
            result = agent.process_input(user_input)

            if result["is_complete"]:
                st.session_state.step2_active = False
                st.session_state.resources = agent.generate_report()
                st.session_state.step2_messages.append({
                    "role": "assistant",
                    "content": "好的，我已经了解你的学习偏好了！下面是我为你定制的双层资源推荐 👇"
                })
                auto_save_and_rerun()
            else:
                st.session_state.step2_messages.append({
                    "role": "assistant",
                    "content": result["next_question"]
                })
                auto_save_and_rerun()

    if not st.session_state.step2_active and st.session_state.resources:
        # Phase 2: 智能刷新提示
        if st.session_state.get("_refresh_resources_was_auto") and not st.session_state.step2_messages:
            st.success("🔄 已基于你的最新画像自动生成个性化资源推荐（无需重复对话）")
            st.session_state._refresh_resources_was_auto = False

        with st.expander("💬 查看偏好提取对话", expanded=False):
            for msg in st.session_state.step2_messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        resources = st.session_state.resources
        resources = re.sub(r'^##\s+(.+)', r'<div class="resource-section"><h3></h3>', resources, flags=re.MULTILINE)
        parts = resources.split('<div class="resource-section">')
        result = parts[0]
        for part in parts[1:]:
            next_div = part.find('<div class="resource-section">')
            if next_div >= 0:
                result += '<div class="resource-section">' + part[:next_div] + '</div>' + part[next_div:]
            else:
                result += '<div class="resource-section">' + part + '</div>'
        st.markdown(result, unsafe_allow_html=True)

        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("⬅ 返回修改画像", use_container_width=True):
                st.session_state._profile_complete = False
                st.session_state.resources = None
                st.session_state.step2_agent = None
                st.session_state.step2_messages = []
                st.session_state.step2_active = True
                st.session_state.step = 1
                auto_save_and_rerun()
        with c2:
            if st.button("🔄 重新对话", use_container_width=True):
                st.session_state.step2_agent = None
                st.session_state.step2_messages = []
                st.session_state.step2_active = True
                st.session_state.resources = None
                auto_save_and_rerun()
        with c3:
            if st.button("→ 进入路径规划", type="primary", use_container_width=True):
                st.session_state.step = 3
                auto_save_and_rerun()


# ============================================================================
# Step 3: 路径规划
# ============================================================================
elif st.session_state.step == 3:
    st.markdown('<p class="phase-title">Step 3: 学习路径规划</p>', unsafe_allow_html=True)
    st.caption(f"📖 课程：{st.session_state.course_name} | 精简高效的学习路径")

    # Phase 2: 智能刷新提示（在生成完成后显示）
    was_refresh = st.session_state.get("_refresh_roadmap", False)

    if not st.session_state.roadmap:
        with st.spinner("正在规划你的学习路径..."):
            agents = create_agents(
                course_name=st.session_state.course_name,
                student_info=st.session_state.profile
            )
            roadmap_agent = agents.roadmap_agent()
            profile_str = json.dumps(st.session_state.profile, ensure_ascii=False)
            # 提取 Step 2 资源报告中的偏好摘要
            resources_hint = ""
            if st.session_state.resources:
                # 取资源报告前 800 字符作为上下文（含画像表格 + 偏好信息）
                resources_hint = f"\n已推荐资源摘要:\n{st.session_state.resources[:800]}"
            prompt = f"""课程: {st.session_state.course_name}
学生画像: {profile_str}{resources_hint}

规划5-8步精简学习路径。输出Markdown表格:

| 步骤 | 难度 | 学习目标 | 推荐资源 |
|------|------|----------|----------|
| 1. xx | ★★ | xx | xx |

从易到难，关键节点设检查点，针对薄弱环节加强。利用已推荐资源中的偏好信息调整路径难度和资源类型。"""
            resp, _ = run_with_fallback(roadmap_agent, prompt)
            st.session_state.roadmap = resp
            st.session_state._refresh_roadmap = False
        auto_save_and_rerun()

    if was_refresh and st.session_state.roadmap:
        st.success("🔄 已根据你的最新学习状态重新规划路径")

    roadmap = st.session_state.roadmap

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-box"><div class="value">5-8</div><div class="label">学习步骤</div></div>', unsafe_allow_html=True)
    with col2:
        completed_dims = sum(1 for v in st.session_state.profile.values() if v and v != "待了解")
        st.markdown(f'<div class="metric-box"><div class="value">{completed_dims}/6</div><div class="label">画像维度</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><div class="value">{st.session_state.course_name[:4]}</div><div class="label">当前课程</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(roadmap)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⬅ 返回资源生成", use_container_width=True):
            st.session_state.step = 2
            auto_save_and_rerun()
    with c2:
        if st.button("→ 进入辅导", type="primary", use_container_width=True):
            st.session_state.step = 4
            auto_save_and_rerun()
    with c3:
        if st.button("📊 学习评估", use_container_width=True):
            st.session_state.step = 5
            auto_save_and_rerun()


# ============================================================================
# Step 4: 智能辅导 + RAG
# ============================================================================
elif st.session_state.step == 4:
    st.markdown('<p class="phase-title">Step 4: 智能辅导</p>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["💬 概念辅导", "📚 RAG 文档问答"])

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
                    course_name=st.session_state.course_name,
                    student_info=st.session_state.profile
                )
                tutor = agents.tutor_agent()
                profile_str = json.dumps(st.session_state.profile, ensure_ascii=False)

                history_text = ""
                for h in st.session_state.tutor_history[-4:]:
                    history_text += f'学生: {h["question"]}\nAI: {h["answer"][:300]}\n\n'

                prompt = f"""学生画像: {profile_str}
当前课程: {st.session_state.course_name}
补充信息: {context_hint if context_hint else '无'}

最近对话:
{history_text}

学生最新消息: {question}

根据上下文判断学生是在提问/回答测验/要求测试/拒绝测验，用对应的模式回应。
如果是回答测验，必须判断对错。答错时在回复末尾加一行:
[WEAKNESS:知识点|||学生答案|||正确答案]"""

                with st.status("辅导老师正在回答...", expanded=True) as status:
                    placeholder = st.empty()
                    full = ""
                    for chunk in stream_chat(tutor, prompt):
                        full += chunk
                        placeholder.markdown(full + "▌")
                    status.update(label="回答完成", state="complete")

                weakness_match = re.search(r'\[WEAKNESS:(.+?)\|\|\|(.+?)\|\|\|(.+?)\]', full)
                if weakness_match:
                    topic = weakness_match.group(1)
                    student_ans = weakness_match.group(2)
                    correct_ans = weakness_match.group(3)
                    full = re.sub(r'\n?\[WEAKNESS:.+?\]', '', full)

                    with st.spinner("正在分析薄弱点并生成补救方案..."):
                        wa = agents.weakness_agent()
                        wa_prompt = f"""课程: {st.session_state.course_name}
学生画像: {profile_str}
薄弱知识点: {topic}
学生错误回答: {student_ans}
正确答案: {correct_ans}
当前学习路径:
{st.session_state.roadmap[:1500] if st.session_state.roadmap else '未生成'}

分析薄弱点并生成补救方案。"""
                        wa_resp, _ = run_with_fallback(wa, wa_prompt)
                        full += "\n---\n\n## 📍 薄弱点分析与补救方案\n\n" + wa_resp
                        status.update(label="薄弱点分析完成", state="complete")

                    st.session_state.weakness_list.append({
                        "topic": topic,
                        "student_ans": student_ans,
                        "correct_ans": correct_ans,
                        "analysis": wa_resp[:500],
                        "time": datetime.now().strftime("%H:%M:%S"),
                    })

                placeholder.markdown(full)
                st.session_state.tutor_history.append({
                    "question": question,
                    "answer": full,
                    "time": datetime.now().strftime("%H:%M:%S"),
                })
                auto_save_and_rerun()

            if st.session_state.tutor_history:
                st.markdown("---")
                st.markdown("### 对话历史")
                for i, entry in enumerate(reversed(st.session_state.tutor_history)):
                    with st.expander(f"Q: {entry['question'][:50]}... ({entry['time']})", expanded=(i == 0)):
                        st.markdown(entry["answer"])

        with col2:
            st.markdown("### 学习统计")
            st.metric("互动次数", len(st.session_state.tutor_history))
            if st.session_state.weakness_list:
                st.markdown("### 🔴 薄弱环节")
                for w in reversed(st.session_state.weakness_list[-5:]):
                    st.caption(f"• {w['topic']} ({w['time']})")
            if st.session_state.profile:
                st.caption("AI 根据你的画像调整讲解方式")
                for dim in ["认知风格", "知识基础"]:
                    val = st.session_state.profile.get(dim, "")
                    if val and val != "待了解":
                        st.caption(f"• {dim}: {val}")

    with tab2:
        col_r1, col_r2 = st.columns([2, 1])

        with col_r1:
            st.markdown("### 基于教材提问")

            if st.session_state.rag_doc_count == 0:
                st.info("还没有上传教材文档。请在左侧栏上传PDF或TXT教材，然后在这里提问。")
            else:
                rag_question = st.text_area("输入问题",
                                             placeholder="比如：第三章的核心概念是什么？",
                                             height=100, key="rag_question")

                if st.button("🔍 搜索答案", type="primary", disabled=not rag_question.strip()):
                    with st.spinner("搜索中..."):
                        agents = create_agents(course_name=st.session_state.course_name)
                        relevant = st.session_state.rag_helper.query(rag_question, k=4)
                        context = "\n\n".join(relevant)

                        rag_bot = agents.rag_tutor_agent()
                        prompt = f"""## 教材检索内容
{context}

## 学生问题
{rag_question}

基于教材内容回答。没有的信息明确告知。引用时标注来源。"""

                        resp, _ = run_with_fallback(rag_bot, prompt)
                        st.session_state.rag_answer = resp
                    auto_save_and_rerun()

                if "rag_answer" in st.session_state and st.session_state.rag_answer:
                    st.markdown("### 答案")
                    st.markdown(st.session_state.rag_answer)

        with col_r2:
            st.markdown("### 知识库状态")
            st.metric("文档块数", st.session_state.rag_doc_count)

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⬅ 返回路径规划", use_container_width=True):
            st.session_state.step = 3
            auto_save_and_rerun()
    with c2:
        if st.button("📊 学习评估", use_container_width=True):
            st.session_state.step = 5
            auto_save_and_rerun()


# ============================================================================
# Step 5: 学习评估（加分项，可选）
# ============================================================================
elif st.session_state.step == 5:
    st.markdown('<p class="phase-title">Step 5: 学习评估（加分项）</p>', unsafe_allow_html=True)
    st.info("💡 这是可选加分项。DeepSeek 评估 + 星火交叉验证，给你最客观的学习诊断。")

    if not st.session_state.eval_report:
        eval_data = f"""## 学生画像
{json.dumps(st.session_state.profile, ensure_ascii=False, indent=2)}

## 学习资源摘要
{st.session_state.resources[:2000] if st.session_state.resources else '未生成'}

## 学习路径摘要
{st.session_state.roadmap[:2000] if st.session_state.roadmap else '未生成'}

## 辅导历史
{json.dumps([{'q': h['question'], 't': h['time']} for h in st.session_state.tutor_history[-5:]], ensure_ascii=False) if st.session_state.tutor_history else '暂无提问'}"""

        agents = create_agents(course_name=st.session_state.course_name)
        with st.spinner("DeepSeek + 星火 交叉验证评估中..."):
            result = agents.cross_validate(eval_data)
            report = result["merged"]
            st.session_state._glm_raw = result.get("glm")
            st.session_state._spark_raw = result.get("spark")
            st.session_state._spark_label = result.get("spark_label", "星火")

        st.session_state.eval_report = report
        auto_save_and_rerun()

    report = st.session_state.eval_report
    st.markdown(report)

    if st.session_state.get("_glm_raw") and st.session_state.get("_spark_raw"):
        with st.expander("查看双模型原始报告"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### DeepSeek 评估")
                st.markdown(st.session_state._glm_raw)
            with col_b:
                spark_label = st.session_state.get("_spark_label", "星火")
                st.markdown(f"#### {spark_label} 评估")
                st.markdown(st.session_state._spark_raw)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⬅ 返回辅导", use_container_width=True):
            st.session_state.step = 4
            auto_save_and_rerun()
    with c2:
        if st.button("🔄 重新开始", use_container_width=True):
            for k in list(st.session_state.keys()):
                if not k.startswith("_") and k not in ("authenticated", "current_uid", "session_resolved"):
                    del st.session_state[k]
            for k, v in LEARNING_DEFAULTS.items():
                st.session_state[k] = v
            auto_save_and_rerun()


# ============================================================================
# 页脚
# ============================================================================
st.markdown('<div class="footer">A3 个性化学习系统 v3 | 六智能体协同 | UID: ' + str(st.session_state.current_uid) + '</div>', unsafe_allow_html=True)
