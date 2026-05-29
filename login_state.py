"""
=============================================================================
A3 v3 登录状态管理 —— LoginAttemptManager
纯逻辑类，无 Streamlit 依赖，可独立单测
=============================================================================
"""
from datetime import datetime, timedelta
from typing import Optional


class LoginAttemptManager:
    """登录失败计数与账户锁定管理

    所有方法通过 atomic_update 安全读写用户 JSON，
    不直接操作文件，不依赖 Streamlit。
    """

    MAX_ATTEMPTS = 5       # 最大失败次数，超过即锁定
    HINT_AT = 4            # 第几次失败后显示「忘记密码？」提示
    LOCK_SECONDS = 60      # 锁定时长（秒）

    # ------------------------------------------------------------------
    # 读取方法（不修改 JSON，仅从已加载的 user_data 判断）
    # ------------------------------------------------------------------

    @staticmethod
    def is_locked(user_data: dict) -> bool:
        """检查账户是否在锁定期内。

        Args:
            user_data: 从 JSON 加载的用户数据字典

        Returns:
            True 如果当前时间 < locked_until
        """
        locked_until = user_data.get("locked_until")
        if not locked_until:
            return False
        try:
            lock_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            return datetime.now() < lock_time
        except (ValueError, TypeError):
            return False

    @staticmethod
    def should_show_hint(user_data: dict) -> bool:
        """是否应该在密码框旁显示「忘记密码？」提示。

        条件：fail_count 达到 HINT_AT 但未达到 MAX_ATTEMPTS。
        锁定后不显示 hint（改为显示锁定提示）。

        Args:
            user_data: 从 JSON 加载的用户数据字典

        Returns:
            True 如果应该显示提示
        """
        count = user_data.get("login_fail_count", 0)
        return LoginAttemptManager.HINT_AT <= count < LoginAttemptManager.MAX_ATTEMPTS

    @staticmethod
    def remaining_lock_seconds(user_data: dict) -> int:
        """剩余锁定时长（秒）。

        Args:
            user_data: 从 JSON 加载的用户数据字典

        Returns:
            剩余秒数，未锁定返回 0
        """
        locked_until = user_data.get("locked_until")
        if not locked_until:
            return 0
        try:
            lock_time = datetime.strptime(locked_until, "%Y-%m-%d %H:%M:%S")
            remaining = (lock_time - datetime.now()).total_seconds()
            return max(0, int(remaining))
        except (ValueError, TypeError):
            return 0

    # ------------------------------------------------------------------
    # 写入方法（通过 atomic_update 安全修改 JSON）
    # ------------------------------------------------------------------

    @staticmethod
    def record_failure(uid: str) -> Optional[dict]:
        """记录一次登录失败。

        递增 login_fail_count；达到 MAX_ATTEMPTS 时设置 locked_until。

        Args:
            uid: 用户 UID

        Returns:
            更新后的用户数据，或 None（用户不存在）
        """
        from user_store import atomic_update

        def _update(user_data):
            count = user_data.get("login_fail_count", 0) + 1
            user_data["login_fail_count"] = count
            if count >= LoginAttemptManager.MAX_ATTEMPTS:
                user_data["locked_until"] = (
                    datetime.now() + timedelta(seconds=LoginAttemptManager.LOCK_SECONDS)
                ).strftime("%Y-%m-%d %H:%M:%S")
            return user_data

        return atomic_update(uid, _update)

    @staticmethod
    def unlock(uid: str) -> Optional[dict]:
        """解锁账户：清零 fail_count，删除 locked_until。

        在以下场景调用：
        - 登录成功
        - 通过密保重置密码
        - 锁定期自然到期后首次操作

        Args:
            uid: 用户 UID

        Returns:
            更新后的用户数据，或 None
        """
        from user_store import atomic_update

        def _update(user_data):
            user_data["login_fail_count"] = 0
            user_data["locked_until"] = None
            return user_data

        return atomic_update(uid, _update)

    @staticmethod
    def clear_if_expired(uid: str) -> Optional[dict]:
        """锁定期已过 → 自动解锁。锁定期未过 → 不做任何操作。

        应在每次登录验证前调用，确保过期锁不阻止合法用户。

        Args:
            uid: 用户 UID

        Returns:
            更新后的用户数据，或 None
        """
        from user_store import load_user

        user_data = load_user(uid)
        if user_data is None:
            return None
        if not LoginAttemptManager.is_locked(user_data):
            locked_until = user_data.get("locked_until")
            if locked_until:
                # 锁已过期，清理
                return LoginAttemptManager.unlock(uid)
        return user_data
