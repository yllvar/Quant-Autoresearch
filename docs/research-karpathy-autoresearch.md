# Karpathy autoresearch vs Quant-Autoresearch 詳細對比研究

> 研究日期：2026-04-01
> 來源：https://github.com/karpathy/autoresearch (commit 973e055)
> 基於雙方源碼的逐層分析

---

## 1. 核心理念對比

### Karpathy autoresearch

**「你不改 Python，你改 Markdown。」**

Karpathy 的哲學是極簡。整個專案只有三個檔案，agent 只改一個，人類只改一個。研究者的角色不是寫訓練程式碼，而是編寫 `program.md` — 即「research org code」，定義研究策略本身。

```
人類寫 program.md → Agent 讀取 → 改 train.py → 跑 5 分鐘 → 看結果 → 重複
```

關鍵金句（from program.md）：
> "If you feel like you're getting stuck in some way, you can rewind but you should probably do this very very sparingly (if ever)."
> "NEVER STOP... The loop runs until the human interrupts you, period."

### Quant-Autoresearch

**「人類寫 Constitution，Agent 在安全沙箱中演化策略。」**

我們的專案在相同理念上增加了多層基礎設施 — ArXiv 研究整合、5 層安全防禦、記憶系統、上下文管理。代價是複雜度大幅增加。

```
人類寫 program.md (Constitution) → 6-Phase Loop → 多模型協作 → 改 EDITABLE REGION
→ RestrictedPython 沙箱回測 → Walk-Forward + Monte Carlo → Playbook 存檔/回退 → 重複
```

---

## 2. Agent Loop 對比

### Karpathy：無框架 Loop（靠 LLM agent 自身）

Karpathy **沒有寫任何 agent 框架**。整個實驗 loop 定義在 `program.md` 裡面，由 Claude/Codex 等 agent 自己執行：

```
LOOP FOREVER:
1. 看看 git 狀態
2. 改 train.py（嘗試一個實驗想法）
3. git commit
4. 跑實驗：uv run train.py > run.log 2>&1
5. 讀結果：grep "^val_bpb:" run.log
6. 如果 grep 為空 → 當 crash 處理 → tail -n 50 run.log → 嘗試修復
7. 記錄到 results.tsv（不 commit）
8. 改進 → 保留 git commit / 退步 → git reset 回去
```

這個 loop 的**所有控制邏輯都在 LLM 的 prompt 裡面**。沒有 Python 程式碼管理 state、沒有 doom-loop detection、沒有 context compaction — 完全靠 LLM 自己的推理能力維持 loop。

### Quant-Autoresearch：6-Phase OPENDEV Loop（Python 框架）

我們的 `engine.py` 用 Python 實現了完整的狀態機：

| Phase | 功能 | Karpathy 有沒有 |
|-------|------|----------------|
| Phase 0: Context Mgmt (ACC) | 監控 token 使用率，70%警告、80%遮罩、90%裁剪、99%LLM摘要 | 無（靠 agent 自己管理） |
| Phase 1: Thinking | 用獨立模型（llama-3.1-8b）生成 reasoning trace，不接觸工具 | 無（直接 action） |
| Phase 2: Action Selection | 用主模型（llama-3.3-70b）選工具、生成 JSON tool calls | 無（agent 直接改檔案） |
| Phase 3: Doom-Loop Detection | 指紋比對，同一 action 重複 3+/20 次 → 暫停 | 無 |
| Phase 4: Execution | 5 層安全檢查 → 工具執行 → 結果 >8k 自動遮罩 | 無（agent 直接跑指令） |
| Phase 5: Observation | 評估結果、Playbook 存檔、失敗回退 | 靠 agent 自己判斷 |

**核心差異**：Karpathy 把「如何做研究」完全交給 LLM 的推理能力；我們用 Python 框架把每個步驟都固化了。

---

## 3. 檔案修改範圍對比

### Karpathy：全檔案修改

Agent 可以改 `train.py` 的**全部內容** — 模型架構、optimizer、超參數、訓練迴圈、batch size，全部 fair game。

實際的 `train.py`（約 500 行）包含：
- 完整 GPT 模型定義（`GPTConfig`, `CausalSelfAttention`, `MLP`, `Block`, `GPT`）
- MuonAdamW optimizer（`polar_express` 正交化、NorMuon variance reduction）
- 超參數區塊：`DEPTH=8`, `TOTAL_BATCH_SIZE=2**19`, `WINDOW_PATTERN="SSSL"`, 各種 LR
- 訓練迴圈（固定 TIME_BUDGET=300s）

Agent 可以自由改變模型深度、寬度、注意力機制、optimizer 策略、學習率 schedule。

### Quant-Autoresearch：EDITABLE REGION 限制

Agent 只能改 `active_strategy.py` 中 `# --- EDITABLE REGION BREAK ---` 到 `# --- EDITABLE REGION END ---` 之間的程式碼（目前約 25 行）。

```python
class TradingStrategy:
    def __init__(self, fast_ma=20, slow_ma=50):  # 超參數（agent 可改）
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma

    def generate_signals(self, data):
        # --- EDITABLE REGION BREAK ---
        # ← agent 只能改這裡面（約 25 行）
        # --- EDITABLE REGION END ---
        return signals
```

對比：
- Karpathy：agent 可以改**整個實驗**的架構
- 我們：agent 只能改**訊號生成邏輯**，不能改回測框架、風險管理、成本模型

---

## 4. 評估機制對比

### Karpathy：固定時間 + 單一指標

```python
# prepare.py (不可修改)
TIME_BUDGET = 300  # 固定 5 分鐘
EVAL_TOKENS = 40 * 524288  # 固定評估 token 數
MAX_SEQ_LEN = 2048  # 固定上下文長度

def evaluate_bpb(model, tokenizer, batch_size):
    """唯一指標：val_bpb（越低越好）"""
    # ... 在固定 validation shard (shard_06542) 上評估
    return total_nats / (math.log(2) * total_bytes)
```

- 每次實驗**完全可比**：同樣的資料、同樣的時間、同樣的指標
- 指標架構無關：改 vocab_size 不影響 val_bpb 的可比性
- Agent 只看一個數字：`val_bpb: 0.997900`

### Quant-Autoresearch：Walk-Forward + Monte Carlo + 多指標

```python
# backtester.py
def walk_forward_validation():
    # 5 個滾動窗口，每個 70/30 train/test
    for i in range(5):
        train_end = int((i + 1) * window_size * 0.7)
        test_start = train_end
        test_end = (i + 1) * window_size
        sharpe, dd, trades, p_val = run_backtest(...)

    # 輸出 4 個指標
    print(f"SCORE: {avg_oos_sharpe}")
    print(f"DRAWDOWN: {avg_oos_dd}")
    print(f"TRADES: {total_oos_trades}")
    print(f"P-VALUE: {avg_oos_pval}")
```

| 指標 | Karpathy | Quant-Autoresearch |
|------|----------|-------------------|
| 主指標 | `val_bpb`（單一） | `SCORE`（平均 OOS Sharpe） |
| 次要指標 | 無 | `DRAWDOWN`, `TRADES`, `P-VALUE` |
| 統計檢定 | 無（靠固定時間保證可比性） | Monte Carlo permutation test（1000 次重排） |
| 防過擬合 | 固定時間（避免過度調參） | Walk-forward 5 窗口 + 強制 1-bar lag |
| 成本模型 | 無 | `BASE_COST=0.0005` + volatility slippage |
| 決策邏輯 | val_bpb 更低 → KEEP，否則 DISCARD | score > best_score → KEEP + Playbook，否則 REVERT |

**Karpathy 的優勢**：所有實驗結果嚴格可比。5 分鐘就是 5 分鐘，val_bpb 就是 val_bpb。
**我們的優勢**：金融回測的現實性更強（成本、滑價、統計顯著性、walk-forward）。

---

## 5. 安全機制對比

### Karpathy：零安全層

```markdown
# program.md
"What you CAN do: Modify train.py — everything is fair game"
"What you CANNOT do: Modify prepare.py. Install new packages."
```

唯一限制是 prompt 指令。Agent 理論上可以：
- 在 `train.py` 裡加 `import os; os.system("rm -rf /")`
- 存取檔案系統、網路
- 任意執行 Python

**為什麼 OK？** 因為 agent 跑在用戶自己的機器上，最壞結果是浪費 GPU 時間。Karpathy 的假設是 Claude/Codex 本身足夠安全。

### Quant-Autoresearch：5 層 defense-in-depth

```
Layer 1: Prompt Guardrails        → program.md 定義規則
Layer 2: Schema Gating            → 工具按 subagent 類型限制
Layer 3: Runtime Approval         → SEMI-AUTO 模式
Layer 4: Tool Validation          → 參數清理 + AST 分析
Layer 5: Lifecycle Hooks          → 執行前後安全檢查
```

加上 `backtester.py` 的安全措施：

```python
FORBIDDEN_BUILTINS = {'exec', 'eval', 'open', 'getattr', 'setattr', 'delattr'}
FORBIDDEN_MODULES = {'socket', 'requests', 'urllib', 'os', 'sys', 'shutil', 'subprocess'}

# RestrictedPython 沙箱
safe_globals = {
    '__builtins__': safe_builtins,  # 只有安全 builtins
    'pd': pd, 'np': np,            # 只提供 pandas 和 numpy
}

# AST 分析阻止 look-ahead bias
if node.func.attr == 'shift' and is_negative_val(arg):
    return False, "Look-ahead bias detected (.shift(-N))"
```

**為什麼必要？** 因為交易策略如果含惡意程式碼（網路請求、檔案存取），可能造成金融損失或資料外洩。

---

## 6. 結果記錄對比

### Karpathy：results.tsv + git branch

```tsv
commit  val_bpb   memory_gb  status    description
a1b2c3d 0.997900  44.0       keep      baseline
b2c3d4e 0.993200  44.2       keep      increase LR to 0.04
c3d4e5f 1.005000  44.0       discard   switch to GeLU activation
d4e5f6g 0.000000  0.0        crash     double model width (OOM)
```

- 每個實驗 = 一個 git commit → 完整的 diff 追蹤
- `keep` → 保留 commit，`discard` → `git reset` 回去
- Agent 自己維護 git 歷史，不 commit results.tsv

### Quant-Autoresearch：experiment_log.json + results.tsv + Playbook (SQLite)

```python
# engine.py
self.experiment_log = "experiments/results/experiment_log.json"
self.playbook = Playbook(db_path="experiments/database/playbook.db")

# 成功 → 存入 Playbook
self.playbook.store_pattern(
    hypothesis="Evolved strategy",
    strategy_code=self.get_current_strategy(),
    performance_metrics=actual_res
)

# 失敗 → 檔案回退
with open(self.strategy_file, "w") as f:
    f.write(self.current_iteration_baseline)
```

| 功能 | Karpathy | Quant-Autoresearch |
|------|----------|-------------------|
| Diff 追蹤 | git commits（每個實驗一個） | 檔案回退（save baseline → restore on fail） |
| 歷史搜尋 | git log | SQLite Playbook（TF-IDF 相似度） |
| 跨實驗記憶 | 無（每次只看最近幾個 commit） | Playbook 可搜尋歷史成功模式 |
| 結果格式 | TSV（簡單可讀） | JSON + TSV + SQLite |

---

## 7. LLM 使用對比

### Karpathy：單一 Agent（Claude/Codex）

Karpathy 不選模型 — 直接用 Claude 或 Codex（或其他 agent），把 `program.md` 丟給它。agent 自己決定如何推理、如何修改程式碼、如何判斷結果。

沒有 model routing、沒有 cost tracking、沒有 token 管理。

### Quant-Autoresearch：多模型路由

```python
# models/router.py — 三種用途用不同模型
models = {
    "thinking":      {"primary": "llama-3.1-8b-instant"},     # Phase 1 推理
    "reasoning":     {"primary": "llama-3.3-70b-versatile"},  # Phase 2 決策
    "summarization": {"primary": "llama-3.1-8b-instant"},     # ACC 摘要
}

# 多 provider 路由 + fallback
providers = {
    "groq":     Groq(api_key=...),
    "moonshot": OpenAI(api_key=..., base_url="https://api.moonshot.cn/v1"),
}
```

加上 cost tracking、retry with backoff、token counting。

**差異**：Karpathy 依賴 frontier model 的推理能力；我們把推理拆分給多個小模型以降低成本。

---

## 8. program.md（Constitution）逐行對比

### Karpathy program.md（約 80 行，關鍵內容）

```markdown
## Experimentation
- 每次跑 5 分鐘（固定）
- 只改 train.py
- 不能改 prepare.py
- 不能加 dependency
- 目標：最低 val_bpb
- Simplicity criterion：簡單方案優先，0.001 改進 + 20 行 hacky code → 不值得

## Logging results
- TSV 格式：commit / val_bpb / memory_gb / status / description
- status: keep, discard, crash

## The experiment loop
- LOOP FOREVER（不停，除非人類中斷）
- 改進 → keep commit / 退步 → git reset
- Timeout: 10 分鐘（正常 5 分鐘 + overhead）
- NEVER STOP, NEVER ask human
```

### Quant-Autoresearch program.md（約 26 行）

```markdown
## Your Mandate
Maximize the Average Walk-Forward Out-of-Sample (OOS) Sharpe Ratio.

## Available Features
Open, High, Low, Close, Volume, returns, volatility, atr

## The Multi-Modal Workflow
1. Hypothesis → 2. Research (ArXiv) → 3. Implementation → 4. Evaluation

## Key Rules
- Vectorized Logic Only (Pandas/NumPy, no for loops)
- Only pd and np available
- No look-ahead bias
- No exec/eval
- No Martingale, max exposure 1.0

GOAL: OOS Sharpe > 1.5
```

**對比**：
- Karpathy 的 program.md 更像**操作手冊**（詳細說明每個步驟怎麼做）
- 我們的 program.md 更像**規則清單**（定義約束和目標）
- Karpathy 有明確的 "simplicity criterion"（簡單方案優先），我們沒有
- Karpathy 有明確的 "NEVER STOP" 指令，我們的 loop 由 `max_iterations` 控制

---

## 9. 資料流對比

### Karpathy

```
HuggingFace (climbmix-400b-shuffle)
  → prepare.py 下載 parquet shards → ~/.cache/autoresearch/
  → 訓練 BPE tokenizer (vocab_size=8192)
  → train.py: dataloader (BOS-aligned, best-fit packing, 100% utilization)
  → evaluate_bpb: 固定 validation shard (shard_06542)
```

一次性準備，之後每次實驗用同樣的資料。資料不可變。

### Quant-Autoresearch

```
yfinance (equities: SPY, QQQ, IWM) + CCXT/Binance (crypto: BTC, ETH)
  → DataConnector → data/cache/ (Parquet)
  → preprocessor.py: 下載預設 dataset
  → backtester.py: load_data() → 讀所有 cached 資料
  → walk_forward_validation: 5 個滾動窗口
```

資料可以透過 `cli.py fetch` 更新。不同 symbol 可能有不同長度（取最短的）。

---

## 10. 可改進方向（基於對比）

### 10.1 從 Karpathy 借鑑

| 改進 | 說明 |
|------|------|
| **Simplicity criterion** | 在 program.md 加入「簡單方案優先」規則。0.001 Sharpe 改進 + 20 行複雜程式碼不值得。刪除程式碼得到相同結果是最佳結果。 |
| **Git-based 追蹤** | 每個實驗做 git commit 而不是只存 baseline string。這樣有完整 diff 歷史，可回溯任意版本。 |
| **NEVER STOP** | 考慮移除 `max_iterations` 硬限制，改為無限 loop 直到人類中斷或達到目標。 |
| **固定評估預算** | 確保每次回測用完全相同的資料窗口和條件，避免「偷偷」改了評估條件。 |
| **Crash 自動處理** | Karpathy 的 program.md 詳細定義了 crash 處理流程（修 typos → retry，fundamental → skip）。我們可以加入類似邏輯。 |
| **results.tsv 格式** | Karpathy 的 TSV 格式更簡潔且可讀（commit hash + 指標 + status + 描述）。 |

### 10.2 我們的優勢（應保持）

| 優勢 | 說明 |
|------|------|
| **Walk-Forward 驗證** | 比 Karpathy 的「跑 5 分鐘看 loss」更抗過擬合 |
| **Monte Carlo 統計檢定** | p-value 提供策略顯著性的量化判斷 |
| **沙箱執行** | RestrictedPython + AST 分析，安全性遠超 prompt-only 限制 |
| **記憶系統** | Playbook 可以跨實驗搜尋和重用成功策略片段 |
| **ArXiv 研究** | 策略改進有學術基礎，不是純粹 trial-and-error |
| **成本模型** | 交易成本 + volatility slippage 讓回測更接近現實 |

### 10.3 我們的潛在問題（需關注）

| 問題 | 說明 |
|------|------|
| **複雜度成本** | 6 個 Phase + 5 層安全 + 多模型路由 = 更多 failure point。Karpathy 的極簡設計意味着更少的 bug。 |
| **EDITABLE REGION 太小** | 只有約 25 行可改。Karpathy agent 可以改整個模型架構。我們的 agent 可能很快在這個小空間裡耗盡想法。 |
| **多指標決策模糊** | SCORE, DRAWDOWN, TRADES, P-VALUE — 如果 Sharpe 改進但 Drawdown 惡化，該不該保留？Karpathy 只看一個數字，決策清晰。 |
| **小模型能力** | 用 llama-3.1-8b 做 thinking、llama-3.3-70b 做決策。Karpathy 用 Claude Opus/Sonnet — 推理能力差距大。 |
| **無 git 歷史** | 我們只存 baseline string 做 revert，沒有完整的 commit 歷史。難以回溯到 3 個版本前的好策略。 |

---

## 11. 架構哲學總結

```
Karpathy autoresearch:
  "Trust the model. Give it freedom. Keep everything else fixed."
  → 極簡框架 + 強模型 = 靠 LLM 推理能力驅動研究
  → 風險：模型能力不夠時 loop 會卡住
  → 優勢：簡單、可維護、容易理解

Quant-Autoresearch:
  "Don't trust the model. Constrain it. Build safety nets."
  → 完整框架 + 多模型 = 靠工程基礎設施降低對模型的依賴
  → 風險：框架本身的 bug 可能比模型的錯誤更難發現
  → 優勢：安全、可追溯、有學術基礎
```

**共同核心**：`program.md` 作為人機介面 — 人類定義「什麼是好」，AI 自主探索「如何達到好」。
