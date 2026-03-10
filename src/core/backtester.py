import os
import sys
import pandas as pd
import numpy as np
import importlib.util
import re

import ast

CACHE_DIR = "data/cache"
STRATEGY_FILE = "src/strategies/active_strategy.py"

FORBIDDEN_BUILTINS = {'exec', 'eval', 'open', 'getattr', 'setattr', 'delattr'}
FORBIDDEN_MODULES = {'socket', 'requests', 'urllib', 'os', 'sys', 'shutil', 'subprocess'}

def security_check():
    """
    Performs security analysis on strategy.py using AST to find forbidden patterns.
    """
    if not os.path.exists(STRATEGY_FILE):
        return False, "strategy.py not found"
    
    try:
        with open(STRATEGY_FILE, "r") as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            # Check for forbidden function calls
            if isinstance(node, ast.Call):
                # Call by name
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                    return False, f"Forbidden builtin function found: {node.func.id}"
                
                # Check for negative shift (look-ahead)
                if isinstance(node.func, ast.Attribute) and node.func.attr == 'shift':
                    # Check positional arguments
                    for arg in node.args:
                        if is_negative_val(arg):
                            return False, "Look-ahead bias detected (.shift(-N))"
                    # Check keyword arguments
                    for kw in node.keywords:
                        if kw.arg == 'periods' and is_negative_val(kw.value):
                            return False, "Look-ahead bias detected (.shift(periods=-N))"
                
            # Check for forbidden imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_MODULES:
                        return False, f"Forbidden module import found: {alias.name}"
            if isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_MODULES:
                    return False, f"Forbidden module import found: {node.module}"
                                
        return True, ""
    except Exception as e:
        return False, f"AST Parsing Error: {e}"

def is_negative_val(node):
    """Helper to check if an AST node represents a negative constant."""
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
            return node.operand.value > 0
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value < 0
    if isinstance(node, ast.BinOp):
        # Recursively check for negative components in BinOp (coarse but safe)
        return is_negative_val(node.left) or is_negative_val(node.right)
    return False

def load_data():
    data = {}
    for file in os.listdir(CACHE_DIR):
        if file.endswith(".parquet"):
            symbol = file.replace(".parquet", "").replace("_", "-")
            df = pd.read_parquet(os.path.join(CACHE_DIR, file))
            data[symbol] = df
    return data

def run_backtest(strategy_instance, data, start_idx, end_idx):
    """
    Evaluates strategy on a specific window [start_idx:end_idx].
    Warms up indicators by passing the full history up to end_idx.
    """
    total_returns = []
    BASE_COST = 0.0005 # 0.05%
    
    for symbol, df in data.items():
        # Provide history up to end_idx for indicator calculation
        history_df = df.iloc[:end_idx].copy()
        
        try:
            # Agent generates signals for the entire period provided
            full_signals = strategy_instance.generate_signals(history_df)
            
            # Robustness: Force into Series if LLM returned numpy array
            if not isinstance(full_signals, pd.Series):
                full_signals = pd.Series(full_signals, index=history_df.index)
            
            # Fill NaNs with 0 to prevent downstream crashes
            full_signals = full_signals.fillna(0)
            
            # Slice to only the test window
            signals = full_signals.iloc[start_idx:end_idx]
        except Exception as e:
            print(f"Error in {symbol} strategy: {e}", file=sys.stderr)
            return -10.0, 0.0, 0
            
        # Enforced Lag: Shift signals by 1 to prevent look-ahead bias
        signals = full_signals.shift(1).fillna(0).iloc[start_idx:end_idx]
        
        # Returns for the test window
        test_returns = df.iloc[start_idx:end_idx]['returns']
        daily_returns = test_returns * signals
        
        # Costs: base cost + volatility slippage
        trades = signals.diff().abs().fillna(0)
        vol = df.iloc[start_idx:end_idx]['volatility']
        slippage = vol * 0.1 
        costs = trades * (BASE_COST + slippage)
        
        net_returns = daily_returns - costs
        total_returns.append(net_returns)
        
    if not total_returns:
        return -10.0
        
    combined_returns = pd.concat(total_returns, axis=1).mean(axis=1)
    
    # Sharpe Ratio (Annualized)
    if combined_returns.std() == 0:
        sharpe = 0.0
    else:
        sharpe = (combined_returns.mean() / combined_returns.std()) * np.sqrt(252)
    
    # Max Drawdown
    cum_returns = (1 + combined_returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Total Trades (rough estimate sum across symbols)
    total_trades = 0
    for symbol, df in data.items():
        history_df = df.iloc[:end_idx].copy()
        try:
            full_signals = strategy_instance.generate_signals(history_df)
            signals = full_signals.iloc[start_idx:end_idx]
            total_trades += signals.diff().abs().sum()
        except:
            pass

    return sharpe, max_drawdown, total_trades

def walk_forward_validation():
    is_safe, msg = security_check()
    if not is_safe:
        print(f"SECURITY ERROR: {msg}")
        sys.exit(1)
        
    # Load Strategy
    try:
        spec = importlib.util.spec_from_file_location("strategy", STRATEGY_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        strategy_class = getattr(module, "TradingStrategy")
        strategy_instance = strategy_class()
    except Exception as e:
        print(f"STRATEGY LOAD ERROR: {e}")
        sys.exit(1)
        
    data = load_data()
    if not data:
        print("DATA ERROR: No cached data found.")
        sys.exit(1)
        
    # Determine the shortest timeframe to align windows
    min_len = min([len(df) for df in data.values()])
    
    # Walk-forward: 5 windows
    # 70% train / 30% test? No, easier to just do rolling OOS.
    # Let's do 5 split windows.
    window_size = min_len // 5
    oos_sharpes = []
    oos_drawdowns = []
    oos_trades = []
    
    for i in range(5):
        train_end = int((i + 1) * window_size * 0.7)
        test_start = train_end
        test_end = (i + 1) * window_size
        
        # We only care about OOS performance for the final score
        sharpe, dd, trades = run_backtest(strategy_instance, data, test_start, test_end)
        oos_sharpes.append(sharpe)
        oos_drawdowns.append(dd)
        oos_trades.append(trades)
        
    avg_oos_sharpe = np.mean(oos_sharpes)
    avg_oos_dd = np.mean(oos_drawdowns)
    total_oos_trades = np.sum(oos_trades)
    
    score = avg_oos_sharpe
        
    print(f"SCORE: {score:.4f}")
    print(f"DRAWDOWN: {avg_oos_dd:.4f}")
    print(f"TRADES: {int(total_oos_trades)}")

if __name__ == "__main__":
    walk_forward_validation()
