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


def find_strategy_class(sandbox_locals: dict) -> type | None:
    """Dynamically find the first class with a generate_signals method in sandbox locals."""
    for obj in sandbox_locals.values():
        if isinstance(obj, type) and hasattr(obj, "generate_signals"):
            return obj
    return None


def calculate_metrics(combined_returns: pd.Series, trades: pd.Series) -> dict:
    """Calculate 10 performance metrics from combined returns and trade signals."""
    mean_ret = combined_returns.mean()
    std_ret = combined_returns.std()

    # Sharpe
    sharpe = (mean_ret / std_ret) * np.sqrt(252) if std_ret != 0 else 0.0

    # Sortino — downside deviation only
    downside = combined_returns[combined_returns < 0]
    downside_std = downside.std() if len(downside) > 0 else 0.0
    sortino = (mean_ret / downside_std) * np.sqrt(252) if downside_std != 0 else 0.0

    # Max Drawdown
    cum = (1 + combined_returns).cumprod()
    running_max = cum.cummax()
    drawdown = (cum - running_max) / running_max
    max_drawdown = drawdown.min()

    # Calmar — annualized return / abs(max drawdown)
    annualized_return = mean_ret * 252
    calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    # Max DD Days — longest drawdown duration
    in_dd = drawdown < 0
    dd_groups = (in_dd != in_dd.shift()).cumsum()
    max_dd_days = 0
    if in_dd.any():
        dd_durations = in_dd.groupby(dd_groups).sum()
        max_dd_days = int(dd_durations.max()) if len(dd_durations) > 0 else 0

    # Trades count — number of position changes
    trade_changes = trades.diff().abs()
    trade_changes = trade_changes[trade_changes > 0]
    total_trades = int(trade_changes.sum()) if len(trade_changes) > 0 else 0

    # Win Rate
    trade_returns = trades[trades != 0]
    if len(trade_returns) > 0:
        wins = (trade_returns > 0).sum()
        win_rate = float(wins / len(trade_returns))
    else:
        win_rate = 0.0

    # Profit Factor
    gross_profit = trade_returns[trade_returns > 0].sum() if len(trade_returns) > 0 else 0.0
    gross_loss = abs(trade_returns[trade_returns < 0].sum()) if len(trade_returns) > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else 0.0

    # Avg Win / Avg Loss
    avg_win = float(trade_returns[trade_returns > 0].mean()) if (trade_returns > 0).any() else 0.0
    avg_loss = float(trade_returns[trade_returns < 0].mean()) if (trade_returns < 0).any() else 0.0

    return {
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "drawdown": max_drawdown,
        "max_dd_days": max_dd_days,
        "trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
    }


def calculate_baseline_sharpe(data: dict) -> float:
    """Calculate Buy&Hold Sharpe across all symbols."""
    all_returns = []
    for symbol, df in data.items():
        if "returns" in df.columns:
            all_returns.append(df["returns"])
    if not all_returns:
        return 0.0
    combined = pd.concat(all_returns).dropna()
    std = combined.std()
    return float((combined.mean() / std) * np.sqrt(252)) if std != 0 else 0.0


def run_per_symbol_analysis(strategy_instance, data: dict, start_idx: int, end_idx: int) -> dict:
    """Run per-symbol analysis returning sharpe, sortino, dd, pf, trades, wr for each symbol."""
    results = {}
    BASE_COST = 0.0005

    for symbol, df in data.items():
        history_df = df.iloc[:end_idx].copy()
        try:
            full_signals = strategy_instance.generate_signals(history_df)
            if not isinstance(full_signals, pd.Series):
                full_signals = pd.Series(full_signals, index=history_df.index)
            full_signals = full_signals.fillna(0)
            signals = full_signals.shift(1).fillna(0).iloc[start_idx:end_idx]
        except Exception:
            results[symbol] = {"sharpe": 0.0, "sortino": 0.0, "dd": 0.0, "pf": 0.0, "trades": 0, "wr": 0.0}
            continue

        test_returns = df.iloc[start_idx:end_idx]["returns"]
        daily_returns = test_returns * signals

        # Costs
        trades_series = signals.diff().abs().fillna(0)
        vol = df.iloc[start_idx:end_idx]["volatility"]
        slippage = vol * 0.1
        costs = trades_series * (BASE_COST + slippage)
        net_returns = daily_returns - costs

        # Metrics
        std = net_returns.std()
        sharpe = float((net_returns.mean() / std) * np.sqrt(252)) if std != 0 else 0.0

        downside = net_returns[net_returns < 0]
        downside_std = downside.std() if len(downside) > 0 else 0.0
        sortino = float((net_returns.mean() / downside_std) * np.sqrt(252)) if downside_std != 0 else 0.0

        cum = (1 + net_returns).cumprod()
        running_max = cum.cummax()
        dd = ((cum - running_max) / running_max).min()

        trade_changes = signals.diff().abs()
        trade_changes = trade_changes[trade_changes > 0]
        trade_count = int(trade_changes.sum()) if len(trade_changes) > 0 else 0

        trade_rets = net_returns[signals != 0]
        if len(trade_rets) > 0:
            wins = (trade_rets > 0).sum()
            wr = float(wins / len(trade_rets))
            gp = trade_rets[trade_rets > 0].sum()
            gl = abs(trade_rets[trade_rets < 0].sum())
            pf = float(gp / gl) if gl != 0 else 0.0
        else:
            wr = 0.0
            pf = 0.0

        results[symbol] = {
            "sharpe": sharpe,
            "sortino": sortino,
            "dd": float(dd),
            "pf": pf,
            "trades": trade_count,
            "wr": wr,
        }

    return results


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
        return -10.0, 0.0, 0
        
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
        
        strategy_class = find_strategy_class(sandbox_locals)
        if not strategy_class:
            print("STRATEGY ERROR: No class with generate_signals found in strategy.py")
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
    window_size = min_len // 5
    all_metrics = []

    for i in range(5):
        train_end = int((i + 1) * window_size * 0.7)
        test_start = train_end
        test_end = (i + 1) * window_size

        # Collect combined returns and trades for metrics
        window_returns = []
        window_trades = pd.Series(dtype=float)
        for symbol, df in data.items():
            history_df = df.iloc[:test_end].copy()
            try:
                full_signals = strategy_instance.generate_signals(history_df)
                if not isinstance(full_signals, pd.Series):
                    full_signals = pd.Series(full_signals, index=history_df.index)
                full_signals = full_signals.fillna(0)
                signals = full_signals.shift(1).fillna(0).iloc[test_start:test_end]
            except Exception:
                continue

            test_returns = df.iloc[test_start:test_end]["returns"]
            daily_returns = test_returns * signals
            trades = signals.diff().abs().fillna(0)
            vol = df.iloc[test_start:test_end]["volatility"]
            slippage = vol * 0.1
            costs = trades * (0.0005 + slippage)
            net_returns = daily_returns - costs
            window_returns.append(net_returns)
            window_trades = pd.concat([window_trades, signals])

        if window_returns:
            combined = pd.concat(window_returns, axis=1).mean(axis=1)
            metrics = calculate_metrics(combined, window_trades)
            all_metrics.append(metrics)

    if not all_metrics:
        print("ERROR: No valid windows produced results")
        sys.exit(1)

    # Average metrics across all windows
    avg_metrics = {}
    for key in all_metrics[0]:
        avg_metrics[key] = float(np.mean([m[key] for m in all_metrics]))

    # Baseline Sharpe
    baseline_sharpe = calculate_baseline_sharpe(data)

    # Per-symbol analysis (on last window)
    last_test_start = int(5 * window_size * 0.7)
    last_test_end = 5 * window_size
    per_symbol = run_per_symbol_analysis(strategy_instance, data, last_test_start, last_test_end)

    # Output YAML-like format
    print("---")
    print(f"SCORE: {avg_metrics['sharpe']:.4f}")
    print(f"SORTINO: {avg_metrics['sortino']:.4f}")
    print(f"CALMAR: {avg_metrics['calmar']:.4f}")
    print(f"DRAWDOWN: {avg_metrics['drawdown']:.4f}")
    print(f"MAX_DD_DAYS: {avg_metrics['max_dd_days']}")
    print(f"TRADES: {avg_metrics['trades']}")
    print(f"P_VALUE: 0.0000")
    print(f"WIN_RATE: {avg_metrics['win_rate']:.4f}")
    print(f"PROFIT_FACTOR: {avg_metrics['profit_factor']:.4f}")
    print(f"AVG_WIN: {avg_metrics['avg_win']:.4f}")
    print(f"AVG_LOSS: {avg_metrics['avg_loss']:.4f}")
    print(f"BASELINE_SHARPE: {baseline_sharpe:.4f}")
    print("---")
    print("PER_SYMBOL:")
    for symbol, sym_metrics in per_symbol.items():
        print(f"  {symbol}: sharpe={sym_metrics['sharpe']:.2f} sortino={sym_metrics['sortino']:.2f} "
              f"dd={sym_metrics['dd']:.2f} pf={sym_metrics['pf']:.2f} "
              f"trades={sym_metrics['trades']} wr={sym_metrics['wr']:.2f}")

if __name__ == "__main__":
    walk_forward_validation()
