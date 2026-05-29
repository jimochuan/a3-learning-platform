"""
=============================================================================
Step 5 模块测试
=============================================================================
"""


def test_render_importable():
    """测试 render 函数可导入"""
    from modules.step5_eval.step import render
    assert callable(render), "render should be callable"
    print("  PASS: test_render_importable")


def test_eval_agent_creatable():
    """测试 eval_agent 可以从 shared.agents 创建"""
    from shared.agents import create_agents
    agents = create_agents(
        course_name="Python程序设计",
        student_info={"知识基础": "入门"},
    )
    eval_agent = agents.eval_agent()
    assert eval_agent is not None, "eval_agent should not be None"
    print("  PASS: test_eval_agent_creatable")


def test_cross_validate_callable():
    """测试 cross_validate 方法存在且可调用"""
    from shared.agents import create_agents
    agents = create_agents(course_name="Python程序设计")
    assert callable(agents.cross_validate), "cross_validate should be callable"
    print("  PASS: test_cross_validate_callable")


if __name__ == "__main__":
    test_render_importable()
    test_eval_agent_creatable()
    test_cross_validate_callable()
    print("\nALL TESTS PASSED: Step 5")
