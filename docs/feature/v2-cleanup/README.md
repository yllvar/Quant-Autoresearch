# V2 Cleanup — 移除舊架構

## Overview

Phase 2 of the V2 upgrade. Removes all V1 components superseded by the program.md-driven architecture where Claude Code/Codex directly controls the agent loop.

## Branch

`feature/v2-cleanup`

## Issues

| Issue | Scope | Status |
| --- | --- | --- |
| [#1](https://github.com/ricoyudog/Quant-Autoresearch/issues/1) | Umbrella: Phase 2 總覽 | pending |
| [#2](https://github.com/ricoyudog/Quant-Autoresearch/issues/2) | 2.1: 移除 engine.py 和 context/ | done |
| [#3](https://github.com/ricoyudog/Quant-Autoresearch/issues/3) | 2.2: 移除 safety guard 和 tool registry | done |
| [#4](https://github.com/ricoyudog/Quant-Autoresearch/issues/4) | 2.3: 移除 model router 和 token counter | done |
| [#5](https://github.com/ricoyudog/Quant-Autoresearch/issues/5) | 2.4: 清理 prompts 目錄 | done |
| [#6](https://github.com/ricoyudog/Quant-Autoresearch/issues/6) | 2.5: 移除舊架構相關測試 | done |
| [#7](https://github.com/ricoyudog/Quant-Autoresearch/issues/7) | 2.6: 更新 pyproject.toml 依賴 | done |

## Execution Order

```
#2 → #3 → #4 → #5 → #6 → #7
```

Each sub-issue depends on the previous one. #7 is the final verification gate.

## Docs

- [v2-cleanup-development-plan.md](./v2-cleanup-development-plan.md) — Main development plan with task detail
- [v2-cleanup-test-plan.md](./v2-cleanup-test-plan.md) — Verification and test plan

## Governing Specs

- [upgrade-plan-v2.md](../../upgrade-plan-v2.md) — Complete V2 upgrade design
- [CLAUDE.md](../../../CLAUDE.md) — V1 architecture (will be updated in Phase 4)
