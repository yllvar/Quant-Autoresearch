# Sprint 2 — Backend Plan

> Feature: `v2-phase1`
> Role: Backend
> Derived from: #8 (Phase 1: Backtester + program.md + strategy interface) — interface + tests portion
> Last Updated: 2026-04-02 (Sprint 2 closeout)

## 0) Governing Specs

1. `docs/upgrade-plan-v2.md` — Section 5 (program.md complete design), Section 8 (test plan), Section 3 (results.tsv format), Section 4 (Obsidian notes)
2. `docs/feature/v2-phase1/v2-phase1-development-plan.md` — Tasks PROG-01, STRAT-01, TEST-01, TEST-02, TEST-03, COMMIT-02

## 1) Sprint Mission

Create the root `program.md` file that serves as the complete instruction set for the Claude Code/Codex agent, remove the EDITABLE REGION markers from `active_strategy.py` to enable full-file modification, and write comprehensive tests for all new backtester functions and the strategy interface.

## 2) Scope / Out of Scope

**Scope**
- Write `program.md` at repository root (complete agent instruction file per Section 5 spec)
- Remove `# --- EDITABLE REGION BREAK ---` and `# --- EDITABLE REGION END ---` from `active_strategy.py`
- Create `tests/unit/test_backtester_v2.py` with tests for all new backtester functions
- Create `tests/unit/test_strategy_interface.py` with tests for dynamic loading and free-form strategy
- Run full test suite to verify everything passes

**Out of Scope**
- `results.tsv` creation or `experiments/notes/` directory — runtime concern, not code
- CLI simplification — Phase 3
- Obsidian vault setup — Phase 3
- Updating `CLAUDE.md` — Phase 4
- Deflated Sharpe Ratio — future session

## 3) Step-by-Step Plan

### Step 1 — Write root program.md (PROG-01)
- [x] Create `program.md` at repository root
- [x] Content follows `docs/upgrade-plan-v2.md` Section 5 spec exactly:
  - **Setup** section: run tag, branch creation, in-scope files, data verification, baseline run
  - **Experimentation** section: what CAN/CANNOT do, vectorized only, no shift(-N)
  - **The goal** section: highest SCORE (Average Walk-Forward OOS Sharpe)
  - **Output format** section: full YAML-like format with all 12 metrics + PER_SYMBOL block
  - **Decision rules** section: KEEP/DISCARD criteria, simplicity criterion
  - **Logging results** section: results.tsv format
  - **Obsidian experiment notes** section: note format and structure
  - **The experiment loop** section: NEVER STOP, 13-step loop
- [x] Verify: `test -f program.md && wc -l program.md` → 137 lines

### Step 2 — Remove EDITABLE REGION markers (STRAT-01)
- [x] Open `src/strategies/active_strategy.py`
- [x] Remove line 23: `# --- EDITABLE REGION BREAK ---`
- [x] Remove line 50: `# --- EDITABLE REGION END ---`
- [x] Verify file still valid Python: `python -c "import ast; ast.parse(...); print('VALID')"`
- [x] Verify markers gone: `grep "EDITABLE REGION" ... || echo "MARKERS REMOVED"`
- [x] Verify `TradingStrategy` class still intact: `grep "class TradingStrategy"`

### Step 3 — Write tests/unit/test_backtester_v2.py (TEST-01)
- [x] Create test file with the following test functions:

#### find_strategy_class tests
- [x] `test_find_strategy_class_found` — mock class with generate_signals is found
- [x] `test_find_strategy_class_not_found` — empty dict returns None
- [x] `test_find_strategy_class_multiple` — first matching class returned
- [x] `test_find_strategy_class_non_class_ignored` — functions/variables ignored

#### calculate_metrics tests
- [x] `test_calculate_metrics_basic` — all 10 keys present in return dict
- [x] `test_calculate_metrics_zero_std` — constant returns → sharpe=0, sortino=0
- [x] `test_calculate_metrics_all_positive` — win_rate=1.0, avg_loss=0
- [x] `test_calculate_metrics_all_negative` — win_rate=0.0, profit_factor=0
- [x] `test_calculate_metrics_sortino_vs_sharpe` — sortino > sharpe for upside-skewed returns
- [x] `test_calculate_metrics_calmar` — known return path gives expected calmar
- [x] `test_calculate_metrics_drawdown` — known drawdown value
- [x] `test_calculate_metrics_max_dd_days` — known drawdown duration
- [x] `test_calculate_metrics_profit_factor` — known PF value
- [x] `test_calculate_metrics_win_rate` — known WR value
- [x] `test_calculate_metrics_avg_win_loss` — known avg values

#### calculate_baseline_sharpe tests
- [x] `test_calculate_baseline_sharpe_basic` — multi-symbol dict returns positive float
- [x] `test_calculate_baseline_sharpe_zero_std` — constant returns → 0.0
- [x] `test_calculate_baseline_sharpe_single_symbol` — works with one symbol
- [x] `test_calculate_baseline_sharpe_empty` — empty dict returns 0.0
- [x] `test_calculate_baseline_sharpe_no_returns_column` — missing column returns 0.0

#### run_per_symbol_analysis tests
- [x] `test_run_per_symbol_analysis_basic` — returns dict with all symbols as keys
- [x] `test_run_per_symbol_analysis_keys` — each symbol has sharpe, sortino, dd, pf, trades, wr
- [x] `test_run_per_symbol_analysis_signal_lag` — signals shifted by 1 bar
- [x] `test_run_per_symbol_analysis_exception_handling` — strategy error produces zeroed metrics
- [x] `test_run_per_symbol_analysis_non_series_signals` — non-Series signals handled

#### Output format tests
- [x] `test_output_format_has_all_metrics` — stdout contains all metric lines
- [x] `test_output_format_has_per_symbol` — stdout contains PER_SYMBOL block

### Step 4 — Write tests/unit/test_strategy_interface.py (TEST-02)
- [x] Create test file with the following test functions:

#### Dynamic loading tests
- [x] `test_free_form_class_accepted` — custom class name works via find_strategy_class
- [x] `test_custom_class_name` — "MomentumStrategy" loads correctly
- [x] `test_multiple_methods_allowed` — class with generate_signals + helper methods
- [x] `test_no_generate_signals_rejected` — class without generate_signals returns None
- [x] `test_non_class_with_generate_signals_ignored` — function named generate_signals ignored

#### Strategy file tests
- [x] `test_editable_region_removed` — no EDITABLE REGION in active_strategy.py
- [x] `test_strategy_file_exists` — active_strategy.py exists
- [x] `test_strategy_file_valid_python` — file parses as valid Python
- [x] `test_strategy_has_trading_strategy_class` — TradingStrategy class present
- [x] `test_trading_strategy_has_generate_signals` — generate_signals method exists
- [x] `test_strategy_has_imports` — file has pandas and numpy imports
- [x] `test_strategy_in_sandbox` — active_strategy.py compiles in RestrictedPython
- [x] `test_strategy_returns_series` — generate_signals returns pd.Series for sample data
- [x] `test_strategy_signal_range` — signals in {-1, 0, 1}
- [x] `test_strategy_class_init` — TradingStrategy can be instantiated with default params

#### Free-form strategy tests
- [x] `test_custom_named_strategy_via_sandbox` — custom class works in sandbox
- [x] `test_multiple_strategies_returns_first` — first matching class returned

### Step 5 — Run full test suite (TEST-03)
- [x] `pytest tests/unit/test_backtester_v2.py -v` → 25 passed
- [x] `pytest tests/unit/test_strategy_interface.py -v` → 17 passed
- [x] `pytest tests/unit/ -v --tb=short` → 79 passed, 0 failures
- [x] All tests pass with 0 failures

### Step 6 — Commit Sprint 2 (COMMIT-02)
- [ ] `git add program.md src/strategies/active_strategy.py tests/unit/test_backtester_v2.py tests/unit/test_strategy_interface.py`
- [ ] `git commit -m "feat(v2-phase1): add program.md, remove EDITABLE REGION, add backtester and strategy tests"`

## 4) Test Plan

Tests are the deliverable of this sprint. Verification is that all tests pass:

```bash
# New tests
pytest tests/unit/test_backtester_v2.py tests/unit/test_strategy_interface.py -v
# → 42 passed

# Full suite (new + existing)
pytest --tb=short -v
# → 79 passed in 0.81s
```

## 5) Verification Commands

```bash
# program.md exists and is substantive
test -f program.md && wc -l program.md
# → program.md, 137 lines

# EDITABLE REGION gone
grep "EDITABLE REGION" src/strategies/active_strategy.py && echo "FAIL" || echo "MARKERS REMOVED"
# → MARKERS REMOVED

# Test files exist
test -f tests/unit/test_backtester_v2.py && echo "backtester_v2 tests EXIST"
test -f tests/unit/test_strategy_interface.py && echo "strategy_interface tests EXIST"
# → both EXIST

# Count test functions
grep -c "def test_" tests/unit/test_backtester_v2.py
# → 25
grep -c "def test_" tests/unit/test_strategy_interface.py
# → 17

# Run all
pytest tests/unit/ --tb=short -q
# → 79 passed
```

## 6) Implementation Update Space

### Completed Work

- Created `program.md` at repository root (137 lines) following Section 5 spec
- Removed both EDITABLE REGION markers from `active_strategy.py`
- Created `tests/unit/test_backtester_v2.py` with 25 tests (4 find_strategy_class + 11 calculate_metrics + 5 calculate_baseline_sharpe + 5 run_per_symbol_analysis + 2 output format)
- Created `tests/unit/test_strategy_interface.py` with 17 tests (5 dynamic loading + 10 strategy file + 2 free-form)
- Total new tests: 42, all passing
- Full suite: 79 passed, 0 failures

### Command Results

```
$ pytest tests/unit/ --tb=short -q
79 passed in 0.81s
```

### Blockers / Deviations

- None

### Follow-ups

- Phase 3: CLI simplification, Obsidian vault setup (#9)
- Phase 4: CLAUDE.md update (#10)
- Future session: Deflated Sharpe Ratio to replace P_VALUE placeholder (#12)
