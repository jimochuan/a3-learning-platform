"""
=============================================================================
A3 v3 Step 1 Unit Tests
=============================================================================
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def test_import_render():
    """Test that the render function is importable."""
    from modules.step1_profile.step import render
    assert callable(render), "render should be a callable function"
    print("  [PASS] render function import OK")


def test_import_MOCK_DATA():
    """Test that MOCK_DATA is present and has required keys."""
    from modules.step1_profile.step import MOCK_DATA
    assert "step" in MOCK_DATA
    assert "course_name" in MOCK_DATA
    assert "profile" in MOCK_DATA
    assert "dialogue" in MOCK_DATA
    print("  [PASS] MOCK_DATA keys OK")


def test_profile_agent_creation():
    """Test that profile_agent() can be created from shared.agents."""
    from shared.agents import create_agents
    agents = create_agents(course_name="TestCourse")
    pa = agents.profile_agent()
    assert pa is not None, "profile_agent should return an Agent instance"
    # Check it has the expected interface
    assert hasattr(pa, "run"), "Agent should have 'run' method"
    print("  [PASS] profile_agent creation OK")


def test_defaults_keys():
    """Test that DEFAULTS contains all needed keys for Step 1."""
    from shared.session_state import DEFAULTS
    required_keys = [
        "step",
        "course_name",
        "profile",
        "dialogue",
        "resources",
        "roadmap",
        "tutor_history",
        "weakness_list",
        "eval_report",
    ]
    for k in required_keys:
        assert k in DEFAULTS, f"Missing required key in DEFAULTS: {k}"
    print("  [PASS] DEFAULTS contains all required keys")


def test_profile_dimensions():
    """Test that PROFILE_DIMENSIONS is a non-empty list."""
    from shared.config import PROFILE_DIMENSIONS
    assert isinstance(PROFILE_DIMENSIONS, list), "PROFILE_DIMENSIONS should be a list"
    assert len(PROFILE_DIMENSIONS) >= 4, "PROFILE_DIMENSIONS should have at least 4 entries"
    print("  [PASS] PROFILE_DIMENSIONS OK")


def test_init_session():
    """Test that init_session is importable and callable."""
    from shared.session_state import init_session
    assert callable(init_session), "init_session should be callable"
    print("  [PASS] init_session import OK")


if __name__ == "__main__":
    print("=" * 60)
    print("A3 v3 Step 1 — Unit Tests")
    print("=" * 60)

    test_import_render()
    test_import_MOCK_DATA()
    test_profile_agent_creation()
    test_defaults_keys()
    test_profile_dimensions()
    test_init_session()

    print("=" * 60)
    print("ALL TESTS PASSED: Step 1")
    print("=" * 60)
