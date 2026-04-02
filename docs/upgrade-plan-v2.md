# Quant-Autoresearch V2 升級設計（完整計畫）

> 日期：2026-04-01
> 基於 Karpathy autoresearch 對比研究的架構重設計
> 遷移方式：開 v2 branch，完整實現後再合併

---

## 設計決策總覽

| # | 項目 | 決定 |
|---|------|------|
| 1 | Agent Loop | 移除 Python 框架，program.md 驅動 Claude Code/Codex |
| 2 | 停止條件 | NEVER STOP + 時間參考（program.md 裡寫 session 時長） |
| 3 | 修改範圍 | `active_strategy.py` 全檔案可改 |
| 4 | 策略介面 | 完全自由，backtester 動態載入（掃描 generate_signals 方法） |
| 5 | 安全機制 | 保留 RestrictedPython 沙箱 + AST 安全檢查 |
| 6 | Backtester 指標 | 新增 Sortino, Profit Factor, Win Rate, 盈虧比, Calmar, Buy&Hold baseline, Per-Symbol 拆分 |
| 7 | 決策邏輯 | Sharpe 為主 + 硬性約束（p_value > 0.05 或 SCORE < BASELINE_SHARPE → 自動 discard） |
| 8 | Simplicity | 寫入 program.md，由 agent 自行判斷 |
| 9 | Git 追蹤 | 每實驗一 commit + reset on failure |
| 10 | Results 格式 | TSV 多指標（commit / sharpe / sortino / calmar / drawdown / max_dd_days / trades / win_rate / profit_factor / p_value / baseline_sharpe / status / description） |
| 11 | Playbook | 保留作可選工具，不再是 loop 的一部分 |
| 12 | Obsidian 記錄 | 新增：每次實驗生成 Obsidian 筆記，記錄假說、改動、結果、觀察 |
| 13 | 研究能力 | 保留作 skill，後續 session 專門討論 |
| 14 | 資料管道 | 後續 session 專門討論 |
| 15 | 過擬合防禦 | 後續 session 專門討論 |
| 16 | 測試 | 全面重寫 |
| 17 | CLI | 簡化為 setup_data, fetch, backtest |

---

## 1. 新架構總覽

```
┌──────────────────────────────────────────────────────┐
│                    program.md                         │
│  (人類編輯 — 研究策略指令、約束、實驗 loop)            │
└─────────────────────┬────────────────────────────────┘
                      │ Claude Code / Codex 讀取
                      ▼
┌──────────────────────────────────────────────────────┐
│              Claude Code / Codex                      │
│  (Agent 自主運行，無 Python 框架控制)                  │
│                                                       │
│  LOOP FOREVER:                                        │
│    1. 讀現況 + results.tsv 歷史                        │
│    2. 提出假說                                         │
│    3. 改 active_strategy.py                           │
│    4. git commit                                      │
│    5. 跑 backtester → parse 結果                       │
│    6. 檢查硬性約束（p_value, baseline）                 │
│    7. keep / reset                                    │
│    8. 記錄 results.tsv                                │
│    9. 寫 Obsidian 實驗筆記                             │
└────────┬──────────────────┬───────────────────────────┘
         │                  │
    修改  ▼                  ▼ 執行
┌──────────────┐   ┌──────────────────────────────────┐
│ active_      │   │  src/core/backtester.py           │
│ strategy.py  │   │  (固定 — agent 不可改)             │
│ (全檔案可改) │   │                                   │
│              │   │  • 動態載入策略 class               │
│              │   │  • RestrictedPython 沙箱           │
│              │   │  • AST 安全檢查                    │
│              │   │  • Walk-Forward 5 窗口             │
│              │   │  • Monte Carlo permutation         │
│              │   │  • 強制 1-bar lag                  │
│              │   │  • Volatility-adjusted slippage    │
│              │   │  • 多指標輸出                      │
│              │   │  • Per-Symbol 拆分                 │
│              │   │  • Buy&Hold baseline               │
└──────────────┘   └──────────────┬───────────────────┘
                                  │ 讀取
                      ┌───────────▼───────────┐
                      │     data/cache/        │
                      │     (Parquet files)    │
                      └────────────────────────┘

輸出檔案：
├── results.tsv              ← 所有實驗結果
├── experiments/notes/       ← Obsidian 實驗筆記
│   ├── 001-baseline.md
│   ├── 002-add-atr-filter.md
│   └── ...
└── run.log                  ← 最近一次回測 log
```

---

## 2. Backtester 完整輸出格式

### 2.1 輸出範例

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
  QQQ: sharpe=0.58 sortino=0.85 dd=-0.11 pf=1.80 trades=30 wr=0.53
  IWM: sharpe=0.43 sortino=0.68 dd=-0.15 pf=1.40 trades=25 wr=0.48
  BTC: sharpe=0.54 sortino=0.81 dd=-0.18 pf=1.60 trades=30 wr=0.60
```

### 2.2 指標定義

| 指標 | 計算方式 | 意義 |
|------|----------|------|
| **SCORE** | (mean/stdev) * sqrt(252) | 年化 Sharpe Ratio（主決策指標） |
| **SORTINO** | (mean/downside_stdev) * sqrt(252) | 只懲罰下行波動 |
| **CALMAR** | annualized_return / abs(max_drawdown) | 收益 vs 最大回撤 |
| **DRAWDOWN** | max peak-to-trough decline | 最大回撤幅度 |
| **MAX_DD_DAYS** | longest drawdown duration in days | 最大回撤持續天數 |
| **TRADES** | sum of abs(signal.diff()) | 總交易次數 |
| **P_VALUE** | Monte Carlo 1000 permutations | 策略是否統計顯著 |
| **WIN_RATE** | winning_trades / total_trades | 勝率 |
| **PROFIT_FACTOR** | gross_profit / gross_loss | 盈虧比（>1.5 穩定，>2.0 優秀） |
| **AVG_WIN** | mean of positive trade returns | 平均盈利 |
| **AVG_LOSS** | mean of negative trade returns | 平均虧損 |
| **BASELINE_SHARPE** | Buy&Hold 的 Sharpe | 簡單持有基準 |

### 2.3 硬性約束（Hard Constraints）

```
if P_VALUE > 0.05:
    → 自動 DISCARD（策略不顯著）
if SCORE < BASELINE_SHARPE:
    → 自動 DISCARD（打不過 Buy&Hold）
```

這兩個約束在 program.md 裡明確寫出，agent 必須遵守。

---

## 3. results.tsv 格式

```tsv
commit	sharpe	sortino	calmar	drawdown	max_dd_days	trades	win_rate	profit_factor	p_value	baseline_sharpe	status	description
a1b2c3d	0.5432	0.8100	1.2300	-0.1200	45	120	0.5500	1.8500	0.0300	0.4500	keep	baseline EMA crossover
b2c3d4e	0.6100	0.9200	1.4500	-0.1000	38	98	0.5800	2.1000	0.0150	0.4500	keep	add ATR regime filter
c3d4e5f	0.4800	0.6800	0.9500	-0.1500	62	45	0.4200	1.2000	0.1200	0.4500	discard	try Bollinger Band mean reversion
e5f6g7h	0.0000	0.0000	0.0000	0.0000	0	0	0.0000	0.0000	1.0000	0.0000	crash	division by zero in volatility calc
f6g7h8i	0.6500	0.9800	1.5600	-0.0900	32	110	0.6000	2.3000	0.0080	0.4500	keep	combine momentum + regime filter
```

---

## 4. Obsidian 實驗筆記

每次實驗生成一個 Markdown 筆記，存入 `experiments/notes/`。

### 4.1 筆記格式

```markdown
---
id: 003
commit: f6g7h8i
date: 2026-04-01T14:30:00
status: keep
tags: [momentum, regime-filter, combination]
---

# Experiment 003: Combine momentum + regime filter

## Hypothesis
Combining the ROC momentum signal with the ATR regime filter should reduce
false signals during high-volatility periods while maintaining trend capture.

## Changes
- Modified signal logic in `generate_signals()`:
  - Added ROC(14) as primary momentum indicator
  - Used ATR EMA regime filter as gate
  - Only go long/short when regime is low-vol AND momentum confirms

## Results
| Metric | Value | vs Baseline |
|--------|-------|-------------|
| Sharpe | 0.6500 | +0.1068 |
| Sortino | 0.9800 | +0.1700 |
| Profit Factor | 2.3000 | +0.4500 |
| Win Rate | 60% | +5% |
| P-Value | 0.008 | Significant |

## Per-Symbol
- SPY: 0.62 (strong in low-vol regime)
- QQQ: 0.58 (good trend capture)
- IWM: 0.43 (weaker, needs investigation)
- BTC: 0.54 (decent, crypto regime detection works)

## Observations
- IWM underperforms — likely because small-cap regime behavior differs
- Consider symbol-specific regime thresholds in next experiment
- Profit Factor improvement suggests the filter is cutting bad trades effectively

## Next Ideas
- [ ] Try symbol-specific ATR thresholds
- [ ] Add a momentum acceleration indicator
- [ ] Test with longer lookback (20 → 30)
```

### 4.2 目錄結構

```
experiments/
├── notes/                    ← Obsidian vault 指向這裡
│   ├── 001-baseline.md
│   ├── 002-add-atr-filter.md
│   └── 003-combine-momentum-regime.md
├── results/
│   └── results.tsv
└── logs/
    └── run.log
```

用戶可以用 Obsidian 開啟 `experiments/` 作為 vault，即可瀏覽所有實驗筆記。

---

## 5. program.md 完整設計

```markdown
# Quant Autoresearch

Autonomous quantitative strategy discovery.

## Setup

To set up a new experiment:
1. **Agree on a run tag** with the user (e.g. `apr1`).
   The branch `quant-research/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b quant-research/<tag>` from main.
3. **Read the in-scope files**:
   - `src/core/backtester.py` — fixed evaluation harness. Do NOT modify.
   - `src/strategies/active_strategy.py` — the file you modify.
4. **Verify data exists**: Check `data/cache/` has Parquet files.
   If not, tell the human to run `uv run python cli.py setup_data`.
5. **Initialize files**:
   - Create `results.tsv` with header row.
   - Create `experiments/notes/` directory.
6. **Run baseline** — always run the unmodified strategy first.
7. **Confirm and go**.

## Experimentation

Each experiment:
```bash
uv run python src/core/backtester.py > run.log 2>&1
```

**What you CAN do:**
- Modify `src/strategies/active_strategy.py` — the ENTIRE file is fair game.
  Change class names, add methods, change hyperparameters, redesign signal logic.
  The only requirement: the file must define at least one class with a
  `generate_signals(self, data)` method that returns a Series of signals.

**What you CANNOT do:**
- Modify `src/core/backtester.py`. It is read-only.
- Install new packages. The sandbox only provides `pd` and `np`.
- Use `for` loops. Vectorized Pandas/NumPy only.
- Use `.shift(-N)` (look-ahead bias).

## The goal

Get the highest **SCORE** (Average Walk-Forward OOS Sharpe Ratio).

## Output format

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

Extract:
```bash
grep "^SCORE:\|^DRAWDOWN:\|^P-VALUE:\|^BASELINE_SHARPE:\|^PROFIT_FACTOR:" run.log
```

## Decision rules

**KEEP if:**
- SCORE > previous best AND
- P_VALUE <= 0.05 AND
- SCORE > BASELINE_SHARPE

**DISCARD if:**
- SCORE <= previous best OR
- P_VALUE > 0.05 (not statistically significant) OR
- SCORE <= BASELINE_SHARPE (can't beat Buy&Hold)

**Simplicity criterion**:
All else being equal, simpler is better.
- Removing code and getting equal or better results → great outcome.
- A 0.01 Sharpe improvement that adds 20 lines of hacky complexity → probably not worth it.
- A 0.01 Sharpe improvement from deleting code → definitely keep.

## Logging results

Log to `results.tsv` (tab-separated, do NOT commit):
```
commit  sharpe  sortino  calmar  drawdown  max_dd_days  trades  win_rate  profit_factor  p_value  baseline_sharpe  status  description
```

## Obsidian experiment notes

After each experiment, write a note to `experiments/notes/<NNN>-<slug>.md`:
- **Hypothesis**: what are you testing and why
- **Changes**: what did you modify
- **Results**: key metrics in a table
- **Per-Symbol**: individual symbol performance
- **Observations**: what did you learn
- **Next Ideas**: what to try next

These notes let the human understand your reasoning when they review the session.

## The experiment loop

LOOP FOREVER:
1. Check git state: current branch/commit
2. Read `results.tsv` for history
3. Propose hypothesis → modify `src/strategies/active_strategy.py`
4. `git add src/strategies/active_strategy.py && git commit -m "<description>"`
5. `uv run python src/core/backtester.py > run.log 2>&1`
6. `grep "^SCORE:\|^P-VALUE:\|^BASELINE_SHARPE:" run.log`
7. If grep empty → crash. `tail -n 50 run.log`. Fix or skip.
8. Check hard constraints (p_value, baseline_sharpe)
9. Record in results.tsv
10. Write Obsidian note
11. If KEEP → keep commit, advance branch
12. If DISCARD → `git reset --hard HEAD~1`
13. Repeat

**NEVER STOP.** Do NOT ask the human if you should continue.
They might be asleep. Run indefinitely until manually stopped.

**Time awareness**: This session has approximately X hours.
Pace yourself for meaningful experiments, not random changes.

**Stuck?**
- Re-read strategy code for new angles
- Read results.tsv for patterns
- Try combining previous near-misses
- Try more radical architectural changes
- Review your Obsidian notes for forgotten ideas
```

---

## 6. 檔案變動清單

### 新增

```
program.md                           ← 根目錄 program.md（研究指令）
experiments/notes/                    ← Obsidian 實驗筆記目錄
```

### 修改

```
src/core/backtester.py               ← 大改：動態載入 + 多指標 + Per-Symbol + Buy&Hold
src/strategies/active_strategy.py    ← 小改：移除 EDITABLE REGION 標記
cli.py                               ← 簡化：移除 run/status/report/test/research
```

### 移除

```
src/core/engine.py                   ← 整個 6-Phase loop
src/context/compactor.py             ← Context compaction
src/context/composer.py              ← Prompt composition
src/context/__init__.py
src/safety/guard.py                  ← Prompt guardrails, schema gating
src/tools/registry.py                ← Tool registry
src/tools/bm25_search.py             ← 合併到 research skill（後續討論）
src/models/router.py                 ← LLM 路由
src/utils/token_counter.py           ← Token counting
src/prompts/identity.md              ← 併入 program.md
src/prompts/safety_policy.md         ← 安全由 backtester 處理
src/prompts/tool_guidance.md         ← 併入 program.md
src/prompts/quant_rules.md           ← 併入 program.md
src/prompts/git_rules.md             ← 併入 program.md
```

### 保留（不動或小改）

```
src/data/connector.py                ← 不動
src/data/preprocessor.py             ← 不動
src/core/research.py                 ← 保留，後續作 skill
src/memory/playbook.py               ← 保留作可選工具
src/utils/logger.py                  ← 不動
src/utils/telemetry.py               ← 不動
src/utils/iteration_tracker.py       ← 不動
src/utils/retries.py                 ← 不動
```

---

## 7. backtester.py 具體改動

### 7.1 動態載入策略

```python
def find_strategy_class(sandbox_locals: dict):
    """動態掃描 sandbox 載入的策略 class"""
    for name, obj in sandbox_locals.items():
        if isinstance(obj, type) and hasattr(obj, 'generate_signals'):
            return obj
    return None
```

### 7.2 新增指標計算

```python
def calculate_metrics(combined_returns: pd.Series, trades: pd.Series):
    """計算完整的回測指標"""
    mean = combined_returns.mean()
    std = combined_returns.std()
    downside_std = combined_returns[combined_returns < 0].std()

    sharpe = (mean / std) * np.sqrt(252) if std > 0 else 0.0
    sortino = (mean / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0

    # Cumulative returns for drawdown
    cum = (1 + combined_returns).cumprod()
    running_max = cum.cummax()
    drawdown = ((cum - running_max) / running_max).min()

    # Max drawdown duration
    is_dd = cum < running_max
    dd_groups = (is_dd != is_dd.shift()).cumsum()
    max_dd_days = is_dd.groupby(dd_groups).sum().max() if is_dd.any() else 0

    # Annualized return
    total_days = len(combined_returns)
    annualized_return = (1 + combined_returns).prod() ** (252 / total_days) - 1
    calmar = annualized_return / abs(drawdown) if drawdown != 0 else 0.0

    # Trade-level metrics
    winning = trades[trades > 0]
    losing = trades[trades < 0]
    gross_profit = winning.sum() if len(winning) > 0 else 0.0
    gross_loss = abs(losing.sum()) if len(losing) > 0 else 1e-10
    profit_factor = gross_profit / gross_loss
    win_rate = len(winning) / len(trades) if len(trades) > 0 else 0.0
    avg_win = winning.mean() if len(winning) > 0 else 0.0
    avg_loss = losing.mean() if len(losing) > 0 else 0.0

    return {
        'sharpe': sharpe,
        'sortino': sortino,
        'calmar': calmar,
        'drawdown': drawdown,
        'max_dd_days': int(max_dd_days),
        'trades': len(trades),
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
    }
```

### 7.3 Buy&Hold Baseline

```python
def calculate_baseline_sharpe(data: dict):
    """計算 Buy&Hold 基準 Sharpe"""
    baseline_returns = []
    for symbol, df in data.items():
        baseline_returns.append(df['returns'])
    combined = pd.concat(baseline_returns, axis=1).mean(axis=1)
    std = combined.std()
    return (combined.mean() / std) * np.sqrt(252) if std > 0 else 0.0
```

### 7.4 Per-Symbol 輸出

```python
def run_per_symbol_analysis(strategy_instance, data, start_idx, end_idx):
    """Per-symbol 獨立分析"""
    results = {}
    for symbol, df in data.items():
        history_df = df.iloc[:end_idx].copy()
        signals = strategy_instance.generate_signals(history_df)
        if not isinstance(signals, pd.Series):
            signals = pd.Series(signals, index=history_df.index)
        signals = signals.fillna(0).shift(1).fillna(0).iloc[start_idx:end_idx]

        test_returns = df.iloc[start_idx:end_idx]['returns']
        daily_returns = test_returns * signals

        std = daily_returns.std()
        sharpe = (daily_returns.mean() / std) * np.sqrt(252) if std > 0 else 0.0
        downside_std = daily_returns[daily_returns < 0].std()
        sortino = (daily_returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0

        cum = (1 + daily_returns).cumprod()
        dd = ((cum - cum.cummax()) / cum.cummax()).min()

        trades = signals.diff().abs()
        winning = daily_returns[daily_returns > 0]
        losing = daily_returns[daily_returns < 0]
        pf = winning.sum() / abs(losing.sum()) if len(losing) > 0 and losing.sum() != 0 else 0.0
        wr = len(winning) / len(daily_returns[daily_returns != 0]) if len(daily_returns[daily_returns != 0]) > 0 else 0.0

        results[symbol] = {
            'sharpe': round(sharpe, 2),
            'sortino': round(sortino, 2),
            'dd': round(dd, 2),
            'pf': round(pf, 2),
            'trades': int(trades.sum()),
            'wr': round(wr, 2),
        }
    return results
```

---

## 8. 測試計畫（全面重寫）

### 測試結構

```
tests/
├── conftest.py                    ← 共用 fixtures
├── test_backtester.py             ← backtester 核心測試
│   ├── test_dynamic_class_loading
│   ├── test_restricted_python_sandbox
│   ├── test_ast_security_check
│   ├── test_shift_negative_blocked
│   ├── test_forbidden_builtins_blocked
│   ├── test_forbidden_imports_blocked
│   ├── test_walk_forward_validation
│   ├── test_monte_carlo_permutation
│   ├── test_metrics_calculation
│   ├── test_sortino_calculation
│   ├── test_calmar_calculation
│   ├── test_profit_factor
│   ├── test_win_rate
│   ├── test_baseline_sharpe
│   ├── test_per_symbol_analysis
│   └── test_output_format
├── test_strategy_interface.py     ← 策略介面測試
│   ├── test_free_form_class_accepted
│   ├── test_custom_class_name
│   ├── test_multiple_methods_allowed
│   └── test_no_generate_signals_rejected
├── test_data_connector.py         ← 資料載入測試
│   ├── test_parquet_loading
│   ├── test_cache_directory
│   └── test_missing_data_handling
├── test_cli.py                    ← CLI 測試
│   ├── test_setup_data_command
│   ├── test_fetch_command
│   └── test_backtest_command
└── test_integration.py            ← 整合測試
    ├── test_full_backtest_pipeline
    └── test_crash_recovery
```

---

## 9. 實作順序

### Phase 1：基礎建設（backtester + program.md）

1. 開 `v2` branch：`git checkout -b v2`
2. 修改 `src/core/backtester.py`：
   - 加入 `find_strategy_class()` 動態載入
   - 加入 `calculate_metrics()` 多指標
   - 加入 `calculate_baseline_sharpe()` Buy&Hold baseline
   - 加入 `run_per_symbol_analysis()` Per-Symbol 拆分
   - 更新輸出格式
3. 撰寫 `program.md`（根目錄）
4. 移除 `active_strategy.py` 的 EDITABLE REGION 標記
5. 寫測試：`test_backtester.py`, `test_strategy_interface.py`
6. 確認所有測試通過

### Phase 2：清理

7. 移除 `src/core/engine.py`
8. 移除 `src/context/` 目錄
9. 移除 `src/safety/guard.py`
10. 移除 `src/tools/registry.py`, `src/tools/bm25_search.py`
11. 移除 `src/models/router.py`
12. 移除 `src/utils/token_counter.py`
13. 清理 `src/prompts/`（移除 identity.md, safety_policy.md, tool_guidance.md, quant_rules.md, git_rules.md）
14. 移除相關測試
15. 更新 `pyproject.toml`（移除不需要的依賴如 groq, tiktoken）

### Phase 3：CLI + Obsidian

16. 簡化 `cli.py`
17. 建立 `experiments/notes/` 目錄結構
18. 更新 `program.md` 加入 Obsidian 筆記指令
19. 寫 `test_cli.py`

### Phase 4：收尾

20. 保留 Playbook 作為可選工具（不動）
21. 更新 `CLAUDE.md` 反映 V2 架構
22. 更新 `.gitignore` 加入 `results.tsv`, `run.log`
23. 清理 `docs/` 下的舊文件
24. Full test run 確認一切正常

---

## 10. 後續 Session 計畫

| Session | 主題 | 狀態 |
|---------|------|------|
| 1 | 架構設計（本文件） | 完成 |
| 2 | 資料管道設計 | 待討論 |
| 3 | 過擬合防禦設計 | 待討論 |
| 4 | 研究能力設計（Obsidian sources + skills） | 待討論 |
| 5 | V2 實作 | 待開始 |
