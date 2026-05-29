"""
=============================================================================
Step 3 模块测试
=============================================================================
"""


def test_render_importable():
    """测试 render 函数可导入"""
    from modules.step3_roadmap.step import render
    assert callable(render), "render should be callable"
    print("  PASS: test_render_importable")


def test_roadmap_agent_creatable():
    """测试 roadmap_agent 可以从 shared.agents 创建"""
    from shared.agents import create_agents
    agents = create_agents(
        course_name="Python程序设计",
        student_info={"知识基础": "入门"},
    )
    roadmap_agent = agents.roadmap_agent()
    assert roadmap_agent is not None, "roadmap_agent should not be None"
    print("  PASS: test_roadmap_agent_creatable")


if __name__ == "__main__":
    test_render_importable()
    test_roadmap_agent_creatable()
    print("\nALL TESTS PASSED: Step 3")
