import pytest
import os
from unittest.mock import MagicMock, patch
from core.engine import QuantAutoresearchEngine
from safety.guard import SafetyLevel, SubagentType

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    monkeypatch.delenv("WANDB_API_KEY", raising=False)

@pytest.mark.asyncio
async def test_safety_blocking_integration(mock_env, tmp_path):
    """Verify that dangerous tool calls are blocked during engine execution."""
    os.chdir(tmp_path)
    with open("program.md", "w") as f: f.write("# Constitution")
    os.makedirs("prompts", exist_ok=True)
    for p in ["identity.md", "safety_policy.md", "tool_guidance.md", "quant_rules.md", "git_rules.md"]:
        with open(f"prompts/{p}", "w") as f: f.write(f"# {p}")
    
    engine = QuantAutoresearchEngine(safety_level=SafetyLevel.HIGH)
    engine.run_backtest_with_output = MagicMock(return_value=(0.5, 0.1, 0, {}))
    
    # Mock Model Router to propose a dangerous command
    engine.model_router = MagicMock()
    engine.model_router.thinking_phase.return_value = {"success": True, "content": "I need to delete everything.", "model_used": "m"}
    engine.model_router.route_request.return_value = {
        "success": True,
        "content": '```json\n[{"tool_name": "run_command", "parameters": {"command": "rm -rf /"}}, {"tool_name": "search_tools", "parameters": {"query": "test"}}]\n```',
        "model_used": "m"
    }

    engine.tool_registry = MagicMock()
    # Mock execute_tool to verify it's NOT called for the dangerous command
    engine.tool_registry.execute_tool = MagicMock(return_value={"result": "ok"})
    
    await engine.run(max_iterations=1)
    
    # Verifications
    # 1. run_command should be blocked
    # 2. search_tools should be executed (if it's safe for executor)
    
    # Check observations
    blocked_obs = [obs for obs in engine.iteration_history if obs.get("tool") == "run_command" and obs.get("status") == "blocked"]
    success_obs = [obs for obs in engine.iteration_history if obs.get("tool") == "search_tools" and obs.get("status") == "success"]
    
    assert len(blocked_obs) == 1
    assert len(success_obs) == 1
    
    # Verify the dangerous command was NOT passed to the registry
    for call in engine.tool_registry.execute_tool.call_args_list:
        assert call[0][0] != "run_command" or "rm -rf" not in call[0][1].get("command", "")
