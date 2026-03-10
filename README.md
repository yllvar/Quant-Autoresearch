# 📊 Quant Autoresearch: Autonomous Strategy Discovery

<img width="2752" height="1536" alt="Quant Autoresearch Header" src="https://github.com/user-attachments/assets/5e84b668-c81f-4c41-bd0a-f4db95846b0d" />

**Quant Autoresearch** is an autonomous framework for quantitative strategy discovery. Based on the **OPENDEV** terminal-agent architecture, it treats alpha generation as a long-horizon **code evolution problem**.

Unlike traditional backtesters, this system deploys a compound AI ensemble that formulates hypotheses, analyzes academic literature (ArXiv), writes Python code, and validates performance in a secure, sandboxed environment.

---

## 🏗️ Core Architecture

### 1. The Constitution (`src/prompts/program.md`)
Defines immutable behavioral constraints, risk limits (e.g., "Max Drawdown < 20%"), and the investment mandate. These rules are injected into every reasoning step.

### 2. Knowledge Core (Agentic RAG)
Powered by `bm25s` for high-speed retrieval of quantitative finance papers. The agent decides when to "read" academic theory to ground its code generation in proven science rather than LLM hallucination.

### 3. Truth Engine (`src/core/backtester.py`)
A sandboxed validation layer implementing strict **Defense-in-Depth Safety**:
*   **Walk-Forward Validation:** Prevents overfitting via rolling out-of-sample windows.
*   **Forced Signal Lag:** Eliminates look-ahead bias by shifting signals by 1 bar.
*   **Volatility-Adjusted Slippage:** Models realistic market impact during choppy regimes.
*   **RestrictedPython Sandboxing:** Executes AI strategies in a hardened, non-virtualized sandbox. It strips all standard `import` statements and provides only `pd` and `np` in a safe global namespace, blocking access to `os`, `sys`, and other sensitive built-ins.

### 4. Adaptive Context Compaction (ACC)
Ensures long-horizon autonomy by monitoring token pressure and automatically pruning or summarizing old observations to prevent context overflow.

---

## 📂 Project Structure

```text
├── cli.py              # Main entry point (CLI)
├── src/
│   ├── core/           # Engine logic, research RAG, and backtester
│   ├── strategies/     # AI-evolved strategies (active_strategy.py)
│   ├── safety/         # 5-layer safety guardrails
│   ├── models/         # Multi-provider LLM routing (Groq, Moonshot)
│   ├── memory/         # SQLite-based pattern playbook
│   ├── tools/          # Tool registry and execution
│   └── prompts/        # System instructions & "The Constitution"
├── data/cache/         # Local Parquet market data files
└── experiments/        # Results, logs, and SQLite databases
```

---

## 🚀 Quick Start

### 1. Installation
Requires **Python 3.10+** and the **`uv`** package manager.

```bash
# Clone the repository
git clone https://github.com/yllvar/quant-autoresearch.git
cd quant-autoresearch

# Install dependencies using uv
uv sync
```

### 2. Configuration
Create a `.env` file with your API keys:
```env
GROQ_API_KEY=your_key_here
MOONSHOT_API_KEY=your_key_here
WANDB_API_KEY=your_key_here
WANDB_PROJECT=quant-autoresearch
```

### 3. Initialize & Ingest Data
```bash
# Fetch and index market data (SPY, QQQ, BTC, ETH)
python src/data/preprocessor.py
```

### 4. Run the Research Loop
Start the autonomous discovery process:
```bash
# Run for 10 iterations with high safety
python cli.py run --iterations 10 --safety high --approval semi
```

### 5. Check Status & Reports
```bash
python cli.py status
python cli.py report
```

---

## 🛡️ Safety & Security
This project uses a **5-Layer Defense-in-Depth** system:
1.  **Prompt Guardrails:** Behavioral constraints in system prompts.
2.  **Schema Gating:** Dangerous tools are hidden from non-executor subagents.
3.  **Runtime Approval:** "Semi-Auto" mode for high-risk operations.
4.  **Tool Validation:** Argument sanitization before execution.
5.  **Look-Ahead Scanner:** AST-based code analysis to block `shift(-1)` or future data leaks.

---

## 📊 Performance Tracking
Integration with **Weights & Biases (W&B)** provides real-time telemetry of:
*   Strategy Evolution (Sharpe Ratio improvement over time).
*   Token Usage & API Cost.
*   Agent Reasoning Traces and Tool Success Rates.

---

## 📄 License
MIT License. **Disclaimer:** This software is for research purposes only. Do not deploy evolved strategies to live capital without exhaustive manual review.
