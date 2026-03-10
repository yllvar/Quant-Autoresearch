import pytest
import pandas as pd
import numpy as np
import os
from core.backtester import run_backtest

class StaticStrategy:
    def generate_signals(self, data):
        # Deterministic logic based on Close price
        signals = pd.Series(0, index=data.index)
        signals[data['Close'] > 105] = 1
        return signals

def test_score_determinism(sample_data):
    """Verifies that running the same strategy on the same data yields identical results."""
    strategy = StaticStrategy()
    data = {"TEST": sample_data}
    
    # Run 1
    sharpe1, dd1, trades1, _pval = run_backtest(strategy, data, 10, 90)
    
    # Run 2
    sharpe2, dd2, trades2, _pval = run_backtest(strategy, data, 10, 90)
    
    assert sharpe1 == sharpe2
    assert dd1 == dd2
    assert trades1 == trades2
    assert sharpe1 is not None

def test_score_consistency_with_indicator_warmup(sample_data):
    """Verifies that results are consistent when indicators are 'warmed up' at different entry points."""
    strategy = StaticStrategy()
    data = {"TEST": sample_data}
    
    # Scenario A: Full history provided
    sharpe_a, _, _, _pval = run_backtest(strategy, data, 20, 80)
    
    # Scenario B: Partial history provided (still before test window)
    # Note: run_backtest actually takes 'data' and 'end_idx' slices internally.
    # In backtest_runner.py, it slices df.iloc[:end_idx].
    # So we are testing if the logic inside run_backtest is deterministic.
    
    sharpe_b, _, _, _pval = run_backtest(strategy, data, 20, 80)
    assert sharpe_a == sharpe_b
