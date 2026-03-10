import os
import sys
import pandas as pd
import numpy as np
import re
import ast
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Guards import safer_getattr, full_write_guard
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem
from data.connector import DataConnector

CACHE_DIR = os.environ.get("CACHE_DIR", "data/cache")
STRATEGY_FILE = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STRATEGY_FILE", "src/strategies/active_strategy.py")

FORBIDDEN_BUILTINS = {'exec', 'eval', 'open', 'getattr', 'setattr', 'delattr'}
FORBIDDEN_MODULES = {'socket', 'requests', 'urllib', 'os', 'sys', 'shutil', 'subprocess'}

def security_check(file_path: str = None):
    """
    Performs security analysis on a strategy file using AST to find forbidden patterns.
    """
    target = file_path or STRATEGY_FILE
    if not os.path.exists(target):
        return False, f"Strategy file not found: {target}"
    
    try:
        with open(target, "r") as f:
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
    connector = DataConnector(CACHE_DIR)
    return connector.load_all_cached()

def monte_carlo_permutation_test(combined_returns, n_permutations=1000):
    """
    Performs a Monte Carlo permutation test to evaluate if the strategy's Sharpe
    ratio is statistically significant compared to random behavior.
    """
    if len(combined_returns) == 0 or combined_returns.std() == 0:
        return 1.0
        
    actual_sharpe = (combined_returns.mean() / combined_returns.std()) * np.sqrt(252)
    
    # Generate random permutations of the returns
    permuted_sharpes = []
    returns_values = combined_returns.values
    for _ in range(n_permutations):
        permuted_returns = np.random.permutation(returns_values)
        std = permuted_returns.std()
        if std > 0:
            perm_sharpe = (permuted_returns.mean() / std) * np.sqrt(252)
            permuted_sharpes.append(perm_sharpe)
        else:
            permuted_sharpes.append(0.0)
            
    # Calculate p-value (proportion of random sharpes >= actual sharpe)
    p_value = np.sum(np.array(permuted_sharpes) >= actual_sharpe) / n_permutations
    return p_value

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
        return -10.0, 0.0, 0, 1.0
        
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
    
    # Multi-tenant / Robustness point 1: Monte Carlo
    p_value = monte_carlo_permutation_test(combined_returns)
    
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

    return sharpe, max_drawdown, total_trades, p_value

def walk_forward_validation():
    is_safe, msg = security_check()
    if not is_safe:
        print(f"SECURITY ERROR: {msg}")
        sys.exit(1)
        
    # Load Strategy via RestrictedPython Sandbox
    try:
        with open(STRATEGY_FILE, "r") as f:
            strategy_lines = f.readlines()
        
        # Strip import statements for restricted execution
        sanitized_code = []
        for line in strategy_lines:
            if not (line.strip().startswith("import ") or line.strip().startswith("from ")):
                sanitized_code.append(line)
        strategy_code = "".join(sanitized_code)
        
        # Define the restricted environment
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
        
        # Compile the code in restricted mode
        byte_code = compile_restricted(strategy_code, filename='strategy.py', mode='exec')
        
        # Execute in safe scope
        sandbox_locals = {}
        exec(byte_code, safe_globals, sandbox_locals)
        
        strategy_class = sandbox_locals.get("TradingStrategy")
        if not strategy_class:
            print("STRATEGY ERROR: TradingStrategy class not found in strategy.py")
            sys.exit(1)
            
        strategy_instance = strategy_class()
    except Exception as e:
        print(f"STRATEGY LOAD ERROR (Restricted): {e}")
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
    oos_pvals = []
    
    for i in range(5):
        train_end = int((i + 1) * window_size * 0.7)
        test_start = train_end
        test_end = (i + 1) * window_size
        
        # We only care about OOS performance for the final score
        sharpe, dd, trades, p_val = run_backtest(strategy_instance, data, test_start, test_end)
        oos_sharpes.append(sharpe)
        oos_drawdowns.append(dd)
        oos_trades.append(trades)
        oos_pvals.append(p_val)
        
    avg_oos_sharpe = np.mean(oos_sharpes)
    avg_oos_dd = np.mean(oos_drawdowns)
    total_oos_trades = np.sum(oos_trades)
    avg_oos_pval = np.mean(oos_pvals)
    
    score = avg_oos_sharpe
        
    print(f"SCORE: {score:.4f}")
    print(f"DRAWDOWN: {avg_oos_dd:.4f}")
    print(f"TRADES: {int(total_oos_trades)}")
    print(f"P-VALUE: {avg_oos_pval:.4f}")

if __name__ == "__main__":
    walk_forward_validation()
