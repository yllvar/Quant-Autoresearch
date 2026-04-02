# Quant Autoresearch

Autonomous quantitative strategy discovery.

## Setup

To set up a new experiment:
1. **Agree on a run tag** with the user (e.g. `apr1`).
   The branch `quant-research/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b quant-research/<tag>` from main.
3. **Read the in-scope files**:
   - `src/core/backtester.py` — fixed evaluation harness. Do NOT modify.
   - `src/strategies/active_strategy.py` — the file you modify.
4. **Verify data exists**: Check `data/cache/` has Parquet files.
   If not, tell the human to run `uv run python cli.py setup_data`.
5. **Initialize files**:
   - Create `results.tsv` with header row.
   - Create `experiments/notes/` directory.
6. **Run baseline** — always run the unmodified strategy first.
7. **Confirm and go**.

## Experimentation

Each experiment:
```bash
uv run python src/core/backtester.py > run.log 2>&1
```

**What you CAN do:**
- Modify `src/strategies/active_strategy.py` — the ENTIRE file is fair game.
  Change class names, add methods, change hyperparameters, redesign signal logic.
  The only requirement: the file must define at least one class with a
  `generate_signals(self, data)` method that returns a Series of signals.

**What you CANNOT do:**
- Modify `src/core/backtester.py`. It is read-only.
- Install new packages. The sandbox only provides `pd` and `np`.
- Use `for` loops. Vectorized Pandas/NumPy only.
- Use `.shift(-N)` (look-ahead bias).

## The goal

Get the highest **SCORE** (Average Walk-Forward OOS Sharpe Ratio).

## Output format

```
---
SCORE: 0.5432
SORTINO: 0.8100
CALMAR: 1.2300
DRAWDOWN: -0.1200
MAX_DD_DAYS: 45
TRADES: 120
P_VALUE: 0.0300
WIN_RATE: 0.5500
PROFIT_FACTOR: 1.8500
AVG_WIN: 0.0120
AVG_LOSS: -0.0080
BASELINE_SHARPE: 0.4500
---
PER_SYMBOL:
  SPY: sharpe=0.62 sortino=0.90 dd=-0.10 pf=2.10 trades=35 wr=0.57
  ...
```

Extract:
```bash
grep "^SCORE:\|^DRAWDOWN:\|^P-VALUE:\|^BASELINE_SHARPE:\|^PROFIT_FACTOR:" run.log
```

## Decision rules

**KEEP if:**
- SCORE > previous best AND
- P_VALUE <= 0.05 AND
- SCORE > BASELINE_SHARPE

**DISCARD if:**
- SCORE <= previous best OR
- P_VALUE > 0.05 (not statistically significant) OR
- SCORE <= BASELINE_SHARPE (can't beat Buy&Hold)

**Simplicity criterion**:
All else being equal, simpler is better.
- Removing code and getting equal or better results -> great outcome.
- A 0.01 Sharpe improvement that adds 20 lines of hacky complexity -> probably not worth it.
- A 0.01 Sharpe improvement from deleting code -> definitely keep.

## Logging results

Log to `results.tsv` (tab-separated, do NOT commit):
```
commit  sharpe  sortino  calmar  drawdown  max_dd_days  trades  win_rate  profit_factor  p_value  baseline_sharpe  status  description
```

## Obsidian experiment notes

After each experiment, write a note to `experiments/notes/<NNN>-<slug>.md`:
- **Hypothesis**: what are you testing and why
- **Changes**: what did you modify
- **Results**: key metrics in a table
- **Per-Symbol**: individual symbol performance
- **Observations**: what did you learn
- **Next Ideas**: what to try next

These notes let the human understand your reasoning when they review the session.

## The experiment loop

LOOP FOREVER:
1. Check git state: current branch/commit
2. Read `results.tsv` for history
3. Propose hypothesis -> modify `src/strategies/active_strategy.py`
4. `git add src/strategies/active_strategy.py && git commit -m "<description>"`
5. `uv run python src/core/backtester.py > run.log 2>&1`
6. `grep "^SCORE:\|^P-VALUE:\|^BASELINE_SHARPE:" run.log`
7. If grep empty -> crash. `tail -n 50 run.log`. Fix or skip.
8. Check hard constraints (p_value, baseline_sharpe)
9. Record in results.tsv
10. Write Obsidian note
11. If KEEP -> keep commit, advance branch
12. If DISCARD -> `git reset --hard HEAD~1`
13. Repeat

**NEVER STOP.** Do NOT ask the human if you should continue.
They might be asleep. Run indefinitely until manually stopped.

**Time awareness**: This session has approximately X hours.
Pace yourself for meaningful experiments, not random changes.

**Stuck?**
- Re-read strategy code for new angles
- Read results.tsv for patterns
- Try combining previous near-misses
- Try more radical architectural changes
- Review your Obsidian notes for forgotten ideas
