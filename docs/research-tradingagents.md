# TradingAgents 架構研究

> 研究日期：2026-04-01
> 來源：https://github.com/tauricresearch/tradingagents
> 目的：為 V2 研究能力設計（Session 4）提供參考

---

## 1. 核心架構

### 1.1 LangGraph 多 Agent 協作管道

TradingAgents 使用 LangGraph StateGraph 編排一條多階段決策管道：

```
輸入 (ticker, date)
    ↓
┌─────────────────────────────────────────┐
│  Phase 1: Analyst Team (並行)           │
│  ┌──────────┐ ┌──────────┐             │
│  │Fundmental│ │Sentiment │             │
│  │Analyst   │ │Analyst   │             │
│  └────┬─────┘ └────┬─────┘             │
│  ┌────┴─────┐ ┌────┴─────┐             │
│  │  News    │ │Technical │             │
│  │ Analyst  │ │ Analyst  │             │
│  └────┬─────┘ └────┬─────┘             │
└───────┼─────────────┼──────────────────┘
        ↓             ↓
┌─────────────────────────────────────────┐
│  Phase 2: Research Debate               │
│  Bull Researcher ←→ Bear Researcher     │
│  (多輪辯論，可配置輪數)                    │
│         ↓                               │
│  Research Manager (綜合雙方觀點)          │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  Phase 3: Trading Decision              │
│  Trader Agent (生成交易計畫)              │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│  Phase 4: Risk Debate                   │
│  Aggressive ←→ Conservative ←→ Neutral │
│  (三方辯論)                              │
│         ↓                               │
│  Risk Manager → Portfolio Manager       │
│         ↓                               │
│  最終 Signal (買/賣/持有 + 倉位)          │
└─────────────────────────────────────────┘
```

### 1.2 編排技術

- **LangGraph StateGraph**：用狀態圖定義 agent 間的數據流和控制流
- **條件邊（Conditional Edges）**：根據狀態決定下一個節點
- **ToolNode**：LangChain 工具節點，自動處理工具調用
- **並行執行**：4 個 analyst 可並行運行

---

## 2. LLM 策略

### 2.1 雙層模型

```python
# 配置
deep_thinking_llm = ChatOpenAI(model="o4-mini")    # 深度推理
quick_thinking_llm = ChatOpenAI(model="gpt-4o-mini") # 快速回應
```

- **deep_thinking**：用於研究辯論、風險評估等需要深度推理的場景
- **quick_thinking**：用於格式化、摘要等簡單任務
- 可配置 LLM provider（OpenAI、Anthropic 等）

### 2.2 對比我們的方案

| 面向 | TradingAgents | Quant-Autoresearch V2 |
|------|--------------|----------------------|
| 模型數量 | 2 層（deep + quick） | 1 個 frontier model |
| 成本控制 | 按任務分派 | 全部用同一模型 |
| 依賴 | OpenAI API | Claude Code / Codex |

---

## 3. 記憶系統

### 3.1 ChromaDB 向量記憶

```python
# 每個 agent 有獨立的 ChromaDB collection
episodic_memory = ChromaDB(
    collection_name=f"{agent_name}_memory",
    embedding_function=OpenAIEmbeddings()
)
```

- **Episodic Memory**：每個 agent 的歷史決策存入向量數據庫
- **語義搜尋**：用 embedding 相似度檢索相關歷史經驗
- **Per-Agent 隔離**：不同 agent 的記憶互不干擾

### 3.2 對比我們的方案

| 面向 | TradingAgents | Quant-Autoresearch V2 |
|------|--------------|----------------------|
| 儲存 | ChromaDB（向量） | Obsidian（Markdown） |
| 搜尋 | Embedding 相似度 | 全文搜尋 / 人類瀏覽 |
| 隔離 | Per-agent collection | 全域筆記 |
| 人類可讀 | 否（向量） | 是（Markdown） |
| 依賴 | ChromaDB + OpenAI | 無額外依賴 |

---

## 4. 數據層

### 4.1 Vendor Routing

```python
# 自動 fallback 的數據源路由
data_sources = {
    "yfinance": yfinance_source,       # 主要
    "alpha_vantage": alpha_vantage,     # 備用
}
```

- 多數據源自動切換
- Look-ahead bias 防護：在數據獲取層過濾到 `curr_date`
- 支持基本面、技術面、新聞、情緒等多維度數據

### 4.2 對比我們的方案

| 面向 | TradingAgents | Quant-Autoresearch V2 |
|------|--------------|----------------------|
| 數據源 | yfinance + Alpha Vantage | 本地 massive-minute-aggs |
| 數據類型 | 日線 + 新聞 + 情緒 | 分鐘級 OHLCV |
| Look-ahead 防護 | 數據獲取層 | AST 安全檢查 + shift(1) |
| 延遲 | 即時 API | 本地查詢（更快） |

---

## 5. 工具增強（Tool-Augmented Analysts）

### 5.1 LangChain @tool 註解

```python
@tool
def get_fundamentals(ticker: str, date: str) -> str:
    """Get fundamental data for a stock."""
    ...

@tool
def get_technical_indicators(ticker: str, date: str) -> str:
    """Get technical indicators for a stock."""
    ...
```

- 每個 analyst 有專門的工具集
- LangGraph ToolNode 自動處理工具調用循環
- 工具結果注入 agent 的上下文

### 5.2 對比我們的方案

| 面向 | TradingAgents | Quant-Autoresearch V2 |
|------|--------------|----------------------|
| 工具定義 | LangChain @tool | Codex skills / CLI 命令 |
| 工具分派 | LangGraph 按節點 | program.md 指引 |
| 可擴展性 | 新增 @tool 即可 | 新增 skill / CLI 命令 |

---

## 6. 值得借鑑的設計模式

### 6.1 辯論機制（Bull vs Bear）

**核心思想**：強制考慮反面觀點，避免確認偏誤。

- Bull Researcher 找支持買入的理由
- Bear Researcher 找反對買入的理由
- Research Manager 綜合兩方觀點做決策

**對我們的啟發**：可以在 Obsidian 實驗筆記模板中加入「反面論證」欄位，要求 agent 記錄「為什麼這個策略可能失敗」。

### 6.2 多輪辯論配置

```python
# 可配置辯論輪數
debate_rounds = config.get("debate_rounds", 3)
```

**對我們的啟發**：研究深度可配置 — 可以設計淺度研究（快速實驗）和深度研究（關鍵決策前）兩種模式。

### 6.3 結構化輸出（Pydantic）

每個 agent 的輸出都是 Pydantic model，保證介面一致性。

**對我們的啟發**：實驗筆記的格式可以更結構化，方便 agent 解析歷史實驗。

### 6.4 工具專門化

不同 analyst 使用不同工具集，避免工具氾濫。

**對我們的啟發**：研究 skills 可以按用途分類 — 過擬合防禦工具、市場結構研究工具、策略驗證工具等。

---

## 7. 不需要借鑑的部分

| 項目 | 原因 |
|------|------|
| LangGraph 依賴 | 增加複雜度，我們的 program.md 更簡潔 |
| 多 agent 協作 | 我們是策略演化，不是投資決策管道 |
| ChromaDB 向量記憶 | Obsidian 更輕量且人類可讀 |
| 無回測引擎 | 回測是我們的核心價值，他們不涉及 |
| OpenAI 依賴 | 我們用 Claude Code，不綁定特定 API |
| 新聞/情緒數據 | 我們的策略基於 OHLCV，不需要另類數據 |

---

## 8. 對 Session 4 的啟發

基於以上研究，Session 4 研究能力設計可以考慮：

1. **結構化實驗筆記**：借鑑 Pydantic 結構化輸出，設計固定格式的 Obsidian 筆記模板
2. **反面論證欄位**：借鑑 Bull/Bear 辯論，要求 agent 記錄策略可能失敗的原因
3. **研究深度分級**：借鑑可配置辯論輪數，設計淺度/深度兩種研究模式
4. **工具分類**：借鑑工具專門化，按用途組織研究 skills
5. **保持簡潔**：避免 LangGraph 級別的框架複雜度，用 program.md 指引即可

---

## 學術參考

- TradingAgents: https://github.com/tauricresearch/tradingagents
- LangGraph: https://github.com/langchain-ai/langgraph
- 相關論文：TradingAgents: Multi-Agents LLM Financial Trading Framework (2025)
