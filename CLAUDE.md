# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quant Autoresearch is an autonomous quantitative strategy discovery framework. It deploys a compound AI ensemble (OPENDEV architecture) that formulates hypotheses, searches ArXiv literature, writes Python trading strategy code, and validates performance in a sandboxed environment. The system runs a 6-phase autonomous research loop treating alpha generation as a long-horizon code evolution problem.

## Commands

### Install & Run

```bash
uv sync                              # Install all dependencies
uv sync --all-extras --dev           # Install with dev dependencies
uv run python cli.py run --iterations 10 --safety high --approval semi  # Run research loop
uv run python cli.py setup_data      # Download default market data (SPY, QQQ, IWM, BTC, ETH)
uv run python cli.py fetch SPY --start 2020-01-01  # Fetch specific symbol
uv run python cli.py status          # Check system status
uv run python cli.py report          # Generate performance report
```

### Testing

```bash
pytest                                          # Run all tests
pytest tests/unit/test_engine_opendev.py         # Run single test file
pytest tests/unit/test_engine_opendev.py::test_engine_initialization  # Run single test
pytest --cov=src --cov-report=term-missing       # Run with coverage
pytest tests/unit/                               # Run unit tests only
pytest tests/integration/                        # Run integration tests only
pytest tests/security/                           # Run security tests only
pytest tests/regression/                         # Run regression tests only
```

Test config is in `pytest.ini`: `asyncio_mode = auto`, `pythonpath = src`, `testpaths = tests`. Shared fixtures are in `tests/conftest.py`.

## Architecture

### 6-Phase OPENDEV Loop (`src/core/engine.py`)

The engine runs an enhanced ReAct loop:

1. **Phase 0 - Context Management (ACC)**: `ContextCompactor` (`src/context/compactor.py`) monitors token usage. At 70% warning, 80% mask old outputs, 90% aggressive pruning, 99% LLM summarization.
2. **Phase 1 - Thinking**: A reasoning model generates a reasoning trace without tool access (prevents action-first hallucinations).
3. **Phase 2 - Action Selection**: Primary model reviews reasoning trace, selects tools from `LazyToolRegistry` (`src/tools/registry.py`), produces JSON tool calls. Prompts assembled by `PromptComposer` (`src/context/composer.py`).
4. **Phase 3 - Doom-Loop Detection**: Fingerprints planned actions. If same action repeats 3+ times in 20-operation window, execution pauses.
5. **Phase 4 - Execution**: Tools execute through 5-layer safety system. Results >8k chars auto-masked.
6. **Phase 5 - Observation**: Results logged. Successful strategies (improved Sharpe) stored in `Playbook`. Failed strategies trigger code reversion.

Loop terminates when OOS Sharpe > 2.0 or max iterations reached.

### Key Components

- **`src/core/engine.py`** - `QuantAutoresearchEngine`: central orchestrator
- **`src/core/backtester.py`** - Walk-forward validation with RestrictedPython sandbox, Monte Carlo permutation test, AST analysis blocks `shift(-1)` and dangerous builtins
- **`src/core/research.py`** - ArXiv search + BM25 local paper retrieval + web search (Exa/SerpAPI)
- **`src/safety/guard.py`** - `SafetyGuard`: 5-layer defense-in-depth (prompt guardrails, schema gating, runtime approval, tool validation, lifecycle hooks)
- **`src/models/router.py`** - `ModelRouter`: multi-provider LLM routing (Groq, Moonshot/OpenAI-compatible) with fallback, cost tracking, retry with backoff
- **`src/memory/playbook.py`** - `Playbook`: SQLite-based episodic memory with TF-IDF similarity search
- **`src/data/connector.py`** - `DataConnector`: unified market data (yfinance for equities, CCXT/Binance for crypto, Parquet/CSV cache)
- **`src/strategies/active_strategy.py`** - The strategy file the AI agent evolves. Only the `EDITABLE REGION` section is modified. `TradingStrategy` class.

### Critical Patterns

- **Strategy Evolution**: The AI modifies ONLY the `# --- EDITABLE REGION BREAK ---` to `# --- EDITABLE REGION END ---` section in `active_strategy.py`. The backtester runs this in a RestrictedPython sandbox with only `pd` and `np` available.
- **Walk-Forward Validation**: 5 rolling OOS windows (70/30 train/test) with forced signal lag, volatility-adjusted slippage, Monte Carlo permutation testing.
- **Model Router**: Routes by phase to different LLM providers with automatic fallback. Global singleton `model_router`.
- **Lazy Tool Discovery**: Tools loaded into context only when needed, saving context window space.
- **Global Singletons**: `model_router`, `telemetry`, `iteration_tracker`, `token_counter`, `logger` are module-level singletons.
- **Prompt Composition**: `PromptComposer` assembles modular prompts from sections in `src/prompts/` (identity, safety, tools, quant rules, git rules) with dynamic system reminders.

### Immutable Constraints

`src/prompts/program.md` ("The Constitution") defines behavioral constraints, risk limits (e.g., max drawdown < 20%), and investment mandate injected into every reasoning step.

## Environment Variables

Required in `.env`:
- `GROQ_API_KEY` - Groq LLM API (required)
- `MOONSHOT_API_KEY` - Moonshot API (optional, enables Moonshot models)
- `WANDB_API_KEY` / `WANDB_PROJECT` - W&B telemetry (optional)
- `EXA_API_KEY` or `SERPAPI_KEY` - Web search (optional)
- `THINKING_MODEL` / `REASONING_MODEL` - Override default model choices (optional)

## Code Style

- Python 3.10+ syntax (project uses 3.12.0), lines under 120 chars, 4-space indent
- Import order: stdlib -> third-party -> local (alphabetical within groups)
- Type hints on all function signatures (`from typing import Dict, List, Optional, Tuple, Any`)
- Google-style docstrings
- `PascalCase` classes, `snake_case` functions/variables, `UPPER_SNAKE_CASE` constants
- Private methods prefixed with underscore
- Async/await for I/O-bound operations, `asyncio.run()` at entry points

## Data & Cache

- `data/cache/` (Parquet files) is gitignored. Run `uv run python cli.py setup_data` to populate.
- `experiments/` (logs, results, databases) is gitignored. Logs rotate at 10MB with 5 backups in `experiments/logs/`.

## CI

GitHub Actions (`.github/workflows/ci.yml`): uv install -> Python 3.12 -> `uv sync --all-extras --dev` -> `pytest --cov=.` -> upload to Codecov.
