# Quant-Autoresearch V2 過擬合防禦設計

> 日期：2026-04-01
> 基於 López de Prado、Bailey 等學術研究的防禦架構
> Session 3 專題設計

---

## 設計決策總覽

| # | 項目 | 決定 |
|---|------|------|
| 1 | Sharpe 計算 | Newey-West 完全替代原始 Sharpe（修正分鐘級序列相關） |
| 2 | 多重測試修正 | Deflated Sharpe Ratio 作為輸出指標（參考用） |
| 3 | Walk-Forward | 保留 5 窗口作快速篩選 |
| 4 | CPCV | 作為最終驗證步驟（agent 按需調用 CLI） |
| 5 | Monte Carlo | 移除，用 Deflated SR 替代 |
| 6 | Regime 檢查 | CLI 命令，agent 按需調用 |
| 7 | 參數穩定性 | CLI 命令，agent 按需調用 |
| 8 | Obsidian 整合 | Agent 在 loop 中可參考過擬合防禦研究筆記 |

---

## 1. 防禦架構總覽

```
┌─────────────────────────────────────────────────────────┐
│                  防禦層級                                │
│                                                         │
│  Layer 1: 內建防禦（每次回測自動執行）                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │ • Newey-West Sharpe（替代原始 Sharpe）           │    │
│  │ • Deflated Sharpe Ratio（輸出參考）              │    │
│  │ • Walk-Forward 5 窗口                            │    │
│  │ • 強制 1-bar lag                                 │    │
│  │ • Volatility-adjusted slippage                   │    │
│  │ • SCORE < BASELINE_SHARPE → 自動 DISCARD        │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
│                    策略通過快速篩選？                      │
│                          │ Yes                           │
│                          ▼                               │
│  Layer 2: 進階驗證（Agent 按需調用 CLI）                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ • CPCV 組合交叉驗證（最終驗證）                   │    │
│  │ • Regime 穩健性檢查                              │    │
│  │ • 參數穩定性測試                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
│  Layer 3: 指導（program.md + Obsidian）                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ • Simplicity criterion（簡單優先）               │    │
│  │ • 過擬合防禦研究筆記（Obsidian 參考）             │    │
│  │ • Agent 自主判斷何時使用進階工具                  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: 內建防禦

### 2.1 Newey-West 調整 Sharpe Ratio

**為什麼需要：** 分鐘級收益有強烈的序列相關性（bid-ask bounce 造成負自相關，非同步交易造成正自相關）。傳統 Sharpe 用 `mean / std * sqrt(252*390)` 年化，任何標準差偏差都會被放大 314 倍。

**實作：**

```python
def newey_west_sharpe(returns: pd.Series, max_lag: int = None) -> float:
    """
    計算 Newey-West 調整後的年化 Sharpe Ratio。

    修正分鐘級收益的序列相關性對標準差估計的偏差。

    Args:
        returns: 策略淨收益 Series（分鐘級）
        max_lag: 最大滯後階數。默認用 T^(1/3) 法則

    Returns:
        float: Newey-West 調整後的年化 Sharpe Ratio
    """
    T = len(returns)
    if T < 2 or returns.std() == 0:
        return 0.0

    # 法則：L = floor(T^(1/3))
    if max_lag is None:
        max_lag = int(T ** (1/3))

    mu = returns.mean()

    # 計算自協方差
    gamma_0 = returns.var()
    nw_var = gamma_0

    for j in range(1, max_lag + 1):
        gamma_j = returns.cov(returns.shift(j))
        # Bartlett 權重
        weight = 1 - j / (max_lag + 1)
        nw_var += 2 * weight * gamma_j

    nw_var = max(nw_var, 1e-10)  # 防止負方差

    # 年化：分鐘級 → 252 天 × 390 bars/day
    annualization = np.sqrt(252 * 390)
    return (mu / np.sqrt(nw_var)) * annualization
```

**輸出格式變更：**

```
---
SCORE: 0.4521          ← Newey-West Sharpe（替代原始）
NAIVE_SHARPE: 0.6832   ← 原始 Sharpe（僅參考，顯示偏差程度）
DEFLATED_SR: 0.92      ← Deflated Sharpe Ratio
SORTINO: 0.8100
CALMAR: 1.2300
DRAWDOWN: -0.1200
MAX_DD_DAYS: 45
TRADES: 120
WIN_RATE: 0.5500
PROFIT_FACTOR: 1.8500
AVG_WIN: 0.0120
AVG_LOSS: -0.0080
BASELINE_SHARPE: 0.4500
NW_SHARPE_BIAS: 0.2311  ← NAIVE - NW（偏差量，越大表示序列相關越嚴重）
---
```

### 2.2 Deflated Sharpe Ratio

**為什麼需要：** Agent 在 loop 中測試了 N 個策略後，最好的那個可能只是運氣。DSR 考慮了測試次數和非正態性。

**實作：**

```python
from scipy.stats import norm

def deflated_sharpe_ratio(returns: pd.Series, n_trials: int,
                          skew: float = None, kurtosis: float = None) -> float:
    """
    計算 Deflated Sharpe Ratio。

    考慮三個偏差：
    1. 收益非正態性（偏度和峰度）
    2. 追蹤記錄長度
    3. 測試次數（多重比較）

    Args:
        returns: 策略淨收益 Series
        n_trials: 已進行的策略測試次數（從 results.tsv 讀取）
        skew: 收益偏度（None 則自動計算）
        kurtosis: 收益峰度（None 則自動計算）

    Returns:
        float: DSR 值（0-1，>0.95 表示顯著）
    """
    T = len(returns)
    sr = (returns.mean() / returns.std()) * np.sqrt(252 * 390) if returns.std() > 0 else 0

    if skew is None:
        skew = returns.skew()
    if kurtosis is None:
        kurtosis = returns.kurtosis()

    # PSR (Probabilistic Sharpe Ratio) 的標準誤
    # SE[SR] = sqrt((1 - skew*SR + (kurtosis-1)/4 * SR^2) / (T-1))
    se_sr = np.sqrt((1 - skew * sr + (kurtosis - 1) / 4 * sr**2) / max(T - 1, 1))

    # 期望最大 Sharpe（在 n_trials 次測試後）
    # SR* = E[max(SR_1,...,SR_n) | all SR_i = 0]
    # 使用 Gumbel 分佈近似
    if n_trials > 1:
        euler_gamma = 0.5772
        z = norm.ppf(1 - 1 / n_trials)
        sr_star = (1 - euler_gamma) * norm.ppf(1 - 1 / n_trials) + \
                  euler_gamma * norm.ppf(1 - 1 / (n_trials * np.e))
        # 用 SR* 調整後的標準
        sr_star_adjusted = sr_star * se_sr
    else:
        sr_star_adjusted = 0

    # DSR = P(SR > SR*)
    dsr = norm.cdf((sr - sr_star_adjusted) / se_sr) if se_sr > 0 else 0.5

    return dsr
```

**整合方式：**
- `n_trials` 從 `results.tsv` 計算（已執行的實驗數量）
- 輸出為參考指標，不做硬性約束
- Agent 在 program.md 裡被告知：DSR < 0.95 時要謹慎

### 2.3 硬性約束（保留 + 調整）

```
# Layer 1 硬性約束（在 backtester 內自動執行）

if SCORE < BASELINE_SHARPE:
    → 自動 DISCARD（打不過 Buy&Hold）

# 注意：Monte Carlo P_VALUE 已移除
# 由 Deflated SR 提供多重測試保護（參考用，非強制）
```

### 2.4 保留的防禦

| 防禦 | 說明 |
|------|------|
| Walk-Forward 5 窗口 | 保留，作快速篩選 |
| 強制 1-bar lag | 保留，shift(1) |
| Volatility-adjusted slippage | 保留，BASE_COST=0.0005 + vol*0.1 |
| AST 安全檢查 | 保留，禁止 shift(-N) |
| RestrictedPython 沙箱 | 保留 |

---

## 3. Layer 2: 進階驗證（CLI 命令）

### 3.1 CPCV 組合交叉驗證

**用途：** 替代/補充 Walk-Forward 的最終驗證。比 Walk-Forward 更嚴格——用組合交叉驗證產生 Sharpe Ratio 分佈，而非單一數字。

**CLI 命令：**

```bash
# 跑 CPCV 驗證（最終確認步驟）
uv run python cli.py validate --method cpcv --groups 8 --test-groups 2
```

**實作邏輯：**

```python
def run_cpcv(strategy_class, data_config, n_groups=8, n_test=2):
    """
    Combinatorial Purged Cross-Validation

    1. 將時間軸分為 N 個連續組
    2. 對所有 C(N,k) 組合：
       - k 個組作為測試集
       - N-k 個組作為訓練集
       - 在邊界處 purge + embargo
    3. 計算每條路徑的 Sharpe
    4. 返回 Sharpe 分佈

    C(8,2) = 28 條路徑
    C(6,1) = 6 條路徑（更快）
    """
    from itertools import combinations

    groups = split_into_groups(data_config, n_groups)

    oos_sharpes = []
    for test_idx in combinations(range(n_groups), n_test):
        train_idx = [i for i in range(n_groups) if i not in test_idx]

        # Purging: 移除訓練集尾部可能洩漏的樣本
        # Embargo: 測試集前加 buffer
        train_data = get_purged_data(groups, train_idx, test_idx, purge_bars=390)
        test_data = get_embargoed_data(groups, test_idx, embargo_bars=0)

        # 載入分鐘數據 + 跑策略
        strategy = strategy_class()
        signals = strategy.generate_signals(train_data)
        oos_sharpe = evaluate_oos(strategy, test_data)
        oos_sharpes.append(oos_sharpe)

    return {
        'sharpe_distribution': oos_sharpes,
        'mean_sharpe': np.mean(oos_sharpes),
        'std_sharpe': np.std(oos_sharpes),
        'pct_positive': np.mean([s > 0 for s in oos_sharpes]),
        'worst_sharpe': np.min(oos_sharpes),
        'best_sharpe': np.max(oos_sharpes),
    }
```

**輸出範例：**

```
CPCV Validation (8 groups, 2 test)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paths tested:    28
Mean OOS Sharpe: 0.42
Std OOS Sharpe:  0.15
% Positive:      82.1%
Worst path:      -0.08
Best path:       0.71
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verdict: MODERATE — Positive in most paths but variance is high.
Consider regime-specific analysis.
```

**Agent 使用指引（寫在 program.md）：**

```markdown
## CPCV Validation

After achieving a SCORE improvement of >0.05 over baseline, run:
\`\`\`bash
uv run python cli.py validate --method cpcv --groups 8 --test-groups 2
\`\`\`

Interpretation:
- % Positive > 80% → Strong signal, likely genuine
- % Positive 60-80% → Moderate, check regime analysis
- % Positive < 60% → Weak, probably overfit
```

### 3.2 Regime 穩健性檢查

**用途：** 檢查策略在不同市場環境下的表現，避免只在特定環境賺錢。

**CLI 命令：**

```bash
uv run python cli.py validate --method regime
```

**實作邏輯：**

```python
def regime_analysis(strategy_returns: pd.Series, market_data: pd.DataFrame):
    """
    基於簡單規則的 Regime 分類 + 分段績效分析。

    Regime 定義：
    - Bull Quiet:  20d return > 0, 20d vol < median
    - Bull Vol:    20d return > 0, 20d vol >= median
    - Bear Quiet:  20d return <= 0, 20d vol < median
    - Bear Vol:    20d return <= 0, 20d vol >= median
    """
    # 用日線數據判定 regime
    rolling_ret = market_data['close'].pct_change(20)
    rolling_vol = market_data['returns'].rolling(20).std()
    vol_median = rolling_vol.median()

    regimes = pd.Series(index=market_data.index, dtype=str)
    regimes[(rolling_ret > 0) & (rolling_vol < vol_median)] = 'bull_quiet'
    regimes[(rolling_ret > 0) & (rolling_vol >= vol_median)] = 'bull_volatile'
    regimes[(rolling_ret <= 0) & (rolling_vol < vol_median)] = 'bear_quiet'
    regimes[(rolling_ret <= 0) & (rolling_vol >= vol_median)] = 'bear_volatile'

    # 分段計算績效
    results = {}
    for regime in regimes.unique():
        mask = regimes == regime
        regime_returns = strategy_returns[mask]
        if len(regime_returns) > 0:
            results[regime] = {
                'sharpe': newey_west_sharpe(regime_returns),
                'return': regime_returns.sum(),
                'count': len(regime_returns),
                'win_rate': (regime_returns > 0).mean(),
            }

    return results
```

**輸出範例：**

```
Regime Robustness Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Regime          Sharpe   Return   Bars    Win%
──────────────────────────────────────────
bull_quiet       0.82   +12.3%   45000   54%
bull_volatile    0.31    +3.1%   28000   51%
bear_quiet      -0.12    -1.8%   22000   48%
bear_volatile   -0.45    -5.2%   15000   45%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verdict: CONCENTRATED — 85% of profits from bull regimes.
Bear performance is negative. Consider adding defensive logic.
```

### 3.3 參數穩定性測試

**用途：** 檢測策略是否依賴特定參數值。參數微調 ±20% 後如果策略崩潰，說明是過擬合。

**CLI 命令：**

```bash
uv run python cli.py validate --method stability --perturbation 0.2 --steps 5
```

**實作邏輯：**

```python
def parameter_stability_test(strategy_class, data_config,
                              perturbation: float = 0.2, steps: int = 5):
    """
    參數穩定性測試。

    1. 識別策略的 tuneable 參數（__init__ 的數值參數）
    2. 對每個參數 ±perturbation 範圍內取 steps 個值
    3. 跑回測，計算 Sharpe
    4. 計算穩定性分數（>50% peak Sharpe 的比例）
    """
    # 從策略 class 的 __init__ 提取參數
    import inspect
    sig = inspect.signature(strategy_class.__init__)
    params = {}
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        if isinstance(param.default, (int, float)):
            params[name] = param.default

    stability_scores = {}
    for param_name, default_val in params.items():
        sharpes = []
        for delta in np.linspace(-perturbation, perturbation, steps):
            test_val = default_val * (1 + delta)
            # 創建帶 perturbed 參數的策略實例
            kwargs = {param_name: test_val}
            strategy = strategy_class(**kwargs)
            # 跑回測
            sharpe = run_full_backtest(strategy, data_config)
            sharpes.append(sharpe)

        peak = max(sharpes)
        threshold = peak * 0.5
        above_threshold = sum(1 for s in sharpes if s > threshold)
        stability_scores[param_name] = {
            'stability': above_threshold / len(sharpes),
            'peak_sharpe': peak,
            'min_sharpe': min(sharpes),
            'sharpes': sharpes,
        }

    overall_stability = np.mean([s['stability'] for s in stability_scores.values()])

    return {
        'overall_stability': overall_stability,
        'parameters': stability_scores,
    }
```

**輸出範例：**

```
Parameter Stability Test (±20% perturbation, 5 steps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Parameter         Stability   Peak    Min    Range
─────────────────────────────────────────────────
lookback          0.80        0.52    0.31   0.21
threshold         0.60        0.48    0.12   0.36
smoothing         1.00        0.51    0.45   0.06
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall Stability: 0.80 (GOOD)
Warning: 'threshold' has low stability (0.60).
The strategy is sensitive to this parameter.
```

---

## 4. program.md 過擬合防禦指引

```markdown
## Overfitting Defense

The backtester automatically applies:
- **Newey-West Sharpe** (corrected for minute-bar serial correlation)
- **Walk-Forward 5 windows** (quick screening)
- **Deflated Sharpe Ratio** (adjusts for number of tests run)

### SCORE interpretation
- SCORE is Newey-West adjusted. It is usually LOWER than naive Sharpe.
- NW_SHARPE_BIAS shows the adjustment magnitude.
- A large bias (>0.1) means serial correlation is significant.

### When to use advanced validation

1. **After improving SCORE by >0.05 over previous best:**
   ```bash
   uv run python cli.py validate --method cpcv --groups 8 --test-groups 2
   ```
   If % Positive < 60%, the improvement may be overfit.

2. **After making parameter changes:**
   ```bash
   uv run python cli.py validate --method stability --perturbation 0.2
   ```
   If stability < 0.6, the strategy is tuned to noise.

3. **Periodically (every 5-10 experiments):**
   ```bash
   uv run python cli.py validate --method regime
   ```
   Check that profits aren't concentrated in one market environment.

### Red flags
- NW_SHARPE_BIAS > 0.3 → Strategy may be exploiting serial correlation, not alpha
- DEFLATED_SR < 0.5 → Not significant after accounting for multiple tests
- CPCV % Positive < 50% → Strategy is likely overfit
- Any parameter stability < 0.5 → Sharp optimum, likely data mining
```

---

## 5. Backtester 輸出格式更新

### 5.1 每次回測的輸出

```
---
SCORE: 0.4521
NAIVE_SHARPE: 0.6832
DEFLATED_SR: 0.9200
SORTINO: 0.8100
CALMAR: 1.2300
DRAWDOWN: -0.1200
MAX_DD_DAYS: 45
TRADES: 120
WIN_RATE: 0.5500
PROFIT_FACTOR: 1.8500
AVG_WIN: 0.0120
AVG_LOSS: -0.0080
BASELINE_SHARPE: 0.4500
NW_SHARPE_BIAS: 0.2311
---
PER_SYMBOL:
  SPY: sharpe=0.52 sortino=0.80 dd=-0.10 pf=2.10 trades=35 wr=0.57
  QQQ: sharpe=0.48 sortino=0.75 dd=-0.11 pf=1.80 trades=30 wr=0.53
  ...
```

### 5.2 results.tsv 格式更新

```tsv
commit	score	naive_sharpe	deflated_sr	sortino	calmar	drawdown	max_dd_days	trades	win_rate	profit_factor	baseline_sharpe	nw_bias	status	description
a1b2c3d	0.4521	0.6832	0.9200	0.8100	1.2300	-0.1200	45	120	0.5500	1.8500	0.4500	0.2311	keep	baseline momentum strategy
```

### 5.3 硬性約束（Layer 1）

```python
# 內建約束（backtester 自動執行）
if SCORE < BASELINE_SHARPE:
    → DISCARD（打不過 Buy&Hold）

# 參考約束（agent 自行判斷）
# if DEFLATED_SR < 0.5:
#     → 策略可能不顯著，謹慎
# if NW_SHARPE_BIAS > 0.3:
#     → 序列相關偏差大，需要調查
```

---

## 6. 檔案變動清單

### 修改

```
src/core/backtester.py       ← 大改：
                                 • Newey-West Sharpe 替代原始 Sharpe
                                 • 新增 Deflated Sharpe Ratio 計算
                                 • 移除 Monte Carlo permutation test
                                 • 輸出新增 NAIVE_SHARPE, DEFLATED_SR, NW_SHARPE_BIAS
                                 • results.tsv 格式更新

program.md                   ← 新增過擬合防禦指引段落

results.tsv                  ← 新增 naive_sharpe, deflated_sr, nw_bias 欄位
```

### 新增

```
src/validation/__init__.py           ← 驗證模組
src/validation/cpcv.py               ← CPCV 組合交叉驗證
src/validation/regime.py             ← Regime 穩健性分析
src/validation/stability.py          ← 參數穩定性測試
src/validation/newey_west.py         ← Newey-West Sharpe 計算
src/validation/deflated_sr.py        ← Deflated Sharpe Ratio 計算
```

### CLI 命令

```
cli.py validate --method cpcv         ← CPCV 驗證
cli.py validate --method regime       ← Regime 分析
cli.py validate --method stability    ← 參數穩定性
```

---

## 7. 效能影響

| 項目 | 計算成本 | 影響 |
|------|----------|------|
| Newey-West Sharpe | O(T × L)，T=100K, L=46 | 可忽略（<1 秒） |
| Deflated SR | O(1) | 可忽略 |
| Walk-Forward 5 窗口 | 與 V1 相同 | 不變 |
| ~~Monte Carlo 1000~~ | ~~O(T × 1000)~~ | **移除**（省 ~30 秒） |
| CPCV (C(8,2)=28 路徑) | 28 × 單次回測 | ~2-5 分鐘（按需） |
| Regime 分析 | O(T) | <5 秒（按需） |
| 參數穩定性 | 5 × N_params × 回測 | ~5-15 分鐘（按需） |

**淨效果：** 每次實驗更快（移除 Monte Carlo 省了 ~30 秒），進階驗證只在需要時跑。

---

## 8. 學術參考

| 技術 | 參考 |
|------|------|
| Newey-West Sharpe | Lo, A.W., "The Statistics of Sharpe Ratios," *Financial Analysts Journal*, 2002 |
| Deflated Sharpe Ratio | Bailey & López de Prado, "The Deflated Sharpe Ratio," *Journal of Portfolio Management*, 2014 |
| CPCV | López de Prado, M., *Advances in Financial Machine Learning*, Chapter 12, 2018 |
| MinTRL | Bailey & López de Prado, "The Sharpe Ratio Efficient Frontier," *Journal of Risk*, 2012 |
| PBO/CSCV | Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting," *Journal of Risk*, 2017 |
| Multiple Testing | Harvey, Liu & Zhu, "... and the Cross-Section of Expected Returns," *Review of Financial Studies*, 2016 |
| FDR | Benjamini & Hochberg, "Controlling the False Discovery Rate," *JRSS-B*, 1995 |
