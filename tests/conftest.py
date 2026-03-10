import pytest
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

# Add src and root to path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))
sys.path.append(str(root_dir / "src"))

import shutil

@pytest.fixture
def sample_data():
    """Provides a small deterministic OHLCV dataset."""
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    data = pd.DataFrame({
        "Open": np.linspace(100, 110, 100),
        "High": np.linspace(101, 111, 100),
        "Low": np.linspace(99, 109, 100),
        "Close": np.linspace(100.5, 110.5, 100),
        "Volume": [1000] * 100,
        "returns": [0.001] * 100,
        "volatility": [0.01] * 100,
        "atr": [1.0] * 100
    }, index=dates)
    return data

@pytest.fixture
def temp_cache(tmp_path):
    """Temporary directory for data caching tests."""
    cache_dir = tmp_path / "data_cache"
    cache_dir.mkdir()
    return cache_dir

@pytest.fixture
def mock_strategy_file(tmp_path):
    """Creates a temporary strategy.py for testing."""
    strategy_path = tmp_path / "strategy.py"
    content = """
import pandas as pd
class TradingStrategy:
    def __init__(self): pass
    def generate_signals(self, data):
        return pd.Series(1, index=data.index)
"""
    strategy_path.write_text(content)
    return strategy_path
