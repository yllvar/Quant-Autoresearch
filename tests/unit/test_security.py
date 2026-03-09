import pytest
import os
import ast
from backtest_runner import security_check

def create_strategy_file(content):
    with open("strategy.py", "w") as f:
        f.write(content)

def test_security_check_safe_strategy():
    safe_code = """
import pandas as pd
class TradingStrategy:
    def generate_signals(self, data):
        return pd.Series(1, index=data.index)
"""
    create_strategy_file(safe_code)
    is_safe, msg = security_check()
    assert is_safe
    assert msg == ""

def test_security_check_forbidden_builtin():
    evil_code = """
class TradingStrategy:
    def generate_signals(self, data):
        exec('print("evil")')
        return None
"""
    create_strategy_file(evil_code)
    is_safe, msg = security_check()
    assert not is_safe
    assert "Forbidden builtin function found: exec" in msg

def test_security_check_forbidden_import():
    evil_code = """
import socket
class TradingStrategy:
    def generate_signals(self, data):
        return None
"""
    create_strategy_file(evil_code)
    is_safe, msg = security_check()
    assert not is_safe
    assert "Forbidden module import found: socket" in msg

def test_security_check_lookahead_bias():
    evil_codes = [
        "data.shift(-1)",
        "data.shift(periods=-2)",
        "data.shift(-1 * 1)"
    ]
    for code in evil_codes:
        content = f"""
class TradingStrategy:
    def generate_signals(self, data):
        return {code}
"""
        create_strategy_file(content)
        is_safe, msg = security_check()
        assert not is_safe
        assert "Look-ahead bias detected" in msg

def test_security_check_from_import():
    evil_code = """
from os import system
class TradingStrategy:
    def generate_signals(self, data):
        return None
"""
    create_strategy_file(evil_code)
    is_safe, msg = security_check()
    assert not is_safe
    assert "Forbidden module import found: os" in msg
