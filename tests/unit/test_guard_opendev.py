import pytest
from safety.guard import SafetyGuard, SafetyLevel, SubagentType, ApprovalMode

def test_guard_initialization():
    guard = SafetyGuard(safety_level=SafetyLevel.HIGH)
    assert guard.safety_level == SafetyLevel.HIGH
    assert guard.approval_mode == ApprovalMode.SEMI
    assert len(guard.tool_history) == 0

def test_schema_gating_planner():
    guard = SafetyGuard()
    # Planner should have access to read-only tools but not execution tools
    res = guard.defense_in_depth_check({"tool_name": "search_research"}, SubagentType.PLANNER)
    assert res["safe"] is True
    
    res = guard.defense_in_depth_check({"tool_name": "run_backtest"}, SubagentType.PLANNER)
    assert res["safe"] is False
    assert any("not allowed for planner subagent" in e for e in res["errors"])

def test_schema_gating_executor():
    guard = SafetyGuard()
    # Executor should have access to execution tools but not research tools
    res = guard.defense_in_depth_check({"tool_name": "run_backtest"}, SubagentType.EXECUTOR)
    assert res["safe"] is True
    
    res = guard.defense_in_depth_check({"tool_name": "search_research"}, SubagentType.EXECUTOR)
    assert res["safe"] is False
    assert any("not allowed for executor subagent" in e for e in res["errors"])

def test_doom_loop_detection():
    guard = SafetyGuard()
    # Execute same tool 3 times
    op = {"tool_name": "test_tool", "parameters": {"a": 1}}
    history = []
    # check_doom_loop takes (fingerprint, history)
    for _ in range(3):
        guard.check_doom_loop(str(op), history)
    
    # The 4th time should trigger loop detection
    is_loop = guard.check_doom_loop(str(op), history)
    assert is_loop is True

def test_forbidden_functions():
    guard = SafetyGuard()
    # Test Layer 4: Tool Validation (Simple check for high-risk commands)
    res = guard.defense_in_depth_check({"tool_name": "run_command", "parameters": {"command": "rm -rf /"}}, SubagentType.FULL_ACCESS)
    assert res["safe"] is False
    assert any("Dangerous command" in e for e in res["errors"])

def test_approval_logic_semi():
    guard = SafetyGuard(approval_mode=ApprovalMode.SEMI)
    # run_backtest is medium risk
    res = guard.defense_in_depth_check({"tool_name": "run_backtest"}, SubagentType.EXECUTOR)
    assert res["safe"] is True
    assert "approval_required" in res
    assert res["approval_required"] is True

def test_approval_logic_high_safety():
    guard = SafetyGuard(safety_level=SafetyLevel.CRITICAL)
    # Critical safety might block more or require more approvals
    res = guard.defense_in_depth_check({"tool_name": "generate_strategy_code"}, SubagentType.EXECUTOR)
    assert res["safe"] is True
    # Implementation might vary, but verify it doesn't crash
