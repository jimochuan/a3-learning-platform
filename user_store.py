"""
=============================================================================
A3 v3 用户数据存储模块
JSON 文件读写 · filelock 并发锁 · 检查点管理 · 用户搜索
=============================================================================
"""
import json
import logging
import os
import shutil
import time
from datetime import datetime
from typing import Optional

from filelock import FileLock
from auth import SECURITY_QUESTION

logger = logging.getLogger(__name__)

# ============================================================================
# 路径配置
# ============================================================================
USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "user_data")
os.makedirs(USER_DATA_DIR, exist_ok=True)


def _user_file_path(uid: str) -> str:
    """获取用户 JSON 文件路径"""
    return os.path.join(USER_DATA_DIR, f"uid_{uid}.json")


def _checkpoint_path(uid: str) -> str:
    """获取用户检查点文件路径"""
    return os.path.join(USER_DATA_DIR, f"uid_{uid}.checkpoint.json")


def _lock_path(uid: str) -> str:
    """获取文件锁路径"""
    return os.path.join(USER_DATA_DIR, f"uid_{uid}.lock")


# ============================================================================
# 原子写入
# ============================================================================
def _atomic_write(filepath: str, data: dict) -> None:
    """原子写入 JSON：先写临时文件，再 rename（防止写一半崩溃导致数据损坏）

    在 Windows 上 os.replace 可能因文件短暂被占用而失败，自动重试最多 3 次。
    """
    import tempfile
    dirname = os.path.dirname(filepath)
    with tempfile.NamedTemporaryFile(mode="w", dir=dirname, delete=False,
                                     suffix=".tmp", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        tmpname = f.name
    for attempt in range(3):
        try:
            os.replace(tmpname, filepath)  # 原子操作
            return
        except PermissionError:
            if attempt < 2:
                time.sleep(0.05 * (attempt + 1))  # 递增等待
            else:
                raise


# ============================================================================
# 带锁的用户数据操作
# ============================================================================
def load_user(uid: str) -> Optional[dict]:
    """加载用户数据

    Args:
        uid: 用户 UID

    Returns:
        用户数据字典；用户不存在返回 None
    """
    path = _user_file_path(uid)
    lock = FileLock(_lock_path(uid), timeout=5)
    try:
        with lock:
            if not os.path.exists(path):
                return None
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("load_user(%s) failed: %s", uid, e)
        return None


def save_user(uid: str, data: dict) -> None:
    """保存用户数据（带文件锁 + 原子写入）

    Args:
        uid: 用户 UID
        data: 用户数据字典
    """
    path = _user_file_path(uid)
    lock = FileLock(_lock_path(uid), timeout=5)
    data["last_save_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with lock:
        _atomic_write(path, data)


def create_user(uid: str, password: str, security_answer: str) -> dict:
    """创建新用户（明文存储密码和密保答案）

    Args:
        uid: 唯一 4 位数字 UID
        password: 明文密码
        security_answer: 密保答案（明文）

    Returns:
        新用户数据字典
    """
    data = {
        "uid": uid,
        "password": password,
        "security_question": SECURITY_QUESTION,
        "security_answer": security_answer.strip(),
        "latest_progress": "",
        "history_progress": [],
        "user_portrait": {},
        "session_records": [],
        "last_save_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_user(uid, data)
    return data


def delete_user(uid: str) -> None:
    """删除用户数据（含检查点和锁文件）

    Args:
        uid: 用户 UID
    """
    lock = FileLock(_lock_path(uid), timeout=5)
    with lock:
        for p in [_user_file_path(uid), _checkpoint_path(uid)]:
            if os.path.exists(p):
                os.remove(p)
    lock_path = _lock_path(uid)
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except (PermissionError, OSError):
        pass


# ============================================================================
# 检查点管理（用于"不保存退出 → 回滚"）
# ============================================================================
def save_checkpoint(uid: str) -> None:
    """创建检查点：复制当前 JSON 作为检查点"""
    src = _user_file_path(uid)
    dst = _checkpoint_path(uid)
    lock = FileLock(_lock_path(uid), timeout=5)
    with lock:
        if os.path.exists(src):
            temp_dst = dst + ".tmp"
            shutil.copy2(src, temp_dst)
            for attempt in range(3):
                try:
                    os.replace(temp_dst, dst)
                    break
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.05 * (attempt + 1))
                    else:
                        raise


def delete_checkpoint(uid: str) -> None:
    """删除检查点文件"""
    cp = _checkpoint_path(uid)
    if os.path.exists(cp):
        os.remove(cp)


def has_checkpoint(uid: str) -> bool:
    """检查是否存在检查点"""
    return os.path.exists(_checkpoint_path(uid))


def rollback_to_checkpoint(uid: str) -> Optional[dict]:
    """回滚到检查点版本

    Returns:
        检查点数据；无检查点返回 None
    """
    cp = _checkpoint_path(uid)
    if not os.path.exists(cp):
        return None
    with open(cp, "r", encoding="utf-8") as f:
        data = json.load(f)
    save_user(uid, data)
    delete_checkpoint(uid)
    return data


# ============================================================================
# 原子更新（消除读-改-写竞态）
# ============================================================================
def atomic_update(uid: str, update_fn) -> Optional[dict]:
    """在单个锁内完成 读取→修改→写入，消除 auto_save 竞态窗口

    Args:
        uid: 用户 UID
        update_fn: Callable[[dict], Optional[dict]]，接收用户数据，返回修改后的数据
                   （返回 None 表示放弃更新）

    Returns:
        更新后的用户数据；用户不存在或 update_fn 返回 None 时返回 None
    """
    path = _user_file_path(uid)
    lock = FileLock(_lock_path(uid), timeout=10)
    with lock:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = update_fn(data)
        if data is None:
            return None
        data["last_save_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _atomic_write(path, data)
        return data


# ============================================================================
# 用户搜索与管理
# ============================================================================
def list_all_uids() -> set:
    """列出所有已注册 UID"""
    uids = set()
    if not os.path.exists(USER_DATA_DIR):
        return uids
    for fname in os.listdir(USER_DATA_DIR):
        if fname.startswith("uid_") and fname.endswith(".json") and not fname.endswith(".checkpoint.json"):
            uid_part = fname[4:-5]
            from auth import validate_uid
            if validate_uid(uid_part)[0]:
                uids.add(uid_part)
    return uids


def list_all_users_full() -> list:
    """列出所有用户的完整数据（用于管理员面板）

    Returns:
        用户数据字典列表，按 UID 排序
    """
    users = []
    for uid in sorted(list_all_uids()):
        data = load_user(uid)
        if data:
            users.append(data)
    return users


def delete_all_users() -> int:
    """删除所有用户数据（含检查点和锁文件）

    Returns:
        删除的用户数量
    """
    uids = list_all_uids()
    for uid in uids:
        delete_user(uid)
    return len(uids)


def user_has_history(uid: str) -> bool:
    """判断用户是否有学习历史记录

    Args:
        uid: 用户 UID

    Returns:
        True 如果 history_progress 非空或有实质学习数据
    """
    data = load_user(uid)
    if data is None:
        return False
    has_progress = bool(data.get("history_progress", []))
    has_sessions = bool(data.get("session_records", []))
    has_portrait = bool(data.get("user_portrait", {}))
    return has_progress or has_sessions or has_portrait


# ============================================================================
# 学生快照与变更检测（Phase 2：老用户动态更新）
# ============================================================================
def save_student_snapshot(uid: str) -> dict:
    """保存当前学习状态快照（退出时调用），用于下次回来时对比变更

    Returns:
        写入的快照字典
    """
    data = load_user(uid)
    if data is None:
        return {}

    from datetime import datetime
    snapshot = {
        "profile": data.get("user_portrait", {}),
        "course": (data.get("session_records") or {}).get("course_name", ""),
        "weakness_count": len(data.get("session_records") or {} if isinstance(data.get("session_records"), dict) else data.get("session_records", [])),
        "progress_steps": len(data.get("history_progress", [])),
        "last_course": (data.get("session_records") or {}).get("course_name", "") if isinstance(data.get("session_records"), dict) else "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["student_snapshot"] = snapshot
    save_user(uid, data)
    return snapshot


def detect_changes(uid: str) -> dict:
    """对比当前画像与上次快照，检测学习状态变化

    Returns:
        {
            "has_snapshot": bool,       # 是否有历史快照可对比
            "has_changes": bool,        # 是否有实质性变化
            "changes": [str],           # 人类可读的变化描述列表
            "profile_then": dict,       # 上次画像
            "profile_now": dict,        # 当前画像
            "should_refresh_resources": bool,  # 是否建议刷新资源
            "should_refresh_roadmap": bool,    # 是否建议刷新路径
            "suggestion": str,          # 一句话建议
        }
    """
    data = load_user(uid)
    if data is None:
        return {"has_snapshot": False, "has_changes": False, "changes": [],
                "should_refresh_resources": False, "should_refresh_roadmap": False,
                "suggestion": ""}

    snapshot = data.get("student_snapshot", {})
    if not snapshot:
        return {"has_snapshot": False, "has_changes": False, "changes": [],
                "should_refresh_resources": False, "should_refresh_roadmap": False,
                "suggestion": ""}

    old_profile = snapshot.get("profile", {})
    new_profile = data.get("user_portrait", {})

    changes = []
    should_refresh_resources = False
    should_refresh_roadmap = False

    # 1. 知识基础变化
    old_basis = old_profile.get("知识基础", "")
    new_basis = new_profile.get("知识基础", "")
    if old_basis and new_basis and old_basis != new_basis and old_basis != "待了解" and new_basis != "待了解":
        changes.append(f"知识基础：{old_basis} → {new_basis}")
        should_refresh_resources = True
        should_refresh_roadmap = True

    # 2. 学习目标变化
    old_goal = old_profile.get("学习目标", "")
    new_goal = new_profile.get("学习目标", "")
    if old_goal and new_goal and old_goal != new_goal and old_goal != "待了解" and new_goal != "待了解":
        changes.append(f"学习目标：{old_goal} → {new_goal}")
        should_refresh_roadmap = True

    # 3. 薄弱环节变化
    old_weak = old_profile.get("薄弱环节", "")
    new_weak = new_profile.get("薄弱环节", "")
    if old_weak and new_weak and old_weak != new_weak and old_weak != "待了解" and new_weak != "待了解":
        changes.append(f"薄弱环节：{old_weak} → {new_weak}")
        should_refresh_resources = True
        should_refresh_roadmap = True

    # 4. 兴趣领域变化
    old_interest = old_profile.get("兴趣领域", "")
    new_interest = new_profile.get("兴趣领域", "")
    if old_interest and new_interest and old_interest != new_interest and old_interest != "待了解" and new_interest != "待了解":
        changes.append(f"兴趣领域：{old_interest} → {new_interest}")
        should_refresh_resources = True

    # 5. 认知风格变化（罕见但可能）
    old_style = old_profile.get("认知风格", "")
    new_style = new_profile.get("认知风格", "")
    if old_style and new_style and old_style != new_style and old_style != "待了解" and new_style != "待了解":
        changes.append(f"认知风格：{old_style} → {new_style}")
        should_refresh_resources = True

    # 6. 课程变化
    old_course = snapshot.get("last_course", "")
    new_course = (data.get("session_records") or {}).get("course_name", "")
    if old_course and new_course and old_course != new_course:
        changes.append(f"学习课程：{old_course} → {new_course}")
        should_refresh_resources = True
        should_refresh_roadmap = True

    # 7. 学习进度推进
    old_steps = snapshot.get("progress_steps", 0)
    new_steps = len(data.get("history_progress", []))
    if new_steps > old_steps + 1:
        changes.append(f"学习进度：已完成 {old_steps} 步 → {new_steps} 步")
        should_refresh_roadmap = True

    has_changes = len(changes) > 0

    # 生成建议
    suggestion = ""
    if has_changes:
        parts = []
        if should_refresh_resources:
            parts.append("更新学习资源")
        if should_refresh_roadmap:
            parts.append("调整学习路径")
        suggestion = "建议" + "、".join(parts) + "以匹配你的最新状态"
    elif old_profile and new_profile:
        suggestion = "学习状态稳定，可以继续上次的学习进度"

    return {
        "has_snapshot": True,
        "has_changes": has_changes,
        "changes": changes,
        "profile_then": old_profile,
        "profile_now": new_profile,
        "should_refresh_resources": should_refresh_resources,
        "should_refresh_roadmap": should_refresh_roadmap,
        "suggestion": suggestion,
    }
