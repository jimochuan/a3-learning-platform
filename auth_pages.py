"""Auth page renderers for A3 v3."""
import streamlit as st
from auth import SECURITY_QUESTION, verify_password, generate_uid, hash_password, verify_security_answer, validate_uid, is_uid_available
from user_store import load_user, save_user, create_user, list_all_uids, save_checkpoint, list_all_users_full, delete_user
from login_state import LoginAttemptManager

def render_login_page():
    st.markdown(
        '<div class="auth-header">'
        '<h1>A3 个性化学习系统</h1>'
        '<p class="auth-subtitle">六智能体协同 · 个性化学习</p>'
        '</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        uid = st.text_input("UID", max_chars=20, placeholder="输入你的UID")
        password = st.text_input("密码", type="password", placeholder="输入密码")

        # 根据输入 UID 实时检测锁定状态（用于禁用按钮和倒计时提示）
        is_locked = False
        lock_remaining = 0
        show_hint = st.session_state.get("_show_pwd_hint", False)
        if uid and validate_uid(uid)[0]:
            user_data_pre = load_user(uid)
            if user_data_pre:
                is_locked = LoginAttemptManager.is_locked(user_data_pre)
                lock_remaining = LoginAttemptManager.remaining_lock_seconds(user_data_pre)
                if not is_locked:
                    show_hint = show_hint or LoginAttemptManager.should_show_hint(user_data_pre)

        submitted = st.form_submit_button("登 录", type="primary", use_container_width=True, disabled=is_locked)

        # 锁定状态倒计时提示
        if is_locked:
            st.markdown(
                f'<div class="auth-msg-error" style="margin-top:0.5rem;">'
                f'⏳ 账户已锁定 {lock_remaining} 秒。请等待或点击下方「忘记密码」重置'
                f'</div>', unsafe_allow_html=True)

        # 第4次失败后显示忘记密码提示
        if show_hint and not is_locked:
            st.markdown(
                f'<div class="auth-msg-error" style="margin-top:0.5rem;background:#fffbeb;border:1px solid #fcd34d;color:#92400e;">'
                f'💡 忘记密码了？点击下方「忘记密码」按钮通过密保答案重置'
                f'</div>', unsafe_allow_html=True)

        if submitted:
            if not uid or not password:
                st.session_state.auth_msg = "请输入 UID 和密码"
                st.session_state.auth_msg_type = "error"
            else:
                uid_valid, uid_err = validate_uid(uid)
                if not uid_valid:
                    st.session_state.auth_msg = uid_err
                    st.session_state.auth_msg_type = "error"
                else:
                    # 清理过期锁（锁定期已过则自动解锁）
                    LoginAttemptManager.clear_if_expired(uid)
                    user_data = load_user(uid)
                    if user_data is None:
                        st.session_state.auth_msg = "用户不存在，请先注册"
                        st.session_state.auth_msg_type = "error"
                    elif LoginAttemptManager.is_locked(user_data):
                        remaining = LoginAttemptManager.remaining_lock_seconds(user_data)
                        st.session_state.auth_msg = f"账户已锁定，请等待 {remaining} 秒。或点击下方「忘记密码」重置"
                        st.session_state.auth_msg_type = "error"
                    elif not verify_password(password, user_data.get("password", "")):
                        # 记录失败（仅当 UID 存在时）
                        updated = LoginAttemptManager.record_failure(uid)
                        if updated and LoginAttemptManager.is_locked(updated):
                            st.session_state.auth_msg = "账户已锁定 1 分钟。请等待或点击下方「忘记密码」重置"
                            st.session_state.auth_msg_type = "error"
                        elif updated and LoginAttemptManager.should_show_hint(updated):
                            st.session_state.auth_msg = "密码错误 — 忘记密码了？点击下方按钮重置"
                            st.session_state.auth_msg_type = "error"
                            st.session_state._show_pwd_hint = True
                        else:
                            st.session_state.auth_msg = "密码错误"
                            st.session_state.auth_msg_type = "error"
                    else:
                        # 登录成功 → 解锁账户
                        LoginAttemptManager.unlock(uid)
                        st.session_state.authenticated = True
                        st.session_state.current_uid = uid
                        st.session_state.session_resolved = False
                        save_checkpoint(uid)
                        st.session_state.auth_msg = ""
                        if "_show_pwd_hint" in st.session_state:
                            del st.session_state._show_pwd_hint
                        st.rerun()

    # Error / success message (inside card)
    if st.session_state.auth_msg:
        cls = "auth-msg-success" if st.session_state.auth_msg_type == "success" else "auth-msg-error"
        st.markdown(f'<div class="{cls}">{st.session_state.auth_msg}</div>', unsafe_allow_html=True)


    # ---- Footer ----
    st.markdown('<div class="auth-footer">', unsafe_allow_html=True)
    st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)
    _, c1, c2, c3, _ = st.columns([1.5, 1, 1, 1, 1.5])
    with c1:
        if st.button("注册新用户", key="login_reg"):
            st.session_state.auth_page = "register"; st.session_state.auth_msg = ""
            for k in ("_show_pwd_hint",):
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    with c2:
        if st.button("忘记密码", key="login_fgt"):
            st.session_state.auth_page = "forgot_pwd"; st.session_state.auth_msg = ""
            for k in ("_show_pwd_hint",):
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    with c3:
        if st.button("🔧 管理", key="login_adm"):
            st.session_state.auth_page = "admin"; st.session_state.auth_msg = ""
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_register_page():
    # ---- Card: brand + form ----
    st.markdown(
        '<div class="auth-header">'
        '<h1>A3 个性化学习系统</h1>'
        '<p class="auth-subtitle">创建新账号</p>'
        '</div>', unsafe_allow_html=True)

    with st.form("register_form"):
        new_uid = st.text_input("设置 UID", max_chars=20, placeholder="3-20位")
        password = st.text_input("设置密码", type="password", placeholder="设置登录密码")
        confirm_pwd = st.text_input("确认密码", type="password", placeholder="再次输入密码")
        sec_answer = st.text_input(f"密保问题：{SECURITY_QUESTION}", placeholder="选择一个不容易被他人猜到的答案")
        st.caption("💡 提示：答案不一定要是真实朋友名字，选择一个只有你知道的答案会更安全")
        submitted = st.form_submit_button("注 册", type="primary", use_container_width=True)
        if submitted:
            if not new_uid or not password or not confirm_pwd or not sec_answer:
                st.session_state.auth_msg = "请填写所有字段"
                st.session_state.auth_msg_type = "error"
            else:
                uid_valid, uid_err = validate_uid(new_uid)
                if not uid_valid:
                    st.session_state.auth_msg = uid_err
                    st.session_state.auth_msg_type = "error"
                elif not is_uid_available(new_uid):
                    st.session_state.auth_msg = "该 UID 已被注册，请换一个"
                    st.session_state.auth_msg_type = "error"
                elif len(password) < 4:
                    st.session_state.auth_msg = "密码至少4个字符"
                    st.session_state.auth_msg_type = "error"
                elif password != confirm_pwd:
                    st.session_state.auth_msg = "两次密码输入不一致"
                    st.session_state.auth_msg_type = "error"
                else:
                    create_user(new_uid, password, sec_answer)
                    st.session_state.auth_msg = f"注册成功！你的 UID 是 {new_uid}，请牢记"
                    st.session_state.auth_msg_type = "success"
                    st.session_state._reg_uid = new_uid
                    st.rerun()

    # Error / success message (inside card)
    if st.session_state.auth_msg:
        cls = "auth-msg-success" if st.session_state.auth_msg_type == "success" else "auth-msg-error"
        st.markdown(f'<div class="{cls}">{st.session_state.auth_msg}</div>', unsafe_allow_html=True)
        if st.session_state.get("_reg_uid"):
            st.markdown(f'<div class="uid-display">{st.session_state._reg_uid}</div>', unsafe_allow_html=True)
            st.info("请务必记住你的 UID，后续登录需要用到")


    # ---- Footer ----
    st.markdown('<div class="auth-footer">', unsafe_allow_html=True)
    st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)
    _, c, _ = st.columns([2, 1, 2])
    with c:
        if st.button("返回登录", key="reg_back"):
            st.session_state.auth_page = "login"; st.session_state.auth_msg = ""
            if "_reg_uid" in st.session_state: del st.session_state._reg_uid
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_forgot_pwd_page():
    if not st.session_state.get("_pwd_reset_verified"):
        # ---- Step 1: verify identity ----
        st.markdown(
            '<div class="auth-header">'
            '<h1>A3 个性化学习系统</h1>'
            '<p class="auth-subtitle">重置密码 · 验证身份</p>'
            '</div>', unsafe_allow_html=True)

        with st.form("forgot_pwd_verify"):
            uid = st.text_input("UID", max_chars=20, placeholder="输入你的UID")
            sec_answer = st.text_input(f"密保问题：{SECURITY_QUESTION}", placeholder="输入注册时填写的答案")

            # 实时检测锁定状态
            is_locked = False
            lock_remaining = 0
            show_hint = False
            if uid and validate_uid(uid)[0]:
                user_data_pre = load_user(uid)
                if user_data_pre:
                    is_locked = LoginAttemptManager.is_locked(user_data_pre)
                    lock_remaining = LoginAttemptManager.remaining_lock_seconds(user_data_pre)
                    if not is_locked:
                        show_hint = LoginAttemptManager.should_show_hint(user_data_pre)

            submitted = st.form_submit_button("验证身份", type="primary", use_container_width=True)

            # 锁定状态提示（但不阻止验证——这是恢复通道）
            if is_locked:
                st.markdown(
                    f'<div class="auth-msg-error" style="margin-top:0.5rem;">'
                    f'⏳ 账户处于锁定状态（剩余 {lock_remaining} 秒）。验证通过后将自动解锁'
                    f'</div>', unsafe_allow_html=True)

            # 接近锁定时显示提示
            if show_hint and not is_locked:
                st.markdown(
                    f'<div class="auth-msg-error" style="margin-top:0.5rem;background:#fffbeb;border:1px solid #fcd34d;color:#92400e;">'
                    f'⚠️ 注意：连续验证失败 {LoginAttemptManager.HINT_AT} 次后将锁定账户'
                    f'</div>', unsafe_allow_html=True)

            if submitted:
                if not uid or not sec_answer:
                    st.session_state.auth_msg = "请填写 UID 和密保答案"
                    st.session_state.auth_msg_type = "error"
                else:
                    uid_valid, uid_err = validate_uid(uid)
                    if not uid_valid:
                        st.session_state.auth_msg = uid_err
                        st.session_state.auth_msg_type = "error"
                    else:
                        LoginAttemptManager.clear_if_expired(uid)
                        user_data = load_user(uid)
                        if user_data is None:
                            st.session_state.auth_msg = "用户不存在"
                            st.session_state.auth_msg_type = "error"
                        elif LoginAttemptManager.is_locked(user_data):
                            remaining = LoginAttemptManager.remaining_lock_seconds(user_data)
                            if not verify_security_answer(sec_answer, user_data.get("security_answer", "")):
                                st.session_state.auth_msg = f"密保答案错误。账户已锁定（剩余 {remaining} 秒），请等待后重试"
                                st.session_state.auth_msg_type = "error"
                            else:
                                LoginAttemptManager.unlock(uid)
                                st.session_state._pwd_reset_verified = True
                                st.session_state._pwd_reset_uid = uid
                                st.session_state.auth_msg = "身份验证通过，账户已解锁"
                                st.session_state.auth_msg_type = "success"
                                st.rerun()
                        elif not verify_security_answer(sec_answer, user_data.get("security_answer", "")):
                            updated = LoginAttemptManager.record_failure(uid)
                            if updated and LoginAttemptManager.is_locked(updated):
                                st.session_state.auth_msg = "密保验证失败次数过多，账户已锁定 1 分钟。请等待后重试"
                                st.session_state.auth_msg_type = "error"
                            elif updated and LoginAttemptManager.should_show_hint(updated):
                                st.session_state.auth_msg = "密保答案错误 — 已失败多次，请仔细回忆或等待后重试"
                                st.session_state.auth_msg_type = "error"
                            else:
                                st.session_state.auth_msg = "密保答案错误"
                                st.session_state.auth_msg_type = "error"
                        else:
                            LoginAttemptManager.unlock(uid)
                            st.session_state._pwd_reset_verified = True
                            st.session_state._pwd_reset_uid = uid
                            st.session_state.auth_msg = ""
                            st.rerun()

        # Error / success message (inside card)
        if st.session_state.auth_msg:
            cls = "auth-msg-success" if st.session_state.auth_msg_type == "success" else "auth-msg-error"
            st.markdown(f'<div class="{cls}">{st.session_state.auth_msg}</div>', unsafe_allow_html=True)

    else:
        # ---- Step 2: set new password ----
        st.markdown(
            '<div class="auth-header">'
            '<h1>A3 个性化学习系统</h1>'
            '<p class="auth-subtitle">设置新密码</p>'
            '</div>', unsafe_allow_html=True)

        with st.form("forgot_pwd_reset"):
            st.info(f"身份验证通过（UID: {st.session_state._pwd_reset_uid}），请设置新密码")
            new_pwd = st.text_input("新密码", type="password", placeholder="设置新密码")
            confirm_pwd = st.text_input("确认新密码", type="password", placeholder="再次输入")
            submitted = st.form_submit_button("重置密码", type="primary", use_container_width=True)
            if submitted:
                if not new_pwd or not confirm_pwd:
                    st.session_state.auth_msg = "请填写密码"; st.session_state.auth_msg_type = "error"
                elif len(new_pwd) < 4:
                    st.session_state.auth_msg = "密码至少4个字符"; st.session_state.auth_msg_type = "error"
                elif new_pwd != confirm_pwd:
                    st.session_state.auth_msg = "两次密码输入不一致"; st.session_state.auth_msg_type = "error"
                else:
                    uid = st.session_state._pwd_reset_uid
                    user_data = load_user(uid)
                    user_data["password"] = new_pwd
                    save_user(uid, user_data)
                    LoginAttemptManager.unlock(uid)
                    st.session_state.auth_msg = "密码重置成功！请返回登录"
                    st.session_state.auth_msg_type = "success"
                    del st.session_state._pwd_reset_verified
                    del st.session_state._pwd_reset_uid
                    st.session_state.auth_page = "login"
                    st.rerun()

        # Error / success message (inside card)
        if st.session_state.auth_msg:
            cls = "auth-msg-success" if st.session_state.auth_msg_type == "success" else "auth-msg-error"
            st.markdown(f'<div class="{cls}">{st.session_state.auth_msg}</div>', unsafe_allow_html=True)


    # ---- Footer (shown in both steps) ----
    st.markdown('<div class="auth-footer">', unsafe_allow_html=True)
    st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)
    _, c, _ = st.columns([2, 1, 2])
    with c:
        if st.button("返回登录", key="fgt_back"):
            st.session_state.auth_page = "login"; st.session_state.auth_msg = ""
            for k in ("_pwd_reset_verified", "_pwd_reset_uid"):
                if k in st.session_state: del st.session_state[k]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_admin_page():
    """管理员面板 —— 查看所有用户明文数据 + 一键操作"""
    st.markdown(
        '<div class="auth-header">'
        '<h1>A3 个性化学习系统</h1>'
        '<p class="auth-subtitle">管理员面板</p>'
        '</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div style="max-width:1200px;margin:0 auto;padding:1rem;">', unsafe_allow_html=True)

        # 警告横幅
        st.warning("⚠️ 用户数据包含明文密码，请勿在公共场合打开此页面")

        # 加载所有用户
        users = list_all_users_full()
        if not users:
            st.info("暂无注册用户")
        else:
            st.markdown(f"### 用户列表（共 {len(users)} 人）")

            # 构建表格数据
            for i, u in enumerate(users):
                uid = u.get("uid", "?")
                password = u.get("password", "")
                sec_answer = u.get("security_answer", "")
                is_locked = LoginAttemptManager.is_locked(u)
                fail_count = u.get("login_fail_count", 0)
                lock_remaining = LoginAttemptManager.remaining_lock_seconds(u)
                last_save = u.get("last_save_time", "无")
                has_data = bool(u.get("history_progress") or u.get("session_records") or u.get("user_portrait"))

                # 用户卡片
                with st.expander(f"{'🔒' if is_locked else '👤'} UID: {uid} | 密码: {password} | 密保: {sec_answer} | {'🔒 锁定中' if is_locked else '✅ 正常'}", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("UID", uid)
                        st.metric("失败次数", fail_count)
                    with col2:
                        st.metric("密码", password, delta=None, delta_color="off")
                        if is_locked:
                            st.metric("锁定剩余", f"{lock_remaining}秒")
                    with col3:
                        st.metric("密保答案", sec_answer)
                        st.caption(f"最后活跃: {last_save}")

                    if has_data:
                        st.caption("📚 有学习数据")
                    else:
                        st.caption("🆕 新用户，无学习数据")

                    # 操作按钮
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if is_locked:
                            if st.button(f"🔓 解锁", key=f"unlock_{uid}", use_container_width=True):
                                LoginAttemptManager.unlock(uid)
                                st.session_state.auth_msg = f"用户 {uid} 已解锁"
                                st.session_state.auth_msg_type = "success"
                                st.rerun()
                    with c2:
                        if st.button(f"🔑 重置密码", key=f"reset_pwd_{uid}", use_container_width=True):
                            new_pwd = "a3v3"
                            user_data = load_user(uid)
                            if user_data:
                                user_data["password"] = new_pwd
                                save_user(uid, user_data)
                                st.session_state.auth_msg = f"用户 {uid} 密码已重置为: {new_pwd}"
                                st.session_state.auth_msg_type = "success"
                                st.rerun()
                    with c3:
                        if not has_data:
                            if st.button(f"🗑️ 删除", key=f"delete_{uid}", use_container_width=True):
                                delete_user(uid)
                                st.session_state.auth_msg = f"用户 {uid} 已删除"
                                st.session_state.auth_msg_type = "success"
                                st.rerun()

            # 汇总表（紧凑模式）
            st.markdown("---")
            st.markdown("### 紧凑视图")
            import pandas as pd
            table_data = []
            for u in users:
                table_data.append({
                    "UID": u.get("uid", ""),
                    "密码": u.get("password", ""),
                    "密保答案": u.get("security_answer", ""),
                    "锁定": "🔒" if LoginAttemptManager.is_locked(u) else "✗",
                    "失败": u.get("login_fail_count", 0),
                    "剩余秒": LoginAttemptManager.remaining_lock_seconds(u),
                    "最后活跃": u.get("last_save_time", "")[:16] if u.get("last_save_time") else "",
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 批量操作
            st.markdown("---")
            st.markdown("### 批量操作")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("🔓 解锁全部用户", use_container_width=True):
                    for u in users:
                        LoginAttemptManager.unlock(u.get("uid", ""))
                    st.session_state.auth_msg = "所有用户已解锁"
                    st.session_state.auth_msg_type = "success"
                    st.rerun()
            with bc2:
                if st.button("🔄 刷新数据", use_container_width=True):
                    st.rerun()

        if st.session_state.get("auth_msg"):
            cls = "auth-msg-success" if st.session_state.auth_msg_type == "success" else "auth-msg-error"
            st.markdown(f'<div class="{cls}">{st.session_state.auth_msg}</div>', unsafe_allow_html=True)

        st.markdown("---")
        if st.button("返回登录", use_container_width=True):
            st.session_state.auth_page = "login"; st.session_state.auth_msg = ""
            st.rerun()

