"""
=============================================================================
A3 v3 用户认证模块
UID 生成 · UID 校验 · 明文密码 · 登录验证 · 密保验证 · 密码重置
=============================================================================
"""
import random
import re
from typing import Optional, Tuple


# ============================================================================
# UID 校验规则（数字+字母，3-20位）
# ============================================================================
UID_MIN_LEN = 3
UID_MAX_LEN = 20
UID_PATTERN = re.compile(r'^[a-zA-Z0-9]{3,20}$')


def validate_uid(uid: str) -> Tuple[bool, str]:
    """校验 UID 格式

    Args:
        uid: 待校验的 UID 字符串

    Returns:
        (is_valid, error_message) — is_valid 为 True 表示格式正确
    """
    if not uid:
        return False, "请输入 UID"
    if len(uid) < UID_MIN_LEN or len(uid) > UID_MAX_LEN:
        return False, f"UID 长度需在 {UID_MIN_LEN}-{UID_MAX_LEN} 位之间"
    if not UID_PATTERN.match(uid):
        return False, "UID 只能包含字母和数字"
    return True, ""


def is_uid_available(uid: str) -> bool:
    """检查 UID 是否未被注册（不加载 user_store 到 auth 模块级别以避免循环导入）"""
    from user_store import load_user
    return load_user(uid) is None


# ============================================================================
# UID 生成（保留，供管理员面板等场景使用）
# ============================================================================
def generate_uid(existing_uids: set) -> str:
    """生成唯一 4 位数字 UID（与其他用户不重复）

    Args:
        existing_uids: 已存在的 UID 集合

    Returns:
        4 位数字字符串，如 "1001"
    """
    for _ in range(10000):
        uid = str(random.randint(1000, 9999))
        if uid not in existing_uids:
            return uid
    for i in range(1000, 10000):
        uid = str(i)
        if uid not in existing_uids:
            return uid
    raise RuntimeError("所有 4 位 UID 已用完（9000 个用户），请联系管理员")


# ============================================================================
# 密码处理（明文存储）
# ============================================================================
def hash_password(password: str) -> str:
    """存储密码（明文）

    直接返回明文密码。函数名保持 hash_password 以兼容旧调用方。

    Args:
        password: 明文密码

    Returns:
        明文密码（去首尾空格）
    """
    return password.strip()


def verify_password(password: str, stored_password: str) -> bool:
    """验证密码是否匹配（直接字符串比较）

    Args:
        password: 用户输入的密码
        stored_password: 存储的密码

    Returns:
        True 如果密码正确
    """
    return password == stored_password


# ============================================================================
# 密保处理（明文存储）
# ============================================================================
SECURITY_QUESTION = "我的好朋友是谁？"


def verify_security_answer(user_input: str, stored_answer: str) -> bool:
    """验证密保答案（大小写不敏感，去首尾空格）

    Args:
        user_input: 用户输入的答案
        stored_answer: 存储的答案

    Returns:
        True 如果匹配
    """
    return user_input.strip().lower() == stored_answer.strip().lower()


# ============================================================================
# 登录验证（供 app.py 调用）
# ============================================================================
def validate_login(uid: str, password: str, user_data: Optional[dict]) -> bool:
    """验证登录凭证

    Args:
        uid: 用户输入的 UID
        password: 用户输入的密码
        user_data: 从 JSON 加载的用户数据，None 表示用户不存在

    Returns:
        True 如果验证通过
    """
    if user_data is None:
        return False
    stored_password = user_data.get("password", "")
    return verify_password(password, stored_password)
