"""
=============================================================================
Step 2 单元测试 —— 个性化学习资源模块
=============================================================================
验证 render 可导入、dialogue_resource_agent 可创建、MOCK_DATA 完整。
从项目根目录运行：
    python modules/step2_resource/test_step2.py
=============================================================================
"""
import sys
import os


def _setup_path():
    """确保项目根目录在 sys.path 中。"""
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


_setup_path()


# ============================================================================
# 测试用例
# ============================================================================
def test_import_render():
    """验证 render 函数可导入且可调用。"""
    from modules.step2_resource.step import render

    assert callable(render), "render should be callable"
    print("[PASS] test_import_render")


def test_dialogue_agent_creation():
    """验证 create_dialogue_agent 可创建智能体实例。"""
    from shared.dialogue_resource_agent import create_dialogue_agent

    agent = create_dialogue_agent(course_name="Python程序设计")
    assert agent is not None, "Agent should not be None"

    first_q = agent.get_first_question()
    assert first_q and isinstance(first_q, str), (
        f"First question should be a non-empty string, got: {repr(first_q)}"
    )

    # 模拟一轮对话
    result = agent.process_input("我有一点基础，喜欢看视频和动手写代码")
    assert "extracted" in result, "Result should contain 'extracted'"
    assert "next_question" in result, "Result should contain 'next_question'"
    assert "is_complete" in result, "Result should contain 'is_complete'"

    print("[PASS] test_dialogue_agent_creation")


def test_mock_data():
    """验证 MOCK_DATA 包含所有必需字段且值类型正确。"""
    from modules.step2_resource.step import MOCK_DATA

    required_keys = [
        "course_name",
        "profile",
        "step2_agent",
        "step2_messages",
        "step2_active",
        "resources",
    ]
    for key in required_keys:
        assert key in MOCK_DATA, f"MOCK_DATA missing key: {key}"

    assert MOCK_DATA["course_name"] == "Python程序设计"
    assert isinstance(MOCK_DATA["profile"], dict)
    assert "知识基础" in MOCK_DATA["profile"]
    assert MOCK_DATA["step2_agent"] is None
    assert MOCK_DATA["step2_messages"] == []
    assert MOCK_DATA["step2_active"] is True
    assert MOCK_DATA["resources"] is None

    print("[PASS] test_mock_data")


# ============================================================================
# 入口
# ============================================================================
if __name__ == "__main__":
    test_import_render()
    test_dialogue_agent_creation()
    test_mock_data()
    print("\nALL TESTS PASSED: Step 2")
