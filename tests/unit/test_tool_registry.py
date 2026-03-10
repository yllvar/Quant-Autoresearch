import pytest
from unittest.mock import MagicMock, patch
from tools.registry import LazyToolRegistry, SubagentType

@pytest.fixture
def registry():
    with patch("tools.registry.SafetyGuard") as mock_guard:
        # Mock safety check to always be safe
        mock_guard.return_value.defense_in_depth_check.return_value = {
            "safe": True,
            "errors": [],
            "approval_required": False
        }
        return LazyToolRegistry()

def test_registry_initialization(registry):
    assert len(registry.all_tools) > 0
    assert "search_research" in registry.all_tools

def test_search_tools(registry):
    # Search for research tools as planner
    result = registry.search_tools("research", subagent_type=SubagentType.PLANNER)
    assert result["total_matches"] > 0
    assert any(m["tool_name"] == "search_research" for m in result["matches"])

def test_load_tool_schema(registry):
    schema = registry.load_tool_schema("search_research")
    assert schema["name"] == "search_research"
    assert "parameters" in schema

def test_execute_tool_success(registry):
    params = {"query": "test"}
    result = registry.execute_tool("search_research", params)
    assert result["success"] is True
    assert result["tool_name"] == "search_research"

def test_execute_tool_safety_block(registry):
    # Mock safety failure
    registry.safety_guard.defense_in_depth_check.return_value = {
        "safe": False,
        "errors": ["Dangerous command"],
        "approval_required": False
    }
    
    result = registry.execute_tool("run_command", {"command": "rm -rf /"})
    assert result["success"] is False
    assert "Safety check failed" in result["error"]

def test_execute_tool_approval(registry):
    # Mock approval required
    registry.safety_guard.defense_in_depth_check.return_value = {
        "safe": True,
        "errors": [],
        "approval_required": True
    }
    # Mock approval granted
    registry.safety_guard.request_approval.return_value = True
    
    result = registry.execute_tool("write_file", {"file_path": "test.txt", "content": "hello"})
    assert result["success"] is True
    assert registry.safety_guard.request_approval.called

def test_usage_statistics(registry):
    registry.execute_tool("search_research", {"query": "test"})
    stats = registry.get_usage_statistics()
    assert stats["tool_usage_stats"]["search_research"]["total_calls"] == 1
