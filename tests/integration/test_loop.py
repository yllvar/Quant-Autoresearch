import pytest
import os
import json
from unittest.mock import MagicMock, patch
from agent_runner import agent_iteration

def test_agent_iteration_reversion(monkeypatch, tmp_path):
    """Verifies that the agent reverts changes when the score does not improve."""
    os.chdir(tmp_path)
    
    with open("program.md", "w") as f: f.write("Role: Researcher")
    with open("strategy.py", "w") as f:
        f.write("class TradingStrategy:\n    def generate_signals(self, data):\n        # --- EDITABLE REGION BREAK ---\n        # Original\n        # --- EDITABLE REGION END ---\n        return pd.Series(0, index=data.index)")
    
    # Mock research context
    monkeypatch.setattr("agent_runner.get_research_context", lambda x: "Mock Research Context")
    
    # Mock Groq Client
    mock_client = MagicMock()
    
    # Mock Response 1: Hypothesis
    mock_resp_h = MagicMock()
    mock_resp_h.choices[0].message.content = json.dumps({
        "hypothesis": "Test Hypothesis",
        "search_query": "test query"
    })
    
    # Mock Response 2: Code
    mock_resp_c = MagicMock()
    mock_resp_c.choices[0].message.content = json.dumps({
        "code": "pass # Improved?"
    })
    
    # Configure mock_client to return different values sequentially
    mock_client.chat.completions.create.side_effect = [mock_resp_h, mock_resp_c]
    
    monkeypatch.setattr("agent_runner.client", mock_client)
    
    # Mock run_backtest_with_output: score 0.5 then 0.1 (reversion)
    scores = [0.5, 0.1]
    def mock_run_backtest():
        return scores.pop(0), 0.0, 0, {"stdout": "SCORE: 0.5", "stderr": ""}
    monkeypatch.setattr("agent_runner.run_backtest_with_output", mock_run_backtest)
    
    # Run iteration
    agent_iteration()
    
    # Verify reversion
    with open("strategy.py", "r") as f:
        content = f.read()
    assert "Original" in content
    assert "Improved?" not in content

def test_agent_iteration_improvement(monkeypatch, tmp_path):
    """Verifies that the agent keeps changes when the score improves."""
    os.chdir(tmp_path)
    
    with open("program.md", "w") as f: f.write("Role: Researcher")
    with open("strategy.py", "w") as f:
        f.write("class TradingStrategy:\n    def generate_signals(self, data):\n        # --- EDITABLE REGION BREAK ---\n        # Original\n        # --- EDITABLE REGION END ---\n        return pd.Series(0, index=data.index)")
        
    monkeypatch.setattr("agent_runner.get_research_context", lambda x: "Mock Research Context")
    
    mock_client = MagicMock()
    mock_resp_h = MagicMock()
    mock_resp_h.choices[0].message.content = json.dumps({
        "hypothesis": "Better Hypothesis",
        "search_query": "better query"
    })
    mock_resp_c = MagicMock()
    mock_resp_c.choices[0].message.content = json.dumps({
        "code": "pass # Better!"
    })
    mock_client.chat.completions.create.side_effect = [mock_resp_h, mock_resp_c]
            
    monkeypatch.setattr("agent_runner.client", mock_client)
    
    # Mock run_backtest_with_output: score 0.1 then 0.5 (improvement)
    scores = [0.1, 0.5]
    def mock_run_backtest():
        return scores.pop(0), 0.0, 0, {"stdout": "SCORE: 0.5", "stderr": ""}
    monkeypatch.setattr("agent_runner.run_backtest_with_output", mock_run_backtest)
    
    agent_iteration()
    
    with open("strategy.py", "r") as f:
        content = f.read()
    assert "Better!" in content
    assert "Original" not in content
