# Sprint 1 — Backend Plan

> Feature: `v2-cleanup`
> Role: Backend
> Derived from: #2 (移除 engine.py 和 context/) + #3 (移除 safety guard 和 tool registry)
> Last Updated: 2026-04-02

## 0) Governing Specs

1. `docs/upgrade-plan-v2.md` — V2 升級設計（第 607-610 行）
2. `docs/feature/v2-cleanup/v2-cleanup-development-plan.md` — Section "Core framework" + "Safety & Tools"

## 1) Sprint Mission

移除 V1 的核心 Python 控制框架：6-Phase OPENDEV engine loop、context 管理模組（compactor + composer）、safety guard 五層防禦系統、以及 tool registry（LazyToolRegistry + BM25 search）。這些功能在 V2 中分別由 program.md 驅動的 Claude Code agent 和 backtester 沙箱取代。

## 2) Scope / Out of Scope

**Scope**
- Delete `src/core/engine.py`
- Delete `src/context/` entire directory (3 files + `__init__.py`)
- Delete `src/safety/guard.py`
- Delete `src/tools/registry.py`
- Delete `src/tools/bm25_search.py`
- Clean up `src/safety/__init__.py` and `src/tools/__init__.py`
- Clean all imports referencing removed classes in surviving files

**Out of Scope**
- `src/models/router.py` + `src/utils/token_counter.py` — Sprint 2
- `src/prompts/` cleanup — Sprint 2
- Test file deletion — Sprint 3
- `pyproject.toml` dependency removal — Sprint 3

## 3) Step-by-Step Plan

### Step 1 — Create feature branch + baseline
- [x] `git checkout -b feature/v2-cleanup main`
- [x] Run `pytest --tb=short -q` and record test count as baseline
- [x] Record baseline: `38 tests collected, 9 collection errors (all GROQ_API_KEY or module-import related)`

### Step 2 — Remove engine.py (#2 CORE-02)
- [x] `git rm src/core/engine.py`
- [x] Search for references: `grep -rn "QuantAutoresearchEngine\|from src.core.engine" src/ tests/ cli.py`
- [x] Clean any imports found in surviving files (cli.py updated)
- [x] Verify: `grep -rn "QuantAutoresearchEngine" src/ cli.py` returns 0 hits

### Step 3 — Remove context/ directory (#2 CORE-03)
- [x] `git rm -r src/context/`
- [x] Search for references: `grep -rn "ContextCompactor\|PromptComposer\|from src.context" src/ tests/ cli.py`
- [x] Clean any imports found in surviving files (cli.py updated)
- [x] Verify: `grep -rn "ContextCompactor\|PromptComposer" src/ cli.py` returns 0 hits

### Step 4 — Remove safety guard (#3 SAFE-01)
- [x] `git rm src/safety/guard.py`
- [x] Search for references: `grep -rn "SafetyGuard\|from src.safety.guard" src/ tests/ cli.py`
- [x] Clean any imports found in surviving files (cli.py updated)
- [x] Verify: `grep -rn "SafetyGuard" src/ cli.py` returns 0 hits

### Step 5 — Remove tool registry + bm25 (#3 TOOL-01, TOOL-02)
- [x] `git rm src/tools/registry.py`
- [x] `git rm src/tools/bm25_search.py`
- [x] Search for references: `grep -rn "LazyToolRegistry\|BM25Search\|from src.tools.registry\|from src.tools.bm25" src/ tests/ cli.py`
- [x] Clean any imports found in surviving files (cli.py updated)
- [x] Verify: `grep -rn "LazyToolRegistry\|BM25Search" src/ cli.py` returns 0 hits

### Step 6 — Clean up empty directories (#3 TOOL-03)
- [x] Check if `src/safety/` only has `__init__.py`: `ls src/safety/`
- [x] If only `__init__.py` remains: `git rm src/safety/__init__.py && rmdir src/safety/`
- [x] Check if `src/tools/` only has `__init__.py`: `ls src/tools/`
- [x] If only `__init__.py` remains: `git rm src/tools/__init__.py && rmdir src/tools/`

### Step 7 — Commit sprint 1 changes
- [x] `git add -A && git commit -m "refactor(v2): remove engine, context, safety guard, and tool registry"`

## 4) Test Plan

- [x] After Step 2-3: verify `python -c "from src.core.backtester import *"` still works
- [x] After Step 4-5: verify `python -c "from src.strategies.active_strategy import TradingStrategy"` still works
- [x] After Step 6: verify no surviving file can import removed modules:
  ```bash
  grep -rn "QuantAutoresearchEngine\|ContextCompactor\|PromptComposer\|SafetyGuard\|LazyToolRegistry\|BM25Search" src/ cli.py || echo "CLEAN"
  ```

## 5) Verification Commands

```bash
# Confirm files are deleted
test ! -f src/core/engine.py && echo "engine.py GONE"
test ! -d src/context && echo "context/ GONE"
test ! -f src/safety/guard.py && echo "guard.py GONE"
test ! -f src/tools/registry.py && echo "registry.py GONE"
test ! -f src/tools/bm25_search.py && echo "bm25_search.py GONE"

# Import cleanliness
grep -rn "QuantAutoresearchEngine\|ContextCompactor\|PromptComposer\|SafetyGuard\|LazyToolRegistry\|BM25Search" src/ cli.py || echo "ALL CLEAN"

# Surviving modules still work
python -c "from src.core.backtester import *; from src.strategies.active_strategy import *; print('SURVIVORS OK')"
```

## 6) Implementation Update Space

### Completed Work

- All 7 steps completed and committed (f7b4dcf refactor, 1d8f548 docs; rebased onto fork/main)
- Deleted 9 files: engine.py, context/{__init__,compactor,composer}.py, safety/{__init__,guard}.py, tools/{__init__,registry,bm25_search}.py
- Updated cli.py: removed all imports of deleted modules, preserved working commands (fetch, ingest, setup_data, research), stubbed V1-dependent commands (run, status, report, test)
- 38 surviving tests pass; 13 test files have collection errors referencing deleted modules (Sprint 3 targets)

### Command Results

- Baseline: 9 collection errors (GROQ_API_KEY / module import)
- Post-deletion: 38 tests pass, 13 collection errors (expected — Sprint 3 cleanup targets)
- Import scan: `grep -rn "QuantAutoresearchEngine|ContextCompactor|PromptComposer|SafetyGuard|LazyToolRegistry|BM25Search" src/ cli.py` → CLEAN

### Blockers / Deviations

- Worktree created from HEAD (16636a8) instead of fork/main (8d6297d); rebased onto fork/main after commit to include docs
- `experiments/logs/` dir missing in worktree; created manually before baseline run
- No `.env` file with `GROQ_API_KEY` — baseline tests can't instantiate ModelRouter (Sprint 2 target anyway)

### Follow-ups

- Sprint 2: remove models/router.py, utils/token_counter.py, clean prompts/
- Sprint 3: delete 12-13 broken test files, update conftest.py, remove groq/tiktoken deps
