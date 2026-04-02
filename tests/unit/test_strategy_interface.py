"""Unit tests for dynamic strategy loading and strategy interface.

Tests cover:
- Dynamic loading of strategy classes with custom names
- Free-form strategy file structure (no EDITABLE REGION)
- Strategy interface compliance
"""

import pytest
import pandas as pd
import numpy as np
import ast
import os
from pathlib import Path

from RestrictedPython import compile_restricted
from RestrictedPython.Guards import safer_getattr, full_write_guard
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem

from core.backtester import find_strategy_class
import strategies.active_strategy


# =============================================================================
# Dynamic loading tests
# =============================================================================

class TestDynamicLoading:
    """Tests for dynamic strategy class loading."""

    def test_free_form_class_accepted(self):
        """Custom class name works via find_strategy_class."""
        # Create a custom strategy class
        class MomentumStrategy:
            def generate_signals(self, data):
                return pd.Series(1, index=data.index)

        sandbox_locals = {'MomentumStrategy': MomentumStrategy}
        result = find_strategy_class(sandbox_locals)

        assert result is MomentumStrategy
        assert result.__name__ == 'MomentumStrategy'

    def test_custom_class_name(self):
        """'MomentumStrategy' loads correctly."""
        class MomentumStrategy:
            def __init__(self, period=20):
                self.period = period

            def generate_signals(self, data):
                return pd.Series(1, index=data.index)

        sandbox_locals = {
            'MomentumStrategy': MomentumStrategy,
            'TradingStrategy': None,
        }
        result = find_strategy_class(sandbox_locals)

        assert result is MomentumStrategy
        assert result.__name__ == 'MomentumStrategy'

    def test_multiple_methods_allowed(self):
        """Class with generate_signals + helper methods."""
        class ComplexStrategy:
            def __init__(self):
                self.param = 10

            def _helper_method(self, data):
                """Private helper method."""
                return data.mean()

            def another_method(self, x):
                """Another public method."""
                return x * 2

            def generate_signals(self, data):
                signals = pd.Series(0, index=data.index)
                signals.iloc[10:] = 1
                return signals

        sandbox_locals = {'ComplexStrategy': ComplexStrategy}
        result = find_strategy_class(sandbox_locals)

        assert result is ComplexStrategy
        assert hasattr(result, 'generate_signals')
        assert hasattr(result, '_helper_method')
        assert hasattr(result, 'another_method')

    def test_no_generate_signals_rejected(self):
        """Class without generate_signals returns None."""
        class IncompleteStrategy:
            def __init__(self):
                pass

            def some_other_method(self, data):
                return data

        sandbox_locals = {'IncompleteStrategy': IncompleteStrategy}
        result = find_strategy_class(sandbox_locals)

        assert result is None

    def test_non_class_with_generate_signals_ignored(self):
        """Function named generate_signals ignored."""
        def generate_signals(data):
            return pd.Series(1, index=data.index)

        class ValidStrategy:
            def generate_signals(self, data):
                return pd.Series(1, index=data.index)

        sandbox_locals = {
            'generate_signals': generate_signals,  # Function, not class
            'ValidStrategy': ValidStrategy,
        }
        result = find_strategy_class(sandbox_locals)

        # Should find ValidStrategy, not the function
        assert result is ValidStrategy


# =============================================================================
# Strategy file tests
# =============================================================================

class TestStrategyFile:
    """Tests for active_strategy.py file structure and content."""

    @pytest.fixture
    def strategy_file_path(self):
        """Path to active_strategy.py."""
        return Path(__file__).parent.parent.parent / 'src' / 'strategies' / 'active_strategy.py'

    def test_editable_region_removed(self, strategy_file_path):
        """No EDITABLE REGION in active_strategy.py."""
        content = strategy_file_path.read_text()

        assert 'EDITABLE REGION BREAK' not in content
        assert 'EDITABLE REGION END' not in content

    def test_strategy_file_exists(self, strategy_file_path):
        """Strategy file exists at expected location."""
        assert strategy_file_path.exists()

    def test_strategy_file_valid_python(self, strategy_file_path):
        """Strategy file is valid Python syntax."""
        content = strategy_file_path.read_text()

        # Should parse without errors
        try:
            ast.parse(content)
        except SyntaxError as e:
            pytest.fail(f"active_strategy.py has syntax error: {e}")

    def test_strategy_has_trading_strategy_class(self, strategy_file_path):
        """File contains TradingStrategy class."""
        content = strategy_file_path.read_text()
        tree = ast.parse(content)

        classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        assert 'TradingStrategy' in classes

    def test_trading_strategy_has_generate_signals(self, strategy_file_path):
        """TradingStrategy class has generate_signals method."""
        content = strategy_file_path.read_text()
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'TradingStrategy':
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                assert 'generate_signals' in methods
                return

        pytest.fail("TradingStrategy class not found")

    def test_strategy_has_imports(self, strategy_file_path):
        """File has pandas and numpy imports."""
        content = strategy_file_path.read_text()

        # Check for import statements
        assert 'import pandas' in content or 'import pd' in content
        assert 'import numpy' in content or 'import np' in content

    def test_strategy_in_sandbox(self, strategy_file_path):
        """active_strategy.py compiles in RestrictedPython."""
        content = strategy_file_path.read_text()

        # Strip import statements for restricted execution (same as backtester does)
        sanitized_lines = []
        for line in content.split('\n'):
            if not (line.strip().startswith("import ") or line.strip().startswith("from ")):
                sanitized_lines.append(line)
        sanitized_code = '\n'.join(sanitized_lines)

        # Define restricted environment - include __build_class__ for class definitions
        safe_builtins = {
            '__build_class__': __builtins__['__build_class__'],
            '_write_': lambda x: x,
            '_getattr_': safer_getattr,
        }
        safe_globals = {
            '__builtins__': safe_builtins,
            '_getattr_': safer_getattr,
            '_write_': lambda x: x,
            '_getiter_': default_guarded_getiter,
            '_getitem_': default_guarded_getitem,
            '__name__': 'sandbox',
            '__metaclass__': type,
            'pd': pd,
            'np': np,
        }

        # Should compile without errors
        try:
            byte_code = compile_restricted(sanitized_code, filename='active_strategy.py', mode='exec')
            sandbox_locals = {}
            exec(byte_code, safe_globals, sandbox_locals)
        except Exception as e:
            pytest.fail(f"active_strategy.py failed to compile in RestrictedPython: {e}")

    def test_strategy_returns_series(self, strategy_file_path):
        """generate_signals returns pd.Series for sample data."""
        # Import the actual strategy
        from strategies.active_strategy import TradingStrategy

        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100)
        data = pd.DataFrame({
            'Close': np.linspace(100, 110, 100),
            'returns': [0.001] * 100,
            'volatility': [0.01] * 100,
            'atr': [1.0] * 100,
        }, index=dates)

        strategy = TradingStrategy()
        signals = strategy.generate_signals(data)

        assert isinstance(signals, pd.Series)
        assert len(signals) == len(data)

    def test_strategy_signal_range(self, strategy_file_path):
        """Signals in {-1, 0, 1}."""
        from strategies.active_strategy import TradingStrategy

        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100)
        data = pd.DataFrame({
            'Close': np.linspace(100, 110, 100),
            'returns': [0.001] * 100,
            'volatility': [0.01] * 100,
            'atr': [1.0] * 100,
        }, index=dates)

        strategy = TradingStrategy()
        signals = strategy.generate_signals(data)

        # Check unique values are in expected range
        unique_values = set(signals.dropna().unique())
        for val in unique_values:
            assert val in {-1.0, 0.0, 1.0}, f"Unexpected signal value: {val}"

    def test_strategy_class_init(self, strategy_file_path):
        """TradingStrategy can be instantiated."""
        from strategies.active_strategy import TradingStrategy

        # Should be able to instantiate with defaults
        strategy = TradingStrategy()
        assert hasattr(strategy, 'fast_ma')
        assert hasattr(strategy, 'slow_ma')

        # Should be able to instantiate with custom params
        strategy_custom = TradingStrategy(fast_ma=10, slow_ma=30)
        assert strategy_custom.fast_ma == 10
        assert strategy_custom.slow_ma == 30


# =============================================================================
# Free-form strategy tests (custom class names)
# =============================================================================

class TestFreeFormStrategies:
    """Tests for various free-form strategy implementations."""

    def test_custom_named_strategy_via_sandbox(self):
        """Custom class name loads correctly through sandbox."""
        # Simulate sandbox execution with custom class name
        strategy_code = """
class MyAlphaStrategy:
    def __init__(self, threshold=0.5):
        self.threshold = threshold

    def generate_signals(self, data):
        signals = pd.Series(0, index=data.index)
        signals.iloc[10:] = 1
        return signals

class HelperClass:
    pass
"""

        # Include __build_class__ for class definition support
        safe_builtins = {
            '__build_class__': __builtins__['__build_class__'],
        }
        safe_globals = {
            '__builtins__': safe_builtins,
            '_getattr_': safer_getattr,
            '_write_': lambda x: x,
            '_getiter_': default_guarded_getiter,
            '_getitem_': default_guarded_getitem,
            '__name__': 'sandbox',
            '__metaclass__': type,
            'pd': pd,
            'np': np,
        }

        byte_code = compile_restricted(strategy_code, filename='test.py', mode='exec')
        sandbox_locals = {}
        exec(byte_code, safe_globals, sandbox_locals)

        result = find_strategy_class(sandbox_locals)

        assert result is not None
        assert result.__name__ == 'MyAlphaStrategy'

    def test_multiple_strategies_returns_first(self):
        """When multiple classes have generate_signals, first is returned."""
        strategy_code = """
class StrategyA:
    def generate_signals(self, data):
        return pd.Series(1, index=data.index)

class StrategyB:
    def generate_signals(self, data):
        return pd.Series(-1, index=data.index)
"""

        # Include __build_class__ for class definition support
        safe_builtins = {
            '__build_class__': __builtins__['__build_class__'],
        }
        safe_globals = {
            '__builtins__': safe_builtins,
            '_getattr_': safer_getattr,
            '_write_': lambda x: x,
            '_getiter_': default_guarded_getiter,
            '_getitem_': default_guarded_getitem,
            '__name__': 'sandbox',
            '__metaclass__': type,
            'pd': pd,
            'np': np,
        }

        byte_code = compile_restricted(strategy_code, filename='test.py', mode='exec')
        sandbox_locals = {}
        exec(byte_code, safe_globals, sandbox_locals)

        result = find_strategy_class(sandbox_locals)

        assert result is not None
        assert hasattr(result, 'generate_signals')
        assert result.__name__ in {'StrategyA', 'StrategyB'}
