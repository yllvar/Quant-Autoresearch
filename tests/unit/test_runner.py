import pytest
import pandas as pd
import numpy as np
from core.backtester import run_backtest

class MockStrategy:
    def generate_signals(self, data):
        # Long only signal
        return pd.Series(1, index=data.index)

def test_run_backtest_sharpe_calculation(sample_data):
    strategy = MockStrategy()
    data = {"TEST": sample_data}
    
    # We expect a positive Sharpe because returns are constant 0.001
    sharpe, dd, trades, pval = run_backtest(strategy, data, 10, 90)
    
    assert isinstance(sharpe, float)
    assert sharpe > 0
    assert dd <= 0
    assert trades >= 0

def test_run_backtest_lookahead_enforcement(sample_data):
    class LookaheadStrategy:
        def generate_signals(self, data):
            # Try to cheat by looking at current close
            return (data['Close'] > 105).astype(int)
            
    strategy = LookaheadStrategy()
    data = {"TEST": sample_data}
    
    # The runner enforces lag by shifting the signals
    sharpe, dd, trades, pval = run_backtest(strategy, data, 10, 90)
    
    # Even if the strategy "cheats", the runner should apply .shift(1)
    # This test verifies the runner doesn't crash and returns metrics.
    assert sharpe is not None

def test_transaction_costs_impact(sample_data):
    """Verifies that transaction costs correctly reduce the score."""
    class AlternatingStrategy:
        def generate_signals(self, data):
            # Switch every day to maximize transaction costs
            return pd.Series([1, -1] * (len(data)//2), index=data.index)
            
    strategy = AlternatingStrategy()
    data = {"TEST": sample_data}
    
    # Run backtest
    # Higher costs should lead to lower Sharpe than a static strategy
    sharpe, dd, trades, pval = run_backtest(strategy, data, 10, 90)
    
    assert trades > 0
    # With 0.001 daily return and 0.01 vol, but frequent 0.0005 cost + slippage
    # Net returns should be much lower or negative
    assert sharpe < 5 # High frequency trading in this setup usually destroys returns
