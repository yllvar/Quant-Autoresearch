import pytest
import os
import json
from unittest.mock import MagicMock, patch
from core.engine import QuantAutoresearchEngine
from safety.guard import SafetyLevel, SubagentType

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "mock_key")
    # Ensure WandB is disabled
    monkeypatch.delenv("WANDB_API_KEY", raising=False)

@pytest.mark.asyncio
async def test_engine_full_loop_iteration(mock_env, tmp_path):
    """Integration test for the full 6-phase loop."""
    os.chdir(tmp_path)
    
    # Setup minimal project structure
    with open("program.md", "w") as f: f.write("# Constitution")
    os.makedirs("prompts", exist_ok=True)
    for p in ["identity.md", "safety_policy.md", "tool_guidance.md", "quant_rules.md", "git_rules.md"]:
        with open(f"prompts/{p}", "w") as f: f.write(f"# {p}")
    
    # Initialize Engine
    engine = QuantAutoresearchEngine(safety_level=SafetyLevel.LOW)
    
    # Mock Backtest Result (Baseline)
    engine.run_backtest_with_output = MagicMock(return_value=(0.5, 0.1, 0, {}))
    
    # Mock Model Router
    engine.model_router = MagicMock()
    # Phase 1 Thinking response
    engine.model_router.thinking_phase.return_value = {
        "success": True,
        "content": "I should search for momentum strategies.",
        "model_used": "mock-think-model"
    }
    # Phase 2 Reasoning response (Action selection)
    def mock_route_request(phase, messages):
        if phase == "reasoning":
            return {
                "success": True,
                "content": '```json\n[{"tool_name": "search_tools", "parameters": {"query": "momentum"}}]\n```',
                "model_used": "mock-action-model"
            }
        return {"success": False}
    
    engine.model_router.route_request.side_effect = mock_route_request
    # Usage stats
    engine.model_router.usage_stats = {"total_cost": 0.01, "thinking_calls": 1, "reasoning_calls": 1}
    
    # Mock Tool Registry
    engine.tool_registry = MagicMock()
    # Mock search_tools to return matches
    engine.tool_registry.search_tools.return_value = {"matches": [{"tool_name": "search_tools", "description": "Search"}]}
    engine.tool_registry.execute_tool.return_value = {"result": "Found some tools"}
    
    # Run 1 iteration
    await engine.run(max_iterations=1)
    
    # Verifications
    assert engine.iteration_count == 1
    assert engine.best_score == 0.5
    assert engine.model_router.thinking_phase.called
    assert engine.model_router.route_request.called
    assert engine.tool_registry.execute_tool.called
    assert len(engine.iteration_history) > 0 # Should have the observation
