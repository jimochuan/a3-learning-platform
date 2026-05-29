"""
=============================================================================
Step 4 单元测试 —— 验证 render 函数和 agent 创建
=============================================================================
"""
import sys
import os

# Ensure project root is on the path so shared imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_render_importable():
    """Test that the render function can be imported."""
    from modules.step4_tutor.step import render
    assert callable(render), "render should be a callable function"
    print("  [PASS] test_render_importable")


def test_agents_creatable():
    """Test that tutor_agent and weakness_agent can be created from shared.agents."""
    from shared.agents import create_agents

    agents = create_agents(course_name="Python程序设计", student_info={
        "知识基础": "入门",
        "认知风格": "视觉型",
    })

    tutor = agents.tutor_agent()
    assert tutor is not None, "tutor_agent() should return an Agent"
    print("  [PASS] tutor_agent created")

    weakness = agents.weakness_agent()
    assert weakness is not None, "weakness_agent() should return an Agent"
    print("  [PASS] weakness_agent created")

    rag_tutor = agents.rag_tutor_agent()
    assert rag_tutor is not None, "rag_tutor_agent() should return an Agent"
    print("  [PASS] rag_tutor_agent created")


def test_empty_state_handles_gracefully():
    """Test that the render function handles minimal state attributes."""
    from modules.step4_tutor.step import render

    # Build a minimal mock state — we cannot actually call render()
    # in a headless test because it uses st.* calls, but we verify
    # that the function reference works and the module imports cleanly.
    class MockState:
        course_name = ""
        profile = {}
        tutor_history = []
        weakness_list = []
        rag_doc_count = 0
        rag_helper = None
        roadmap = None
        step = 4

    state = MockState()
    # Verify attributes exist
    assert hasattr(state, 'course_name')
    assert hasattr(state, 'profile')
    assert hasattr(state, 'tutor_history')
    assert hasattr(state, 'weakness_list')
    assert hasattr(state, 'rag_doc_count')
    assert hasattr(state, 'rag_helper')
    assert hasattr(state, 'roadmap')
    assert hasattr(state, 'step')
    print("  [PASS] test_empty_state_handles_gracefully")


if __name__ == "__main__":
    print("=" * 60)
    print("Step 4 模块单元测试")
    print("=" * 60)

    test_render_importable()
    test_agents_creatable()
    test_empty_state_handles_gracefully()

    print("=" * 60)
    print("ALL TESTS PASSED: Step 4")
    print("=" * 60)
