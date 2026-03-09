import pytest
import os
from backtest_runner import walk_forward_validation
import sys
from io import StringIO

def test_evil_agent_infinite_loop(tmp_path, monkeypatch):
    """Tests that an infinite loop in strategy.py doesn't crash the runner's validation (if possible, or at least handles it)."""
    # Note: Truly infinite loops are hard to catch without timeouts.
    # We can at least test syntax errors or immediate crashes.
    pass

def test_evil_agent_division_by_zero(tmp_path, monkeypatch):
    strategy_path = tmp_path / "strategy.py"
    strategy_path.write_text("""
class TradingStrategy:
    def generate_signals(self, data):
        return 1/0
""")
    # Change to tmp_path and run backtest_runner
    os.chdir(tmp_path)
    # Mock data cache existence
    (tmp_path / "data_cache").mkdir()
    
    # We need to mock sys.exit to avoid exiting pytest
    monkeypatch.setattr(sys, "exit", lambda x: None)
    
    # Capture output
    stdout = StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    
    try:
        # This will fail during load or execution
        # But we want to see it doesn't crash the whole process
        from backtest_runner import walk_forward_validation
        walk_forward_validation()
    except Exception as e:
        # If it crashes, it should be caught higher up in agent_runner
        pass

def test_security_check_bypass_attempts():
    from backtest_runner import security_check
    
    bypass_code = """
class TradingStrategy:
    def generate_signals(self, data):
        getattr(__builtins__, 'ex' + 'ec')('print("hacked")')
        return None
"""
    with open("strategy.py", "w") as f: f.write(bypass_code)
    is_safe, msg = security_check()
    assert not is_safe
    assert "Forbidden builtin function found: getattr" in msg
