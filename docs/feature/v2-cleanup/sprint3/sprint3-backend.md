# Sprint 3 — Backend Plan

> Feature: `v2-cleanup`
> Role: Backend
> Derived from: #6 (移除舊架構相關測試) + #7 (更新 pyproject.toml 依賴)
> Last Updated: 2026-04-02

## 0) Governing Specs

1. `docs/upgrade-plan-v2.md` — V2 升級設計（第 614-615 行）
2. `docs/feature/v2-cleanup/v2-cleanup-development-plan.md` — Section "Tests" + "Dependencies to remove"
3. `docs/feature/v2-cleanup/v2-cleanup-test-plan.md` — Full test removal matrix

## 1) Sprint Mission

移除所有對應已刪除模組的測試文件，清理 conftest.py，更新 pyproject.toml 移除不再需要的依賴，並執行最終驗證確保整個 codebase 乾淨可運行。這是 V2 cleanup 的最後一道關卡。

## 2) Scope / Out of Scope

**Scope**
- Delete 12 test files for removed modules
- Evaluate 3 borderline test files (keep/clean/delete)
- Clean `tests/conftest.py` of fixtures for removed modules
- Remove `groq` from pyproject.toml
- Remove `tiktoken` from pyproject.toml
- Evaluate `openai` dependency (keep or remove)
- Global grep for all removed module imports in surviving files
- Final verification: `uv sync` + `pytest` + CLI

**Out of Scope**
- Writing new V2 tests
- Any code changes beyond import cleanup and dep removal
- `CLAUDE.md` update — Phase 4

## 3) Step-by-Step Plan

### Step 1 — Delete unit test files (#6 TEST-01)
- [ ] `git rm tests/unit/test_engine_opendev.py`
- [ ] `git rm tests/unit/test_guard_opendev.py`
- [ ] `git rm tests/unit/test_tool_registry.py`
- [ ] `git rm tests/unit/test_router_routing.py`
- [ ] `git rm tests/unit/test_compactor_acc.py`
- [ ] `git rm tests/unit/test_compactor_logic.py`
- [ ] `git rm tests/unit/test_composer_modular.py`
- [ ] `git rm tests/unit/test_bm25_tool.py`

### Step 2 — Delete integration/regression test files (#6 TEST-02)
- [ ] `git rm tests/integration/test_engine_integration.py`
- [ ] `git rm tests/integration/test_loop.py`
- [ ] `git rm tests/regression/test_engine_arity.py`
- [ ] `git rm tests/regression/test_editable_region.py`

### Step 3 — Evaluate borderline test files (#6 TEST-04)
- [ ] Check `tests/security/test_safety_workflow.py` for SafetyGuard references:
  ```bash
  grep -n "SafetyGuard\|from src.safety" tests/security/test_safety_workflow.py
  ```
  - If references found → clean imports or delete entire file
  - If no references → keep
  - Decision: `_____`
- [ ] Check `tests/unit/test_runner.py` for engine references:
  ```bash
  grep -n "engine\|QuantAutoresearchEngine\|from src.core.engine" tests/unit/test_runner.py
  ```
  - If references found → clean imports or delete entire file
  - If no references → keep
  - Decision: `_____`
- [ ] Check `tests/regression/test_determinism.py` for removed module references:
  ```bash
  grep -n "engine\|router\|guard\|compactor\|composer\|registry\|token_counter\|bm25" tests/regression/test_determinism.py
  ```
  - If references found → clean imports or delete entire file
  - If no references → keep
  - Decision: `_____`

### Step 4 — Clean conftest.py (#6 TEST-03)
- [ ] `grep -n "engine\|guard\|router\|compactor\|composer\|registry\|token_counter\|bm25" tests/conftest.py`
- [ ] Remove or comment out any fixtures referencing deleted modules
- [ ] Verify: `python -c "import tests.conftest"` or `pytest --collect-only -q` succeeds

### Step 5 — Global import scan (#6 TEST-05)
- [ ] Run full scan of all surviving files:
  ```bash
  grep -rn "from src.core.engine\|from src.context\|from src.safety.guard\|from src.tools.registry\|from src.tools.bm25\|from src.models.router\|from src.utils.token_counter\|QuantAutoresearchEngine\|ContextCompactor\|PromptComposer\|SafetyGuard\|LazyToolRegistry\|ModelRouter\|BM25Search\|token_counter\|model_router" src/ tests/ cli.py
  ```
- [ ] If any hits found → fix the import in that file
- [ ] Verify: grep returns 0 hits

### Step 6 — Commit test cleanup
- [ ] `git add -A && git commit -m "refactor(v2): remove old architecture tests and clean conftest"`

### Step 7 — Evaluate openai dependency (#7 DEP-01)
- [ ] Check if any surviving file uses `openai`:
  ```bash
  grep -rn "import openai\|from openai" src/ cli.py
  ```
- [ ] If used by research.py or other surviving code → KEEP, add comment in pyproject.toml
- [ ] If only used by deleted router.py → SAFE TO REMOVE
- [ ] Decision: `_____ (remove / keep because _____)`

### Step 8 — Update pyproject.toml (#7 DEP-02)
- [ ] Remove `groq>=0.4.0` line
- [ ] Remove `tiktoken>=0.5.0` line
- [ ] If DEP-01 decided to remove: remove `openai>=2.26.0` line
- [ ] Verify pyproject.toml is valid: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`

### Step 9 — Install and verify (#7 DEP-03, DEP-04)
- [ ] Run `uv sync --all-extras --dev`
- [ ] Record result: `_____ (success / error: _____)`
- [ ] Run `pytest --tb=short -v`
- [ ] Record result: `_____ tests, _____ passed, _____ failed, _____ errors`
- [ ] Run `uv run python cli.py status`
- [ ] Record result: `_____ (success / error: _____)`

### Step 10 — Commit dependency changes
- [ ] `git add -A && git commit -m "refactor(v2): remove unused dependencies from pyproject.toml"`

### Step 11 — Push feature branch
- [ ] `git push fork feature/v2-cleanup`
- [ ] Record: branch pushed, all sprints complete

## 4) Test Plan

- [ ] After Step 1-4: `pytest --collect-only -q` — all remaining tests can be collected
- [ ] After Step 5: global grep returns 0 hits for removed modules
- [ ] After Step 8: `uv sync` succeeds without errors
- [ ] After Step 9: `pytest` passes with 0 failures
- [ ] After Step 9: `cli.py status` runs without import errors

## 5) Verification Commands (Final Gate)

```bash
# Dependency sync
uv sync --all-extras --dev && echo "DEPS OK"

# Full import check of all surviving modules
python -c "
from src.core.backtester import *
from src.core.research import *
from src.data.connector import *
from src.memory.playbook import *
from src.strategies.active_strategy import *
from src.utils.logger import logger
from src.utils.telemetry import telemetry
from src.utils.iteration_tracker import iteration_tracker
from src.utils.retries import retry_with_backoff
print('ALL IMPORTS OK')
"

# Test suite
pytest --tb=short -v

# CLI
uv run python cli.py status

# No removed module references anywhere
grep -rn "QuantAutoresearchEngine\|ContextCompactor\|PromptComposer\|SafetyGuard\|LazyToolRegistry\|ModelRouter\|BM25Search\|token_counter\|model_router\|from src.core.engine\|from src.context\|from src.safety.guard\|from src.tools.registry\|from src.tools.bm25\|from src.models.router\|from src.utils.token_counter" src/ tests/ cli.py || echo "ZERO REFERENCES TO REMOVED MODULES"
```

## 6) Implementation Update Space

### Completed Work

- (leave blank until implemented)

### Command Results

- (leave blank until implemented)

### Blockers / Deviations

- (leave blank until implemented)

### Follow-ups

- (leave blank until implemented)
