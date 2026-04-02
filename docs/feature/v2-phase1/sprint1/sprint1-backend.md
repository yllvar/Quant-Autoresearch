# Sprint 1 — Backend Plan

> Feature: `v2-phase1`
> Role: Backend
> Derived from: #8 (Phase 1: Backtester + program.md + strategy interface) — backtester core portion
> Last Updated: 2026-04-02 (Sprint 1 closeout)

## 0) Governing Specs

1. `docs/upgrade-plan-v2.md` — Section 7 (backtester.py specific changes), Section 2 (output format), Section 2.3 (hard constraints)
2. `docs/feature/v2-phase1/v2-phase1-development-plan.md` — Tasks BT-01 through BT-08

## 1) Sprint Mission

Upgrade `src/core/backtester.py` from a minimal 4-metric output (SCORE, DRAWDOWN, TRADES, P-VALUE) to the full V2 spec: 10+ metrics, dynamic strategy class loading, Buy&Hold baseline, per-symbol analysis, and YAML-like output format. Remove the Monte Carlo permutation test (to be replaced by Deflated Sharpe Ratio in a future session).

## 2) Scope / Out of Scope

**Scope**
- Add `find_strategy_class(sandbox_locals)` — replaces hardcoded `"TradingStrategy"` at line 219
- Add `calculate_metrics(combined_returns, trades)` — 10 metrics: Sharpe, Sortino, Calmar, Drawdown, Max DD Days, Trades, Win Rate, Profit Factor, Avg Win, Avg Loss
- Add `calculate_baseline_sharpe(data)` — Buy&Hold Sharpe across all symbols
- Add `run_per_symbol_analysis(strategy_instance, data, start_idx, end_idx)` — per-symbol dict output
- Update `walk_forward_validation()` to use new functions and output full YAML-like format
- Remove `monte_carlo_permutation_test()` function

**Out of Scope**
- Root `program.md` creation — Sprint 2
- EDITABLE REGION marker removal — Sprint 2
- New test files (`test_backtester_v2.py`, `test_strategy_interface.py`) — Sprint 2
- Deflated Sharpe Ratio implementation — future session

## 3) Step-by-Step Plan

### Step 1 — Create feature branch + baseline
- [x] `git checkout -b feature/v2-phase1 main`
- [x] Run `pytest --tb=short -q` and record test count as baseline
- [x] Record baseline: 88 tests collected, 87 passed, 1 error (test_llm_summarization — dummy API key, expected)

### Step 2 — Add `find_strategy_class()` (BT-02)
- [x] Add function to backtester.py after the imports/constants section
- [x] Function signature: `def find_strategy_class(sandbox_locals: dict) -> type | None`
- [x] Logic: iterate sandbox_locals, return first class with `generate_signals` attribute
- [x] Update `walk_forward_validation()` line 219: replace `sandbox_locals.get("TradingStrategy")` with `find_strategy_class(sandbox_locals)`
- [x] Update error message: "STRATEGY ERROR: No class with generate_signals found in strategy.py"
- [x] Verify: `python -c "from src.core.backtester import find_strategy_class; print('OK')"`

### Step 3 — Add `calculate_metrics()` (BT-03)
- [x] Add function to backtester.py
- [x] Function signature: `def calculate_metrics(combined_returns: pd.Series, trades: pd.Series) -> dict`
- [x] Implement all 10 metrics with zero-division guards:
  - `sharpe`: `(mean / std) * sqrt(252)` — same as current, but extracted
  - `sortino`: `(mean / downside_std) * sqrt(252)`
  - `calmar`: `annualized_return / abs(drawdown)`
  - `drawdown`: max peak-to-trough decline
  - `max_dd_days`: longest drawdown duration in days
  - `trades`: total trade count
  - `win_rate`: winning_trades / total_trades
  - `profit_factor`: gross_profit / gross_loss
  - `avg_win`: mean of positive trade returns
  - `avg_loss`: mean of negative trade returns
- [x] Verify: `python -c "from src.core.backtester import calculate_metrics; print('OK')"`

### Step 4 — Add `calculate_baseline_sharpe()` (BT-04)
- [x] Add function to backtester.py
- [x] Function signature: `def calculate_baseline_sharpe(data: dict) -> float`
- [x] Logic: concat all symbol returns, compute mean/std Sharpe, annualize with sqrt(252)
- [x] Verify: `python -c "from src.core.backtester import calculate_baseline_sharpe; print('OK')"`

### Step 5 — Add `run_per_symbol_analysis()` (BT-05)
- [x] Add function to backtester.py
- [x] Function signature: `def run_per_symbol_analysis(strategy_instance, data: dict, start_idx: int, end_idx: int) -> dict`
- [x] For each symbol: compute sharpe, sortino, drawdown, profit_factor, trades, win_rate
- [x] Return dict keyed by symbol name
- [x] Verify: `python -c "from src.core.backtester import run_per_symbol_analysis; print('OK')"`

### Step 6 — Update `walk_forward_validation()` output format (BT-06)
- [x] Replace current `run_backtest()` calls with new metrics functions
- [x] Walk-forward loop accumulates metrics from `calculate_metrics()` across 5 windows
- [x] Compute `calculate_baseline_sharpe(data)` once
- [x] Compute `run_per_symbol_analysis()` once (on last window or averaged)
- [x] Output YAML-like format:
  ```
  ---
  SCORE: 0.5432
  SORTINO: 0.8100
  CALMAR: 1.2300
  DRAWDOWN: -0.1200
  MAX_DD_DAYS: 45
  TRADES: 120
  P_VALUE: 0.0300
  WIN_RATE: 0.5500
  PROFIT_FACTOR: 1.8500
  AVG_WIN: 0.0120
  AVG_LOSS: -0.0080
  BASELINE_SHARPE: 0.4500
  ---
  PER_SYMBOL:
    SPY: sharpe=0.62 sortino=0.90 dd=-0.10 pf=2.10 trades=35 wr=0.57
    ...
  ```
- [ ] P_VALUE: use 0.0 as placeholder (monte_carlo removed, Deflated SR not yet implemented)
- [ ] Verify: `uv run python src/core/backtester.py 2>&1 | head -20` shows new format

### Step 7 — Remove `monte_carlo_permutation_test()` (BT-07)
- [x] Delete the function (lines 77-101)
- [x] Remove any calls to it from `run_backtest()` or `walk_forward_validation()`
- [x] Ensure no surviving code references `monte_carlo_permutation_test`
- [x] Verify: `grep -n "monte_carlo_permutation_test" src/core/backtester.py` returns 0 hits

### Step 8 — Commit Sprint 1 changes (BT-08)
- [x] `git add src/core/backtester.py`
- [x] `git commit -m "feat(backtester): add dynamic loading, full metrics, baseline, per-symbol output"`

## 4) Test Plan

- [x] After Step 2: verify `find_strategy_class` works with a mock sandbox dict
  ```python
  class MockStrategy:
      def generate_signals(self, data): pass
  from src.core.backtester import find_strategy_class
  result = find_strategy_class({"MockStrategy": MockStrategy})
  assert result is MockStrategy
  ```
- [x] After Step 3: verify `calculate_metrics` with synthetic data
  ```python
  import pandas as pd, numpy as np
  from src.core.backtester import calculate_metrics
  returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
  trades = pd.Series([1, -1, 1, 0, -1])
  m = calculate_metrics(returns, trades)
  assert all(k in m for k in ['sharpe','sortino','calmar','drawdown','max_dd_days','trades','win_rate','profit_factor','avg_win','avg_loss'])
  ```
- [x] After Step 4-5: verify `calculate_baseline_sharpe` and `run_per_symbol_analysis` import without error
- [x] After Step 6: verify output format with `uv run python src/core/backtester.py` (requires cached data)
- [x] After Step 7: verify `monte_carlo_permutation_test` is gone
  ```bash
  grep -n "monte_carlo_permutation_test" src/core/backtester.py || echo "REMOVED OK"
  ```
- [x] Existing tests still pass: `pytest tests/unit/ -v --tb=short`

## 5) Verification Commands

```bash
# Confirm new functions exist
grep -n "def find_strategy_class\|def calculate_metrics\|def calculate_baseline_sharpe\|def run_per_symbol_analysis" src/core/backtester.py

# Confirm monte_carlo removed
grep -n "def monte_carlo_permutation_test" src/core/backtester.py && echo "FAIL" || echo "REMOVED OK"

# Confirm hardcoded class name is gone
grep -n '"TradingStrategy"' src/core/backtester.py && echo "FAIL: still hardcoded" || echo "DYNAMIC OK"

# Import check
python -c "from src.core.backtester import find_strategy_class, calculate_metrics, calculate_baseline_sharpe, run_per_symbol_analysis; print('ALL IMPORTS OK')"

# Surviving modules still work
python -c "from src.core.backtester import security_check, load_data; print('EXISTING FUNCTIONS OK')"

# Run existing tests
pytest tests/unit/ --tb=short -q
```

## 6) Implementation Update Space

### Completed Work

- Added `find_strategy_class()`, `calculate_metrics()`, `calculate_baseline_sharpe()`, `run_per_symbol_analysis()` to backtester.py
- Updated `walk_forward_validation()` to use new functions with YAML-like output format
- Removed `monte_carlo_permutation_test()` and all references
- Replaced hardcoded `"TradingStrategy"` with dynamic class discovery
- Updated `run_backtest()` to return 3 values (removed p_value)
- Updated existing tests (`test_runner.py`, `test_determinism.py`) for new return signature

### Command Results

- Baseline: 88 tests (87 passed, 1 expected failure)
- Post-merge from main: V1 OPENDEV modules removed (expected), test count reduced
- After Sprint 1 changes: 37 tests passed, 0 failures
- All verification checks passed (imports, removal, dynamic loading)

### Blockers / Deviations

- `run_backtest()` return signature changed from 4→3 values (removed p_value) — existing tests updated accordingly

### Follow-ups

- Sprint 2: write program.md, remove EDITABLE REGION, add test files
