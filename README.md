# Quant Autoresearch

**Quant Autoresearch** is an institutional-grade, autonomous framework for quantitative strategy discovery. Adapted from the Karpathy's `autoresearch` philosophy https://github.com/karpathy/autoresearch and engineered with the **OPENDEV** terminal-agent architecture, it treats the search for alpha as a **long-horizon code evolution problem**.

Unlike traditional backtesters that require manual hypothesis testing, Quant Autoresearch deploys a **compound AI system** where specialized sub-agents iterate on strategy logic, grounded in academic literature and real-time market data, while humans define only the constraints (the "Constitution").

> **Core Philosophy:** The human defines the *goals* and *risk guardrails*. The AI acts as the *Quantitative Researcher*, formulating hypotheses, reading academic papers, editing code, and validating against a secure, immutable truth engine.

---

## 🏗️ Architecture: The OPENDEV Paradigm

Quant Autoresearch moves beyond simple loops to a robust, multi-layered agent harness designed for long-horizon autonomy.

### 1. The Constitution (`program.md`)
The single source of truth for behavioral constraints. It defines the investment mandate, risk limits (e.g., "Max Drawdown < 20%"), and ethical boundaries. The agent cannot override these rules; they are injected dynamically at every reasoning step.

### 2. The Knowledge Core (BM25 + ArXiv)
Powered by **`bm25s`** for sub-10ms lexical retrieval. Before writing code, agents query a local index of thousands of quantitative finance papers (`q-fin.*` from ArXiv). This grounds strategy generation in proven academic theory rather than LLM hallucination.
*   *Feature:* Agentic Search – The agent decides *when* to retrieve knowledge based on the task context.

### 3. The Data Fabric (CCXT + Polygon + FRED)
A unified, lazy-loading data layer replacing fragile scrapers.
*   **Crypto:** Direct exchange integration via **`ccxt`** (Binance, Kraken, etc.) for high-frequency OHLCV, funding rates, and order book snapshots.
*   **Equities/Macro:** Integration with **Polygon.io** (free tier) and **FRED** for regime filtering (e.g., "Only trade momentum when Yield Curve > 0").
*   **Integrity:** All data is cached locally in Parquet format with strict look-ahead bias prevention.

### 4. The Truth Engine (`backtest_runner.py`)
An immutable, sandboxed execution environment implementing **Defense-in-Depth Safety**:
*   **Walk-Forward Validation:** Rolling 70/30 train/test windows to prevent overfitting.
*   **Forced Signal Lag:** Automatically shifts all agent signals by 1 bar to eliminate look-ahead bias.
*   **Dynamic Slippage:** Transaction costs scale with volatility to prevent "free money" exploits in choppy markets.
*   **Security Scanner:** Regex-based pre-execution checks block forbidden patterns (`eval`, `shift(-1)`, network calls).

### 5. The Agent Harness (Extended ReAct Loop)
Built on the **OPENDEV** reference architecture:
*   **Multi-Model Routing:** Uses expensive models (Claude 3.5 Sonnet) for complex reasoning and cheap models (Haiku) for summarization/context compaction.
*   **Adaptive Context Compaction (ACC):** Monitors token pressure and progressively prunes/masks old observations to sustain overnight runs without context overflow.
*   **System Reminders:** Event-driven nudges injected at decision points to counteract "instruction fade-out" during long sessions.
*   **Doom-Loop Detection:** Fingerprint-based detection halts the agent if it repeats the same failed action 3 times.

---

## 🚀 Quick Start

### Prerequisites
*   Python 3.10+
*   `uv` package manager recommended
*   API Keys: Anthropic (for Agent), optional CCXT/Polygon for live data

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/quant-autoresearch.git
cd quant-autoresearch

# Install dependencies
uv sync
```

### 2. Initialize the Environment
Sets up the local SQLite database, downloads the initial ArXiv corpus, and builds the BM25 index.
```bash
quant-research init --download-papers
```

### 3. Populate Market Data
Fetches historical data from CCXT and Polygon. Runs once to cache data locally.
```bash
quant-research ingest crypto --symbols BTC,ETH,SOL --days 365
quant-research ingest equities --symbols SPY,QQQ --days 365
```

### 4. Launch the Autonomous Loop
Starts the agent with adaptive context management and safety guards enabled.
```bash
# Run for 4 hours or 100 iterations (whichever comes first)
quant-research run --duration 240 --max-iters 100 --model claude-3-5-sonnet

# Advanced: Enable "Thinking Mode" for deeper deliberation before coding
quant-research run --thinking-level HIGH --critique-model haiku
```

### 5. Analyze Results
Generates a dashboard of the evolution frontier, risk/reward scatter plots, and kept strategies.
```bash
quant-research report
# Or open the Jupyter notebook manually
jupyter notebook analysis.ipynb
```

---

## 🛡️ Safety & Security Model

Quant Autoresearch employs a **5-Layer Defense-in-Depth** architecture to ensure safe autonomous operation:

1.  **Prompt Guardrails:** Behavioral constraints embedded in the dynamic system prompt.
2.  **Schema Gating:** Dangerous tools (e.g., `rm`, `sudo`, `write_file` outside sandbox) are removed from the agent's schema entirely during planning phases.
3.  **Runtime Approval:** Configurable trust levels (Manual/Semi-Auto/Auto) for high-risk actions.
4.  **Tool Validation:** Argument sanitization and stale-read detection before execution.
5.  **Lifecycle Hooks:** External scripts can intercept `PreToolUse` events to enforce project-specific policies.

---

## 📊 Key Features

| Feature | Description |
| :--- | :--- |
| **Agentic RAG** | Uses `bm25s` to retrieve specific mathematical formulations from ArXiv papers before coding. |
| **Context Engineering** | Adaptive compaction keeps sessions alive indefinitely by masking old tool outputs. |
| **Multi-Asset Support** | Unified interface for Crypto (CCXT), Equities (Polygon), and Macro (FRED). |
| **Dual-Memory** | Separates episodic memory (session summary) from working memory (recent steps) for bounded thinking. |
| **Shadow Git** | Automatic per-step undo capability via shadow git snapshots, independent of your main repo. |
| **CLI Native** | Full control via terminal slash-commands (`/undo`, `/compact`, `/mode plan`). |

---

## 🧠 Under the Hood

This project implements the architectural patterns described in **"Building AI Coding Agents for the Terminal" (OPENDEV, arXiv:2603.05344)**:
*   **Compound AI System:** Not a single model, but a routed ensemble of specialists.
*   **Extended ReAct Loop:** Explicit Thinking → Critique → Action phases.
*   **Lazy Tool Discovery:** Tools are loaded on-demand via keyword search to save context tokens.
*   **Event-Driven Reminders:** Counteracts attention decay in long-horizon tasks.

---

## 📄 License

MIT License. Designed for research and educational purposes.
*Disclaimer: This software is for experimental use only. Do not deploy evolved strategies to live capital without rigorous manual review and out-of-sample validation.*
