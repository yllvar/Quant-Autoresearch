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
- [ ] `git rm src/models/router.py`
- [ ] Search for references: `grep -rn "ModelRouter\|model_router\|from src.models.router" src/ tests/ cli.py`
- [ ] Clean any imports found in surviving files
- [ ] Check if `src/models/` only has `__init__.py`: `ls src/models/`
- [ ] If only `__init__.py`: `git rm src/models/__init__.py && rmdir src/models/`
- [ ] Verify: `grep -rn "ModelRouter\|model_router" src/ cli.py` returns 0 hits

### Step 2 — Remove token counter (#4 MODEL-02)
- [ ] `git rm src/utils/token_counter.py`
- [ ] Search for references: `grep -rn "token_counter\|from src.utils.token_counter" src/ tests/ cli.py`
- [ ] Clean any imports found in surviving files
- [ ] Verify: `grep -rn "token_counter" src/ cli.py` returns 0 hits

### Step 3 — Verify surviving utils (#4 MODEL-03)
- [ ] Run: `python -c "from src.utils.logger import logger; from src.utils.telemetry import telemetry; from src.utils.iteration_tracker import iteration_tracker; from src.utils.retries import retry_with_backoff; print('ALL UTILS OK')"`
- [ ] If any import fails, investigate and fix the broken reference

### Step 4 — Remove V1 prompt files (#5 PROMPT-01)
- [ ] `git rm src/prompts/identity.md`
- [ ] `git rm src/prompts/safety_policy.md`
- [ ] `git rm src/prompts/tool_guidance.md`
- [ ] `git rm src/prompts/quant_rules.md`
- [ ] `git rm src/prompts/git_rules.md`
- [ ] Verify: `ls src/prompts/` — should show only `__init__.py` and possibly `program.md`

### Step 5 — Evaluate V1 program.md (#5 PROMPT-02)
- [ ] Read `src/prompts/program.md` to compare with V2 `program.md` spec in upgrade-plan-v2.md section 5
- [ ] If V1 program.md content is fully superseded by V2: `git rm src/prompts/program.md`
- [ ] If V1 has unique content not in V2 plan: note it and keep temporarily
- [ ] Decision recorded: `_____ (superseded and removed / kept for unique content: _____)`

### Step 6 — Clean prompts directory (#5 PROMPT-01 continued)
- [ ] If all .md files deleted: check `src/prompts/__init__.py`
- [ ] If `__init__.py` is empty or only exports deleted content: `git rm src/prompts/__init__.py`
- [ ] If directory is empty: `rmdir src/prompts/`
- [ ] Verify: `ls src/prompts/ 2>&1` — should show "No such file or directory"

### Step 7 — Commit sprint 2 changes
- [ ] `git add -A && git commit -m "refactor(v2): remove model router, token counter, and V1 prompts"`

## 4) Test Plan

- [ ] After Step 1-2: verify no broken imports in surviving code:
  ```bash
  grep -rn "ModelRouter\|model_router\|token_counter" src/ cli.py || echo "CLEAN"
  ```
- [ ] After Step 3: verify surviving utils all import correctly
- [ ] After Step 4-6: verify no surviving file references deleted prompts:
  ```bash
  grep -rn "identity.md\|safety_policy.md\|tool_guidance.md\|quant_rules.md\|git_rules.md" src/ cli.py || echo "CLEAN"
  ```

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

- (leave blank until implemented)

### Command Results

- (leave blank until implemented)

### Blockers / Deviations

- (leave blank until implemented)

### Follow-ups

- (leave blank until implemented)
