# Quant-Autoresearch V2 資料管道設計

> 日期：2026-04-01
> 基於本地 massive-minute-aggs 數據集（US Stocks SIP 分鐘級）
> Session 2 專題設計

---

## 設計決策總覽

| # | 項目 | 決定 |
|---|------|------|
| 1 | 數據源 | 本地 massive-minute-aggs（US Stocks SIP，分鐘級，11K+ tickers） |
| 2 | 市場範圍 | 美股專注 |
| 3 | 時間粒度 | 日線 + 分鐘線都支持，策略 focus 在分鐘級 |
| 4 | Symbol 範圍 | 全自由（11K+ tickers） |
| 5 | 數據準備 | 即時查詢（DuckDB），無中間快取（日線除外） |
| 6 | 特徵工程 | 只提供原始 OHLCV，策略自行計算所有指標 |
| 7 | 策略介面 | 雙方法：`select_universe(daily_data)` + `generate_signals(minute_data)` |
| 8 | 選股邏輯 | 策略驅動（日線摘要 → 篩選 tickers → 載入分鐘數據） |
| 9 | 日線快取 | 預計算 DuckDB 資料庫（11K tickers 日線聚合） |
| 10 | 日線快取建構 | CLI 命令初始化（setup_data），只跑一次 |
| 11 | 分鐘數據查詢 | CLI subprocess + CSV 解析 |
| 12 | 回測期間 | Agent 自由選擇，記錄在 Obsidian 筆記 |
| 13 | Walk-Forward | 5 窗口，以交易日為單位，含完整交易時段 |
| 14 | 回測窗口查詢 | 即時查詢每個窗口的分鐘數據 |

---

## 1. 數據源

### 1.1 本地數據集：massive-minute-aggs

```
Dataset Root: ~/Library/Mobile Documents/com~apple~CloudDocs/massive data/us_stocks_sip/minute_aggs_parquet_v1
CLI Binary:   /Users/chunsingyu/softwares/massive-minute-aggs-parquet/.venv/bin/minute-aggs
File Count:   1,256 Parquet files
Date Range:   2021-03-30 ~ 2026-03-30 (~5 years)
Tickers:      ~11,274 US stocks
Granularity:  1-minute bars (OHLCV + transactions)
```

### 1.2 Schema（邏輯層）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `ticker` | string | 股票代碼 |
| `session_date` | date | 交易日期 |
| `window_start_ns` | int64 | 納秒級時間戳 |
| `open` | float64 | 開盤價（已從 fixed-point 轉換） |
| `high` | float64 | 最高價 |
| `low` | float64 | 最低價 |
| `close` | float64 | 收盤價 |
| `volume` | float64 | 成交量 |
| `transactions` | int | 成交筆數 |

### 1.3 CLI 命令參考

```bash
# 數據集統計
minute-aggs stats

# Schema 確認
minute-aggs schema

# 查詢特定 ticker 的分鐘數據
minute-aggs bars --symbols AAPL MSFT --start 2025-11-03 --end 2025-11-05 --limit 1000

# SQL 查詢（DuckDB）
minute-aggs sql --query "SELECT ticker, avg(close) AS avg_close FROM minute_aggs WHERE session_date BETWEEN DATE '2025-11-03' AND DATE '2025-11-05' GROUP BY 1 ORDER BY 2 DESC"

# 輸出到檔案
minute-aggs bars --symbols AAPL --start 2025-11-03 --end 2025-11-05 --output /path/output.csv
```

---

## 2. 整體架構

```
┌─────────────────────────────────────────────────────────┐
│                      program.md                          │
│  （Agent 自由選擇回測期間、策略方向）                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Claude Code / Codex                      │
│                                                           │
│  LOOP FOREVER:                                            │
│    1. 讀 results.tsv + Obsidian 筆記                      │
│    2. 提出假說（含選股邏輯 + 交易邏輯）                   │
│    3. 改 active_strategy.py                               │
│    4. git commit                                          │
│    5. 跑 backtester → parse 結果                          │
│    6. keep / reset                                        │
│    7. 記錄 results.tsv + Obsidian 筆記                    │
└────────┬──────────────────────────────────┬──────────────┘
         │ 修改                              │ 執行
         ▼                                   ▼
┌──────────────────┐    ┌──────────────────────────────────┐
│ active_          │    │  src/core/backtester.py           │
│ strategy.py      │    │  (固定 — agent 不可改)             │
│ (全檔案可改)     │    │                                   │
│                  │    │  Phase A: 載入日線 DuckDB          │
│ • select_universe│    │  Phase B: select_universe()       │
│ • generate_      │    │  Phase C: 查詢分鐘數據 (CLI)      │
│   signals        │    │  Phase D: generate_signals()      │
│                  │    │  Phase E: Walk-Forward 評估        │
│                  │    │  Phase F: 多指標輸出               │
└──────────────────┘    └──────────┬───────────────────────┘
                                   │ 查詢
                    ┌──────────────┴──────────────┐
                    │                              │
              ┌─────▼──────┐              ┌────────▼────────┐
              │ 日線快取    │              │ 分鐘原始數據    │
              │ (DuckDB)   │              │ (CLI subprocess)│
              │            │              │                  │
              │ 11K tickers│              │ massive-minute-  │
              │ 日線 OHLCV │              │ aggs-parquet     │
              └────────────┘              └─────────────────┘
```

---

## 3. 日線快取（DuckDB）

### 3.1 建構命令

```bash
# V2 CLI 命令
uv run python cli.py setup_data
```

這個命令會：

1. 用 CLI sql 查詢全庫分鐘數據，按 ticker + session_date 聚合
2. 計算日線 OHLCV
3. 存入本地 DuckDB 檔案

### 3.2 DuckDB Schema

```sql
CREATE TABLE daily_bars (
    ticker       VARCHAR,        -- 股票代碼
    session_date DATE,           -- 交易日期
    open         DOUBLE,         -- 開盤價（當日第一根 bar）
    high         DOUBLE,         -- 最高價
    low          DOUBLE,         -- 最低價
    close        DOUBLE,         -- 收盤價（當日最後一根 bar）
    volume       DOUBLE,         -- 總成交量
    transactions INTEGER,        -- 總成交筆數
    vwap         DOUBLE,         -- 成交量加權平均價
    PRIMARY KEY (ticker, session_date)
);
```

### 3.3 建構邏輯

```python
def build_daily_cache(output_path: str = "data/daily_cache.duckdb"):
    """從分鐘數據建構日線 DuckDB 快取"""
    import duckdb

    CLI = "/Users/chunsingyu/softwares/massive-minute-aggs-parquet/.venv/bin/minute-aggs"
    DATASET = "~/Library/Mobile Documents/com~apple~CloudDocs/massive data/us_stocks_sip/minute_aggs_parquet_v1"

    # 按月聚合，避免一次性載入太多數據
    con = duckdb.connect(output_path)
    con.execute("CREATE TABLE IF NOT EXISTS daily_bars (...)")

    # 逐月查詢並聚合
    for year in range(2021, 2027):
        for month in range(1, 13):
            start = f"{year}-{month:02d}-01"
            end = f"{year}-{month:02d}-28"

            # 用 CLI sql 查詢該月所有 ticker 的聚合日線
            cmd = [
                CLI, "sql",
                "--query", f"""
                    SELECT
                        ticker,
                        session_date,
                        FIRST(open ORDER BY window_start_ns) AS open,
                        MAX(high) AS high,
                        MIN(low) AS low,
                        LAST(close ORDER BY window_start_ns) AS close,
                        SUM(volume) AS volume,
                        SUM(transactions) AS transactions,
                        SUM(close * volume) / NULLIF(SUM(volume), 0) AS vwap
                    FROM minute_aggs
                    WHERE session_date BETWEEN DATE '{start}' AND DATE '{end}'
                    GROUP BY ticker, session_date
                """,
                "--output", f"/tmp/daily_agg_{year}_{month}.csv"
            ]
            subprocess.run(cmd)

            # 載入 CSV 到 DuckDB
            csv_path = f"/tmp/daily_agg_{year}_{month}.csv"
            if os.path.exists(csv_path):
                con.execute(f"""
                    INSERT INTO daily_bars
                    SELECT * FROM read_csv('{csv_path}')
                """)
                os.remove(csv_path)

    con.close()
```

### 3.4 使用方式

```python
import duckdb

def load_daily_data(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """載入日線快取數據"""
    con = duckdb.connect("data/daily_cache.duckdb", read_only=True)

    query = "SELECT * FROM daily_bars"
    if start_date and end_date:
        query += f" WHERE session_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'"
    elif start_date:
        query += f" WHERE session_date >= DATE '{start_date}'"

    df = con.execute(query).fetchdf()
    con.close()
    return df
```

---

## 4. Backtester 資料流程

### 4.1 完整流程

```
backtester.py walk_forward_validation()
    │
    ├── 1. 載入日線 DuckDB 快取
    │      load_daily_data() → pd.DataFrame (all tickers, daily OHLCV)
    │
    ├── 2. 呼叫策略的 select_universe()
    │      strategy.select_universe(daily_data) → list[str]
    │      (策略根據 momentum、volume、板塊等篩選)
    │
    ├── 3. Walk-Forward 5 窗口
    │      for i in range(5):
    │          │
    │          ├── 3a. 計算窗口邊界（以交易日為單位）
    │          │       train_end = 第 N 個交易日
    │          │       test_start = train_end + 1
    │          │       test_end = 第 M 個交易日
    │          │
    │          ├── 3b. 查詢分鐘數據（CLI subprocess）
    │          │       for ticker in selected_tickers:
    │          │           minute-aggs bars --symbols {ticker}
    │          │             --start {test_start} --end {test_end}
    │          │             --output /tmp/window_{i}_{ticker}.csv
    │          │       → 讀取 CSV → pd.DataFrame
    │          │
    │          ├── 3c. 呼叫策略的 generate_signals()
    │          │       strategy.generate_signals(minute_data_dict)
    │          │       → dict[str, pd.Series]  {ticker: signals}
    │          │
    │          └── 3d. 計算窗口績效
    │                signals → P&L → Sharpe / Drawdown / etc.
    │
    └── 4. 輸出結果
           SCORE: ...
           SORTINO: ...
           ...
```

### 4.2 CLI Subprocess 查詢

```python
def query_minute_data(tickers: list[str], start_date: str, end_date: str) -> dict[str, pd.DataFrame]:
    """通過 CLI 查詢分鐘數據"""
    CLI = "/Users/chunsingyu/softwares/massive-minute-aggs-parquet/.venv/bin/minute-aggs"

    result = {}
    # 批量查詢（CLI 支持多 symbol）
    symbols_str = " ".join(tickers)
    cmd = [
        CLI, "bars",
        "--symbols", *tickers,
        "--start", start_date,
        "--end", end_date,
        "--output", "/tmp/minute_query.csv"
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if proc.returncode == 0 and os.path.exists("/tmp/minute_query.csv"):
        df = pd.read_csv("/tmp/minute_query.csv")
        # 按 ticker 分組
        for ticker, group in df.groupby("ticker"):
            result[ticker] = group.reset_index(drop=True)
        os.remove("/tmp/minute_query.csv")

    return result
```

---

## 5. 策略介面

### 5.1 策略 Class 定義

```python
class MyStrategy:
    """
    策略必須（至少）定義 generate_signals 方法。
    select_universe 是可選的 — 如果沒有定義，backtester 使用所有可用 tickers。
    """

    def select_universe(self, daily_data: pd.DataFrame) -> list[str]:
        """
        從日線數據中選擇要交易的 ticker 列表。

        參數:
            daily_data: DataFrame，包含所有 ticker 的日線數據。
                       欄位: ticker, session_date, open, high, low, close, volume, transactions, vwap

        返回:
            list[str]: 選中的 ticker 列表

        範例: 選擇昨日高動量的 top 50 ticker
            latest = daily_data.sort_values('session_date').groupby('ticker').last()
            latest['mom_5d'] = latest['close'].pct_change(5)
            return latest.nlargest(50, 'mom_5d').index.tolist()
        """
        pass

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
        """
        為每個 ticker 生成交易信號。

        參數:
            data: dict[str, pd.DataFrame]
                key = ticker 符號
                value = 分鐘級 OHLCV DataFrame
                欄位: ticker, session_date, window_start_ns, open, high, low, close, volume, transactions

        返回:
            dict[str, pd.Series]
                key = ticker 符號
                value = 信號 Series (1=做多, 0=觀望, -1=做空)
                index 必須與對應 DataFrame 的 index 對齊

        注意:
            - 只能使用 pd 和 np
            - 不能使用 for 迴圈（向量化運算）
            - 不能使用 .shift(-N)（look-ahead bias）
            - 信號會被自動 shift(1) 強制 1-bar lag
        """
        pass
```

### 5.2 動態載入

```python
def find_strategy_methods(sandbox_locals: dict):
    """動態掃描 sandbox 載入的策略 class"""
    for name, obj in sandbox_locals.items():
        if isinstance(obj, type) and hasattr(obj, 'generate_signals'):
            has_universe = hasattr(obj, 'select_universe')
            return obj, has_universe
    return None, False
```

### 5.3 最小策略範例

```python
class SimpleStrategy:
    def select_universe(self, daily_data):
        # 選擇過去 20 日成交量最高的 30 支股票
        latest = daily_data.groupby('ticker').last()
        return latest.nlargest(30, 'volume').index.tolist()

    def generate_signals(self, data):
        signals = {}
        for ticker, df in data.items():
            # 20-bar 動量
            mom = df['close'].pct_change(20)
            signals[ticker] = (mom > 0.01).astype(int) - (mom < -0.01).astype(int)
        return signals
```

---

## 6. Walk-Forward 設計（分鐘級）

### 6.1 窗口劃分

以交易日為單位，5 個滾動窗口：

```python
def get_trading_days(start_date: str, end_date: str) -> list[str]:
    """從日線快取取得交易日列表"""
    con = duckdb.connect("data/daily_cache.duckdb", read_only=True)
    result = con.execute(f"""
        SELECT DISTINCT session_date
        FROM daily_bars
        WHERE session_date BETWEEN DATE '{start_date}' AND DATE '{end_date}'
        ORDER BY session_date
    """).fetchall()
    con.close()
    return [str(r[0]) for r in result]

def calculate_walk_forward_windows(start_date: str, end_date: str, n_windows: int = 5):
    """計算 walk-forward 窗口邊界"""
    trading_days = get_trading_days(start_date, end_date)
    n_days = len(trading_days)
    window_size = n_days // n_windows

    windows = []
    for i in range(n_windows):
        train_start_idx = 0
        train_end_idx = (i + 1) * window_size
        test_start_idx = train_end_idx
        test_end_idx = (i + 2) * window_size if i < n_windows - 1 else n_days

        windows.append({
            'train_start': trading_days[train_start_idx],
            'train_end': trading_days[train_end_idx - 1],
            'test_start': trading_days[test_start_idx],
            'test_end': trading_days[min(test_end_idx - 1, n_days - 1)],
        })

    return windows
```

### 6.2 交易時段處理

每個交易日包含 9:30 AM - 4:00 PM ET 的分鐘數據（390 根 bar）。

```python
# 查詢時自動處理：CLI 返回的數據已經按 window_start_ns 排序
# 每個 session_date 包含完整的交易時段
# 不需要額外處理 overnight gap（跨交易日不自動連接）
```

---

## 7. CLI 命令變更（V2）

```bash
# 初始化：建構日線 DuckDB 快取
uv run python cli.py setup_data

# 更新日線快取（加入最新數據）
uv run python cli.py update_data

# 跑回測（agent 通過 program.md 指揮，不直接用這個命令）
uv run python src/core/backtester.py
```

### 移除的命令

```
cli.py fetch <symbol>     ← 不需要，數據已在本地
cli.py ingest <file>      ← 不需要
cli.py run                ← V2 由 Claude Code 直接跑 backtester
cli.py status             ← 不需要
cli.py report             ← 不需要
cli.py test               ← 不需要
cli.py research           ← 保留作 skill，後續 session 討論
```

---

## 8. 檔案變動清單

### 新增

```
data/daily_cache.duckdb              ← 日線聚合快取（DuckDB）
```

### 修改

```
src/core/backtester.py               ← 大改：
                                         • 載入日線 DuckDB
                                         • CLI subprocess 查詢分鐘數據
                                         • 雙方法策略介面 (select_universe + generate_signals)
                                         • 分鐘級 walk-forward
                                         • 多指標輸出
                                         • Per-Symbol 分析

src/strategies/active_strategy.py    ← 改為雙方法介面

cli.py                               ← 簡化：只留 setup_data, update_data

program.md                           ← 加入：
                                         • 數據集說明（massive-minute-aggs）
                                         • CLI 命令參考
                                         • 策略介面說明（雙方法）
                                         • 回測期間自由選擇
```

### 移除

```
src/data/connector.py                ← 不再需要 yfinance/CCXT
src/data/preprocessor.py             ← 被 setup_data 取代
```

### 保留

```
src/core/research.py                 ← 保留作 skill
src/memory/playbook.py               ← 保留作可選工具
```

---

## 9. 安全考量

### 9.1 沙箱限制（保持不變）

```python
# backtester 的 RestrictedPython 沙箱：
# - 只有 pd 和 np 可用
# - 禁止 exec, eval, open, getattr
# - 禁止 import socket, requests, os, sys, subprocess
# - 禁止 .shift(-N)（look-ahead bias）
```

### 9.2 新增：CLI 查詢安全

```python
# backtester 自己調用 CLI，策略不直接接觸 subprocess
# 策略只在沙箱內運行，無法調用外部命令
# CLI 的 SQL 查詢由 backtester 構造，不接受策略的 SQL 字串
```

---

## 10. 效能考量

### 10.1 數據量估算

```
日線快取: 11K tickers × 1260 trading days × 9 columns ≈ ~100MB (DuckDB)

分鐘查詢（每窗口）:
  30 tickers × 60 trading days × 390 bars/day ≈ 700K rows
  CLI 查詢 + CSV 解析 ≈ 5-15 秒

Walk-Forward 總查詢:
  5 窗口 × 15 秒 ≈ 75 秒（分鐘數據查詢）
  + 策略計算時間 ≈ 30-60 秒
  總計每次實驗 ≈ 2-3 分鐘
```

### 10.2 優化方向

- **批量查詢**: CLI 支持多 symbol，一次查詢多個 tickers
- **窗口快取**: 相同窗口的數據可以在多次實驗間重用（可選）
- **並行查詢**: 多個窗口的 CLI 查詢可以並行執行

---

## 11. 待確認事項（後續 Session）

| # | 項目 | Session |
|---|------|---------|
| 1 | 過擬合防禦設計 | Session 3 |
| 2 | 研究能力設計 | Session 4 |
| 3 | 日線快取的增量更新機制 | 實作時決定 |
| 4 | 分鐘級 Monte Carlo 的效能問題 | Session 3 |
| 5 | 多時間框架策略的支持方式 | 後續討論 |
