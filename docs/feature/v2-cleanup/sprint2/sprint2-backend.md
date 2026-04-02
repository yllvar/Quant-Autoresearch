# Sprint 2 — Backend Plan

> Feature: `v2-cleanup`
> Role: Backend
> Derived from: #4 (移除 model router 和 token counter) + #5 (清理 prompts 目錄)
> Last Updated: 2026-04-02

## 0) Governing Specs

1. `docs/upgrade-plan-v2.md` — V2 升級設計（第 611-613 行）
2. `docs/feature/v2-cleanup/v2-cleanup-development-plan.md` — Section "Model & Tokens" + "Prompts"

## 1) Sprint Mission

移除 V1 的 LLM 路由系統（ModelRouter + 全域 singleton）、token 計數器（TokenCounter）、以及所有 V1 prompt 文件。V2 的推理直接由 Claude Code/Codex 處理，所有指令合併到根目錄 `program.md`。

## 2) Scope / Out of Scope

**Scope**
- Delete `src/models/router.py`
- Delete `src/models/__init__.py` (if empty after router removal)
- Delete `src/utils/token_counter.py`
- Delete `src/prompts/identity.md`
- Delete `src/prompts/safety_policy.md`
- Delete `src/prompts/tool_guidance.md`
- Delete `src/prompts/quant_rules.md`
- Delete `src/prompts/git_rules.md`
- Evaluate and decide on `src/prompts/program.md` (V1 "constitution")
- Clean/remove `src/prompts/__init__.py`
- Clean all imports referencing removed classes/singletons

**Out of Scope**
- Test file deletion — Sprint 3
- `pyproject.toml` dependency removal — Sprint 3
- `openai` package decision (keep or remove from deps) — Sprint 3
- Root `program.md` creation — Phase 1 responsibility

## 3) Step-by-Step Plan

### Step 1 — Remove model router (#4 MODEL-01)
- [x] `git rm src/models/router.py`
- [x] Search for references: `grep -rn "ModelRouter\|model_router\|from src.models.router" src/ tests/ cli.py`
- [x] Clean any imports found in surviving files (none in src/ or cli.py)
- [x] Check if `src/models/` only has `__init__.py`: `ls src/models/`
- [x] If only `__init__.py`: `git rm src/models/__init__.py && rmdir src/models/`
- [x] Verify: `grep -rn "ModelRouter\|model_router" src/ cli.py` returns 0 hits

### Step 2 — Remove token counter (#4 MODEL-02)
- [x] `git rm src/utils/token_counter.py`
- [x] Search for references: `grep -rn "token_counter\|from src.utils.token_counter" src/ tests/ cli.py`
- [x] Clean any imports found in surviving files (none in src/ or cli.py)
- [x] Verify: `grep -rn "token_counter" src/ cli.py` returns 0 hits

### Step 3 — Verify surviving utils (#4 MODEL-03)
- [x] Run: `PYTHONPATH=src python -c "from utils.logger import logger; from utils.telemetry import telemetry; from utils.iteration_tracker import iteration_tracker; from utils.retries import retry_with_backoff; print('ALL UTILS OK')"`
- [x] All surviving utils import correctly

### Step 4 — Remove V1 prompt files (#5 PROMPT-01)
- [x] `git rm src/prompts/identity.md`
- [x] `git rm src/prompts/safety_policy.md`
- [x] `git rm src/prompts/tool_guidance.md`
- [x] `git rm src/prompts/quant_rules.md`
- [x] `git rm src/prompts/git_rules.md`
- [x] Verify: `ls src/prompts/` — only `__init__.py` and `program.md` remained

### Step 5 — Evaluate V1 program.md (#5 PROMPT-02)
- [x] Read `src/prompts/program.md` — V1 Constitution with multi-modal workflow
- [x] Read `docs/upgrade-plan-v2.md` — V2 specifies new program.md at root with different structure
- [x] Decision: **superseded and removed** — V1 content fundamentally different from V2 design
- [x] `git rm src/prompts/program.md`

### Step 6 — Clean prompts directory (#5 PROMPT-01 continued)
- [x] All .md files deleted: checked `src/prompts/__init__.py`
- [x] `__init__.py` only exports deleted content: `git rm src/prompts/__init__.py`
- [x] Directory removed: `src/prompts/` no longer exists
- [x] Verify: `ls src/prompts/ 2>&1` — "No such file or directory"

### Step 7 — Commit sprint 2 changes
- [x] `git commit -m "refactor(v2): remove model router, token counter, and V1 prompts"` — 20eb705

## 4) Test Plan

- [x] After Step 1-2: verify no broken imports in surviving code: CLEAN
- [x] After Step 3: verify surviving utils all import correctly: ALL IMPORTS OK
- [x] After Step 4-6: verify no surviving file references deleted prompts: prompts/ directory gone

## 5) Verification Commands

```bash
# Confirm files deleted
test ! -f src/models/router.py && echo "router.py GONE"
test ! -f src/utils/token_counter.py && echo "token_counter.py GONE"
test ! -f src/prompts/identity.md && echo "identity.md GONE"
test ! -d src/prompts && echo "prompts/ GONE" || ls src/prompts/

# Import cleanliness
grep -rn "ModelRouter\|model_router\|token_counter\|SafetyGuard\|LazyToolRegistry" src/ cli.py || echo "ALL CLEAN"

# Surviving modules
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
```

## 6) Implementation Update Space

### Completed Work

- All 7 steps completed and committed (20eb705)
- Deleted 10 files: models/{__init__,router}.py, utils/token_counter.py, prompts/{__init__,identity,safety_policy,tool_guidance,quant_rules,git_rules,program}.md
- V1 program.md evaluated and removed — fully superseded by V2 design
- Entire src/prompts/ directory removed
- Entire src/models/ directory removed
- 38 surviving tests pass; 13 test files have collection errors referencing deleted modules (Sprint 3 targets)

### Command Results

- File deletion: router.py GONE, models/ GONE, token_counter.py GONE, identity.md GONE, prompts/ GONE
- Import scan: `grep -rn "ModelRouter|model_router|token_counter" src/ cli.py` → CLEAN
- Surviving imports: `from utils.logger import logger; from utils.telemetry import telemetry; from utils.iteration_tracker import iteration_tracker; from utils.retries import retry_with_backoff` → ALL IMPORTS OK
- Tests: 38 passed in 3.15s

### Blockers / Deviations

- None

### Follow-ups

- Sprint 3: delete 13 broken test files, update conftest.py, remove groq/tiktoken deps from pyproject.toml
