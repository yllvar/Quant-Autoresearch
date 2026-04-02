# Quant-Autoresearch V2 研究能力設計

> 日期：2026-04-01
> 基於現有 Obsidian Vault + TradingAgents 架構研究
> Session 4 專題設計

---

## 設計決策總覽

| # | 項目 | 決定 |
|---|------|------|
| 1 | 研究搜索 | 保留 research.py 作 CLI skill，結果記錄到 Obsidian |
| 2 | Obsidian 整合 | 融入現有 vault，新增 `quant-autoresearch/` 子目錄 |
| 3 | Playbook | 移除 SQLite，由 Obsidian 筆記 + results.tsv 替代 |
| 4 | 股票研究 | TradingAgents 風格多 agent 調研 CLI |
| 5 | 知識庫 | 靜態 Markdown 筆記（過擬合防禦、策略模式、微結構、方法論） |
| 6 | 實驗筆記 | 融入 vault 的 `quant-autoresearch/experiments/` |
| 7 | 策略靈感 | Agent 讀取 vault 現有 `trading strategy/` 筆記作參考 |
| 8 | 記憶層級 | 借鑑 OpenClaw 四層記憶架構 |

---

## 1. Obsidian Vault 整合架構

### 1.1 新增目錄結構

在現有 vault 內新增 `quant-autoresearch/` 子目錄，不動現有內容：

```
/Users/chunsingyu/Documents/Obsidian Vault/
├── trading strategy/                    ← 現有（不動）
│   ├── regime/strategies/*.md           ← Agent 可讀取策略靈感
│   ├── trend-following/strategies/*.md
│   ├── mean-reversion/strategies/*.md
│   ├── risk-management/strategies/*.md
│   └── ...
├── AI-Trader/                           ← 現有（不動）
├── OpenClaw/                            ← 現有（不動）
│
├── quant-autoresearch/                  ← ★ 新增
│   ├── experiments/                     ← 實驗筆記（每次回測一個）
│   │   ├── 001-baseline-momentum.md
│   │   ├── 002-add-regime-filter.md
│   │   └── ...
│   ├── research/                        ← 研究結果（CLI 生成）
│   │   ├── 2026-04-01-mean-reversion-lit.md
│   │   ├── 2026-04-02-ticker-AAPL-analysis.md
│   │   └── ...
│   └── knowledge/                       ← 靜態知識庫（手動建立）
│       ├── overfit-defense.md
│       ├── market-microstructure.md
│       ├── strategy-pattern-catalog.md
│       └── experiment-methodology.md
```

### 1.2 Vault 互動模式

```
┌─────────────────────────────────────────────────────────────┐
│                    program.md                                │
│  （指引 agent 如何使用研究能力）                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Claude Code / Codex                          │
│                                                              │
│  實驗 Loop：                                                  │
│    1. 讀 vault 策略筆記 → 取得靈感                            │
│    2. 讀 knowledge/ → 過擬合防禦、方法論參考                   │
│    3. （可選）跑 research CLI → 搜索文獻                      │
│    4. （可選）跑 analyze CLI → 股票深度調研                    │
│    5. 改 active_strategy.py                                  │
│    6. 跑 backtester                                          │
│    7. 實驗筆記 → vault experiments/                           │
│    8. Loop                                                   │
│                                                              │
│  讀取（Read-only）：                                          │
│    • trading strategy/*/strategies/ → 策略模式參考             │
│    • knowledge/ → 學術參考、防禦指引                          │
│    • research/ → 過去搜索結果                                 │
│    • experiments/ → 歷史實驗記錄                              │
│                                                              │
│  寫入（Write）：                                              │
│    • experiments/*.md → 每次實驗結果                          │
│    （research/ 和 analyze 由 CLI 直接寫入）                   │
└──────────────────────────────────────────────────────────────┘
```

### 1.3 與 OpenClaw 記憶架構的對齊

借鑑 OpenClaw 的四層記憶，Quant-Autoresearch 的對應：

| OpenClaw 層級 | 位置 | Quant-Autoresearch 對應 |
|---|---|---|
| 短期（即時） | session context | Claude Code 對話上下文 |
| 工作（每日） | memory/ | `experiments/` 最新筆記 + `run.log` |
| 持久（知識庫） | Obsidian Vault | `trading strategy/` + `knowledge/` + `research/` |
| 長期（精選） | MEMORY.md | `results.tsv`（跨 session 的最佳結果追蹤） |

---

## 2. Research CLI Skill

### 2.1 命令設計

```bash
# 學術文獻搜索（ArXiv）+ 網頁搜索
uv run python cli.py research "<query>"
# 例：uv run python cli.py research "intraday momentum strategy minute bars"

# 指定搜索深度
uv run python cli.py research "<query>" --depth shallow   # 只搜 ArXiv
uv run python cli.py research "<query>" --depth deep      # ArXiv + web + 摘要
```

### 2.2 輸出

結果直接寫入 vault：

```
quant-autoresearch/research/2026-04-01-<slug>.md
```

格式遵循 vault 既有的 YAML frontmatter 慣例：

```markdown
---
note_type: research
research_type: literature
query: "intraday momentum strategy minute bars"
date: 2026-04-01
sources_count: 5
tags:
  - research
  - momentum
  - intraday
---

# Research: Intraday Momentum Strategy Minute Bars

## Academic Papers

### Paper 1: Intraday Momentum in the Stock Market
- **Source**: ArXiv
- **URL**: https://arxiv.org/abs/xxxx.xxxxx
- **Published**: 2025-03-15
- **Summary**: ...（自動生成的摘要）
- **Key Findings**: ...
- **Relevance**: ...（對我們策略的啟發）

### Paper 2: ...

## Web Resources

### [Title](url)
- **Source**: [domain]
- **Snippet**: ...
- **Relevance**: ...

## Synthesis

（深度模式時生成：綜合分析 + 對策略設計的建議）

## Actionable Ideas

- [ ] Idea 1: ...
- [ ] Idea 2: ...
```

### 2.3 實作邏輯

從 V1 的 `src/core/research.py` 重構：

```python
# cli.py research 子命令

def cmd_research(args):
    """研究搜索 CLI skill"""
    query = args.query
    depth = args.depth  # shallow / deep

    # 1. ArXiv 搜索（保留 V1 邏輯）
    papers = search_arxiv(query, max_results=5)

    # 2. Web 搜索（保留 V1 Exa/SerpAPI 邏輯）
    web_results = []
    if depth == "deep":
        web_results = search_web(query)

    # 3. 生成 Markdown 報告
    report = format_research_report(query, papers, web_results, depth)

    # 4. 寫入 Obsidian vault
    vault_path = get_vault_path()  # /Users/chunsingyu/Documents/Obsidian Vault
    slug = slugify(query)
    date = datetime.now().strftime("%Y-%m-%d")
    output_path = f"{vault_path}/quant-autoresearch/research/{date}-{slug}.md"
    write_to_vault(output_path, report)

    # 5. 同時印出到 stdout（agent 可直接讀取）
    print(report)
```

### 2.4 快取策略

保留 V1 的 JSON 快取（`research_cache.json`、`web_research_cache.json`），但增加去重：

```python
# 搜索前先檢查 vault 是否已有相同查詢的結果
def check_existing_research(query, vault_path):
    """檢查 vault 中是否已有相關研究"""
    research_dir = f"{vault_path}/quant-autoresearch/research/"
    if not os.path.exists(research_dir):
        return None

    # 簡單 keyword matching
    query_words = set(query.lower().split())
    for f in os.listdir(research_dir):
        if not f.endswith('.md'):
            continue
        # 讀 frontmatter 的 query 欄位
        existing_query = read_frontmatter(os.path.join(research_dir, f)).get('query', '')
        existing_words = set(existing_query.lower().split())
        overlap = query_words & existing_words
        if len(overlap) / max(len(query_words), 1) > 0.6:
            return os.path.join(research_dir, f)

    return None
```

---

## 3. Stock Research CLI（TradingAgents 風格）

### 3.1 設計理念

借鑑 TradingAgents 的多視角分析架構，但簡化為單 CLI 命令：

```
TradingAgents: 4 analysts → Bull/Bear debate → Research Manager → Trader
我們: analyze CLI → 多維度技術分析 → Bull/Bear 辯論 → 研究報告
```

差異：
- TradingAgents 需要 LangGraph + 多 LLM 呼叫；我們用單一 Claude Code
- TradingAgents 用外部 API 取數據；我們用本地 massive-minute-aggs
- TradingAgents 即時交易決策；我們做策略研究參考

### 3.2 命令設計

```bash
# 單 ticker 分析
uv run python cli.py analyze AAPL

# 多 ticker 比較
uv run python cli.py analyze AAPL MSFT GOOGL

# 指定期間
uv run python cli.py analyze AAPL --start 2025-06-01 --end 2026-03-31

# 輸出到 vault（預設）
uv run python cli.py analyze AAPL --output vault

# 輸出到 stdout（agent 直接讀取）
uv run python cli.py analyze AAPL --output stdout
```

### 3.3 分析流程

```
cli.py analyze AAPL
    │
    ├── Phase 1: 數據載入（massive-minute-aggs CLI）
    │   ├── 日線數據（從 DuckDB 快取）
    │   └── 分鐘數據（近 60 個交易日）
    │
    ├── Phase 2: 技術分析（純計算，無 LLM）
    │   ├── 動量指標：ROC(5), ROC(10), ROC(20)
    │   ├── 波動率：Realized Vol (5d, 20d, 60d)
    │   ├── Regime 分類（基於 vol + return）
    │   ├── 成交量分析：rel_volume, volume_trend
    │   ├── 價格結構：support/resistance levels
    │   └── 統計摘要：Sharpe, max DD, trend strength
    │
    ├── Phase 3: 市場背景（純計算）
    │   ├── 與 SPY 相關性
    │   ├── 板塊輪動定位
    │   └── 市場寬度定位（vs 50d MA）
    │
    └── 輸出：結構化 Markdown 報告
        → stdout（agent 讀取）
        → vault quant-autoresearch/research/（存檔）
```

**注意**：Phase 2 和 Phase 3 都是純數值計算，不呼叫 LLM。Agent（Claude Code）拿到報告後自己做推理。

### 3.4 實作邏輯

```python
def cmd_analyze(args):
    """股票深度分析 CLI skill"""
    tickers = args.tickers
    start = args.start or default_start()  # 預設：60 個交易日前
    end = args.end or today()

    # Phase 1: 載入數據
    daily_data = load_daily_data(start, end)  # DuckDB
    minute_data = {}
    for ticker in tickers:
        minute_data[ticker] = query_minute_data([ticker], start, end)

    # Phase 2+3: 技術分析（對每個 ticker）
    reports = {}
    for ticker in tickers:
        reports[ticker] = {
            'momentum': calc_momentum(daily_data[ticker]),
            'volatility': calc_volatility(daily_data[ticker]),
            'regime': classify_regime(daily_data[ticker]),
            'volume': analyze_volume(daily_data[ticker]),
            'price_structure': find_key_levels(daily_data[ticker]),
            'market_context': calc_market_context(ticker, daily_data),
            'statistics': calc_summary_stats(daily_data[ticker]),
        }

    # 格式化輸出
    output = format_analysis_report(tickers, reports, start, end)

    # 寫入
    if args.output == 'vault':
        write_to_vault(tickers, output)
    print(output)


def calc_momentum(df):
    """動量指標計算"""
    return {
        'roc_5d': (df['close'].iloc[-1] / df['close'].iloc[-6] - 1) if len(df) > 5 else None,
        'roc_20d': (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) if len(df) > 20 else None,
        'roc_60d': (df['close'].iloc[-1] / df['close'].iloc[-61] - 1) if len(df) > 60 else None,
    }

def classify_regime(df):
    """Regime 分類（沿用過擬合防禦 Session 3 的設計）"""
    rolling_ret = df['close'].pct_change(20)
    rolling_vol = df['close'].pct_change().rolling(20).std()
    vol_median = rolling_vol.median()

    current_ret = rolling_ret.iloc[-1]
    current_vol = rolling_vol.iloc[-1]

    if current_ret > 0 and current_vol < vol_median:
        regime = 'bull_quiet'
    elif current_ret > 0 and current_vol >= vol_median:
        regime = 'bull_volatile'
    elif current_ret <= 0 and current_vol < vol_median:
        regime = 'bear_quiet'
    else:
        regime = 'bear_volatile'

    return {
        'current': regime,
        'vol_percentile': (rolling_vol > current_vol).mean(),
    }

def find_key_levels(df):
    """支撐/阻力位（簡單版本：近期高低點）"""
    recent = df.tail(60)
    return {
        'high_60d': recent['high'].max(),
        'low_60d': recent['low'].min(),
        'close': df['close'].iloc[-1],
        'pct_from_high': (df['close'].iloc[-1] / recent['high'].max() - 1),
        'pct_from_low': (df['close'].iloc[-1] / recent['low'].min() - 1),
    }
```

### 3.5 輸出格式

```markdown
---
note_type: research
research_type: stock-analysis
tickers: [AAPL]
date: 2026-04-01
period: 2025-12-01 to 2026-03-31
tags:
  - stock-analysis
  - AAPL
  - technology
---

# Stock Analysis: AAPL

## Executive Summary
- **Regime**: Bull Quiet (low volatility uptrend)
- **Momentum**: Positive across all timeframes
- **Vol**: 22.3% annualized (35th percentile — below median)
- **Price**: $178.45 (-3.2% from 60d high, +8.7% from 60d low)

## Momentum
| Period | ROC |
|--------|-----|
| 5d     | +1.2% |
| 20d    | +4.8% |
| 60d    | +12.3% |

## Volatility
| Window | Realized Vol (ann.) |
|--------|---------------------|
| 5d     | 18.2% |
| 20d    | 22.3% |
| 60d    | 25.1% |

## Regime Classification
- **Current**: Bull Quiet
- **Vol Percentile**: 35th (below median)
- 最近 60 天 regime 分佈：
  - Bull Quiet: 32 天 (53%)
  - Bull Volatile: 15 天 (25%)
  - Bear Quiet: 10 天 (17%)
  - Bear Volatile: 3 天 (5%)

## Price Structure
- 60d High: $184.35
- 60d Low: $164.20
- Current: $178.45
- 距高點: -3.2%
- 距低點: +8.7%
- VWAP: $176.82

## Market Context
- 與 SPY 相關性: 0.78
- 距 50d MA: +2.1%
- 距 200d MA: +5.8%

## Statistics (60d)
- Sharpe: 1.82
- Max Drawdown: -6.2%
- Win Rate (daily): 54%
- Avg Daily Range: 1.8%

## Strategy Implications
（Agent 讀取此報告後自行推理，寫入實驗筆記的 Hypothesis 段落）
```

### 3.6 Agent 使用方式

Agent 在 Claude Code 中這樣用：

```markdown
# program.md 中的指引

## Stock Research

When designing a strategy that requires universe selection, analyze candidate tickers:

\`\`\`bash
uv run python cli.py analyze AAPL MSFT GOOGL --start 2025-06-01
\`\`\`

Use the output to:
- Understand current regime per ticker
- Identify which tickers have strongest momentum
- Check volume characteristics for liquidity
- Validate that the universe is diverse enough

You can also read existing analyses in the vault:
\`\`\`
Read: ~/Documents/Obsidian Vault/quant-autoresearch/research/
\`\`\`
```

---

## 4. Knowledge Base（靜態知識庫）

### 4.1 四個核心筆記

#### `knowledge/overfit-defense.md`

整合 Session 3 的過擬合防禦設計為人類/agent 可讀的參考筆記：

```markdown
---
note_type: knowledge
topic: overfit-defense
last_updated: 2026-04-01
tags: [knowledge, overfitting, backtesting, statistics]
---

# Overfit Defense Reference

## Why Overfitting Happens
（López de Prado 的核心論點摘要）

## Layer 1: Built-in Defenses (every backtest)
- Newey-West Sharpe → 為什麼分鐘數據需要
- Deflated Sharpe Ratio → 為什麼測試次數很重要
- Walk-Forward → 為什麼 rolling OOS 比 single split 好

## Layer 2: Advanced Validation (on-demand)
- CPCV → 什麼時候用，怎麼解讀
- Regime analysis → 什麼時候用，怎麼解讀
- Parameter stability → 什麼時候用，怎麼解讀

## Red Flags
- NW_SHARPE_BIAS > 0.3 → ...
- DEFLATED_SR < 0.5 → ...

## Academic References
- Bailey & López de Prado (2014)
- López de Prado (2018) Chapter 12
- Harvey, Liu & Zhu (2016)
```

#### `knowledge/market-microstructure.md`

```markdown
---
note_type: knowledge
topic: market-microstructure
last_updated: 2026-04-01
tags: [knowledge, microstructure, minute-data]
---

# Market Microstructure for Minute-Level Data

## Bid-Ask Bounce
（為什麼分鐘級收益有負自相關）

## Non-Synchronous Trading
（為什麼分鐘級收益有正自相關）

## Newey-West Adjustment
（為什麼傳統 Sharpe 在分鐘級不可靠）

## Volume Patterns
（開盤/收盤成交量聚集、午餐時段清淡）

## Overnight Gaps
（跨交易日的 gap 處理方式）

## Our Data Characteristics
- Source: US Stocks SIP
- 11,274 tickers
- 390 bars/day (9:30 AM - 4:00 PM ET)
- 5 years (2021-03-30 ~ 2026-03-30)
```

#### `knowledge/strategy-pattern-catalog.md`

```markdown
---
note_type: knowledge
topic: strategy-patterns
last_updated: 2026-04-01
tags: [knowledge, strategies, patterns]
---

# Strategy Pattern Catalog

每個模式連結到 vault 中相關的策略筆記（wikilinks）。

## 1. Momentum
- **Core Idea**: Price continuation
- **Signals**: ROC, EMA crossover, breakout
- **Works Best**: Bull Quiet, trending markets
- **Key Risk**: Regime change, mean reversion
- **Vault References**: [[trend-following-tradingview-...]]
- **Common Parameters**: lookback (10-60 bars), threshold

## 2. Mean Reversion
- **Core Idea**: Price returns to mean
- **Signals**: Bollinger Bands, RSI extremes, Z-score
- **Works Best**: Range-bound, bear quiet
- **Key Risk**: Trend continuation, structural break
- **Vault References**: [[regime-cboe-vix-framework]]

## 3. Regime-Based
- **Core Idea**: Adapt strategy to market regime
- **Signals**: Volatility regime, VIX levels, trend strength
- **Works Best**: All regimes (adaptive)
- **Key Risk**: Regime misclassification, lag
- **Vault References**: [[regime-cboe-vix-framework]]

## 4. Risk Management Overlays
- **Position Sizing**: Volatility-adjusted, Kelly criterion
- **Stop Loss**: ATR-based, trailing, time-based
- **Exposure Limits**: Max gross/net exposure

## Implementation Guidelines
- Start simple (momentum → regime → combination)
- Each strategy should be < 30 lines of vectorized code
- Always test parameter stability
- Check regime robustness
```

#### `knowledge/experiment-methodology.md`

```markdown
---
note_type: knowledge
topic: experiment-methodology
last_updated: 2026-04-01
tags: [knowledge, methodology, experiments]
---

# Experiment Methodology

## How to Design a Good Experiment
1. Clear hypothesis → "Adding X filter should improve Y because Z"
2. One variable at a time (usually)
3. Record everything → vault experiments/
4. Compare vs baseline → SCORE must improve

## Common Pitfalls
- Testing too many ideas at once → can't attribute improvement
- Ignoring transaction costs → realistic with BASE_COST=0.0005
- Overfitting to specific period → Walk-Forward handles this
- Survivorship bias → universe is fixed from data snapshot

## Decision Framework
- SCORE improvement > 0.05 → worth keeping
- SCORE improvement < 0.02 but simpler code → worth keeping
- SCORE improvement < 0.02 with more complexity → skip
- SCORE regression > 0.05 → understand why before moving on

## Reading Results
- SCORE = Newey-West Sharpe (usually LOWER than naive)
- NW_SHARPE_BIAS = how much serial correlation affected the estimate
- DEFLATED_SR = statistical significance after multiple tests
- Per-Symbol → check if alpha is concentrated or diversified

## When to Pivot
- 3+ consecutive discards on same approach → try fundamentally different idea
- Read vault strategy notes for new inspiration
- Run research CLI for academic ideas
- Consider combining two near-miss strategies
```

---

## 5. Experiment Note（實驗筆記）

### 5.1 格式

遵循 vault 既有的 YAML frontmatter 慣例，寫入 `quant-autoresearch/experiments/`：

```markdown
---
note_type: experiment
experiment_id: 003
commit: f6g7h8i
date: 2026-04-01T14:30:00
status: keep
strategy_type: momentum
tags:
  - experiment
  - momentum
  - regime-filter
---

# Experiment 003: Combine momentum + regime filter

## Hypothesis
Combining the ROC momentum signal with the ATR regime filter should reduce
false signals during high-volatility periods while maintaining trend capture.

## Strategy Changes
- Added ROC(14) as primary momentum indicator
- Used volatility regime filter as gate
- Only go long/short when regime is low-vol AND momentum confirms

## Results
| Metric | Value | vs Previous Best |
|--------|-------|------------------|
| SCORE (NW Sharpe) | 0.6500 | +0.1068 |
| Naive Sharpe | 0.8200 | +0.1368 |
| Deflated SR | 0.95 | +0.03 |
| Sortino | 0.9800 | +0.1700 |
| Profit Factor | 2.3000 | +0.4500 |
| Win Rate | 60% | +5% |
| NW Bias | 0.17 | -0.06 (better) |

## Per-Symbol
- SPY: sharpe=0.72 (strong in low-vol regime)
- QQQ: sharpe=0.68 (good trend capture)
- IWM: sharpe=0.43 (weaker, needs investigation)

## Observations
- IWM underperforms — small-cap regime behavior differs
- Profit Factor improvement suggests the filter is cutting bad trades
- NW Bias decreased → serial correlation less exploited

## Counter-Argument (Bull/Bear 辯論)
**Why this might fail:**
- Regime classification may lag → entering late, exiting late
- Only tested on 3 tickers → may not generalize to broader universe
- Regime thresholds are arbitrary (median vol) → data-dependent

**Why this might be real:**
- Improvement is consistent across all 3 tickers
- NW Bias decreased (not exploiting serial correlation)
- Walk-Forward confirmed across 5 windows

## Next Ideas
- [ ] Try symbol-specific regime thresholds
- [ ] Expand universe with `select_universe()` to top-50 momentum
- [ ] Run CPCV validation: `cli.py validate --method cpcv`
- [ ] Check regime analysis: `cli.py validate --method regime`
```

### 5.2 Counter-Argument 欄位

借鑑 TradingAgents 的 Bull/Bear 辯論機制。每次實驗筆記都要求 agent 填寫：

- **Why this might fail** — 強制 agent 考慮反面論點
- **Why this might be real** — 正面論據

這取代了 TradingAgents 的多輪辯論（我們用 agent 自我辯論替代多 agent 辯論，更簡潔）。

### 5.3 與 results.tsv 的關係

```
results.tsv = 機器可讀的表格（agent 快速掃描歷史）
experiments/*.md = 人類可讀的筆記（含推理、觀察、反面論證）
```

兩者通過 `experiment_id` 和 `commit` hash 關聯。

---

## 6. 記憶系統設計

### 6.1 四層記憶（對齊 OpenClaw）

```
┌─────────────────────────────────────────────────────────┐
│ Layer 4: 長期記憶（跨 session）                          │
│                                                          │
│ results.tsv                                              │
│ • 保留所有 session 的最佳結果                             │
│ • commit hash → 可追溯完整策略代碼                        │
│ • 人類和 agent 都可查閱                                  │
└─────────────────────────────────────────────────────────┘
        ↑ 精選
┌─────────────────────────────────────────────────────────┐
│ Layer 3: 持久記憶（Obsidian Vault）                      │
│                                                          │
│ quant-autoresearch/                                      │
│ ├── experiments/  → 歷史實驗筆記                         │
│ ├── research/     → 研究搜索結果                         │
│ └── knowledge/    → 靜態知識庫                           │
│                                                          │
│ trading strategy/                                         │
│ └── */strategies/ → 策略模式參考（來自 Reddit/TradingView）│
└─────────────────────────────────────────────────────────┘
        ↑ 查詢
┌─────────────────────────────────────────────────────────┐
│ Layer 2: 工作記憶（session 內）                          │
│                                                          │
│ • 當前 active_strategy.py 的狀態                         │
│ • run.log（最近一次回測輸出）                             │
│ • program.md（研究指令）                                  │
│ • 當前 session 的 experiments/*.md                        │
└─────────────────────────────────────────────────────────┘
        ↑ 載入
┌─────────────────────────────────────────────────────────┐
│ Layer 1: 短期記憶（即時上下文）                           │
│                                                          │
│ • Claude Code 對話上下文                                  │
│ • 最近 2-3 次實驗的結果和觀察                             │
│ • 當前假說和策略邏輯                                     │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Agent 記憶查詢策略

```markdown
# program.md 中的記憶查詢指引

## Memory Access Patterns

1. **每次實驗前**：讀 results.tsv（Layer 4）
   → 了解當前最佳 SCORE、歷史趨勢

2. **每 5 次實驗**：讀 experiments/ 最近筆記（Layer 2-3）
   → 回顧最近的觀察和 Next Ideas

3. **卡住時**：讀 trading strategy/*/strategies/（Layer 3）
   → 從社群策略中找新靈感

4. **新策略類型前**：讀 knowledge/（Layer 3）
   → 複習過擬合防禦、微結構特性

5. **重大改進後**：跑進階驗證（Layer 2 CLI）
   → CPCV、regime、stability 確認
```

---

## 7. program.md 研究能力指引

以下段落加到 program.md：

```markdown
## Research Capabilities

### Reading the Knowledge Base

Your Obsidian vault contains curated strategy research and knowledge:

**Strategy Ideas** (read for inspiration):
- Path: ~/Documents/Obsidian Vault/trading strategy/*/strategies/
- Categories: regime, trend-following, mean-reversion, risk-management, portfolio-construction
- These are community-sourced strategies with structured notes (Thesis, Signal Logic, Entry/Exit)

**Knowledge Base** (read for reference):
- Path: ~/Documents/Obsidian Vault/quant-autoresearch/knowledge/
- Topics: overfit-defense, market-microstructure, strategy-pattern-catalog, experiment-methodology
- Read these when starting a new strategy type or when stuck

### Research CLI

Search academic literature and web resources:
\`\`\`bash
# Quick search
uv run python cli.py research "intraday momentum minute bars"

# Deep search (includes synthesis and actionable ideas)
uv run python cli.py research "mean reversion regime filter" --depth deep
\`\`\`

Results are automatically saved to your vault. Check existing research before searching:
\`\`\`bash
ls ~/Documents/Obsidian\ Vault/quant-autoresearch/research/
\`\`\`

### Stock Analysis CLI

Analyze specific tickers for universe selection or strategy design:
\`\`\`bash
# Single ticker
uv run python cli.py analyze AAPL

# Multiple tickers
uv run python cli.py analyze AAPL MSFT GOOGL --start 2025-06-01
\`\`\`

Output includes: momentum, volatility, regime classification, price structure, market context.
Use this to inform `select_universe()` logic.

### When to Do Research

- **Before starting**: Read 2-3 strategy notes from the vault for inspiration
- **Every 10 experiments**: Run `cli.py research` for fresh academic ideas
- **When designing universe selection**: Run `cli.py analyze` on candidate tickers
- **When stuck**: Read `knowledge/experiment-methodology.md` → pivot strategy
- **After major improvement**: Write detailed Counter-Argument in experiment note
```

---

## 8. Vault 路徑配置

### 8.1 配置方式

在 `program.md` 或 `config/` 中定義 vault 路徑：

```python
# config/vault.py
import os

VAULT_ROOT = os.path.expanduser("~/Documents/Obsidian Vault")
QUANT_DIR = f"{VAULT_ROOT}/quant-autoresearch"

def get_vault_paths():
    return {
        'root': VAULT_ROOT,
        'experiments': f"{QUANT_DIR}/experiments",
        'research': f"{QUANT_DIR}/research",
        'knowledge': f"{QUANT_DIR}/knowledge",
        'strategies': f"{VAULT_ROOT}/trading strategy",
    }

def ensure_dirs():
    """確保 quant-autoresearch 子目錄存在"""
    for path in get_vault_paths().values():
        os.makedirs(path, exist_ok=True)
```

### 8.2 初始化命令

```bash
# 初始化 vault 目錄結構 + 知識庫
uv run python cli.py setup_vault

# 這個命令會：
# 1. 建立 quant-autoresearch/ 子目錄
# 2. 生成四個知識庫筆記（如果不存在）
# 3. 驗證 vault 結構
```

---

## 9. 檔案變動清單

### 新增

```
config/vault.py                       ← Vault 路徑配置
src/research/__init__.py              ← 研究模組（重構自 src/core/research.py）
src/research/arxiv_search.py          ← ArXiv 搜索（重構）
src/research/web_search.py            ← 網頁搜索（重構）
src/research/vault_writer.py          ← Vault 寫入工具
src/analysis/__init__.py              ← 股票分析模組
src/analysis/technical.py             ← 技術指標計算
src/analysis/regime.py                ← Regime 分類（重構自 validation/regime.py）
src/analysis/market_context.py        ← 市場背景分析
```

### 修改

```
cli.py                                ← 新增子命令：
                                         • research <query> [--depth]
                                         • analyze <tickers> [--start] [--end] [--output]
                                         • setup_vault

program.md                            ← 新增研究能力指引段落
                                         （Reading Knowledge Base, Research CLI, Stock Analysis CLI）
```

### 移除

```
src/core/research.py                  ← 重構到 src/research/
src/tools/bm25_search.py              ← 移除（Obsidian 搜索替代）
src/memory/playbook.py                ← 移除（Obsidian 筆記替代）
```

### 保留（不動）

```
src/core/backtester.py                ← V2 回測引擎（Session 2-3 設計）
src/validation/                       ← 過擬合防禦模組（Session 3 設計）
```

---

## 10. CLI 命令總覽

```bash
# 初始化
uv run python cli.py setup_data           ← 建構日線 DuckDB 快取（Session 2）
uv run python cli.py setup_vault          ← 初始化 Obsidian vault 子目錄 + 知識庫

# 研究搜索
uv run python cli.py research "<query>"   ← ArXiv + web 搜索
uv run python cli.py research "<query>" --depth deep

# 股票分析
uv run python cli.py analyze AAPL MSFT    ← 技術分析 + regime + 市場背景

# 進階驗證
uv run python cli.py validate --method cpcv    ← CPCV 驗證（Session 3）
uv run python cli.py validate --method regime   ← Regime 分析（Session 3）
uv run python cli.py validate --method stability ← 參數穩定性（Session 3）
```

---

## 11. 與其他 Session 的整合

### 11.1 Session 2（資料管道）

- `analyze` CLI 使用 DuckDB 日線快取 + massive-minute-aggs CLI
- 技術指標計算復用 backtester 的數據載入邏輯

### 11.2 Session 3（過擬合防禦）

- `knowledge/overfit-defense.md` 是過擬合防禦設計的人類/agent 可讀版本
- `analyze` CLI 的 regime 分類復用 `validation/regime.py` 的邏輯
- 進階驗證命令（CPCV、stability）保持不變

### 11.3 Session 1（架構）

- Playbook 由 Obsidian 筆記替代
- research.py 重構為 CLI skill
- program.md 新增研究能力指引

---

## 12. 效能考量

| 操作 | 耗時 | 頻率 |
|------|------|------|
| 讀 vault 策略筆記 | <1 秒 | 每 session 2-3 次 |
| `research --depth shallow` | 5-10 秒 | 每 10 次實驗 |
| `research --depth deep` | 15-30 秒 | 偶爾 |
| `analyze` (1 ticker) | 5-10 秒 | 按需 |
| `analyze` (5 tickers) | 15-30 秒 | 按需 |
| 讀 knowledge/ 筆記 | <1 秒 | 每個新策略類型 |
| 寫實驗筆記 | <1 秒 | 每次實驗 |

**淨效果**：研究能力不影響回測速度，只在需要時消耗時間。

---

## 13. 未來擴展

| 方向 | 說明 | 優先級 |
|------|------|--------|
| 自動 ingestion | 類似 TradingView 攝取，自動收集 ArXiv 新論文到 vault | 低（V2 之後） |
| Wikilink 智能推薦 | 基於當前策略自動推薦相關 vault 筆記 | 低 |
| 多 agent 辯論 | 真正的 Bull/Bear 多 agent 辯論（TradingAgents 完整版） | 低（V2 之後） |
| Vector search | 對 vault 筆記加輕量向量索引（替代 Playbook 的 TF-IDF） | 中（如果 vault 增長很快） |
